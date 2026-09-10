import io
import json
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIRequestFactory, force_authenticate

from apps.accounts.models import Permission, Role, RolePermission, User
from apps.ai_analysis.models import (
    AIAnalysis,
    AIAnalysisResult,
    AIAnalysisStatusHistory,
    AIModel,
    AIModelConfigVersion,
    ModelVersion,
)
from apps.ai_analysis.tasks.mock_inference import run_mock_analysis_inference
from apps.ai_analysis.api.inference import AnalysisCollectionView
from apps.imaging.models import ImagingStudy


@override_settings(AI_INFERENCE_DEVELOPMENT_ENABLED=True)
class DevelopmentInferenceFlowTests(TestCase):
    def test_real_collection_keeps_generated_get_worklist(self):
        self.assertTrue(callable(getattr(AnalysisCollectionView, "get", None)))

    def test_clinician_can_view_ai_worklist_without_admin_permission(self):
        request = APIRequestFactory().get("/api/v1/ai-analyses")
        force_authenticate(request, user=self.user)

        response = AnalysisCollectionView.as_view()(request)

        self.assertEqual(response.status_code, 200)

    def test_system_admin_requires_ai_job_view_permission(self):
        admin_role = Role.objects.create(code="SYSTEM_ADMIN", name="Synthetic Admin")
        admin = User.objects.create_user(
            login_id="synthetic-ai-admin",
            password="test-only-password",
            name="Synthetic AI Admin",
            role=admin_role,
        )
        request = APIRequestFactory().get("/api/v1/ai-analyses")
        force_authenticate(request, user=admin)

        denied = AnalysisCollectionView.as_view()(request)
        self.assertEqual(denied.status_code, 403)

        permission = Permission.objects.create(
            code="ai.job.view",
            name="View AI jobs",
            domain="AI",
        )
        RolePermission.objects.create(role=admin_role, permission=permission)

        request = APIRequestFactory().get("/api/v1/ai-analyses")
        force_authenticate(request, user=admin)
        allowed = AnalysisCollectionView.as_view()(request)
        self.assertEqual(allowed.status_code, 200)

    def setUp(self):
        now = timezone.now()
        role = Role.objects.create(code="RADIOLOGY", name="Synthetic Radiology")
        self.user = User.objects.create_user(
            login_id="synthetic-inference-user",
            password="test-only-password",
            name="Synthetic User",
            role=role,
        )
        self.study = ImagingStudy.objects.create(
            patient=None,
            imaging_order=None,
            study_instance_uid="1.2.826.0.1.3680043.10.999.1",
            accession_number="SYNTHETIC-ONLY",
            orthanc_study=None,
            study_datetime=now,
            modalities=["CT"],
            study_description="Synthetic inference contract test",
            series_count=0,
            instance_count=0,
            status="AVAILABLE",
            last_synced_at=now,
            created_at=now,
            updated_at=now,
        )
        model = AIModel.objects.create(
            code="synthetic-mock-model",
            display_name="Synthetic Mock Model",
            task_type="MOCK",
            disease_scope="NONE",
            supported_modalities=["CT"],
            description="Synthetic test model without weights",
            is_enabled=True,
            created_at=now,
            updated_at=now,
        )
        self.version = ModelVersion.objects.create(
            model=model,
            version="MOCK-1",
            mlflow_registered_model_name="MOCK",
            mlflow_model_version="0",
            mlflow_run="MOCK",
            artifact_uri="MOCK",
            container_image_digest="MOCK",
            code_commit_sha="MOCK",
            input_contract={},
            output_contract={"schema_version": "MOCK"},
            preprocessing_config={},
            validation_status="APPROVED",
            is_active=True,
            performance_metrics={"accuracy_simulated": False},
            created_at=now,
            updated_at=now,
        )
        self.config = AIModelConfigVersion.objects.create(
            model_version=self.version,
            config_version="MOCK-1",
            threshold_config={},
            is_active=True,
            created_at=now,
        )

    def request_body(self, outcome="success"):
        return {
            "study_id": str(self.study.id),
            "model_version_id": str(self.version.id),
            "model_config_version_id": str(self.config.id),
            "requested_by_id": str(self.user.id),
            "analysis_type": "MOCK_INFERENCE",
            "priority": "NORMAL",
            "outcome": outcome,
        }

    def create_analysis(self, outcome="success"):
        with patch.object(run_mock_analysis_inference, "apply_async") as publish:
            response = self.client.post(
                "/api/v1/dev/ai-analyses",
                self.request_body(outcome),
                content_type="application/json",
            )
        self.assertEqual(response.status_code, 202)
        analysis = AIAnalysis.objects.get(pk=response.json()["analysis_id"])
        publish.assert_called_once_with(
            args=[str(analysis.id), outcome],
            retry=False,
        )
        return analysis

    def test_success_is_stored_in_existing_tables_and_readable(self):
        analysis = self.create_analysis()
        mock_response = {
            "analysis_id": str(analysis.id),
            "mode": "MOCK",
            "is_mock": True,
            "accuracy_simulated": False,
            "status": "SUCCEEDED",
            "result": {"message": "Synthetic pipeline verification only"},
        }
        with patch(
            "apps.ai_analysis.tasks.mock_inference.urlopen",
            return_value=io.BytesIO(json.dumps(mock_response).encode()),
        ):
            run_mock_analysis_inference(str(analysis.id), "success")

        response = self.client.get(
            f"/api/v1/dev/ai-analyses/{analysis.id}"
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "COMPLETED")
        self.assertEqual(
            [row["status"] for row in data["history"]],
            ["QUEUED", "PROCESSING", "COMPLETED"],
        )
        self.assertTrue(data["result"]["is_mock"])
        result = AIAnalysisResult.objects.get(analysis=analysis)
        self.assertEqual(result.severity, "MOCK")
        self.assertIsNone(result.is_positive)

    def test_failure_is_stored_and_readable(self):
        analysis = self.create_analysis("failure")
        from urllib.error import HTTPError
        error = HTTPError("mock", 500, "failure", {}, None)
        with patch(
            "apps.ai_analysis.tasks.mock_inference.urlopen",
            side_effect=error,
        ):
            run_mock_analysis_inference(str(analysis.id), "failure")
        response = self.client.get(
            f"/api/v1/dev/ai-analyses/{analysis.id}"
        )
        data = response.json()
        self.assertEqual(data["status"], "FAILED")
        self.assertEqual(data["failure_code"], "MOCK_INFERENCE_FAILED")
        self.assertFalse(AIAnalysisResult.objects.filter(analysis=analysis).exists())

    def test_duplicate_delivery_does_not_run_twice(self):
        analysis = self.create_analysis()
        with patch("apps.ai_analysis.tasks.mock_inference.urlopen") as call:
            AIAnalysis.objects.filter(pk=analysis.id).update(status="COMPLETED")
            run_mock_analysis_inference(str(analysis.id), "success")
        call.assert_not_called()
        self.assertEqual(
            AIAnalysisStatusHistory.objects.filter(analysis=analysis).count(),
            1,
        )

    @override_settings(AI_INFERENCE_DEVELOPMENT_ENABLED=False)
    def test_endpoint_is_hidden_when_disabled(self):
        response = self.client.post(
            "/api/v1/dev/ai-analyses",
            self.request_body(),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 404)

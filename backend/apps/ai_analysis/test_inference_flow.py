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
from apps.ai_analysis.api.inference import AIResultReviewCollectionView, AnalysisCollectionView, AnalysisResultView
from apps.imaging.models import ImagingStudy
from apps.patients.models import Patient, PatientCareAssignment


@override_settings(AI_INFERENCE_DEVELOPMENT_ENABLED=True)
class DevelopmentInferenceFlowTests(TestCase):
    def test_real_collection_keeps_generated_get_worklist(self):
        self.assertTrue(callable(getattr(AnalysisCollectionView, "get", None)))

    def test_clinician_can_view_ai_worklist_without_admin_permission(self):
        request = APIRequestFactory().get("/api/v1/ai-analyses")
        force_authenticate(request, user=self.user)

        response = AnalysisCollectionView.as_view()(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 0)
        self.assertEqual(response.data["results"], [])

    def test_system_admin_requires_ai_job_view_permission(self):
        admin_role = Role.objects.get(code="SYSTEM_ADMIN")
        admin = User.objects.create_user(
            login_id="synthetic-ai-admin",
            password="test-only-password",
            name="Synthetic AI Admin",
            role=admin_role,
        )

        permission = Permission.objects.get(code="ai.job.view")
        RolePermission.objects.filter(
            role=admin_role,
            permission=permission,
        ).delete()

        request = APIRequestFactory().get("/api/v1/ai-analyses")
        force_authenticate(request, user=admin)

        denied = AnalysisCollectionView.as_view()(request)
        self.assertEqual(denied.status_code, 403)

        RolePermission.objects.create(
            role=admin_role,
            permission=permission,
        )

        request = APIRequestFactory().get("/api/v1/ai-analyses")
        force_authenticate(request, user=admin)
        allowed = AnalysisCollectionView.as_view()(request)
        self.assertEqual(allowed.status_code, 200)

    def setUp(self):
        now = timezone.now()
        role = Role.objects.get(code="RADIOLOGY")
        self.user = User.objects.create_user(
            login_id="synthetic-inference-user",
            password="test-only-password",
            name="Synthetic User",
            role=role,
        )
        self.patient = Patient.objects.create(
            patient_no="SYNTHETIC-AI-PATIENT",
            name="Synthetic AI Patient",
            created_by=self.user,
        )
        PatientCareAssignment.objects.create(
            patient=self.patient,
            clinician=self.user,
            role=PatientCareAssignment.AssignmentRole.PRIMARY,
            source=PatientCareAssignment.Source.AI_ANALYSIS,
        )
        self.study = ImagingStudy.objects.create(
            patient=self.patient,
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

        result_request = APIRequestFactory().get(
            f"/api/v1/ai-analyses/{analysis.id}/result"
        )
        force_authenticate(result_request, user=self.user)
        result_response = AnalysisResultView.as_view()(
            result_request, analysis_id=analysis.id
        )
        self.assertEqual(result_response.status_code, 200)
        result_data = result_response.data
        self.assertEqual(result_data["analysis_id"], str(analysis.id))
        self.assertEqual(result_data["result_id"], str(result.id))
        self.assertEqual(result_data["severity"], "MOCK")
        self.assertEqual(result_data["structured_findings"]["is_mock"], True)
        self.assertEqual(result_data["artifacts"], [])

        review_request = APIRequestFactory().post(
            f"/api/v1/ai-results/{result.id}/reviews",
            {"decision": "ACCEPT", "comment": "Synthetic clinical review"},
            format="json",
        )
        force_authenticate(review_request, user=self.user)
        review_response = AIResultReviewCollectionView.as_view()(review_request, result_id=result.id)
        self.assertEqual(review_response.status_code, 201)
        self.assertEqual(review_response.data["decision"], "ACCEPT")

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

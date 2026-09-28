from django.utils import timezone
from rest_framework.test import APITestCase
from unittest.mock import patch

from apps.accounts.models import Role, RoleCode, User
from apps.ai_analysis.models import AIModel, AIModelConfigVersion, AIRoutingConfigVersion, ModelVersion
from apps.ai_analysis.services.model_validation import ModelValidationResult, ValidationCheck


class MLModelAdminAPITests(APITestCase):
    def setUp(self):
        role = Role.objects.get(code=RoleCode.SYSTEM_ADMIN)
        self.admin = User.objects.create_user(
            login_id="ml-console-admin",
            password="test-password",
            name="ML console admin",
            role=role,
        )
        now = timezone.now()
        self.model = AIModel.objects.create(
            code="ML-CONSOLE-TEST",
            display_name="ML Console Test Model",
            task_type="SEGMENTATION",
            disease_scope="ANEURYSM",
            supported_modalities=["MRA"],
            description="Test model",
            is_enabled=True,
            created_at=now,
            updated_at=now,
        )
        self.validated = self._version("1.0.0", "VALIDATED", now)
        self.approved = self._version("0.9.0", "APPROVED", now)
        self.draft = self._version("1.1.0", "DRAFT", now)
        for version in (self.validated, self.approved):
            AIModelConfigVersion.objects.create(
                model_version=version,
                config_version="1",
                threshold_config={},
                is_active=True,
                created_at=now,
            )
        self.previous_routing = AIRoutingConfigVersion.objects.create(
            version="mra-old",
            modality="MRA",
            analysis_type="ANEURYSM",
            target_model_version=self.approved,
            is_active=True,
            created_at=now,
        )
        self.client.force_authenticate(self.admin)

    def _version(self, version, validation_status, now):
        return ModelVersion.objects.create(
            model=self.model,
            version=version,
            mlflow_registered_model_name="test-model",
            mlflow_model_version=version,
            mlflow_run="test-run",
            artifact_uri="gs://test-bucket/manifest.json",
            container_image_digest="sha256:test",
            code_commit_sha="test",
            input_contract={},
            output_contract={},
            preprocessing_config={},
            validation_status=validation_status,
            is_active=False,
            performance_metrics={"dice": 0.9},
            created_at=now,
            updated_at=now,
        )

    def test_overview_and_approval(self):
        response = self.client.get("/api/v1/admin/ml/overview")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["versions"]), 3)

        response = self.client.post(
            f"/api/v1/admin/ml/model-versions/{self.validated.id}/approve",
            {"reason": "technical validation completed", "confirmation": True},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["validation_status"], "APPROVED")

    @patch("apps.ai_analysis.api.model_admin.MLModelVersionValidationService")
    def test_validation_creates_active_config_and_keeps_version_inactive(self, service_class):
        service_class.return_value.validate.return_value = ModelValidationResult(
            checks=[ValidationCheck("READY", "Readiness", True, "ready")],
            threshold_config={"threshold": 0.45},
            input_contract={"schema_version": "1.0", "modality": "MRA"},
            output_contract={"schema_version": "1.0", "outputs": ["mask"]},
            preprocessing_config={"spacing": "1,1,1"},
        )

        response = self.client.post(
            f"/api/v1/admin/ml/model-versions/{self.draft.id}/validate",
            {"reason": "artifact and metrics verified", "confirmation": True},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.draft.refresh_from_db()
        self.assertEqual(self.draft.validation_status, "VALIDATED")
        self.assertFalse(self.draft.is_active)
        config = AIModelConfigVersion.objects.get(model_version=self.draft, is_active=True)
        self.assertEqual(config.threshold_config, {"threshold": 0.45})

    @patch("apps.ai_analysis.api.model_admin.MLModelVersionValidationService")
    def test_failed_validation_keeps_draft_and_does_not_create_config(self, service_class):
        service_class.return_value.validate.return_value = ModelValidationResult(
            checks=[ValidationCheck("METRICS", "Metrics", False, "missing")],
        )

        response = self.client.post(
            f"/api/v1/admin/ml/model-versions/{self.draft.id}/validate",
            {"reason": "validate candidate", "confirmation": True},
            format="json",
        )

        self.assertEqual(response.status_code, 422)
        self.draft.refresh_from_db()
        self.assertEqual(self.draft.validation_status, "DRAFT")
        self.assertFalse(AIModelConfigVersion.objects.filter(model_version=self.draft).exists())

    def test_routing_activation_switches_the_active_route(self):
        routing = AIRoutingConfigVersion.objects.create(
            version="mra-new",
            modality="MRA",
            analysis_type="ANEURYSM",
            target_model_version=self.approved,
            is_active=False,
            created_at=timezone.now(),
        )

        response = self.client.post(
            f"/api/v1/admin/ml/routing-configs/{routing.id}/activate",
            {"reason": "rollback test", "confirmation": True},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["is_active"])
        self.previous_routing.refresh_from_db()
        self.approved.refresh_from_db()
        self.assertFalse(self.previous_routing.is_active)
        self.assertTrue(self.approved.is_active)

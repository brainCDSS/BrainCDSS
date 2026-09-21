from django.utils import timezone
from rest_framework.test import APITestCase

from apps.accounts.models import Role, RoleCode, User
from apps.ai_analysis.models import AIModel, AIModelConfigVersion, AIRoutingConfigVersion, ModelVersion


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
        self.assertEqual(len(response.data["versions"]), 2)

        response = self.client.post(
            f"/api/v1/admin/ml/model-versions/{self.validated.id}/approve",
            {"reason": "technical validation completed", "confirmation": True},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["validation_status"], "APPROVED")

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

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase
from django.utils import timezone as django_timezone
from rest_framework.test import APITestCase

from apps.accounts.models import Role, RoleCode, User
from apps.ai_analysis.models import AIModel, AIRoutingConfigVersion, ModelVersion
from apps.ai_analysis.services.mlflow_registry import (
    MLflowRegistryClient,
    MLflowRegistryError,
    RegistryModelVersion,
)


class MLflowRegistryClientTests(SimpleTestCase):
    @patch("apps.ai_analysis.services.mlflow_registry.id_token.fetch_id_token", return_value="short-lived-token")
    @patch("apps.ai_analysis.services.mlflow_registry.MlflowClient")
    def test_uses_fresh_cloud_run_token_for_read_only_client(self, client_class, fetch_token):
        client = client_class.return_value
        registered_model = MagicMock()
        registered_model.name = "aneurysm-model"
        client.search_registered_models.return_value = [registered_model]
        client.search_model_versions.return_value = [MagicMock(version="7", run_id="run-7", source="gs://models/7", creation_timestamp=1_700_000_000_000, last_updated_timestamp=1_700_000_100_000, tags={})]
        client.get_run.return_value = MagicMock(data=MagicMock(metrics={"dice": 0.91}, params={"seed": "7"}, tags={}), info=MagicMock(artifact_uri="gs://runs/7"))

        with patch.dict("os.environ", {"MLFLOW_TRACKING_URI": "https://mlflow.example", "MLFLOW_CLOUD_RUN_AUDIENCE": "https://mlflow.example"}, clear=True):
            records = MLflowRegistryClient().list_model_versions()

        self.assertEqual(records[0].model_version, "7")
        fetch_token.assert_called_once()
        client_class.assert_called_once_with(tracking_uri="https://mlflow.example")
        client.search_registered_models.assert_called_once_with(max_results=1_000, page_token=None)


class MLflowSyncAPITests(APITestCase):
    def setUp(self):
        role = Role.objects.get(code=RoleCode.SYSTEM_ADMIN)
        self.admin = User.objects.create_user(login_id="mlflow-sync-admin", password="test-password", name="MLflow sync admin", role=role)
        now = django_timezone.now()
        self.model = AIModel.objects.create(code="ANEURYSM-MLFLOW", display_name="Aneurysm Registry Model", task_type="SEGMENTATION", disease_scope="ANEURYSM", supported_modalities=["MRA"], description="Test model", is_enabled=True, created_at=now, updated_at=now)
        self.client.force_authenticate(self.admin)

    def _record(self, version="5", *, dice=0.91):
        return RegistryModelVersion(registered_model_name="ANEURYSM-MLFLOW", model_version=version, run_id=f"run-{version}", artifact_uri=f"gs://models/{version}", created_at=datetime(2026, 1, 1, tzinfo=timezone.utc), updated_at=datetime(2026, 1, 2, tzinfo=timezone.utc), metrics={"dice": dice}, params={"seed": "7"}, tags={"model_version": {"code_commit_sha": "commit-5"}, "run": {"stage": "candidate"}})

    def _sync(self, records):
        with patch("apps.ai_analysis.api.model_admin.MLflowModelVersionSyncService") as service_class:
            from apps.ai_analysis.services.mlflow_sync import MLflowModelVersionSyncService
            registry = MagicMock()
            registry.list_model_versions.return_value = records
            service_class.return_value.sync.side_effect = MLflowModelVersionSyncService(registry).sync
            return self.client.post("/api/v1/admin/ml/mlflow/sync", {}, format="json")

    def test_sync_creates_draft_version_and_is_idempotent(self):
        record = self._record()
        first = self._sync([record])
        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.data["created"], 1)
        version = ModelVersion.objects.get(mlflow_registered_model_name=record.registered_model_name, mlflow_model_version=record.model_version)
        self.assertEqual(version.validation_status, "DRAFT")
        self.assertFalse(version.is_active)
        self.assertEqual(version.performance_metrics["dice"], 0.91)

        second = self._sync([record])
        self.assertEqual(second.status_code, 200)
        self.assertEqual(second.data["created"], 0)
        self.assertEqual(second.data["skipped"], 1)
        self.assertEqual(ModelVersion.objects.filter(mlflow_registered_model_name=record.registered_model_name, mlflow_model_version="5").count(), 1)

    def test_sync_updates_metadata_without_changing_approval_or_routing(self):
        existing = ModelVersion.objects.create(model=self.model, version="5", mlflow_registered_model_name="ANEURYSM-MLFLOW", mlflow_model_version="5", mlflow_run="old-run", artifact_uri="gs://old", container_image_digest="", code_commit_sha="", input_contract={}, output_contract={}, preprocessing_config={}, validation_status="APPROVED", is_active=True, performance_metrics={"dice": 0.1}, created_at=django_timezone.now(), updated_at=django_timezone.now())
        routing = AIRoutingConfigVersion.objects.create(version="keep-active-routing", modality="MRA", analysis_type="ANEURYSM", target_model_version=existing, is_active=True, created_at=django_timezone.now())

        response = self._sync([self._record(dice=0.96)])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["updated"], 1)
        existing.refresh_from_db()
        routing.refresh_from_db()
        self.assertEqual(existing.validation_status, "APPROVED")
        self.assertTrue(existing.is_active)
        self.assertTrue(routing.is_active)
        self.assertEqual(existing.performance_metrics["dice"], 0.96)

    def test_mlflow_failure_does_not_change_database(self):
        with patch("apps.ai_analysis.api.model_admin.MLflowModelVersionSyncService") as service_class:
            service_class.return_value.sync.side_effect = MLflowRegistryError("unavailable")
            response = self.client.post("/api/v1/admin/ml/mlflow/sync", {}, format="json")

        self.assertEqual(response.status_code, 503)
        self.assertEqual(ModelVersion.objects.count(), 0)

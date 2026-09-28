import json
from types import SimpleNamespace

from django.test import SimpleTestCase

from apps.ai_analysis.services.model_validation import MLModelVersionValidationService


class _Blob:
    def __init__(self, exists=True, text=""):
        self._exists = exists
        self._text = text

    def exists(self):
        return self._exists

    def download_as_text(self):
        return self._text


class _Bucket:
    def __init__(self, blobs):
        self.blobs = blobs

    def blob(self, name):
        return self.blobs.get(name, _Blob(False))


class _Storage:
    def __init__(self, blobs):
        self.blobs = blobs

    def bucket(self, _name):
        return _Bucket(self.blobs)


class MLModelVersionValidationServiceTests(SimpleTestCase):
    def _version(self, *, include_metric=True):
        metrics = {"standard.dice": 0.91} if include_metric else {"epochs": 300}
        metrics["_mlflow"] = {
            "params": {"threshold": "0.45", "spacing": "1,1,1"},
            "tags": {
                "model_version": {
                    "experiment_id": "A-B05",
                    "experiment_status": "COMPLETE",
                    "model_bundle_uri": "gs://models/aneurysm/A-B05",
                    "manifest_uri": "gs://models/aneurysm/A-B05/manifest.json",
                    "checkpoint_uri": "gs://models/aneurysm/A-B05/checkpoint.pth",
                    "analysis_type": "CEREBRAL_ANEURYSM_MRA",
                    "modality": "MRA",
                    "input_channels": "1",
                    "channel_order": "MRA",
                },
                "run": {},
            },
        }
        return SimpleNamespace(
            mlflow_run="run-id",
            mlflow_registered_model_name="cerebral-aneurysm-mra",
            performance_metrics=metrics,
        )

    def _storage(self):
        manifest = {
            "experiment_id": "A-B05",
            "registered_model_name": "cerebral-aneurysm-mra",
            "gcs_uri": "gs://models/aneurysm/A-B05",
            "patient_data_included": False,
            "files": [{"name": "checkpoint.pth", "sha256": "a" * 64}],
        }
        return _Storage({
            "aneurysm/A-B05/manifest.json": _Blob(text=json.dumps(manifest)),
            "aneurysm/A-B05/checkpoint.pth": _Blob(),
        })

    def test_valid_registry_bundle_passes_and_builds_runtime_config(self):
        result = MLModelVersionValidationService(self._storage()).validate(self._version())

        self.assertTrue(result.passed)
        self.assertEqual(result.threshold_config, {"threshold": 0.45})
        self.assertEqual(result.input_contract["modality"], "MRA")
        self.assertTrue(all(check.passed for check in result.checks))

    def test_training_only_metrics_do_not_pass_performance_validation(self):
        result = MLModelVersionValidationService(self._storage()).validate(
            self._version(include_metric=False)
        )

        self.assertFalse(result.passed)
        failed = {check.code for check in result.checks if not check.passed}
        self.assertIn("PERFORMANCE_METRICS", failed)

    def test_admin_threshold_override_is_used_when_run_threshold_is_missing(self):
        version = self._version()
        version.performance_metrics["_mlflow"]["params"]["threshold"] = ""

        result = MLModelVersionValidationService(self._storage()).validate(
            version, threshold_override=0.6
        )

        self.assertTrue(result.passed)
        self.assertEqual(result.threshold_config, {"threshold": 0.6})

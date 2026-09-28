"""Technical readiness validation for synchronized MLflow model versions."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import PurePosixPath
from urllib.parse import urlparse

from google.cloud import storage

from apps.ai_analysis.models import ModelVersion


TRAINING_ONLY_METRICS = {"epochs", "val_epoch", "val_positive_cases"}


@dataclass
class ValidationCheck:
    code: str
    label: str
    passed: bool
    message: str

    def as_dict(self) -> dict[str, object]:
        return {
            "code": self.code,
            "label": self.label,
            "passed": self.passed,
            "message": self.message,
        }


@dataclass
class ModelValidationResult:
    checks: list[ValidationCheck] = field(default_factory=list)
    threshold_config: dict[str, object] = field(default_factory=dict)
    input_contract: dict[str, object] = field(default_factory=dict)
    output_contract: dict[str, object] = field(default_factory=dict)
    preprocessing_config: dict[str, object] = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        return bool(self.checks) and all(check.passed for check in self.checks)

    def as_dict(self) -> dict[str, object]:
        return {
            "passed": self.passed,
            "checks": [check.as_dict() for check in self.checks],
        }


def _gs_parts(uri: str) -> tuple[str, str] | None:
    parsed = urlparse(uri)
    if parsed.scheme != "gs" or not parsed.netloc or not parsed.path.strip("/"):
        return None
    return parsed.netloc, parsed.path.lstrip("/")


def _metadata(version: ModelVersion) -> tuple[dict[str, object], dict[str, object], dict[str, object]]:
    metrics = version.performance_metrics if isinstance(version.performance_metrics, dict) else {}
    mlflow = metrics.get("_mlflow", {})
    mlflow = mlflow if isinstance(mlflow, dict) else {}
    params = mlflow.get("params", {})
    params = params if isinstance(params, dict) else {}
    tag_groups = mlflow.get("tags", {})
    tag_groups = tag_groups if isinstance(tag_groups, dict) else {}
    run_tags = tag_groups.get("run", {})
    version_tags = tag_groups.get("model_version", {})
    tags = {
        **(run_tags if isinstance(run_tags, dict) else {}),
        **(version_tags if isinstance(version_tags, dict) else {}),
    }
    return metrics, params, tags


class MLModelVersionValidationService:
    def __init__(self, storage_client=None):
        self.storage_client = storage_client or storage.Client()

    def validate(self, version: ModelVersion, *, threshold_override: float | None = None) -> ModelValidationResult:
        result = ModelValidationResult()
        metrics, params, tags = _metadata(version)
        experiment_id = str(tags.get("experiment_id", "") or "")
        bundle_uri = str(tags.get("model_bundle_uri", "") or "")
        manifest_uri = str(tags.get("manifest_uri", "") or "")
        checkpoint_uri = str(tags.get("checkpoint_uri", "") or "")

        required = {
            "Run ID": version.mlflow_run,
            "Registered Model": version.mlflow_registered_model_name,
            "Experiment ID": experiment_id,
            "Model bundle URI": bundle_uri,
            "Manifest URI": manifest_uri,
            "Checkpoint URI": checkpoint_uri,
        }
        missing = [label for label, value in required.items() if not value]
        result.checks.append(ValidationCheck(
            "METADATA_COMPLETE", "Registry 메타데이터", not missing,
            "필수 Registry 메타데이터가 모두 존재합니다." if not missing else f"누락: {', '.join(missing)}",
        ))

        complete = str(tags.get("experiment_status", "")).upper() == "COMPLETE"
        result.checks.append(ValidationCheck(
            "EXPERIMENT_COMPLETE", "학습 완료 상태", complete,
            "MLflow experiment_status가 COMPLETE입니다." if complete else "experiment_status가 COMPLETE가 아닙니다.",
        ))

        performance = {
            key: value for key, value in metrics.items()
            if key != "_mlflow" and key not in TRAINING_ONLY_METRICS and isinstance(value, (int, float))
        }
        result.checks.append(ValidationCheck(
            "PERFORMANCE_METRICS", "평가 성능 지표", bool(performance),
            f"평가 지표 {len(performance)}개가 확인됐습니다." if performance else "Dice, Recall, Precision 등 평가용 metric이 없습니다.",
        ))

        try:
            threshold = float(threshold_override if threshold_override is not None else params.get("threshold", ""))
            threshold_valid = 0 <= threshold <= 1
        except (TypeError, ValueError):
            threshold = 0.0
            threshold_valid = False
        result.checks.append(ValidationCheck(
            "THRESHOLD_VALID", "판정 Threshold", threshold_valid,
            f"threshold={threshold:g}" if threshold_valid else "0~1 범위의 threshold parameter가 필요합니다.",
        ))

        manifest = self._load_manifest(manifest_uri, result)
        self._check_checkpoint(checkpoint_uri, manifest, result)
        self._check_manifest(version, experiment_id, bundle_uri, manifest, result)

        if result.passed:
            analysis_type = str(tags.get("analysis_type", "") or "")
            modality = str(tags.get("modality", "") or "")
            result.threshold_config = {"threshold": threshold}
            result.input_contract = {
                "schema_version": "1.0",
                "analysis_type": analysis_type,
                "modality": modality,
                "input_channels": tags.get("input_channels", ""),
                "channel_order": tags.get("channel_order", ""),
            }
            result.output_contract = {
                "schema_version": "1.0",
                "outputs": ["mask", "lesion_count", "total_volume_ml", "structured_findings"],
            }
            result.preprocessing_config = {
                key: params[key]
                for key in ("spacing", "patch_size", "plans.output_identifier")
                if params.get(key) not in (None, "")
            }
        return result

    def _load_manifest(self, uri: str, result: ModelValidationResult) -> dict[str, object] | None:
        parts = _gs_parts(uri)
        if parts is None:
            result.checks.append(ValidationCheck("MANIFEST_ACCESSIBLE", "Manifest 접근", False, "유효한 gs:// manifest URI가 아닙니다."))
            return None
        try:
            blob = self.storage_client.bucket(parts[0]).blob(parts[1])
            if not blob.exists():
                result.checks.append(ValidationCheck("MANIFEST_ACCESSIBLE", "Manifest 접근", False, "GCS manifest 객체가 없습니다."))
                return None
            value = json.loads(blob.download_as_text())
            if not isinstance(value, dict):
                raise ValueError("manifest root is not an object")
        except Exception as exc:
            result.checks.append(ValidationCheck("MANIFEST_ACCESSIBLE", "Manifest 접근", False, f"Manifest를 읽지 못했습니다: {exc}"))
            return None
        result.checks.append(ValidationCheck("MANIFEST_ACCESSIBLE", "Manifest 접근", True, "GCS manifest를 정상적으로 읽었습니다."))
        return value

    def _check_checkpoint(self, uri: str, manifest: dict[str, object] | None, result: ModelValidationResult) -> None:
        parts = _gs_parts(uri)
        exists = False
        if parts is not None:
            try:
                exists = self.storage_client.bucket(parts[0]).blob(parts[1]).exists()
            except Exception:
                exists = False
        result.checks.append(ValidationCheck(
            "CHECKPOINT_ACCESSIBLE", "Checkpoint 접근", exists,
            "GCS checkpoint 객체가 존재합니다." if exists else "GCS checkpoint 객체를 확인할 수 없습니다.",
        ))

        checkpoint_name = PurePosixPath(parts[1]).name if parts else ""
        files = manifest.get("files", []) if manifest else []
        entry = next((item for item in files if isinstance(item, dict) and item.get("name") == checkpoint_name), None)
        digest = str(entry.get("sha256", "")) if isinstance(entry, dict) else ""
        digest_valid = bool(re.fullmatch(r"[a-fA-F0-9]{64}", digest))
        result.checks.append(ValidationCheck(
            "CHECKPOINT_DECLARED", "Checkpoint 무결성 선언", digest_valid,
            "Manifest의 checkpoint SHA-256 형식이 유효합니다." if digest_valid else "Manifest에 checkpoint 파일과 유효한 SHA-256이 필요합니다.",
        ))

    @staticmethod
    def _check_manifest(version, experiment_id, bundle_uri, manifest, result) -> None:
        consistent = bool(manifest) and all((
            str(manifest.get("experiment_id", "")) == experiment_id,
            str(manifest.get("registered_model_name", "")) == version.mlflow_registered_model_name,
            str(manifest.get("gcs_uri", "")).rstrip("/") == bundle_uri.rstrip("/"),
            manifest.get("patient_data_included") is False,
        ))
        result.checks.append(ValidationCheck(
            "MANIFEST_CONSISTENT", "Manifest 일치", consistent,
            "실험 ID, 모델명, bundle URI 및 비식별 선언이 일치합니다." if consistent else "Manifest 내용이 Registry 메타데이터와 일치하지 않습니다.",
        ))

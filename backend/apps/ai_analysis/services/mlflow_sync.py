"""Idempotent MLflow Registry to BrainCDSS ModelVersion synchronization."""

from __future__ import annotations

from dataclasses import dataclass, field
import re

from django.db import transaction
from django.utils import timezone

from apps.ai_analysis.models import AIModel, ModelVersion
from apps.ai_analysis.services.mlflow_registry import (
    MLflowRegistryClient,
    RegistryModelVersion,
)
from apps.audit.services.audit_event import record_audit_event


@dataclass
class MLflowSyncResult:
    discovered: int = 0
    created: int = 0
    updated: int = 0
    skipped: int = 0
    error_details: list[dict[str, str]] = field(default_factory=list)

    def as_dict(self) -> dict[str, object]:
        return {
            "discovered": self.discovered,
            "created": self.created,
            "updated": self.updated,
            "skipped": self.skipped,
            "errors": len(self.error_details),
            "error_details": self.error_details,
        }


def _safe_tags(tags: dict[str, object]) -> dict[str, object]:
    return {str(key): value for key, value in tags.items()}


def _performance_metrics(record: RegistryModelVersion) -> dict[str, object]:
    # Keep actual numeric metrics at the top level for the existing overview UI,
    # while retaining MLflow params/tags under a namespaced metadata key.
    return {
        **{str(key): value for key, value in record.metrics.items()},
        "_mlflow": {
            "experiment_id": _tag_value(record, "experiment_id") or record.experiment_id,
            "mlflow_experiment_id": record.experiment_id,
            "params": {str(key): value for key, value in record.params.items()},
            "tags": _safe_tags(record.tags),
            "model_bundle_uri": _tag_value(record, "model_bundle_uri"),
            "manifest_uri": _tag_value(record, "manifest_uri"),
            "checkpoint_uri": _tag_value(record, "checkpoint_uri"),
        },
    }


def _tag_value(record: RegistryModelVersion, key: str) -> object:
    version_tags = record.tags.get("model_version", {})
    run_tags = record.tags.get("run", {})
    if isinstance(version_tags, dict) and version_tags.get(key) not in (None, ""):
        return version_tags[key]
    if isinstance(run_tags, dict):
        return run_tags.get(key, "")
    return ""


def _normalized_identifier(value: object) -> str:
    return re.sub(r"[^a-z0-9]", "", str(value).casefold())


def _matching_model(record: RegistryModelVersion) -> AIModel | None:
    existing_model_ids = list(
        ModelVersion.objects.filter(
            mlflow_registered_model_name=record.registered_model_name
        )
        .values_list("model_id", flat=True)
        .distinct()
    )
    if len(existing_model_ids) == 1:
        return AIModel.objects.filter(pk=existing_model_ids[0]).first()
    if len(existing_model_ids) > 1:
        return None

    aliases = {record.registered_model_name}
    for tag_group in (record.tags.get("model_version", {}), record.tags.get("run", {})):
        if isinstance(tag_group, dict):
            aliases.update(
                str(tag_group.get(key, ""))
                for key in ("analysis_type", "model_name")
                if tag_group.get(key)
            )
    normalized_aliases = {_normalized_identifier(alias) for alias in aliases}
    candidates = [
        model
        for model in AIModel.objects.all()
        if _normalized_identifier(model.code) in normalized_aliases
        or _normalized_identifier(model.display_name) in normalized_aliases
    ]
    return candidates[0] if len(candidates) == 1 else None


def _metadata(record: RegistryModelVersion) -> dict[str, object]:
    tags = record.tags.get("model_version", {})
    return {
        "version": record.model_version,
        "mlflow_run": record.run_id,
        "artifact_uri": record.artifact_uri,
        "container_image_digest": str(tags.get("container_image_digest", "")),
        "code_commit_sha": str(
            tags.get("code_commit_sha", "") or tags.get("source_git_commit", "")
        ),
        "performance_metrics": _performance_metrics(record),
    }


class MLflowModelVersionSyncService:
    """Synchronize metadata only; workflow and routing changes are forbidden."""

    def __init__(self, registry_client: MLflowRegistryClient | None = None):
        self.registry_client = registry_client or MLflowRegistryClient()

    def sync(self, *, request) -> MLflowSyncResult:
        result = MLflowSyncResult()
        records = self.registry_client.list_model_versions()
        result.discovered = len(records)
        for record in records:
            try:
                self._sync_record(record=record, request=request, result=result)
            except Exception as exc:
                result.skipped += 1
                result.error_details.append(
                    {
                        "registered_model_name": record.registered_model_name,
                        "model_version": record.model_version,
                        "code": "SYNC_RECORD_FAILED",
                        "message": str(exc),
                    }
                )
        return result

    def _sync_record(self, *, record, request, result) -> None:
        model = _matching_model(record)
        if model is None:
            result.skipped += 1
            result.error_details.append(
                {
                    "registered_model_name": record.registered_model_name,
                    "model_version": record.model_version,
                    "code": "AI_MODEL_MAPPING_NOT_FOUND",
                    "message": "No unique BrainCDSS AIModel mapping exists.",
                }
            )
            return

        with transaction.atomic():
            # Serializes concurrent syncs of the same logical AI model despite
            # the legacy schema lacking a database uniqueness constraint.
            locked_model = AIModel.objects.select_for_update().get(pk=model.pk)
            matches = list(
                ModelVersion.objects.select_for_update().filter(
                    mlflow_registered_model_name=record.registered_model_name,
                    mlflow_model_version=record.model_version,
                )
            )
            if len(matches) > 1:
                result.skipped += 1
                result.error_details.append(
                    {
                        "registered_model_name": record.registered_model_name,
                        "model_version": record.model_version,
                        "code": "DUPLICATE_MODEL_VERSION",
                        "message": "Multiple existing BrainCDSS ModelVersion rows match this MLflow version.",
                    }
                )
                return

            metadata = _metadata(record)
            if matches:
                version = matches[0]
                changed = [
                    field
                    for field, value in metadata.items()
                    if getattr(version, field) != value
                ]
                if not changed:
                    result.skipped += 1
                    return
                before = {
                    field: getattr(version, field)
                    for field in changed
                }
                for field in changed:
                    setattr(version, field, metadata[field])
                version.updated_at = timezone.now()
                version.save(update_fields=[*changed, "updated_at"])
                record_audit_event(
                    source_service="backend.ai_analysis",
                    action="AI_MODEL_VERSION_MLFLOW_SYNC_UPDATED",
                    resource_type="ModelVersion",
                    resource_id=version.id,
                    outcome="SUCCESS",
                    request=request,
                    before_json=before,
                    after_json={field: getattr(version, field) for field in changed},
                )
                result.updated += 1
                return

            version = ModelVersion.objects.create(
                model=locked_model,
                mlflow_registered_model_name=record.registered_model_name,
                mlflow_model_version=record.model_version,
                input_contract={},
                output_contract={},
                preprocessing_config={},
                validation_status="DRAFT",
                is_active=False,
                created_at=record.created_at,
                updated_at=record.updated_at,
                **metadata,
            )
            record_audit_event(
                source_service="backend.ai_analysis",
                action="AI_MODEL_VERSION_MLFLOW_SYNC_CREATED",
                resource_type="ModelVersion",
                resource_id=version.id,
                outcome="SUCCESS",
                request=request,
                after_json={
                    "mlflow_registered_model_name": record.registered_model_name,
                    "mlflow_model_version": record.model_version,
                    "validation_status": "DRAFT",
                    "is_active": False,
                },
            )
            result.created += 1

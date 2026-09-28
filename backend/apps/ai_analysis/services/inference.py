"""State transitions for the development inference bridge."""

import uuid

from django.db import transaction
from django.utils import timezone

from apps.ai_analysis.models import (
    AIAnalysis,
    AIAnalysisInputArtifact,
    AIAnalysisInputSeries,
    AIAnalysisResult,
    AIAnalysisStatusHistory,
    AIResultArtifact,
)
from apps.imaging.models import NiftiArtifact


def _canonical_request_id(
    value=None,
):
    """
    Normalize one BrainOn correlation identifier.

    HTTP-originated jobs must receive the middleware request ID.
    A new UUID is created only for jobs that have no parent
    HTTP request, such as an independent background root job.
    """
    if value not in (
        None,
        "",
    ):
        try:
            return str(
                uuid.UUID(
                    str(value)
                )
            )
        except (
            ValueError,
            TypeError,
            AttributeError,
        ) as exc:
            raise ValueError(
                "REQUEST_ID_INVALID"
            ) from exc

    return str(
        uuid.uuid4()
    )


def transition_analysis(analysis, *, status, stage, reason_code=None):
    """Persist the current state and its append-only history together."""
    previous_status = analysis.status
    now = timezone.now()
    analysis.status = status
    analysis.stage = stage
    analysis.failure_code = reason_code
    analysis.updated_at = now
    if status == "PROCESSING" and analysis.started_at is None:
        analysis.started_at = now
    if status in {"COMPLETED", "FAILED"}:
        analysis.completed_at = now
    analysis.save()
    AIAnalysisStatusHistory.objects.create(
        analysis=analysis,
        previous_status=previous_status,
        status=status,
        stage=stage,
        reason_code=reason_code,
        occurred_at=now,
    )


def create_queued_analysis(*, study, model_version, model_config_version,
                           requested_by, analysis_type, priority, inputs=None,
                           series_ids=None, routing_config_version=None,
                           request_id=None):
    """Create a synthetic-input job using the existing clinical schema."""
    now = timezone.now()
    with transaction.atomic():
        analysis = AIAnalysis.objects.create(
            study=study,
            model_version=model_version,
            model_config_version=model_config_version,
            routing_config_version=routing_config_version,
            analysis_type=analysis_type,
            status="QUEUED",
            stage="VALIDATING",
            priority=priority,
            requested_by=requested_by,
            attempt_count=0,
            trace=_canonical_request_id(
                request_id
            ),
            requested_at=now,
            started_at=None,
            completed_at=None,
            failure_code=None,
            created_at=now,
            updated_at=now,
        )
        AIAnalysisStatusHistory.objects.create(
            analysis=analysis,
            previous_status=None,
            status="QUEUED",
            stage="VALIDATING",
            reason_code="SYNTHETIC_DEVELOPMENT_INPUT",
            occurred_at=now,
        )
        for item in inputs or []:
            AIAnalysisInputArtifact.objects.create(
                analysis=analysis,
                role=item["role"],
                uri=item["uri"],
                size_bytes=item["size_bytes"],
                sha256=item["sha256"],
            )
        artifacts_by_series = {
            str(item.series_id): item
            for item in NiftiArtifact.objects.filter(series_id__in=series_ids or [])
        }
        for series_id in series_ids or []:
            artifact = artifacts_by_series.get(str(series_id))
            if artifact:
                AIAnalysisInputSeries.objects.create(
                    analysis=analysis, series=artifact.series, role=artifact.role
                )
    return analysis


def store_mock_result(analysis, response):
    """Store a clearly labelled, non-clinical result in the existing table."""
    AIAnalysisResult.objects.update_or_create(
        analysis=analysis,
        defaults={
            "is_positive": None,
            "confidence": None,
            "lesion_count": None,
            "total_volume_ml": None,
            "max_diameter_mm": None,
            "severity": "MOCK",
            "structured_findings": {
                "is_mock": True,
                "accuracy_simulated": False,
                "mock_response": response,
            },
            "generated_at": timezone.now(),
        },
    )


def store_inference_result(analysis, response):
    """Persist quantitative results and immutable output artifact references."""
    metrics = response.get("metrics") or {}
    outputs = response.get("outputs") or []
    result, _ = AIAnalysisResult.objects.update_or_create(
        analysis=analysis,
        defaults={
            "is_positive": bool(metrics.get("lesion_voxels", 0)),
            "confidence": None,
            "lesion_count": metrics.get("lesion_count"),
            "total_volume_ml": metrics.get("volume_ml"),
            "max_diameter_mm": None,
            "severity": "UNREVIEWED",
            "structured_findings": {
                "model": response.get("model"),
                "metrics": metrics,
                "lesions": metrics.get("lesions") or [],
                "timing_ms": response.get("timing_ms") or {},
                "trace_id": response.get("trace_id"),
                "outputs": outputs,
            },
            "generated_at": timezone.now(),
        },
    )
    AIResultArtifact.objects.filter(result=result).delete()
    for output in outputs:
        AIResultArtifact.objects.create(
            result=result,
            artifact_type=output["type"],
            uri=output["uri"],
            dicom_object_reference=None,
            status="AVAILABLE",
            created_at=timezone.now(),
        )
    return result

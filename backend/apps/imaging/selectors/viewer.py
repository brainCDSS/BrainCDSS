from apps.ai_analysis.models import (
    AIAnalysisResult,
    AIResultArtifact,
)
from apps.imaging.models import SeriesReference
from apps.radiology.models import RadiologyReport


def get_viewer_context_data(
    *,
    study,
):
    series = list(
        SeriesReference.objects
        .filter(study=study)
        .order_by(
            "series_number",
            "id",
        )
    )

    result = (
        AIAnalysisResult.objects
        .select_related(
            "analysis",
            "analysis__model_version",
            "analysis__model_version__model",
        )
        .filter(
            analysis__study=study,
            analysis__status="COMPLETED",
        )
        .order_by(
            "-analysis__completed_at",
            "-generated_at",
            "-id",
        )
        .first()
    )

    artifacts = []

    if result is not None:
        artifacts = list(
            AIResultArtifact.objects
            .select_related(
                "dicom_object_reference",
                "dicom_object_reference__series",
            )
            .filter(
                result=result,
                status="AVAILABLE",
                dicom_object_reference__isnull=False,
                dicom_object_reference__object_type__in=[
                    "SEG",
                    "SR",
                ],
            )
            .order_by(
                "artifact_type",
                "id",
            )
        )

    final_report = (
        RadiologyReport.objects
        .select_related(
            "author",
            "author__role",
            "finalized_by",
        )
        .filter(
            study=study,
            is_current=True,
            status__in=[
                "FINAL",
                "AMENDED",
            ],
        )
        .order_by(
            "-version",
            "-updated_at",
            "-id",
        )
        .first()
    )

    return {
        "series": series,
        "result": result,
        "artifacts": artifacts,
        "final_report": final_report,
    }

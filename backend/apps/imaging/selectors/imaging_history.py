from apps.ai_analysis.models import (
    AIAnalysis,
    AIAnalysisStatusHistory,
)
from apps.imaging.models import (
    DicomTransferJob,
    ImagingOrderStatusHistory,
    ImagingStudy,
)
from apps.radiology.models import RadiologyReport


def list_study_reports(
    *,
    study,
    current_only=False,
    status=None,
):
    queryset = (
        RadiologyReport.objects
        .select_related(
            "author",
            "author__role",
            "finalized_by",
            "finalized_by__role",
        )
        .filter(study=study)
    )

    if current_only:
        queryset = queryset.filter(
            is_current=True
        )

    if status:
        queryset = queryset.filter(
            status=status
        )

    return queryset.order_by(
        "-version",
        "-updated_at",
        "-id",
    )


def get_order_timeline_data(order):
    study = (
        ImagingStudy.objects
        .filter(
            imaging_order=order
        )
        .order_by(
            "-study_datetime",
            "-created_at",
            "-id",
        )
        .first()
    )

    order_history = list(
        ImagingOrderStatusHistory.objects
        .filter(
            imaging_order=order
        )
        .order_by(
            "occurred_at",
            "id",
        )
    )

    transfer_jobs = []
    analyses = []
    analysis_history = []
    reports = []

    if study is not None:
        transfer_jobs = list(
            DicomTransferJob.objects
            .filter(study=study)
        )

        analyses = list(
            AIAnalysis.objects
            .filter(study=study)
            .order_by(
                "requested_at",
                "id",
            )
        )

        if analyses:
            analysis_ids = [
                item.id
                for item in analyses
            ]

            analysis_history = list(
                AIAnalysisStatusHistory.objects
                .filter(
                    analysis_id__in=
                        analysis_ids
                )
                .select_related("analysis")
                .order_by(
                    "occurred_at",
                    "id",
                )
            )

        reports = list(
            RadiologyReport.objects
            .filter(study=study)
            .order_by(
                "created_at",
                "version",
                "id",
            )
        )

    return {
        "study": study,
        "order_history": order_history,
        "transfer_jobs": transfer_jobs,
        "analyses": analyses,
        "analysis_history":
            analysis_history,
        "reports": reports,
    }

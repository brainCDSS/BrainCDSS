from urllib.parse import quote

from drf_spectacular.utils import extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.api.errors import (
    ContractAPIException,
)
from apps.audit.services.audit_event import (
    record_audit_event,
)
from apps.imaging.api.imaging_study_permissions import (
    ImagingSeriesPermission,
)
from apps.imaging.api.viewer_serializers import (
    ViewerContextQuerySerializer,
    ViewerContextResponseSerializer,
    ViewerSessionRequestSerializer,
    ViewerSessionSerializer,
)
from apps.imaging.models import ImagingStudy
from apps.imaging.selectors.imaging_studies import (
    get_scoped_imaging_study,
)
from apps.imaging.selectors.viewer import (
    get_viewer_context_data,
)
from apps.imaging.services.viewer_session import (
    issue_viewer_session,
)



def _viewer_series_item(series):
    return {
        "series_id": series.id,
        "series_instance_uid":
            series.series_instance_uid,
        "series_number":
            series.series_number,
        "modality":
            series.modality,
        "series_description":
            series.series_description,
        "instance_count":
            series.instance_count,
        "slice_thickness": (
            float(series.slice_thickness)
            if series.slice_thickness is not None
            else None
        ),
        "is_complete":
            series.is_complete,
        "is_ai_eligible":
            series.is_ai_eligible,
        "ai_exclusion_reason":
            series.ai_exclusion_reason,
    }


def _retrieve_url(
    *,
    study,
    dicom,
):
    series = dicom.series

    if series is None:
        return None

    return (
        "/dicom-web/studies/"
        f"{quote(study.study_instance_uid, safe='')}"
        "/series/"
        f"{quote(series.series_instance_uid, safe='')}"
        "/instances/"
        f"{quote(dicom.sop_instance_uid, safe='')}"
    )


def _viewer_ai_payload(
    *,
    study,
    result,
    artifacts,
):
    if result is None:
        return None

    return {
        "analysis_id": result.analysis_id,
        "result": {
            "is_positive":
                result.is_positive,
            "confidence": (
                float(result.confidence)
                if result.confidence is not None
                else None
            ),
            "lesion_count":
                result.lesion_count,
            "total_volume_ml": (
                float(result.total_volume_ml)
                if (
                    result.total_volume_ml
                    is not None
                )
                else None
            ),
            "max_diameter_mm": (
                float(result.max_diameter_mm)
                if (
                    result.max_diameter_mm
                    is not None
                )
                else None
            ),
            "severity":
                result.severity,
            "structured_findings":
                result.structured_findings,
        },
        "artifacts": [
            {
                "artifact_id":
                    artifact.id,
                "artifact_type":
                    artifact.artifact_type,
                "dicom_object_reference_id":
                    artifact.dicom_object_reference_id,
                "sop_instance_uid":
                    (
                        artifact
                        .dicom_object_reference
                        .sop_instance_uid
                    ),
                "retrieve_url":
                    _retrieve_url(
                        study=study,
                        dicom=(
                            artifact
                            .dicom_object_reference
                        ),
                    ),
            }
            for artifact in artifacts
            if (
                artifact
                .dicom_object_reference_id
                is not None
            )
        ],
    }


def _report_payload(report):
    if report is None:
        return None

    return {
        "report_id": report.id,
        "status": report.status,
        "version": report.version,
        "findings": report.findings,
        "impression": report.impression,
        "recommendation":
            report.recommendation,
        "author_id":
            report.author_id,
        "author_name":
            report.author.name,
        "finalized_at":
            report.finalized_at,
        "critical_finding":
            report.critical_finding,
        "critical_level":
            report.critical_level,
    }


class ImagingViewerContextView(APIView):
    permission_classes = (
        ImagingSeriesPermission,
    )

    @extend_schema(
        operation_id="api_dicom_002",
        summary=(
            "원본영상·AI Overlay·"
            "Final 판독 Viewer Context"
        ),
        parameters=[
            ViewerContextQuerySerializer,
        ],
        responses={
            200: ViewerContextResponseSerializer,
        },
        tags=["imaging"],
    )
    def get(
        self,
        request,
        study_id,
    ):
        query = ViewerContextQuerySerializer(
            data=request.query_params
        )
        query.is_valid(
            raise_exception=True
        )

        include_ai_overlay = (
            query.validated_data[
                "include_ai_overlay"
            ]
        )

        try:
            study = get_scoped_imaging_study(
                user=request.user,
                study_id=study_id,
            )
        except ImagingStudy.DoesNotExist as exc:
            raise ContractAPIException(
                "IMAGING_STUDY_NOT_FOUND",
                "Imaging study not found.",
                404,
            ) from exc

        if study.status != "AVAILABLE":
            raise ContractAPIException(
                "STUDY_NOT_AVAILABLE",
                (
                    "Viewer can only open "
                    "an AVAILABLE study."
                ),
                409,
            )

        context = get_viewer_context_data(
            study=study
        )

        overlay_available = bool(
            context["result"]
            and context["artifacts"]
        )

        effective_overlay = bool(
            include_ai_overlay
            and overlay_available
        )

        session = issue_viewer_session(
            user=request.user,
            study=study,
            purpose="DIAGNOSIS",
            include_ai_overlay=
                effective_overlay,
            ai_overlay_available=
                overlay_available,
        )

        payload = {
            "study": {
                "study_id": study.id,
                "study_instance_uid":
                    study.study_instance_uid,
                "accession_number":
                    study.accession_number,
                "study_datetime":
                    study.study_datetime,
                "status":
                    study.status,
            },
            "viewer_session":
                session,
            "series": [
                _viewer_series_item(item)
                for item
                in context["series"]
            ],
            "ai": (
                _viewer_ai_payload(
                    study=study,
                    result=context["result"],
                    artifacts=
                        context["artifacts"],
                )
                if effective_overlay
                else None
            ),
            "final_report":
                _report_payload(
                    context["final_report"]
                ),
        }

        record_audit_event(
            source_service="imaging",
            action="VIEW_VIEWER_CONTEXT",
            resource_type="ImagingStudy",
            resource_id=study.id,
            patient_id=study.patient_id,
            outcome="SUCCESS",
            request=request,
        )

        return Response(
            ViewerContextResponseSerializer(
                payload
            ).data
        )


class ImagingViewerSessionView(APIView):
    permission_classes = (
        ImagingSeriesPermission,
    )

    @extend_schema(
        operation_id="api_img_007",
        summary="OHIF Viewer Session 발급",
        request=ViewerSessionRequestSerializer,
        responses={
            201: ViewerSessionSerializer,
        },
        tags=["imaging"],
    )
    def post(
        self,
        request,
        study_id,
    ):
        serializer = (
            ViewerSessionRequestSerializer(
                data=request.data
            )
        )
        serializer.is_valid(
            raise_exception=True
        )

        try:
            study = get_scoped_imaging_study(
                user=request.user,
                study_id=study_id,
            )
        except ImagingStudy.DoesNotExist as exc:
            raise ContractAPIException(
                "IMAGING_STUDY_NOT_FOUND",
                "Imaging study not found.",
                404,
            ) from exc

        if study.status != "AVAILABLE":
            raise ContractAPIException(
                "STUDY_NOT_AVAILABLE",
                (
                    "Viewer can only open "
                    "an AVAILABLE study."
                ),
                409,
            )

        context = get_viewer_context_data(
            study=study
        )

        overlay_available = bool(
            context["result"]
            and context["artifacts"]
        )

        data = serializer.validated_data

        if (
            data["include_ai_overlay"]
            and not overlay_available
        ):
            raise ContractAPIException(
                "AI_OVERLAY_NOT_AVAILABLE",
                (
                    "A completed AI result with "
                    "an AVAILABLE DICOM artifact "
                    "is required."
                ),
                409,
            )

        session = issue_viewer_session(
            user=request.user,
            study=study,
            purpose=data["purpose"],
            include_ai_overlay=
                data["include_ai_overlay"],
            ai_overlay_available=
                overlay_available,
        )

        record_audit_event(
            source_service="imaging",
            action="OPEN_OHIF_VIEWER",
            resource_type="ImagingStudy",
            resource_id=study.id,
            patient_id=study.patient_id,
            outcome="SUCCESS",
            request=request,
            after_json={
                "purpose":
                    data["purpose"],
                "include_ai_overlay":
                    data[
                        "include_ai_overlay"
                    ],
            },
        )

        return Response(
            ViewerSessionSerializer(
                session
            ).data,
            status=201,
        )

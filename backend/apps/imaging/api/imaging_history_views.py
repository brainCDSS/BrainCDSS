from drf_spectacular.utils import extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.api.errors import (
    ContractAPIException,
)
from apps.audit.services.audit_event import (
    record_audit_event,
)
from apps.imaging.api.imaging_history_serializers import (
    ImagingOrderTimelineSerializer,
    StudyReportListSerializer,
    StudyReportQuerySerializer,
)
from apps.imaging.api.imaging_study_permissions import (
    ImagingOrderReadPermission,
)
from apps.imaging.models import ImagingStudy
from apps.imaging.selectors.imaging_history import (
    get_order_timeline_data,
    list_study_reports,
)
from apps.imaging.selectors.imaging_orders import (
    get_scoped_imaging_order,
)
from apps.imaging.selectors.imaging_studies import (
    get_scoped_imaging_study,
)


def _user_payload(user):
    if user is None:
        return None

    return {
        "user_id": user.id,
        "name": user.name,
        "role": user.role.code,
    }


def _report_payload(report):
    return {
        "report_id": report.id,
        "study_id": report.study_id,

        "status": report.status,
        "version": report.version,
        "is_current": report.is_current,

        "findings": report.findings,
        "impression": report.impression,
        "recommendation":
            report.recommendation,

        "structured_findings":
            report.structured_findings,

        "author":
            _user_payload(report.author),

        "referenced_ai_analysis_id":
            report.referenced_ai_analysis_id,

        "preliminary_at":
            report.preliminary_at,

        "finalized_by":
            _user_payload(
                report.finalized_by
            ),

        "finalized_at":
            report.finalized_at,

        "critical_finding":
            report.critical_finding,

        "critical_level":
            report.critical_level,

        "created_at":
            report.created_at,

        "updated_at":
            report.updated_at,
    }


def _event(
    *,
    source,
    type_,
    status,
    occurred_at,
    stage=None,
    reason_code=None,
    reason=None,
):
    return {
        "source": source,
        "type": type_,
        "status": status,
        "stage": stage,
        "occurred_at": occurred_at,
        "reason_code": reason_code,
        "reason": reason,
        "label": (
            f"{source} · {status}"
        ),
    }


class ImagingStudyReportsView(APIView):
    permission_classes = (
        ImagingOrderReadPermission,
    )

    @extend_schema(
        operation_id="api_img_010",
        summary="Study 판독 이력 조회",
        parameters=[
            StudyReportQuerySerializer,
        ],
        responses={
            200: StudyReportListSerializer,
        },
        tags=["imaging"],
    )
    def get(
        self,
        request,
        study_id,
    ):
        query = StudyReportQuerySerializer(
            data=request.query_params
        )
        query.is_valid(
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

        queryset = list_study_reports(
            study=study,
            current_only=
                query.validated_data[
                    "current_only"
                ],
            status=
                query.validated_data.get(
                    "status"
                ),
        )

        results = [
            _report_payload(report)
            for report in queryset
        ]

        payload = {
            "study_id": study.id,
            "count": len(results),
            "results": results,
        }

        record_audit_event(
            source_service="imaging",
            action="VIEW_STUDY_REPORTS",
            resource_type="ImagingStudy",
            resource_id=study.id,
            patient_id=study.patient_id,
            outcome="SUCCESS",
            request=request,
        )

        return Response(
            StudyReportListSerializer(
                payload
            ).data
        )


class ImagingOrderTimelineView(APIView):
    permission_classes = (
        ImagingOrderReadPermission,
    )

    @extend_schema(
        operation_id="api_img_015",
        summary=(
            "Order·PACS·AI·판독 "
            "통합 Timeline 조회"
        ),
        responses={
            200:
                ImagingOrderTimelineSerializer,
        },
        tags=["imaging"],
    )
    def get(
        self,
        request,
        order_id,
    ):
        order = get_scoped_imaging_order(
            user=request.user,
            order_id=order_id,
        )

        if order is None:
            raise ContractAPIException(
                "ORDER_NOT_FOUND",
                "Imaging order not found.",
                404,
            )

        data = get_order_timeline_data(
            order
        )

        study = data["study"]
        events = []

        # ----------------------------------------------------
        # ORDER
        # ----------------------------------------------------
        for history in data[
            "order_history"
        ]:
            events.append(
                _event(
                    source="ORDER",
                    type_="STATUS",
                    status=history.status,
                    occurred_at=
                        history.occurred_at,
                    reason=history.reason,
                )
            )

        # ----------------------------------------------------
        # PACS / DICOM TRANSFER
        # DicomTransferJob에는 별도 History가 없으므로
        # 현재 Job Snapshot을 실제 시각과 함께 표현.
        # ----------------------------------------------------
        for transfer in data[
            "transfer_jobs"
        ]:
            occurred_at = (
                transfer.completed_at
                or transfer.started_at
            )

            if occurred_at is not None:
                events.append(
                    _event(
                        source="PACS",
                        type_="DICOM_TRANSFER",
                        status=
                            transfer.status,
                        occurred_at=
                            occurred_at,
                        reason_code=
                            transfer.last_error_code,
                    )
                )

        # ----------------------------------------------------
        # AI
        # ----------------------------------------------------
        for history in data[
            "analysis_history"
        ]:
            events.append(
                _event(
                    source="AI",
                    type_="ANALYSIS_STATUS",
                    status=history.status,
                    stage=history.stage,
                    occurred_at=
                        history.occurred_at,
                    reason_code=
                        history.reason_code,
                )
            )

        # AI History가 없는 분석도 Timeline에서 사라지지 않게
        history_analysis_ids = {
            item.analysis_id
            for item in data[
                "analysis_history"
            ]
        }

        for analysis in data[
            "analyses"
        ]:
            if (
                analysis.id
                not in history_analysis_ids
            ):
                events.append(
                    _event(
                        source="AI",
                        type_="ANALYSIS",
                        status=
                            analysis.status,
                        stage=
                            analysis.stage,
                        occurred_at=
                            analysis.requested_at,
                        reason_code=
                            analysis.failure_code,
                    )
                )

        # ----------------------------------------------------
        # RADIOLOGY
        # ----------------------------------------------------
        for report in data["reports"]:
            occurred_at = (
                report.finalized_at
                or report.preliminary_at
                or report.updated_at
                or report.created_at
            )

            events.append(
                _event(
                    source="RADIOLOGY",
                    type_="REPORT",
                    status=report.status,
                    occurred_at=occurred_at,
                )
            )

        events.sort(
            key=lambda item:
                item["occurred_at"]
        )

        # ----------------------------------------------------
        # Summary objects
        # ----------------------------------------------------
        latest_transfer = None

        transfers_with_time = [
            item
            for item in data[
                "transfer_jobs"
            ]
            if (
                item.completed_at
                or item.started_at
            )
        ]

        if transfers_with_time:
            latest_transfer = max(
                transfers_with_time,
                key=lambda item: (
                    item.completed_at
                    or item.started_at
                ),
            )

        latest_analysis = (
            max(
                data["analyses"],
                key=lambda item:
                    item.requested_at,
            )
            if data["analyses"]
            else None
        )

        current_reports = [
            item
            for item in data["reports"]
            if item.is_current
        ]

        latest_report = (
            max(
                current_reports,
                key=lambda item:
                    item.version,
            )
            if current_reports
            else (
                max(
                    data["reports"],
                    key=lambda item:
                        item.version,
                )
                if data["reports"]
                else None
            )
        )

        payload = {
            "order": {
                "order_id": order.id,
                "encounter_id":
                    order.encounter_id,
                "patient_id":
                    order.patient_id,
                "modality":
                    order.modality,
                "procedure_code":
                    order.procedure_code,
                "priority":
                    order.priority,
                "status":
                    order.status,
                "requested_at":
                    order.requested_at,
                "scheduled_at":
                    order.scheduled_at,
            },

            "current_status":
                order.status,

            "timeline":
                events,

            "study": (
                {
                    "study_id":
                        study.id,
                    "study_instance_uid":
                        study.study_instance_uid,
                    "accession_number":
                        study.accession_number,
                    "status":
                        study.status,
                    "study_datetime":
                        study.study_datetime,
                }
                if study
                else None
            ),

            "transfer": (
                {
                    "job_id":
                        latest_transfer.id,
                    "transfer_type":
                        latest_transfer.transfer_type,
                    "target_system":
                        latest_transfer.target_system,
                    "status":
                        latest_transfer.status,
                    "attempt_count":
                        latest_transfer.attempt_count,
                    "trace_id":
                        latest_transfer.trace,
                    "last_error_code":
                        latest_transfer.last_error_code,
                }
                if latest_transfer
                else None
            ),

            "analysis": (
                {
                    "analysis_id":
                        latest_analysis.id,
                    "analysis_type":
                        latest_analysis.analysis_type,
                    "status":
                        latest_analysis.status,
                    "stage":
                        latest_analysis.stage,
                    "requested_at":
                        latest_analysis.requested_at,
                }
                if latest_analysis
                else None
            ),

            "report": (
                {
                    "report_id":
                        latest_report.id,
                    "status":
                        latest_report.status,
                    "version":
                        latest_report.version,
                    "is_current":
                        latest_report.is_current,
                    "finalized_at":
                        latest_report.finalized_at,
                }
                if latest_report
                else None
            ),
        }

        return Response(
            ImagingOrderTimelineSerializer(
                payload
            ).data
        )

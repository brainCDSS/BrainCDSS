from __future__ import annotations

from drf_spectacular.utils import (
    OpenApiParameter,
    OpenApiResponse,
    extend_schema,
)
from rest_framework import status
from rest_framework.pagination import (
    PageNumberPagination,
)
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audit.api.errors import (
    AuditContractError,
)
from apps.audit.api.permissions import (
    AuditReadPermission,
)
from apps.audit.api.serializers import (
    AuditDetailQuerySerializer,
    AuditListQuerySerializer,
)
from apps.audit.selectors.audit_logs import (
    audit_log_queryset,
    get_audit_log,
)
from apps.audit.services.audit_access import (
    detail_payload,
    list_payload,
    record_audit_read,
)


def _reason_from_request(request):
    return (
        request.query_params.get(
            "reason"
        )
        or request.headers.get(
            "X-Audit-Reason"
        )
        or ""
    ).strip()


class AuditPagination(
    PageNumberPagination
):
    page_size = 50
    page_size_query_param = (
        "page_size"
    )
    max_page_size = 100


class AuditLogListView(APIView):
    permission_classes = [
        AuditReadPermission,
    ]
    required_permission_code = (
        "audit_log.read"
    )

    @extend_schema(
        operation_id=(
            "api_ops_003_audit_log_list"
        ),
        summary="감사 로그 목록 조회",
        parameters=[
            OpenApiParameter(
                "reason",
                str,
                required=False,
                description=(
                    "조회 사유. X-Audit-Reason "
                    "Header로도 전달 가능."
                ),
            ),
        ],
        responses={
            200: OpenApiResponse(
                description=(
                    "Paginated AuditLog list "
                    "without before/after snapshots."
                )
            ),
            400: OpenApiResponse(
                description=(
                    "AUDIT_REASON_REQUIRED / "
                    "INVALID_AUDIT_RANGE"
                )
            ),
            401: OpenApiResponse(
                description="AUTH_REQUIRED"
            ),
            403: OpenApiResponse(
                description=(
                    "AUDIT_ACCESS_FORBIDDEN"
                )
            ),
        },
        tags=["audit"],
    )
    def get(self, request):
        query = request.query_params.copy()

        reason = _reason_from_request(
            request
        )

        if reason:
            query["reason"] = reason

        serializer = (
            AuditListQuerySerializer(
                data=query
            )
        )

        if not serializer.is_valid():
            errors = serializer.errors

            if (
                "occurred_range"
                in errors
            ):
                raise AuditContractError(
                    "INVALID_AUDIT_RANGE",
                    str(errors),
                    400,
                )

            raise AuditContractError(
                "INVALID_AUDIT_RANGE",
                str(errors),
                400,
            )

        data = (
            serializer.validated_data
        )

        reason = data.get(
            "reason"
        )

        if not reason:
            raise AuditContractError(
                "AUDIT_REASON_REQUIRED",
                (
                    "Audit access reason is "
                    "required (5~500 chars)."
                ),
                400,
            )

        queryset = audit_log_queryset(
            data
        )

        paginator = AuditPagination()

        page = paginator.paginate_queryset(
            queryset,
            request,
            view=self,
        )

        payload = [
            list_payload(log)
            for log in page
        ]

        response = (
            paginator
            .get_paginated_response(
                payload
            )
        )

        record_audit_read(
            request=request,
            reason=reason,
            action=(
                "READ_AUDIT_LOG_LIST"
            ),
        )

        return response


class AuditLogDetailView(APIView):
    permission_classes = [
        AuditReadPermission,
    ]
    required_permission_code = (
        "audit_log.read"
    )

    @extend_schema(
        operation_id=(
            "api_ops_004_audit_log_detail"
        ),
        summary="감사 로그 상세 조회",
        parameters=[
            OpenApiParameter(
                "reason",
                str,
                required=True,
                description=(
                    "감사 로그 상세 조회 사유 "
                    "(5~500자)."
                ),
            ),
        ],
        responses={
            200: OpenApiResponse(
                description=(
                    "AuditLog detail with "
                    "sensitive snapshot masking."
                )
            ),
            400: OpenApiResponse(
                description=(
                    "AUDIT_REASON_REQUIRED"
                )
            ),
            401: OpenApiResponse(
                description="AUTH_REQUIRED"
            ),
            403: OpenApiResponse(
                description=(
                    "AUDIT_ACCESS_FORBIDDEN"
                )
            ),
            404: OpenApiResponse(
                description=(
                    "AUDIT_LOG_NOT_FOUND"
                )
            ),
        },
        tags=["audit"],
    )
    def get(
        self,
        request,
        audit_id,
    ):
        reason = _reason_from_request(
            request
        )

        serializer = (
            AuditDetailQuerySerializer(
                data={
                    "reason": reason,
                }
            )
        )

        if not serializer.is_valid():
            raise AuditContractError(
                "AUDIT_REASON_REQUIRED",
                (
                    "Audit access reason is "
                    "required (5~500 chars)."
                ),
                400,
            )

        log = get_audit_log(
            audit_id
        )

        if log is None:
            raise AuditContractError(
                "AUDIT_LOG_NOT_FOUND",
                "Audit log was not found.",
                404,
            )

        payload = detail_payload(
            log
        )

        record_audit_read(
            request=request,
            reason=(
                serializer
                .validated_data["reason"]
            ),
            action=(
                "READ_AUDIT_LOG_DETAIL"
            ),
            resource_id=log.id,
        )

        return Response(
            payload,
            status=status.HTTP_200_OK,
        )

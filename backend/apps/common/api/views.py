from __future__ import annotations

import os

from django.http import HttpResponse
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import (
    OpenApiResponse,
    extend_schema,
)
from rest_framework.permissions import (
    BasePermission,
)
from rest_framework.views import APIView

from apps.common.api.errors import (
    MetricsForbidden,
)
from apps.common.authentication import (
    ServiceJWTAuthentication,
)
from apps.common.metrics import (
    render_prometheus,
)


def _allowed_internal_ips():
    raw = os.environ.get(
        "INTERNAL_METRICS_ALLOWED_IPS",
        "",
    )

    return {
        value.strip()
        for value in raw.split(",")
        if value.strip()
    }


def _request_ip(request):
    forwarded = request.META.get(
        "HTTP_X_FORWARDED_FOR",
        "",
    )

    if forwarded:
        return forwarded.split(",")[0].strip()

    return request.META.get(
        "REMOTE_ADDR"
    )


class RequiredServiceScopePermission(
    BasePermission
):
    message = "METRICS_FORBIDDEN"

    def has_permission(self, request, view):
        principal = getattr(
            request,
            "user",
            None,
        )

        if not getattr(
            principal,
            "is_service",
            False,
        ):
            return False

        required_scope = getattr(
            view,
            "required_service_scope",
            None,
        )

        if (
            required_scope
            and required_scope
            not in principal.scopes
        ):
            raise MetricsForbidden()

        allowed_ips = _allowed_internal_ips()

        if (
            allowed_ips
            and _request_ip(request)
            not in allowed_ips
        ):
            raise MetricsForbidden()

        return True


class MetricsView(APIView):
    authentication_classes = [
        ServiceJWTAuthentication,
    ]
    permission_classes = [
        RequiredServiceScopePermission,
    ]
    required_service_scope = "metrics.read"

    @extend_schema(
        operation_id="api_ops_005_metrics",
        summary="Prometheus Metrics 조회",
        responses={
            200: OpenApiTypes.STR,
            401: OpenApiResponse(
                description="METRICS_AUTH_FAILED"
            ),
            403: OpenApiResponse(
                description="METRICS_FORBIDDEN"
            ),
            503: OpenApiResponse(
                description="METRICS_UNAVAILABLE"
            ),
        },
        tags=["internal-observability"],
    )
    def get(self, request):
        payload = render_prometheus()

        return HttpResponse(
            payload,
            content_type=(
                "text/plain; version=0.0.4; "
                "charset=utf-8"
            ),
            status=200,
        )

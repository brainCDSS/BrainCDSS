"""
AUTO-GENERATED BrainOn API contract scaffold.

Do not implement business logic in this file.
Replace generated scaffold routes with real
application views as implementation proceeds.
"""

from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from drf_spectacular.utils import (
    OpenApiResponse,
    extend_schema,
)


class ContractNotImplementedView(APIView):
    # Scaffold endpoints never access business data.
    # Real authentication/permission policies are
    # applied when each API is implemented.
    authentication_classes = []
    permission_classes = [AllowAny]

    def _not_implemented(
        self,
        request,
        api_id,
        contract_endpoint,
    ):
        return Response(
            {
                "detail": "Not implemented",
                "api_id": api_id,
                "method": request.method,
                "contract_endpoint": contract_endpoint,
            },
            status=status.HTTP_501_NOT_IMPLEMENTED,
        )


class AuditContractEndpoint001View(ContractNotImplementedView):
    @extend_schema(
        operation_id='contract_api_ops_003',
        summary='감사 로그 목록 조회',
        description='BrainOn final API contract scaffold. API ID: API-OPS-003. Contract endpoint: /api/v1/operations/audit-logs. Role contract: SYSTEM_ADMIN\nPermission: audit_log.read.',
        tags=['audit'],
        responses={
            501: OpenApiResponse(
                description="Not implemented",
            ),
        },
    )
    def get(self, request, *args, **kwargs):
        return self._not_implemented(
            request,
            'API-OPS-003',
            '/api/v1/operations/audit-logs',
        )


class AuditContractEndpoint002View(ContractNotImplementedView):
    @extend_schema(
        operation_id='contract_api_ops_004',
        summary='감사 로그 상세 조회',
        description='BrainOn final API contract scaffold. API ID: API-OPS-004. Contract endpoint: /api/v1/operations/audit-logs/{audit_id}. Role contract: SYSTEM_ADMIN\nPermission: audit_log.read.',
        tags=['audit'],
        responses={
            501: OpenApiResponse(
                description="Not implemented",
            ),
        },
    )
    def get(self, request, *args, **kwargs):
        return self._not_implemented(
            request,
            'API-OPS-004',
            '/api/v1/operations/audit-logs/{audit_id}',
        )


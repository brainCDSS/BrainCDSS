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


class PrescriptionsContractEndpoint001View(ContractNotImplementedView):
    @extend_schema(
        operation_id='contract_api_rx_005',
        summary='환자 처방 목록 조회',
        description='BrainOn final API contract scaffold. API ID: API-RX-005. Contract endpoint: /api/v1/prescriptions. Role contract: PATIENT.',
        tags=['prescriptions'],
        responses={
            501: OpenApiResponse(
                description="Not implemented",
            ),
        },
    )
    def get(self, request, *args, **kwargs):
        return self._not_implemented(
            request,
            'API-RX-005',
            '/api/v1/prescriptions',
        )

    @extend_schema(
        operation_id='contract_api_rx_001',
        summary='처방 생성',
        description='BrainOn final API contract scaffold. API ID: API-RX-001. Contract endpoint: /api/v1/prescriptions. Role contract: NEUROLOGIST/NEUROSURGEON.',
        tags=['prescriptions'],
        responses={
            501: OpenApiResponse(
                description="Not implemented",
            ),
        },
    )
    def post(self, request, *args, **kwargs):
        return self._not_implemented(
            request,
            'API-RX-001',
            '/api/v1/prescriptions',
        )


class PrescriptionsContractEndpoint002View(ContractNotImplementedView):
    @extend_schema(
        operation_id='contract_api_rx_002',
        summary='처방 상세 조회',
        description='BrainOn final API contract scaffold. API ID: API-RX-002. Contract endpoint: /api/v1/prescriptions/{prescription_id}. Role contract: NEUROLOGIST/NEUROSURGEON/PATIENT.',
        tags=['prescriptions'],
        responses={
            501: OpenApiResponse(
                description="Not implemented",
            ),
        },
    )
    def get(self, request, *args, **kwargs):
        return self._not_implemented(
            request,
            'API-RX-002',
            '/api/v1/prescriptions/{prescription_id}',
        )

    @extend_schema(
        operation_id='contract_api_rx_003',
        summary='처방 수정·임시저장',
        description='BrainOn final API contract scaffold. API ID: API-RX-003. Contract endpoint: /api/v1/prescriptions/{prescription_id}. Role contract: NEUROLOGIST/NEUROSURGEON.',
        tags=['prescriptions'],
        responses={
            501: OpenApiResponse(
                description="Not implemented",
            ),
        },
    )
    def patch(self, request, *args, **kwargs):
        return self._not_implemented(
            request,
            'API-RX-003',
            '/api/v1/prescriptions/{prescription_id}',
        )


class PrescriptionsContractEndpoint003View(ContractNotImplementedView):
    @extend_schema(
        operation_id='contract_api_rx_004',
        summary='처방 최종 확정',
        description='BrainOn final API contract scaffold. API ID: API-RX-004. Contract endpoint: /api/v1/prescriptions/{prescription_id}/finalize. Role contract: NEUROLOGIST/NEUROSURGEON\nPermission: medication_safety.check (+ medication_safety.override when required).',
        tags=['prescriptions'],
        responses={
            501: OpenApiResponse(
                description="Not implemented",
            ),
        },
    )
    def post(self, request, *args, **kwargs):
        return self._not_implemented(
            request,
            'API-RX-004',
            '/api/v1/prescriptions/{prescription_id}/finalize',
        )


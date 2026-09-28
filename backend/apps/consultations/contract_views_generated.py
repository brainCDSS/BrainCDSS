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


class ConsultationsContractEndpoint001View(ContractNotImplementedView):
    @extend_schema(
        operation_id='contract_api_con_002',
        summary='협진 목록·상태 조회',
        description='BrainOn final API contract scaffold. API ID: API-CON-002. Contract endpoint: /api/v1/consultations. Role contract: NEUROLOGIST/RADIOLOGY/NEUROSURGEON.',
        tags=['consultations'],
        responses={
            501: OpenApiResponse(
                description="Not implemented",
            ),
        },
    )
    def get(self, request, *args, **kwargs):
        return self._not_implemented(
            request,
            'API-CON-002',
            '/api/v1/consultations',
        )

    @extend_schema(
        operation_id='contract_api_con_001',
        summary='협진 요청 생성',
        description='BrainOn final API contract scaffold. API ID: API-CON-001. Contract endpoint: /api/v1/consultations. Role contract: NEUROLOGIST.',
        tags=['consultations'],
        responses={
            501: OpenApiResponse(
                description="Not implemented",
            ),
        },
    )
    def post(self, request, *args, **kwargs):
        return self._not_implemented(
            request,
            'API-CON-001',
            '/api/v1/consultations',
        )


class ConsultationsContractEndpoint002View(ContractNotImplementedView):
    @extend_schema(
        operation_id='contract_api_con_003',
        summary='협진 상세 조회',
        description='BrainOn final API contract scaffold. API ID: API-CON-003. Contract endpoint: /api/v1/consultations/{consultation_id}. Role contract: NEUROLOGIST/RADIOLOGY/NEUROSURGEON.',
        tags=['consultations'],
        responses={
            501: OpenApiResponse(
                description="Not implemented",
            ),
        },
    )
    def get(self, request, *args, **kwargs):
        return self._not_implemented(
            request,
            'API-CON-003',
            '/api/v1/consultations/{consultation_id}',
        )


class ConsultationsContractEndpoint003View(ContractNotImplementedView):
    @extend_schema(
        operation_id='contract_api_con_004',
        summary='협진 수락',
        description='BrainOn final API contract scaffold. API ID: API-CON-004. Contract endpoint: /api/v1/consultations/{consultation_id}/accept. Role contract: RADIOLOGY/NEUROSURGEON.',
        tags=['consultations'],
        responses={
            501: OpenApiResponse(
                description="Not implemented",
            ),
        },
    )
    def post(self, request, *args, **kwargs):
        return self._not_implemented(
            request,
            'API-CON-004',
            '/api/v1/consultations/{consultation_id}/accept',
        )


class ConsultationsContractEndpoint004View(ContractNotImplementedView):
    @extend_schema(
        operation_id='contract_api_con_005',
        summary='협진 검토 시작',
        description='BrainOn final API contract scaffold. API ID: API-CON-005. Contract endpoint: /api/v1/consultations/{consultation_id}/start. Role contract: RADIOLOGY/NEUROSURGEON.',
        tags=['consultations'],
        responses={
            501: OpenApiResponse(
                description="Not implemented",
            ),
        },
    )
    def post(self, request, *args, **kwargs):
        return self._not_implemented(
            request,
            'API-CON-005',
            '/api/v1/consultations/{consultation_id}/start',
        )


class ConsultationsContractEndpoint005View(ContractNotImplementedView):
    @extend_schema(
        operation_id='contract_api_con_006',
        summary='협진 회신 확정',
        description='BrainOn final API contract scaffold. API ID: API-CON-006. Contract endpoint: /api/v1/consultations/{consultation_id}/respond. Role contract: RADIOLOGY/NEUROSURGEON.',
        tags=['consultations'],
        responses={
            501: OpenApiResponse(
                description="Not implemented",
            ),
        },
    )
    def post(self, request, *args, **kwargs):
        return self._not_implemented(
            request,
            'API-CON-006',
            '/api/v1/consultations/{consultation_id}/respond',
        )


class ConsultationsContractEndpoint006View(ContractNotImplementedView):
    @extend_schema(
        operation_id='contract_api_con_007',
        summary='협진 회신 확인·종결',
        description='BrainOn final API contract scaffold. API ID: API-CON-007. Contract endpoint: /api/v1/consultations/{consultation_id}/view-response. Role contract: NEUROLOGIST.',
        tags=['consultations'],
        responses={
            501: OpenApiResponse(
                description="Not implemented",
            ),
        },
    )
    def post(self, request, *args, **kwargs):
        return self._not_implemented(
            request,
            'API-CON-007',
            '/api/v1/consultations/{consultation_id}/view-response',
        )


class ConsultationsContractEndpoint007View(ContractNotImplementedView):
    @extend_schema(
        operation_id='contract_api_con_008',
        summary='협진 요청 거절',
        description='BrainOn final API contract scaffold. API ID: API-CON-008. Contract endpoint: /api/v1/consultations/{consultation_id}/reject. Role contract: RADIOLOGY/NEUROSURGEON.',
        tags=['consultations'],
        responses={
            501: OpenApiResponse(
                description="Not implemented",
            ),
        },
    )
    def post(self, request, *args, **kwargs):
        return self._not_implemented(
            request,
            'API-CON-008',
            '/api/v1/consultations/{consultation_id}/reject',
        )


class ConsultationsContractEndpoint008View(ContractNotImplementedView):
    @extend_schema(
        operation_id='contract_api_con_009',
        summary='협진 취소',
        description='BrainOn final API contract scaffold. API ID: API-CON-009. Contract endpoint: /api/v1/consultations/{consultation_id}/cancel. Role contract: NEUROLOGIST/RADIOLOGY/NEUROSURGEON.',
        tags=['consultations'],
        responses={
            501: OpenApiResponse(
                description="Not implemented",
            ),
        },
    )
    def post(self, request, *args, **kwargs):
        return self._not_implemented(
            request,
            'API-CON-009',
            '/api/v1/consultations/{consultation_id}/cancel',
        )


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


class MedicationsContractEndpoint001View(ContractNotImplementedView):
    @extend_schema(
        operation_id='contract_api_medm_001',
        summary='처방 가능 약품 검색',
        description='BrainOn final API contract scaffold. API ID: API-MEDM-001. Contract endpoint: /api/v1/medications. Role contract: NEUROLOGIST/NEUROSURGEON.',
        tags=['medications'],
        responses={
            501: OpenApiResponse(
                description="Not implemented",
            ),
        },
    )
    def get(self, request, *args, **kwargs):
        return self._not_implemented(
            request,
            'API-MEDM-001',
            '/api/v1/medications',
        )


class MedicationsContractEndpoint002View(ContractNotImplementedView):
    @extend_schema(
        operation_id='contract_api_medm_002',
        summary='약품 상세·성분 조회',
        description='BrainOn final API contract scaffold. API ID: API-MEDM-002. Contract endpoint: /api/v1/medications/{medication_id}. Role contract: NEUROLOGIST/NEUROSURGEON.',
        tags=['medications'],
        responses={
            501: OpenApiResponse(
                description="Not implemented",
            ),
        },
    )
    def get(self, request, *args, **kwargs):
        return self._not_implemented(
            request,
            'API-MEDM-002',
            '/api/v1/medications/{medication_id}',
        )


class MedicationsContractEndpoint003View(ContractNotImplementedView):
    @extend_schema(
        operation_id='contract_api_med_001',
        summary='복약 일정·이력/순응도 조회',
        description='BrainOn final API contract scaffold. API ID: API-MED-001. Contract endpoint: /api/v1/medication-schedules. Role contract: PATIENT.',
        tags=['medications'],
        responses={
            501: OpenApiResponse(
                description="Not implemented",
            ),
        },
    )
    def get(self, request, *args, **kwargs):
        return self._not_implemented(
            request,
            'API-MED-001',
            '/api/v1/medication-schedules',
        )


class MedicationsContractEndpoint004View(ContractNotImplementedView):
    @extend_schema(
        operation_id='contract_api_med_002',
        summary='복용 상태 기록',
        description='BrainOn final API contract scaffold. API ID: API-MED-002. Contract endpoint: /api/v1/medication-intakes. Role contract: PATIENT.',
        tags=['medications'],
        responses={
            501: OpenApiResponse(
                description="Not implemented",
            ),
        },
    )
    def post(self, request, *args, **kwargs):
        return self._not_implemented(
            request,
            'API-MED-002',
            '/api/v1/medication-intakes',
        )


class MedicationsContractEndpoint005View(ContractNotImplementedView):
    @extend_schema(
        operation_id='contract_api_med_003',
        summary='복용 기록 수정',
        description='BrainOn final API contract scaffold. API ID: API-MED-003. Contract endpoint: /api/v1/medication-intakes/{intake_id}. Role contract: PATIENT.',
        tags=['medications'],
        responses={
            501: OpenApiResponse(
                description="Not implemented",
            ),
        },
    )
    def patch(self, request, *args, **kwargs):
        return self._not_implemented(
            request,
            'API-MED-003',
            '/api/v1/medication-intakes/{intake_id}',
        )


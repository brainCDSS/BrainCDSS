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


class AssessmentsContractEndpoint001View(ContractNotImplementedView):
    @extend_schema(
        operation_id='contract_api_asm_001',
        summary='초기평가 대기 목록 조회',
        description='BrainOn final API contract scaffold. API ID: API-ASM-001. Contract endpoint: /api/v1/assessments/worklist. Role contract: NURSE.',
        tags=['assessments'],
        responses={
            501: OpenApiResponse(
                description="Not implemented",
            ),
        },
    )
    def get(self, request, *args, **kwargs):
        return self._not_implemented(
            request,
            'API-ASM-001',
            '/api/v1/assessments/worklist',
        )


class AssessmentsContractEndpoint002View(ContractNotImplementedView):
    @extend_schema(
        operation_id='contract_api_asm_002',
        summary='초기평가 시작',
        description='BrainOn final API contract scaffold. API ID: API-ASM-002. Contract endpoint: /api/v1/assessments. Role contract: NURSE.',
        tags=['assessments'],
        responses={
            501: OpenApiResponse(
                description="Not implemented",
            ),
        },
    )
    def post(self, request, *args, **kwargs):
        return self._not_implemented(
            request,
            'API-ASM-002',
            '/api/v1/assessments',
        )


class AssessmentsContractEndpoint003View(ContractNotImplementedView):
    @extend_schema(
        operation_id='contract_api_asm_003',
        summary='초기평가 상세·결과 조회',
        description='BrainOn final API contract scaffold. API ID: API-ASM-003. Contract endpoint: /api/v1/assessments/{assessment_id}. Role contract: NURSE/NEUROLOGIST.',
        tags=['assessments'],
        responses={
            501: OpenApiResponse(
                description="Not implemented",
            ),
        },
    )
    def get(self, request, *args, **kwargs):
        return self._not_implemented(
            request,
            'API-ASM-003',
            '/api/v1/assessments/{assessment_id}',
        )

    @extend_schema(
        operation_id='contract_api_asm_004',
        summary='초기평가 입력·임시저장',
        description='BrainOn final API contract scaffold. API ID: API-ASM-004. Contract endpoint: /api/v1/assessments/{assessment_id}. Role contract: NURSE.',
        tags=['assessments'],
        responses={
            501: OpenApiResponse(
                description="Not implemented",
            ),
        },
    )
    def patch(self, request, *args, **kwargs):
        return self._not_implemented(
            request,
            'API-ASM-004',
            '/api/v1/assessments/{assessment_id}',
        )


class AssessmentsContractEndpoint004View(ContractNotImplementedView):
    @extend_schema(
        operation_id='contract_api_asm_005',
        summary='초기평가 완료·담당 신경과 지정',
        description='BrainOn final API contract scaffold. API ID: API-ASM-005. Contract endpoint: /api/v1/assessments/{assessment_id}/complete. Role contract: NURSE.',
        tags=['assessments'],
        responses={
            501: OpenApiResponse(
                description="Not implemented",
            ),
        },
    )
    def post(self, request, *args, **kwargs):
        return self._not_implemented(
            request,
            'API-ASM-005',
            '/api/v1/assessments/{assessment_id}/complete',
        )


class AssessmentsContractEndpoint005View(ContractNotImplementedView):
    @extend_schema(
        operation_id='contract_api_asm_006',
        summary='신경과 긴급·응급 환자 목록 조회',
        description='BrainOn final API contract scaffold. API ID: API-ASM-006. Contract endpoint: /api/v1/neurology/emergency-worklist. Role contract: NEUROLOGIST.',
        tags=['assessments'],
        responses={
            501: OpenApiResponse(
                description="Not implemented",
            ),
        },
    )
    def get(self, request, *args, **kwargs):
        return self._not_implemented(
            request,
            'API-ASM-006',
            '/api/v1/neurology/emergency-worklist',
        )


class AssessmentsContractEndpoint006View(ContractNotImplementedView):
    @extend_schema(
        operation_id='contract_api_evt_001',
        summary='응급 알림 확인 처리(Acknowledge)',
        description='BrainOn final API contract scaffold. API ID: API-EVT-001. Contract endpoint: /api/v1/emergency-events/{event_id}/acknowledge. Role contract: NEUROLOGIST.',
        tags=['assessments'],
        responses={
            501: OpenApiResponse(
                description="Not implemented",
            ),
        },
    )
    def post(self, request, *args, **kwargs):
        return self._not_implemented(
            request,
            'API-EVT-001',
            '/api/v1/emergency-events/{event_id}/acknowledge',
        )


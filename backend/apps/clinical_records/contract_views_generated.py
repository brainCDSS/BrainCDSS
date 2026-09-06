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


class ClinicalRecordsContractEndpoint001View(ContractNotImplementedView):
    @extend_schema(
        operation_id='contract_api_enc_001',
        summary='Encounter 등록',
        description='BrainOn final API contract scaffold. API ID: API-ENC-001. Contract endpoint: /api/v1/encounters. Role contract: NURSE.',
        tags=['clinical_records'],
        responses={
            501: OpenApiResponse(
                description="Not implemented",
            ),
        },
    )
    def post(self, request, *args, **kwargs):
        return self._not_implemented(
            request,
            'API-ENC-001',
            '/api/v1/encounters',
        )


class ClinicalRecordsContractEndpoint002View(ContractNotImplementedView):
    @extend_schema(
        operation_id='contract_api_enc_002',
        summary='Encounter 진료 시작',
        description='BrainOn final API contract scaffold. API ID: API-ENC-002. Contract endpoint: /api/v1/encounters/{encounter_id}/start. Role contract: NURSE/NEUROLOGIST/NEUROSURGEON.',
        tags=['clinical_records'],
        responses={
            501: OpenApiResponse(
                description="Not implemented",
            ),
        },
    )
    def post(self, request, *args, **kwargs):
        return self._not_implemented(
            request,
            'API-ENC-002',
            '/api/v1/encounters/{encounter_id}/start',
        )


class ClinicalRecordsContractEndpoint003View(ContractNotImplementedView):
    @extend_schema(
        operation_id='contract_api_enc_003',
        summary='Encounter 진료 완료',
        description='BrainOn final API contract scaffold. API ID: API-ENC-003. Contract endpoint: /api/v1/encounters/{encounter_id}/complete. Role contract: NURSE/NEUROLOGIST/NEUROSURGEON.',
        tags=['clinical_records'],
        responses={
            501: OpenApiResponse(
                description="Not implemented",
            ),
        },
    )
    def post(self, request, *args, **kwargs):
        return self._not_implemented(
            request,
            'API-ENC-003',
            '/api/v1/encounters/{encounter_id}/complete',
        )


class ClinicalRecordsContractEndpoint004View(ContractNotImplementedView):
    @extend_schema(
        operation_id='contract_api_enc_004',
        summary='Encounter 취소',
        description='BrainOn final API contract scaffold. API ID: API-ENC-004. Contract endpoint: /api/v1/encounters/{encounter_id}/cancel. Role contract: NURSE/NEUROLOGIST/NEUROSURGEON.',
        tags=['clinical_records'],
        responses={
            501: OpenApiResponse(
                description="Not implemented",
            ),
        },
    )
    def post(self, request, *args, **kwargs):
        return self._not_implemented(
            request,
            'API-ENC-004',
            '/api/v1/encounters/{encounter_id}/cancel',
        )


class ClinicalRecordsContractEndpoint005View(ContractNotImplementedView):
    @extend_schema(
        operation_id='contract_api_note_002',
        summary='진료기록/임상소견 목록 조회',
        description='BrainOn final API contract scaffold. API ID: API-NOTE-002. Contract endpoint: /api/v1/clinical-notes. Role contract: NEUROLOGIST.',
        tags=['clinical_records'],
        responses={
            501: OpenApiResponse(
                description="Not implemented",
            ),
        },
    )
    def get(self, request, *args, **kwargs):
        return self._not_implemented(
            request,
            'API-NOTE-002',
            '/api/v1/clinical-notes',
        )

    @extend_schema(
        operation_id='contract_api_note_001',
        summary='의사 SOAP/진료기록 생성',
        description='BrainOn final API contract scaffold. API ID: API-NOTE-001. Contract endpoint: /api/v1/clinical-notes. Role contract: NEUROLOGIST.',
        tags=['clinical_records'],
        responses={
            501: OpenApiResponse(
                description="Not implemented",
            ),
        },
    )
    def post(self, request, *args, **kwargs):
        return self._not_implemented(
            request,
            'API-NOTE-001',
            '/api/v1/clinical-notes',
        )


class ClinicalRecordsContractEndpoint006View(ContractNotImplementedView):
    @extend_schema(
        operation_id='contract_api_note_003',
        summary='진료기록/임상소견 상세 조회',
        description='BrainOn final API contract scaffold. API ID: API-NOTE-003. Contract endpoint: /api/v1/clinical-notes/{note_id}. Role contract: NEUROLOGIST.',
        tags=['clinical_records'],
        responses={
            501: OpenApiResponse(
                description="Not implemented",
            ),
        },
    )
    def get(self, request, *args, **kwargs):
        return self._not_implemented(
            request,
            'API-NOTE-003',
            '/api/v1/clinical-notes/{note_id}',
        )

    @extend_schema(
        operation_id='contract_api_note_004',
        summary='SOAP/임상소견 수정·임시저장',
        description='BrainOn final API contract scaffold. API ID: API-NOTE-004. Contract endpoint: /api/v1/clinical-notes/{note_id}. Role contract: NEUROLOGIST.',
        tags=['clinical_records'],
        responses={
            501: OpenApiResponse(
                description="Not implemented",
            ),
        },
    )
    def patch(self, request, *args, **kwargs):
        return self._not_implemented(
            request,
            'API-NOTE-004',
            '/api/v1/clinical-notes/{note_id}',
        )


class ClinicalRecordsContractEndpoint007View(ContractNotImplementedView):
    @extend_schema(
        operation_id='contract_api_note_005',
        summary='통합 임상소견 최종 확정',
        description='BrainOn final API contract scaffold. API ID: API-NOTE-005. Contract endpoint: /api/v1/clinical-notes/{note_id}/finalize. Role contract: NEUROLOGIST.',
        tags=['clinical_records'],
        responses={
            501: OpenApiResponse(
                description="Not implemented",
            ),
        },
    )
    def post(self, request, *args, **kwargs):
        return self._not_implemented(
            request,
            'API-NOTE-005',
            '/api/v1/clinical-notes/{note_id}/finalize',
        )


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


class MedicationSafetyContractEndpoint001View(ContractNotImplementedView):
    @extend_schema(
        operation_id='contract_api_medsafe_001',
        summary='처방 안전성 검사',
        description='BrainOn final API contract scaffold. API ID: API-MEDSAFE-001. Contract endpoint: /api/v1/prescriptions/safety-check. Role contract: NEUROLOGIST/NEUROSURGEON.',
        tags=['medication_safety'],
        responses={
            501: OpenApiResponse(
                description="Not implemented",
            ),
        },
    )
    def post(self, request, *args, **kwargs):
        return self._not_implemented(
            request,
            'API-MEDSAFE-001',
            '/api/v1/prescriptions/safety-check',
        )


class MedicationSafetyContractEndpoint002View(ContractNotImplementedView):
    @extend_schema(
        operation_id='contract_api_allergy_001',
        summary='환자 알레르기 목록',
        description='BrainOn final API contract scaffold. API ID: API-ALLERGY-001. Contract endpoint: /api/v1/patients/{patient_id}/allergies. Role contract: NURSE/NEUROLOGIST/NEUROSURGEON.',
        tags=['medication_safety'],
        responses={
            501: OpenApiResponse(
                description="Not implemented",
            ),
        },
    )
    def get(self, request, *args, **kwargs):
        return self._not_implemented(
            request,
            'API-ALLERGY-001',
            '/api/v1/patients/{patient_id}/allergies',
        )

    @extend_schema(
        operation_id='contract_api_allergy_002',
        summary='환자 알레르기 등록',
        description='BrainOn final API contract scaffold. API ID: API-ALLERGY-002. Contract endpoint: /api/v1/patients/{patient_id}/allergies. Role contract: NURSE/NEUROLOGIST/NEUROSURGEON.',
        tags=['medication_safety'],
        responses={
            501: OpenApiResponse(
                description="Not implemented",
            ),
        },
    )
    def post(self, request, *args, **kwargs):
        return self._not_implemented(
            request,
            'API-ALLERGY-002',
            '/api/v1/patients/{patient_id}/allergies',
        )


class MedicationSafetyContractEndpoint003View(ContractNotImplementedView):
    @extend_schema(
        operation_id='contract_api_allergy_003',
        summary='환자 알레르기 비활성화',
        description='BrainOn final API contract scaffold. API ID: API-ALLERGY-003. Contract endpoint: /api/v1/patients/{patient_id}/allergies/{allergy_id}. Role contract: NURSE/NEUROLOGIST/NEUROSURGEON.',
        tags=['medication_safety'],
        responses={
            501: OpenApiResponse(
                description="Not implemented",
            ),
        },
    )
    def delete(self, request, *args, **kwargs):
        return self._not_implemented(
            request,
            'API-ALLERGY-003',
            '/api/v1/patients/{patient_id}/allergies/{allergy_id}',
        )


class MedicationSafetyContractEndpoint004View(ContractNotImplementedView):
    @extend_schema(
        operation_id='contract_api_dur_001',
        summary='DUR 수동 동기화 Trigger',
        description='BrainOn final API contract scaffold. API ID: API-DUR-001. Contract endpoint: /api/v1/admin/dur/sync. Role contract: SYSTEM_ADMIN.',
        tags=['medication_safety'],
        responses={
            501: OpenApiResponse(
                description="Not implemented",
            ),
        },
    )
    def post(self, request, *args, **kwargs):
        return self._not_implemented(
            request,
            'API-DUR-001',
            '/api/v1/admin/dur/sync',
        )


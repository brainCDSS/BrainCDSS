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


class PatientsContractEndpoint001View(ContractNotImplementedView):
    @extend_schema(
        operation_id='contract_api_pat_001',
        summary='환자 목록·검색',
        description='BrainOn final API contract scaffold. API ID: API-PAT-001. Contract endpoint: /api/v1/patients. Role contract: NURSE/NEUROLOGIST/NEUROSURGEON/RADIOLOGY.',
        tags=['patients'],
        responses={
            501: OpenApiResponse(
                description="Not implemented",
            ),
        },
    )
    def get(self, request, *args, **kwargs):
        return self._not_implemented(
            request,
            'API-PAT-001',
            '/api/v1/patients',
        )

    @extend_schema(
        operation_id='contract_api_pat_002',
        summary='환자 신규 등록',
        description='BrainOn final API contract scaffold. API ID: API-PAT-002. Contract endpoint: /api/v1/patients. Role contract: NURSE.',
        tags=['patients'],
        responses={
            501: OpenApiResponse(
                description="Not implemented",
            ),
        },
    )
    def post(self, request, *args, **kwargs):
        return self._not_implemented(
            request,
            'API-PAT-002',
            '/api/v1/patients',
        )


class PatientsContractEndpoint002View(ContractNotImplementedView):
    @extend_schema(
        operation_id='contract_api_pat_003',
        summary='신원미상 임시환자 등록',
        description='BrainOn final API contract scaffold. API ID: API-PAT-003. Contract endpoint: /api/v1/patients/temporary. Role contract: NURSE.',
        tags=['patients'],
        responses={
            501: OpenApiResponse(
                description="Not implemented",
            ),
        },
    )
    def post(self, request, *args, **kwargs):
        return self._not_implemented(
            request,
            'API-PAT-003',
            '/api/v1/patients/temporary',
        )


class PatientsContractEndpoint003View(ContractNotImplementedView):
    @extend_schema(
        operation_id='contract_api_pat_004',
        summary='환자 상세',
        description='BrainOn final API contract scaffold. API ID: API-PAT-004. Contract endpoint: /api/v1/patients/{patient_id}. Role contract: NURSE/NEUROLOGIST/NEUROSURGEON/RADIOLOGY.',
        tags=['patients'],
        responses={
            501: OpenApiResponse(
                description="Not implemented",
            ),
        },
    )
    def get(self, request, *args, **kwargs):
        return self._not_implemented(
            request,
            'API-PAT-004',
            '/api/v1/patients/{patient_id}',
        )

    @extend_schema(
        operation_id='contract_api_pat_005',
        summary='환자 기본정보 수정',
        description='BrainOn final API contract scaffold. API ID: API-PAT-005. Contract endpoint: /api/v1/patients/{patient_id}. Role contract: NURSE.',
        tags=['patients'],
        responses={
            501: OpenApiResponse(
                description="Not implemented",
            ),
        },
    )
    def patch(self, request, *args, **kwargs):
        return self._not_implemented(
            request,
            'API-PAT-005',
            '/api/v1/patients/{patient_id}',
        )


class PatientsContractEndpoint004View(ContractNotImplementedView):
    @extend_schema(
        operation_id='contract_api_pat_006',
        summary='임시환자 병합',
        description='BrainOn final API contract scaffold. API ID: API-PAT-006. Contract endpoint: /api/v1/patients/{temp_patient_id}/merge. Role contract: NURSE.',
        tags=['patients'],
        responses={
            501: OpenApiResponse(
                description="Not implemented",
            ),
        },
    )
    def post(self, request, *args, **kwargs):
        return self._not_implemented(
            request,
            'API-PAT-006',
            '/api/v1/patients/{temp_patient_id}/merge',
        )


class PatientsContractEndpoint005View(ContractNotImplementedView):
    @extend_schema(
        operation_id='contract_api_pat_007',
        summary='임시환자 신원확정',
        description='BrainOn final API contract scaffold. API ID: API-PAT-007. Contract endpoint: /api/v1/patients/{patient_id}/identify. Role contract: NURSE.',
        tags=['patients'],
        responses={
            501: OpenApiResponse(
                description="Not implemented",
            ),
        },
    )
    def post(self, request, *args, **kwargs):
        return self._not_implemented(
            request,
            'API-PAT-007',
            '/api/v1/patients/{patient_id}/identify',
        )


class PatientsContractEndpoint006View(ContractNotImplementedView):
    @extend_schema(
        operation_id='contract_api_fav_001',
        summary='찜 병원 목록',
        description='BrainOn final API contract scaffold. API ID: API-FAV-001. Contract endpoint: /api/v1/me/favorite-hospitals. Role contract: PATIENT.',
        tags=['patients'],
        responses={
            501: OpenApiResponse(
                description="Not implemented",
            ),
        },
    )
    def get(self, request, *args, **kwargs):
        return self._not_implemented(
            request,
            'API-FAV-001',
            '/api/v1/me/favorite-hospitals',
        )


class PatientsContractEndpoint007View(ContractNotImplementedView):
    @extend_schema(
        operation_id='contract_api_fav_003',
        summary='병원 찜 해제',
        description='BrainOn final API contract scaffold. API ID: API-FAV-003. Contract endpoint: /api/v1/me/favorite-hospitals/{hospital_id}. Role contract: PATIENT.',
        tags=['patients'],
        responses={
            501: OpenApiResponse(
                description="Not implemented",
            ),
        },
    )
    def delete(self, request, *args, **kwargs):
        return self._not_implemented(
            request,
            'API-FAV-003',
            '/api/v1/me/favorite-hospitals/{hospital_id}',
        )

    @extend_schema(
        operation_id='contract_api_fav_002',
        summary='병원 찜 추가',
        description='BrainOn final API contract scaffold. API ID: API-FAV-002. Contract endpoint: /api/v1/me/favorite-hospitals/{hospital_id}. Role contract: PATIENT.',
        tags=['patients'],
        responses={
            501: OpenApiResponse(
                description="Not implemented",
            ),
        },
    )
    def put(self, request, *args, **kwargs):
        return self._not_implemented(
            request,
            'API-FAV-002',
            '/api/v1/me/favorite-hospitals/{hospital_id}',
        )


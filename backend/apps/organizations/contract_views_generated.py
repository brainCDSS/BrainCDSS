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


class OrganizationsContractEndpoint001View(ContractNotImplementedView):
    @extend_schema(
        operation_id='contract_api_ref_001',
        summary='병원 목록·검색',
        description='BrainOn final API contract scaffold. API ID: API-REF-001. Contract endpoint: /api/v1/hospitals. Role contract: PATIENT/로그인 사용자.',
        tags=['organizations'],
        responses={
            501: OpenApiResponse(
                description="Not implemented",
            ),
        },
    )
    def get(self, request, *args, **kwargs):
        return self._not_implemented(
            request,
            'API-REF-001',
            '/api/v1/hospitals',
        )


class OrganizationsContractEndpoint002View(ContractNotImplementedView):
    @extend_schema(
        operation_id='contract_api_ref_002',
        summary='병원 상세',
        description='BrainOn final API contract scaffold. API ID: API-REF-002. Contract endpoint: /api/v1/hospitals/{hospital_id}. Role contract: PATIENT/로그인 사용자.',
        tags=['organizations'],
        responses={
            501: OpenApiResponse(
                description="Not implemented",
            ),
        },
    )
    def get(self, request, *args, **kwargs):
        return self._not_implemented(
            request,
            'API-REF-002',
            '/api/v1/hospitals/{hospital_id}',
        )


class OrganizationsContractEndpoint003View(ContractNotImplementedView):
    @extend_schema(
        operation_id='contract_api_ref_003',
        summary='병원별 진료과',
        description='BrainOn final API contract scaffold. API ID: API-REF-003. Contract endpoint: /api/v1/hospitals/{hospital_id}/departments. Role contract: PATIENT.',
        tags=['organizations'],
        responses={
            501: OpenApiResponse(
                description="Not implemented",
            ),
        },
    )
    def get(self, request, *args, **kwargs):
        return self._not_implemented(
            request,
            'API-REF-003',
            '/api/v1/hospitals/{hospital_id}/departments',
        )


class OrganizationsContractEndpoint004View(ContractNotImplementedView):
    @extend_schema(
        operation_id='contract_api_ref_004',
        summary='진료과별 의사',
        description='BrainOn final API contract scaffold. API ID: API-REF-004. Contract endpoint: /api/v1/departments/{department_id}/clinicians. Role contract: PATIENT.',
        tags=['organizations'],
        responses={
            501: OpenApiResponse(
                description="Not implemented",
            ),
        },
    )
    def get(self, request, *args, **kwargs):
        return self._not_implemented(
            request,
            'API-REF-004',
            '/api/v1/departments/{department_id}/clinicians',
        )


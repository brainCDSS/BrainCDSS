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


class RadiologyContractEndpoint001View(ContractNotImplementedView):
    @extend_schema(
        operation_id='contract_api_rad_001',
        summary='영상의학과 판독 Worklist 조회',
        description='BrainOn final API contract scaffold. API ID: API-RAD-001. Contract endpoint: /api/v1/radiology/worklist. Role contract: RADIOLOGY.',
        tags=['radiology'],
        responses={
            501: OpenApiResponse(
                description="Not implemented",
            ),
        },
    )
    def get(self, request, *args, **kwargs):
        return self._not_implemented(
            request,
            'API-RAD-001',
            '/api/v1/radiology/worklist',
        )


class RadiologyContractEndpoint002View(ContractNotImplementedView):
    @extend_schema(
        operation_id='contract_api_rad_002',
        summary='판독 Draft 생성',
        description='BrainOn final API contract scaffold. API ID: API-RAD-002. Contract endpoint: /api/v1/radiology-reports. Role contract: RADIOLOGY.',
        tags=['radiology'],
        responses={
            501: OpenApiResponse(
                description="Not implemented",
            ),
        },
    )
    def post(self, request, *args, **kwargs):
        return self._not_implemented(
            request,
            'API-RAD-002',
            '/api/v1/radiology-reports',
        )


class RadiologyContractEndpoint003View(ContractNotImplementedView):
    @extend_schema(
        operation_id='contract_api_rad_003',
        summary='판독문 상세 조회',
        description='BrainOn final API contract scaffold. API ID: API-RAD-003. Contract endpoint: /api/v1/radiology-reports/{report_id}. Role contract: NURSE/NEUROLOGIST/NEUROSURGEON/RADIOLOGY.',
        tags=['radiology'],
        responses={
            501: OpenApiResponse(
                description="Not implemented",
            ),
        },
    )
    def get(self, request, *args, **kwargs):
        return self._not_implemented(
            request,
            'API-RAD-003',
            '/api/v1/radiology-reports/{report_id}',
        )

    @extend_schema(
        operation_id='contract_api_rad_004',
        summary='판독 Draft/예비판독 수정',
        description='BrainOn final API contract scaffold. API ID: API-RAD-004. Contract endpoint: /api/v1/radiology-reports/{report_id}. Role contract: RADIOLOGY.',
        tags=['radiology'],
        responses={
            501: OpenApiResponse(
                description="Not implemented",
            ),
        },
    )
    def patch(self, request, *args, **kwargs):
        return self._not_implemented(
            request,
            'API-RAD-004',
            '/api/v1/radiology-reports/{report_id}',
        )


class RadiologyContractEndpoint004View(ContractNotImplementedView):
    @extend_schema(
        operation_id='contract_api_rad_005',
        summary='예비판독 확정',
        description='BrainOn final API contract scaffold. API ID: API-RAD-005. Contract endpoint: /api/v1/radiology-reports/{report_id}/submit-preliminary. Role contract: RADIOLOGY.',
        tags=['radiology'],
        responses={
            501: OpenApiResponse(
                description="Not implemented",
            ),
        },
    )
    def post(self, request, *args, **kwargs):
        return self._not_implemented(
            request,
            'API-RAD-005',
            '/api/v1/radiology-reports/{report_id}/submit-preliminary',
        )


class RadiologyContractEndpoint005View(ContractNotImplementedView):
    @extend_schema(
        operation_id='contract_api_rad_006',
        summary='최종판독 확정',
        description='BrainOn final API contract scaffold. API ID: API-RAD-006. Contract endpoint: /api/v1/radiology-reports/{report_id}/finalize. Role contract: RADIOLOGY.',
        tags=['radiology'],
        responses={
            501: OpenApiResponse(
                description="Not implemented",
            ),
        },
    )
    def post(self, request, *args, **kwargs):
        return self._not_implemented(
            request,
            'API-RAD-006',
            '/api/v1/radiology-reports/{report_id}/finalize',
        )


class RadiologyContractEndpoint006View(ContractNotImplementedView):
    @extend_schema(
        operation_id='contract_api_rad_007',
        summary='최종판독 정정(Amend)',
        description='BrainOn final API contract scaffold. API ID: API-RAD-007. Contract endpoint: /api/v1/radiology-reports/{report_id}/amend. Role contract: RADIOLOGY.',
        tags=['radiology'],
        responses={
            501: OpenApiResponse(
                description="Not implemented",
            ),
        },
    )
    def post(self, request, *args, **kwargs):
        return self._not_implemented(
            request,
            'API-RAD-007',
            '/api/v1/radiology-reports/{report_id}/amend',
        )


class RadiologyContractEndpoint007View(ContractNotImplementedView):
    @extend_schema(
        operation_id='contract_api_rad_008',
        summary='판독문 수정 이력 조회',
        description='BrainOn final API contract scaffold. API ID: API-RAD-008. Contract endpoint: /api/v1/radiology-reports/{report_id}/revisions. Role contract: RADIOLOGY.',
        tags=['radiology'],
        responses={
            501: OpenApiResponse(
                description="Not implemented",
            ),
        },
    )
    def get(self, request, *args, **kwargs):
        return self._not_implemented(
            request,
            'API-RAD-008',
            '/api/v1/radiology-reports/{report_id}/revisions',
        )


class RadiologyContractEndpoint008View(ContractNotImplementedView):
    @extend_schema(
        operation_id='contract_api_rad_010',
        summary='의료진 측정값 조회',
        description='BrainOn final API contract scaffold. API ID: API-RAD-010. Contract endpoint: /api/v1/radiology-reports/{report_id}/measurements. Role contract: NURSE/NEUROLOGIST/NEUROSURGEON/RADIOLOGY.',
        tags=['radiology'],
        responses={
            501: OpenApiResponse(
                description="Not implemented",
            ),
        },
    )
    def get(self, request, *args, **kwargs):
        return self._not_implemented(
            request,
            'API-RAD-010',
            '/api/v1/radiology-reports/{report_id}/measurements',
        )

    @extend_schema(
        operation_id='contract_api_rad_009',
        summary='의료진 측정값 등록',
        description='BrainOn final API contract scaffold. API ID: API-RAD-009. Contract endpoint: /api/v1/radiology-reports/{report_id}/measurements. Role contract: RADIOLOGY.',
        tags=['radiology'],
        responses={
            501: OpenApiResponse(
                description="Not implemented",
            ),
        },
    )
    def post(self, request, *args, **kwargs):
        return self._not_implemented(
            request,
            'API-RAD-009',
            '/api/v1/radiology-reports/{report_id}/measurements',
        )


class RadiologyContractEndpoint009View(ContractNotImplementedView):
    @extend_schema(
        operation_id='contract_api_rad_011',
        summary='판독 Draft/예비판독 취소',
        description='BrainOn final API contract scaffold. API ID: API-RAD-011. Contract endpoint: /api/v1/radiology-reports/{report_id}/cancel. Role contract: RADIOLOGY.',
        tags=['radiology'],
        responses={
            501: OpenApiResponse(
                description="Not implemented",
            ),
        },
    )
    def post(self, request, *args, **kwargs):
        return self._not_implemented(
            request,
            'API-RAD-011',
            '/api/v1/radiology-reports/{report_id}/cancel',
        )


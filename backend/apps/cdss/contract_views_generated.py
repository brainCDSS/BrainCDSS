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


class CdssContractEndpoint001View(ContractNotImplementedView):
    @extend_schema(
        operation_id='contract_api_cds_001',
        summary='CDS Service Discovery',
        description='BrainOn final API contract scaffold. API ID: API-CDS-001. Contract endpoint: /cds-services. Role contract: SERVICE_SCOPE: cds.discovery.read.',
        tags=['cdss'],
        responses={
            501: OpenApiResponse(
                description="Not implemented",
            ),
        },
    )
    def get(self, request, *args, **kwargs):
        return self._not_implemented(
            request,
            'API-CDS-001',
            '/cds-services',
        )


class CdssContractEndpoint002View(ContractNotImplementedView):
    @extend_schema(
        operation_id='contract_api_cds_002',
        summary='Medication Safety order-select',
        description='BrainOn final API contract scaffold. API ID: API-CDS-002. Contract endpoint: /cds-services/medication-safety-order-select. Role contract: SERVICE_SCOPE: cds.medication-safety.invoke (context.userId=NEUROLOGIST/NEUROSURGEON).',
        tags=['cdss'],
        responses={
            501: OpenApiResponse(
                description="Not implemented",
            ),
        },
    )
    def post(self, request, *args, **kwargs):
        return self._not_implemented(
            request,
            'API-CDS-002',
            '/cds-services/medication-safety-order-select',
        )


class CdssContractEndpoint003View(ContractNotImplementedView):
    @extend_schema(
        operation_id='contract_api_cds_003',
        summary='Medication Safety order-sign',
        description='BrainOn final API contract scaffold. API ID: API-CDS-003. Contract endpoint: /cds-services/medication-safety-order-sign. Role contract: SERVICE_SCOPE: cds.medication-safety.invoke (context.userId=NEUROLOGIST/NEUROSURGEON).',
        tags=['cdss'],
        responses={
            501: OpenApiResponse(
                description="Not implemented",
            ),
        },
    )
    def post(self, request, *args, **kwargs):
        return self._not_implemented(
            request,
            'API-CDS-003',
            '/cds-services/medication-safety-order-sign',
        )


class CdssContractEndpoint004View(ContractNotImplementedView):
    @extend_schema(
        operation_id='contract_api_cds_004',
        summary='뇌졸중 Patient View CDS 호출',
        description='BrainOn final API contract scaffold. API ID: API-CDS-004. Contract endpoint: /cds-services/stroke-patient-view. Role contract: SERVICE_SCOPE: cds.stroke.invoke (context.userId 임상 Role 검증).',
        tags=['cdss'],
        responses={
            501: OpenApiResponse(
                description="Not implemented",
            ),
        },
    )
    def post(self, request, *args, **kwargs):
        return self._not_implemented(
            request,
            'API-CDS-004',
            '/cds-services/stroke-patient-view',
        )


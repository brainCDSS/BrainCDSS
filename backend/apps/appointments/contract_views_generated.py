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


class AppointmentsContractEndpoint001View(ContractNotImplementedView):
    @extend_schema(
        operation_id='contract_api_sch_001',
        summary='의사 진료일정 조회',
        description='BrainOn final API contract scaffold. API ID: API-SCH-001. Contract endpoint: /api/v1/clinicians/{clinician_id}/schedule. Role contract: PATIENT/NURSE/NEUROLOGIST/NEUROSURGEON/RADIOLOGY.',
        tags=['appointments'],
        responses={
            501: OpenApiResponse(
                description="Not implemented",
            ),
        },
    )
    def get(self, request, *args, **kwargs):
        return self._not_implemented(
            request,
            'API-SCH-001',
            '/api/v1/clinicians/{clinician_id}/schedule',
        )

    @extend_schema(
        operation_id='contract_api_sch_002',
        summary='의사 진료일정 저장',
        description='BrainOn final API contract scaffold. API ID: API-SCH-002. Contract endpoint: /api/v1/clinicians/{clinician_id}/schedule. Role contract: NURSE/NEUROLOGIST/NEUROSURGEON/RADIOLOGY.',
        tags=['appointments'],
        responses={
            501: OpenApiResponse(
                description="Not implemented",
            ),
        },
    )
    def put(self, request, *args, **kwargs):
        return self._not_implemented(
            request,
            'API-SCH-002',
            '/api/v1/clinicians/{clinician_id}/schedule',
        )


class AppointmentsContractEndpoint002View(ContractNotImplementedView):
    @extend_schema(
        operation_id='contract_api_slot_001',
        summary='예약 가능 Slot 조회',
        description='BrainOn final API contract scaffold. API ID: API-SLOT-001. Contract endpoint: /api/v1/clinicians/{clinician_id}/slots. Role contract: PATIENT.',
        tags=['appointments'],
        responses={
            501: OpenApiResponse(
                description="Not implemented",
            ),
        },
    )
    def get(self, request, *args, **kwargs):
        return self._not_implemented(
            request,
            'API-SLOT-001',
            '/api/v1/clinicians/{clinician_id}/slots',
        )


class AppointmentsContractEndpoint003View(ContractNotImplementedView):
    @extend_schema(
        operation_id='contract_api_slot_002',
        summary='Slot 차단',
        description='BrainOn final API contract scaffold. API ID: API-SLOT-002. Contract endpoint: /api/v1/slots/{slot_id}/block. Role contract: NURSE/NEUROLOGIST/NEUROSURGEON/RADIOLOGY.',
        tags=['appointments'],
        responses={
            501: OpenApiResponse(
                description="Not implemented",
            ),
        },
    )
    def post(self, request, *args, **kwargs):
        return self._not_implemented(
            request,
            'API-SLOT-002',
            '/api/v1/slots/{slot_id}/block',
        )


class AppointmentsContractEndpoint004View(ContractNotImplementedView):
    @extend_schema(
        operation_id='contract_api_slot_003',
        summary='Slot 차단 해제',
        description='BrainOn final API contract scaffold. API ID: API-SLOT-003. Contract endpoint: /api/v1/slots/{slot_id}/unblock. Role contract: NURSE/NEUROLOGIST/NEUROSURGEON/RADIOLOGY.',
        tags=['appointments'],
        responses={
            501: OpenApiResponse(
                description="Not implemented",
            ),
        },
    )
    def post(self, request, *args, **kwargs):
        return self._not_implemented(
            request,
            'API-SLOT-003',
            '/api/v1/slots/{slot_id}/unblock',
        )


class AppointmentsContractEndpoint005View(ContractNotImplementedView):
    @extend_schema(
        operation_id='contract_api_app_002',
        summary='내 예약 목록',
        description='BrainOn final API contract scaffold. API ID: API-APP-002. Contract endpoint: /api/v1/appointments. Role contract: PATIENT.',
        tags=['appointments'],
        responses={
            501: OpenApiResponse(
                description="Not implemented",
            ),
        },
    )
    def get(self, request, *args, **kwargs):
        return self._not_implemented(
            request,
            'API-APP-002',
            '/api/v1/appointments',
        )

    @extend_schema(
        operation_id='contract_api_app_001',
        summary='예약 요청 생성',
        description='BrainOn final API contract scaffold. API ID: API-APP-001. Contract endpoint: /api/v1/appointments. Role contract: PATIENT.',
        tags=['appointments'],
        responses={
            501: OpenApiResponse(
                description="Not implemented",
            ),
        },
    )
    def post(self, request, *args, **kwargs):
        return self._not_implemented(
            request,
            'API-APP-001',
            '/api/v1/appointments',
        )


class AppointmentsContractEndpoint006View(ContractNotImplementedView):
    @extend_schema(
        operation_id='contract_api_app_003',
        summary='예약 상세',
        description='BrainOn final API contract scaffold. API ID: API-APP-003. Contract endpoint: /api/v1/appointments/{appointment_id}. Role contract: PATIENT/NURSE/NEUROLOGIST/NEUROSURGEON/RADIOLOGY.',
        tags=['appointments'],
        responses={
            501: OpenApiResponse(
                description="Not implemented",
            ),
        },
    )
    def get(self, request, *args, **kwargs):
        return self._not_implemented(
            request,
            'API-APP-003',
            '/api/v1/appointments/{appointment_id}',
        )


class AppointmentsContractEndpoint007View(ContractNotImplementedView):
    @extend_schema(
        operation_id='contract_api_app_004',
        summary='예약 변경 요청',
        description='BrainOn final API contract scaffold. API ID: API-APP-004. Contract endpoint: /api/v1/appointments/{appointment_id}/reschedule. Role contract: PATIENT.',
        tags=['appointments'],
        responses={
            501: OpenApiResponse(
                description="Not implemented",
            ),
        },
    )
    def patch(self, request, *args, **kwargs):
        return self._not_implemented(
            request,
            'API-APP-004',
            '/api/v1/appointments/{appointment_id}/reschedule',
        )


class AppointmentsContractEndpoint008View(ContractNotImplementedView):
    @extend_schema(
        operation_id='contract_api_app_005',
        summary='예약 취소',
        description='BrainOn final API contract scaffold. API ID: API-APP-005. Contract endpoint: /api/v1/appointments/{appointment_id}/cancel. Role contract: PATIENT.',
        tags=['appointments'],
        responses={
            501: OpenApiResponse(
                description="Not implemented",
            ),
        },
    )
    def post(self, request, *args, **kwargs):
        return self._not_implemented(
            request,
            'API-APP-005',
            '/api/v1/appointments/{appointment_id}/cancel',
        )


class AppointmentsContractEndpoint009View(ContractNotImplementedView):
    @extend_schema(
        operation_id='contract_api_app_006',
        summary='승인 대기 예약 목록',
        description='BrainOn final API contract scaffold. API ID: API-APP-006. Contract endpoint: /api/v1/nurse/appointments/requests. Role contract: NURSE/NEUROLOGIST/NEUROSURGEON/RADIOLOGY.',
        tags=['appointments'],
        responses={
            501: OpenApiResponse(
                description="Not implemented",
            ),
        },
    )
    def get(self, request, *args, **kwargs):
        return self._not_implemented(
            request,
            'API-APP-006',
            '/api/v1/nurse/appointments/requests',
        )


class AppointmentsContractEndpoint010View(ContractNotImplementedView):
    @extend_schema(
        operation_id='contract_api_app_007',
        summary='예약 수락',
        description='BrainOn final API contract scaffold. API ID: API-APP-007. Contract endpoint: /api/v1/appointments/{appointment_id}/accept. Role contract: NURSE.',
        tags=['appointments'],
        responses={
            501: OpenApiResponse(
                description="Not implemented",
            ),
        },
    )
    def post(self, request, *args, **kwargs):
        return self._not_implemented(
            request,
            'API-APP-007',
            '/api/v1/appointments/{appointment_id}/accept',
        )


class AppointmentsContractEndpoint011View(ContractNotImplementedView):
    @extend_schema(
        operation_id='contract_api_app_008',
        summary='예약 거절',
        description='BrainOn final API contract scaffold. API ID: API-APP-008. Contract endpoint: /api/v1/appointments/{appointment_id}/reject. Role contract: NURSE.',
        tags=['appointments'],
        responses={
            501: OpenApiResponse(
                description="Not implemented",
            ),
        },
    )
    def post(self, request, *args, **kwargs):
        return self._not_implemented(
            request,
            'API-APP-008',
            '/api/v1/appointments/{appointment_id}/reject',
        )


class AppointmentsContractEndpoint012View(ContractNotImplementedView):
    @extend_schema(
        operation_id='contract_api_app_009',
        summary='의료진 예약 일정',
        description='BrainOn final API contract scaffold. API ID: API-APP-009. Contract endpoint: /api/v1/staff/appointments. Role contract: NURSE/NEUROLOGIST/NEUROSURGEON/RADIOLOGY.',
        tags=['appointments'],
        responses={
            501: OpenApiResponse(
                description="Not implemented",
            ),
        },
    )
    def get(self, request, *args, **kwargs):
        return self._not_implemented(
            request,
            'API-APP-009',
            '/api/v1/staff/appointments',
        )


class AppointmentsContractEndpoint013View(ContractNotImplementedView):
    @extend_schema(
        operation_id='contract_api_app_010',
        summary='예약 진료 완료',
        description='BrainOn final API contract scaffold. API ID: API-APP-010. Contract endpoint: /api/v1/appointments/{appointment_id}/complete. Role contract: NURSE/NEUROLOGIST/NEUROSURGEON.',
        tags=['appointments'],
        responses={
            501: OpenApiResponse(
                description="Not implemented",
            ),
        },
    )
    def post(self, request, *args, **kwargs):
        return self._not_implemented(
            request,
            'API-APP-010',
            '/api/v1/appointments/{appointment_id}/complete',
        )


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


class NotificationsContractEndpoint001View(ContractNotImplementedView):
    @extend_schema(
        operation_id='contract_api_noti_001',
        summary='알림 목록',
        description='BrainOn final API contract scaffold. API ID: API-NOTI-001. Contract endpoint: /api/v1/notifications. Role contract: PATIENT/NURSE/NEUROLOGIST/NEUROSURGEON/RADIOLOGY/SYSTEM_ADMIN.',
        tags=['notifications'],
        responses={
            501: OpenApiResponse(
                description="Not implemented",
            ),
        },
    )
    def get(self, request, *args, **kwargs):
        return self._not_implemented(
            request,
            'API-NOTI-001',
            '/api/v1/notifications',
        )


class NotificationsContractEndpoint002View(ContractNotImplementedView):
    @extend_schema(
        operation_id='contract_api_noti_002',
        summary='알림 읽음',
        description='BrainOn final API contract scaffold. API ID: API-NOTI-002. Contract endpoint: /api/v1/notifications/{notification_id}/read. Role contract: PATIENT/NURSE/NEUROLOGIST/NEUROSURGEON/RADIOLOGY/SYSTEM_ADMIN.',
        tags=['notifications'],
        responses={
            501: OpenApiResponse(
                description="Not implemented",
            ),
        },
    )
    def patch(self, request, *args, **kwargs):
        return self._not_implemented(
            request,
            'API-NOTI-002',
            '/api/v1/notifications/{notification_id}/read',
        )


class NotificationsContractEndpoint003View(ContractNotImplementedView):
    @extend_schema(
        operation_id='contract_api_noti_003',
        summary='알림 설정 조회',
        description='BrainOn final API contract scaffold. API ID: API-NOTI-003. Contract endpoint: /api/v1/notification-preferences. Role contract: PATIENT/NURSE/NEUROLOGIST/NEUROSURGEON/RADIOLOGY/SYSTEM_ADMIN.',
        tags=['notifications'],
        responses={
            501: OpenApiResponse(
                description="Not implemented",
            ),
        },
    )
    def get(self, request, *args, **kwargs):
        return self._not_implemented(
            request,
            'API-NOTI-003',
            '/api/v1/notification-preferences',
        )

    @extend_schema(
        operation_id='contract_api_noti_004',
        summary='알림 설정 변경',
        description='BrainOn final API contract scaffold. API ID: API-NOTI-004. Contract endpoint: /api/v1/notification-preferences. Role contract: PATIENT/NURSE/NEUROLOGIST/NEUROSURGEON/RADIOLOGY/SYSTEM_ADMIN.',
        tags=['notifications'],
        responses={
            501: OpenApiResponse(
                description="Not implemented",
            ),
        },
    )
    def patch(self, request, *args, **kwargs):
        return self._not_implemented(
            request,
            'API-NOTI-004',
            '/api/v1/notification-preferences',
        )


class NotificationsContractEndpoint004View(ContractNotImplementedView):
    @extend_schema(
        operation_id='contract_api_fcm_001',
        summary='FCM Token 등록/갱신',
        description='BrainOn final API contract scaffold. API ID: API-FCM-001. Contract endpoint: /api/v1/devices/fcm-tokens. Role contract: PATIENT/NURSE/NEUROLOGIST/NEUROSURGEON/RADIOLOGY/SYSTEM_ADMIN.',
        tags=['notifications'],
        responses={
            501: OpenApiResponse(
                description="Not implemented",
            ),
        },
    )
    def post(self, request, *args, **kwargs):
        return self._not_implemented(
            request,
            'API-FCM-001',
            '/api/v1/devices/fcm-tokens',
        )


class NotificationsContractEndpoint005View(ContractNotImplementedView):
    @extend_schema(
        operation_id='contract_api_fcm_002',
        summary='FCM Token 비활성/삭제',
        description='BrainOn final API contract scaffold. API ID: API-FCM-002. Contract endpoint: /api/v1/devices/fcm-tokens/{token_id}. Role contract: PATIENT/NURSE/NEUROLOGIST/NEUROSURGEON/RADIOLOGY/SYSTEM_ADMIN.',
        tags=['notifications'],
        responses={
            501: OpenApiResponse(
                description="Not implemented",
            ),
        },
    )
    def delete(self, request, *args, **kwargs):
        return self._not_implemented(
            request,
            'API-FCM-002',
            '/api/v1/devices/fcm-tokens/{token_id}',
        )


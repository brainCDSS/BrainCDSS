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


class AccountsContractEndpoint001View(ContractNotImplementedView):
    @extend_schema(
        operation_id='contract_api_auth_001',
        summary='로그인',
        description='BrainOn final API contract scaffold. API ID: API-AUTH-001. Contract endpoint: /api/v1/auth/login. Role contract: 전체.',
        tags=['accounts'],
        responses={
            501: OpenApiResponse(
                description="Not implemented",
            ),
        },
    )
    def post(self, request, *args, **kwargs):
        return self._not_implemented(
            request,
            'API-AUTH-001',
            '/api/v1/auth/login',
        )


class AccountsContractEndpoint002View(ContractNotImplementedView):
    @extend_schema(
        operation_id='contract_api_auth_002',
        summary='Access Token 재발급',
        description='BrainOn final API contract scaffold. API ID: API-AUTH-002. Contract endpoint: /api/v1/auth/refresh. Role contract: 전체.',
        tags=['accounts'],
        responses={
            501: OpenApiResponse(
                description="Not implemented",
            ),
        },
    )
    def post(self, request, *args, **kwargs):
        return self._not_implemented(
            request,
            'API-AUTH-002',
            '/api/v1/auth/refresh',
        )


class AccountsContractEndpoint003View(ContractNotImplementedView):
    @extend_schema(
        operation_id='contract_api_auth_003',
        summary='로그아웃',
        description='BrainOn final API contract scaffold. API ID: API-AUTH-003. Contract endpoint: /api/v1/auth/logout. Role contract: 로그인 사용자.',
        tags=['accounts'],
        responses={
            501: OpenApiResponse(
                description="Not implemented",
            ),
        },
    )
    def post(self, request, *args, **kwargs):
        return self._not_implemented(
            request,
            'API-AUTH-003',
            '/api/v1/auth/logout',
        )


class AccountsContractEndpoint004View(ContractNotImplementedView):
    @extend_schema(
        operation_id='contract_api_auth_004',
        summary='비밀번호 변경',
        description='BrainOn final API contract scaffold. API ID: API-AUTH-004. Contract endpoint: /api/v1/auth/password. Role contract: 로그인 사용자.',
        tags=['accounts'],
        responses={
            501: OpenApiResponse(
                description="Not implemented",
            ),
        },
    )
    def patch(self, request, *args, **kwargs):
        return self._not_implemented(
            request,
            'API-AUTH-004',
            '/api/v1/auth/password',
        )


class AccountsContractEndpoint005View(ContractNotImplementedView):
    @extend_schema(
        operation_id='contract_api_user_001',
        summary='사용자 목록',
        description='BrainOn final API contract scaffold. API ID: API-USER-001. Contract endpoint: /api/v1/admin/users. Role contract: SYSTEM_ADMIN.',
        tags=['accounts'],
        responses={
            501: OpenApiResponse(
                description="Not implemented",
            ),
        },
    )
    def get(self, request, *args, **kwargs):
        return self._not_implemented(
            request,
            'API-USER-001',
            '/api/v1/admin/users',
        )

    @extend_schema(
        operation_id='contract_api_user_002',
        summary='사용자 생성',
        description='BrainOn final API contract scaffold. API ID: API-USER-002. Contract endpoint: /api/v1/admin/users. Role contract: SYSTEM_ADMIN.',
        tags=['accounts'],
        responses={
            501: OpenApiResponse(
                description="Not implemented",
            ),
        },
    )
    def post(self, request, *args, **kwargs):
        return self._not_implemented(
            request,
            'API-USER-002',
            '/api/v1/admin/users',
        )


class AccountsContractEndpoint006View(ContractNotImplementedView):
    @extend_schema(
        operation_id='contract_api_user_003',
        summary='사용자 상세',
        description='BrainOn final API contract scaffold. API ID: API-USER-003. Contract endpoint: /api/v1/admin/users/{user_id}. Role contract: SYSTEM_ADMIN.',
        tags=['accounts'],
        responses={
            501: OpenApiResponse(
                description="Not implemented",
            ),
        },
    )
    def get(self, request, *args, **kwargs):
        return self._not_implemented(
            request,
            'API-USER-003',
            '/api/v1/admin/users/{user_id}',
        )

    @extend_schema(
        operation_id='contract_api_user_004',
        summary='사용자 수정·활성화',
        description='BrainOn final API contract scaffold. API ID: API-USER-004. Contract endpoint: /api/v1/admin/users/{user_id}. Role contract: SYSTEM_ADMIN.',
        tags=['accounts'],
        responses={
            501: OpenApiResponse(
                description="Not implemented",
            ),
        },
    )
    def patch(self, request, *args, **kwargs):
        return self._not_implemented(
            request,
            'API-USER-004',
            '/api/v1/admin/users/{user_id}',
        )


class AccountsContractEndpoint007View(ContractNotImplementedView):
    @extend_schema(
        operation_id='contract_api_role_001',
        summary='Role/Permission 조회',
        description='BrainOn final API contract scaffold. API ID: API-ROLE-001. Contract endpoint: /api/v1/admin/roles. Role contract: SYSTEM_ADMIN.',
        tags=['accounts'],
        responses={
            501: OpenApiResponse(
                description="Not implemented",
            ),
        },
    )
    def get(self, request, *args, **kwargs):
        return self._not_implemented(
            request,
            'API-ROLE-001',
            '/api/v1/admin/roles',
        )


class AccountsContractEndpoint008View(ContractNotImplementedView):
    @extend_schema(
        operation_id='contract_api_role_002',
        summary='Role Permission 변경',
        description='BrainOn final API contract scaffold. API ID: API-ROLE-002. Contract endpoint: /api/v1/admin/roles/{role_id}/permissions. Role contract: SYSTEM_ADMIN.',
        tags=['accounts'],
        responses={
            501: OpenApiResponse(
                description="Not implemented",
            ),
        },
    )
    def put(self, request, *args, **kwargs):
        return self._not_implemented(
            request,
            'API-ROLE-002',
            '/api/v1/admin/roles/{role_id}/permissions',
        )


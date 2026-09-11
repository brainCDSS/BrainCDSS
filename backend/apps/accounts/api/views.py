from rest_framework import status
from rest_framework.pagination import (
    PageNumberPagination,
)
from rest_framework.permissions import (
    AllowAny,
    IsAuthenticated,
)
from rest_framework.response import Response
from rest_framework.views import APIView

from drf_spectacular.utils import (
    OpenApiResponse,
    extend_schema,
)

from apps.accounts.api.errors import (
    ContractAPIException,
)
from apps.accounts.api.permissions import (
    SystemAdminPermission,
)
from apps.accounts.api.serializers import (
    LoginRequestSerializer,
    LogoutRequestSerializer,
    PaginatedUserSummaryResponseSerializer,
    PasswordChangeRequestSerializer,
    RefreshRequestSerializer,
    RoleListResponseSerializer,
    RolePermissionResponseSerializer,
    RolePermissionUpdateRequestSerializer,
    UserCreateRequestSerializer,
    UserDetailSerializer,
    UserSummarySerializer,
    UserUpdateRequestSerializer,
)
from apps.accounts.models import Role
from apps.accounts.selectors.accounts import (
    permission_payloads_for_role,
    user_detail_payload,
    user_list_queryset,
    user_summary_payload,
    get_user,
)
from apps.accounts.services.accounts import (
    change_password,
    create_user,
    login,
    logout,
    refresh_access_token,
    replace_role_permissions,
    update_user,
)


def _validate(serializer, code="VALIDATION_ERROR"):
    if serializer.is_valid():
        return serializer.validated_data

    raise ContractAPIException(
        code,
        str(serializer.errors),
        400,
    )


class LoginView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(
        operation_id="api_auth_001_login",
        summary="로그인",
        request=LoginRequestSerializer,
        responses={
            200: OpenApiResponse(
                description="access, refresh, user"
            ),
            401: OpenApiResponse(
                description="AUTH_INVALID_CREDENTIALS"
            ),
        },
        tags=["accounts"],
    )
    def post(self, request):
        serializer = LoginRequestSerializer(
            data=request.data
        )

        data = _validate(serializer)

        result = login(
            login_id=data["login_id"],
            password=data["password"],
        )

        return Response(
            result,
            status=status.HTTP_200_OK,
        )


class RefreshView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(
        operation_id="api_auth_002_refresh",
        summary="Access Token 재발급",
        request=RefreshRequestSerializer,
        responses={
            200: OpenApiResponse(
                description="access"
            ),
            401: OpenApiResponse(
                description="AUTH_REFRESH_INVALID"
            ),
        },
        tags=["accounts"],
    )
    def post(self, request):
        serializer = RefreshRequestSerializer(
            data=request.data
        )

        data = _validate(serializer)

        result = refresh_access_token(
            refresh_value=data["refresh"]
        )

        return Response(
            result,
            status=status.HTTP_200_OK,
        )


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="api_auth_003_logout",
        summary="로그아웃",
        request=LogoutRequestSerializer,
        responses={
            204: OpenApiResponse(
                description="No Content"
            ),
            401: OpenApiResponse(
                description="AUTH_TOKEN_INVALID"
            ),
        },
        tags=["accounts"],
    )
    def post(self, request):
        serializer = LogoutRequestSerializer(
            data=request.data
        )

        data = _validate(serializer)

        logout(
            request=request,
            refresh_value=data["refresh"],
        )

        return Response(
            status=status.HTTP_204_NO_CONTENT
        )


class PasswordChangeView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="api_auth_004_password",
        summary="비밀번호 변경",
        request=PasswordChangeRequestSerializer,
        responses={
            200: OpenApiResponse(
                description=(
                    "changed, password_changed_at"
                )
            ),
            400: OpenApiResponse(
                description=(
                    "CURRENT_PASSWORD_INVALID / "
                    "PASSWORD_POLICY"
                )
            ),
        },
        tags=["accounts"],
    )
    def patch(self, request):
        serializer = (
            PasswordChangeRequestSerializer(
                data=request.data,
                context={
                    "user": request.user,
                },
            )
        )

        if not serializer.is_valid():
            code = (
                "PASSWORD_POLICY"
                if "new_password"
                in serializer.errors
                else "VALIDATION_ERROR"
            )

            raise ContractAPIException(
                code,
                str(serializer.errors),
                400,
            )

        result = change_password(
            request=request,
            **serializer.validated_data,
        )

        return Response(
            result,
            status=status.HTTP_200_OK,
        )


class UserPagination(
    PageNumberPagination
):
    page_size = 20


class AdminUsersView(APIView):
    permission_classes = [
        SystemAdminPermission
    ]
    required_permission_code = "user.manage"

    @extend_schema(
        operation_id="api_user_001_list",
        summary="사용자 목록",
        responses={
            200: PaginatedUserSummaryResponseSerializer,
        },
        tags=["accounts"],
    )
    def get(self, request):
        role = request.query_params.get(
            "role"
        )

        search = request.query_params.get(
            "search"
        )

        raw_active = (
            request.query_params.get(
                "is_active"
            )
        )

        is_active = None

        if raw_active is not None:
            value = raw_active.lower()

            if value in {
                "true",
                "1",
            }:
                is_active = True
            elif value in {
                "false",
                "0",
            }:
                is_active = False
            else:
                raise ContractAPIException(
                    "VALIDATION_ERROR",
                    "is_active must be true or false.",
                    400,
                )

        queryset = user_list_queryset(
            role=role,
            is_active=is_active,
            search=search,
        )

        paginator = UserPagination()

        page = paginator.paginate_queryset(
            queryset,
            request,
            view=self,
        )

        results = [
            user_summary_payload(user)
            for user in page
        ]

        return paginator.get_paginated_response(
            results
        )

    @extend_schema(
        operation_id="api_user_002_create",
        summary="사용자 생성",
        request=UserCreateRequestSerializer,
        responses={
            201: UserSummarySerializer,
        },
        tags=["accounts"],
    )
    def post(self, request):
        serializer = UserCreateRequestSerializer(
            data=request.data
        )

        data = _validate(serializer)

        user = create_user(
            request=request,
            **data,
        )

        return Response(
            user_summary_payload(user),
            status=status.HTTP_201_CREATED,
        )


class AdminUserDetailView(APIView):
    permission_classes = [
        SystemAdminPermission
    ]
    required_permission_code = "user.manage"

    @extend_schema(
        operation_id="api_user_003_detail",
        summary="사용자 상세",
        responses={
            200: UserDetailSerializer,
        },
        tags=["accounts"],
    )
    def get(
        self,
        request,
        user_id,
    ):
        user = get_user(user_id)

        if user is None:
            raise ContractAPIException(
                "USER_NOT_FOUND",
                "User was not found.",
                404,
            )

        return Response(
            user_detail_payload(user),
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        operation_id="api_user_004_update",
        summary="사용자 수정·활성화",
        request=UserUpdateRequestSerializer,
        responses={
            200: UserSummarySerializer,
        },
        tags=["accounts"],
    )
    def patch(
        self,
        request,
        user_id,
    ):
        serializer = UserUpdateRequestSerializer(
            data=request.data,
            partial=True,
        )

        data = _validate(serializer)

        user = update_user(
            request=request,
            user_id=user_id,
            data=data,
        )

        return Response(
            user_summary_payload(user),
            status=status.HTTP_200_OK,
        )


class AdminRolesView(APIView):
    permission_classes = [
        SystemAdminPermission
    ]
    required_permission_code = "role.manage"

    @extend_schema(
        operation_id="api_role_001_list",
        summary="Role/Permission 조회",
        responses={
            200: RoleListResponseSerializer,
        },
        tags=["accounts"],
    )
    def get(self, request):
        roles = (
            Role.objects
            .all()
            .order_by("code")
        )

        payload = []

        for role in roles:
            payload.append({
                "id": role.id,
                "code": role.code,
                "name": role.name,
                "description": (
                    role.description
                ),
                "is_active": (
                    role.is_active
                ),
                "permissions": (
                    permission_payloads_for_role(
                        role
                    )
                ),
            })

        return Response(
            {
                "roles": payload,
            },
            status=status.HTTP_200_OK,
        )


class AdminRolePermissionsView(APIView):
    permission_classes = [
        SystemAdminPermission
    ]
    required_permission_code = "role.manage"

    @extend_schema(
        operation_id="api_role_002_permissions",
        summary="Role Permission 변경",
        request=(
            RolePermissionUpdateRequestSerializer
        ),
        responses={
            200: RolePermissionResponseSerializer,
        },
        tags=["accounts"],
    )
    def put(
        self,
        request,
        role_id,
    ):
        serializer = (
            RolePermissionUpdateRequestSerializer(
                data=request.data
            )
        )

        data = _validate(serializer)

        result = replace_role_permissions(
            request=request,
            role_id=role_id,
            permission_codes=(
                data["permission_codes"]
            ),
        )

        return Response(
            result,
            status=status.HTTP_200_OK,
        )

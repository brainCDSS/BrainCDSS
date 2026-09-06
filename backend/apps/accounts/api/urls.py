from django.urls import path

from apps.accounts.api.views import (
    AdminRolePermissionsView,
    AdminRolesView,
    AdminUserDetailView,
    AdminUsersView,
    LoginView,
    LogoutView,
    PasswordChangeView,
    RefreshView,
)


urlpatterns = [
    path(
        "api/v1/auth/login",
        LoginView.as_view(),
        name="api-auth-001",
    ),
    path(
        "api/v1/auth/refresh",
        RefreshView.as_view(),
        name="api-auth-002",
    ),
    path(
        "api/v1/auth/logout",
        LogoutView.as_view(),
        name="api-auth-003",
    ),
    path(
        "api/v1/auth/password",
        PasswordChangeView.as_view(),
        name="api-auth-004",
    ),

    path(
        "api/v1/admin/users",
        AdminUsersView.as_view(),
        name="api-users",
    ),
    path(
        "api/v1/admin/users/<str:user_id>",
        AdminUserDetailView.as_view(),
        name="api-user-detail",
    ),

    path(
        "api/v1/admin/roles",
        AdminRolesView.as_view(),
        name="api-role-001",
    ),
    path(
        (
            "api/v1/admin/roles/"
            "<str:role_id>/permissions"
        ),
        AdminRolePermissionsView.as_view(),
        name="api-role-002",
    ),
]

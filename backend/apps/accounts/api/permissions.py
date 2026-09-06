from rest_framework.permissions import BasePermission

from apps.accounts.api.errors import (
    ContractAPIException,
)
from apps.accounts.models import RolePermission


class SystemAdminPermission(BasePermission):
    """
    Final contract:
      Role = SYSTEM_ADMIN
      + endpoint-specific permission code
    """

    def has_permission(self, request, view):
        user = getattr(
            request,
            "user",
            None,
        )

        if (
            user is None
            or not user.is_authenticated
        ):
            return False

        role = getattr(
            user,
            "role",
            None,
        )

        if (
            role is None
            or role.code != "SYSTEM_ADMIN"
            or not role.is_active
        ):
            raise ContractAPIException(
                "FORBIDDEN_ROLE",
                "SYSTEM_ADMIN role is required.",
                403,
            )

        required = getattr(
            view,
            "required_permission_code",
            None,
        )

        if required:
            allowed = (
                RolePermission.objects
                .filter(
                    role=role,
                    permission__code=required,
                )
                .exists()
            )

            if not allowed:
                raise ContractAPIException(
                    "FORBIDDEN_ROLE",
                    f"Permission '{required}' is required.",
                    403,
                )

        return True

from rest_framework.permissions import BasePermission

from apps.accounts.api.errors import ContractAPIException
from apps.accounts.models import RolePermission


class FCMManagePermission(BasePermission):
    """
    API-FCM-001 / API-FCM-002

    허용 역할:
      PATIENT
      NURSE
      NEUROLOGIST
      NEUROSURGEON
      RADIOLOGY
      SYSTEM_ADMIN

    추가 권한:
      fcm.manage
    """

    allowed_roles = {
        "PATIENT",
        "NURSE",
        "NEUROLOGIST",
        "NEUROSURGEON",
        "RADIOLOGY",
        "SYSTEM_ADMIN",
    }

    required_permission_code = "fcm.manage"

    def has_permission(
        self,
        request,
        view,
    ):
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
            or role.code not in self.allowed_roles
            or not role.is_active
        ):
            raise ContractAPIException(
                "FORBIDDEN_ROLE",
                "FCM token management is not allowed for this role.",
                403,
            )

        allowed = (
            RolePermission.objects
            .filter(
                role=role,
                permission__code=self.required_permission_code,
            )
            .exists()
        )

        if not allowed:
            raise ContractAPIException(
                "FORBIDDEN_PERMISSION",
                "Permission 'fcm.manage' is required.",
                403,
            )

        return True

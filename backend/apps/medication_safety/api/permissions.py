from rest_framework.permissions import BasePermission

from apps.accounts.api.errors import (
    ContractAPIException,
)
from apps.accounts.models import RolePermission


class MedicationSafetyCheckPermission(
    BasePermission
):
    """
    API-MEDSAFE-001:
    NEUROLOGIST / NEUROSURGEON
    + medication_safety.check
    """

    allowed_roles = {
        "NEUROLOGIST",
        "NEUROSURGEON",
    }

    required_permission_code = (
        "medication_safety.check"
    )

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
            or role.code
            not in self.allowed_roles
            or not role.is_active
        ):
            raise ContractAPIException(
                "FORBIDDEN_ROLE",
                (
                    "NEUROLOGIST or "
                    "NEUROSURGEON role "
                    "is required."
                ),
                403,
            )

        allowed = (
            RolePermission.objects
            .filter(
                role=role,
                permission__code=(
                    self.required_permission_code
                ),
            )
            .exists()
        )

        if not allowed:
            raise ContractAPIException(
                "FORBIDDEN_PERMISSION",
                (
                    "Permission "
                    "'medication_safety.check' "
                    "is required."
                ),
                403,
            )

        return True

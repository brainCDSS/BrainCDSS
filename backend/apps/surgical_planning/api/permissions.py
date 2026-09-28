"""Authorization boundary for surgical planning extension APIs."""

from rest_framework.permissions import BasePermission

from apps.accounts.api.errors import ContractAPIException


class SurgicalPlanningPermission(BasePermission):
    """
    Surgical Planning extension API access.

    Current extension contract:
    - NEUROLOGIST
    - NEUROSURGEON
    - RADIOLOGY

    SYSTEM_ADMIN is intentionally excluded because this domain
    contains clinical planning operations.
    """

    allowed_roles = {
        "NEUROLOGIST",
        "NEUROSURGEON",
        "RADIOLOGY",
        "MASTER",
    }

    def has_permission(self, request, view):
        user = getattr(request, "user", None)

        if (
            user is None
            or not getattr(user, "is_authenticated", False)
        ):
            return False

        if not getattr(user, "is_active", False):
            raise ContractAPIException(
                "FORBIDDEN_USER_INACTIVE",
                "Active user account is required.",
                403,
            )

        role = getattr(user, "role", None)

        if (
            role is None
            or not getattr(role, "is_active", False)
            or getattr(role, "code", None)
            not in self.allowed_roles
        ):
            raise ContractAPIException(
                "FORBIDDEN_ROLE",
                (
                    "NEUROLOGIST, NEUROSURGEON, "
                    "or RADIOLOGY role is required."
                ),
                403,
            )

        return True

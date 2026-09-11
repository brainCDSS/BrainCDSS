from rest_framework.permissions import BasePermission

from apps.accounts.api.errors import ContractAPIException


class ImagingStudyPermission(BasePermission):
    allowed_roles = {
        "NEUROLOGIST",
        "NEUROSURGEON",
        "NURSE",
        "RADIOLOGY",
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
                    "Clinical imaging role is required."
                ),
                403,
            )

        return True

class ImagingSeriesPermission(ImagingStudyPermission):
    """
    API-IMG-005 Study Series 조회 권한.
    NURSE는 최종 계약상 제외.
    """
    allowed_roles = {
        "NEUROLOGIST",
        "NEUROSURGEON",
        "RADIOLOGY",
    }



class ImagingOrderReadPermission(
    ImagingStudyPermission
):
    allowed_roles = {
        "NEUROLOGIST",
        "NEUROSURGEON",
        "NURSE",
        "RADIOLOGY",
    }


class ImagingOrderWritePermission(
    ImagingStudyPermission
):
    allowed_roles = {
        "NEUROLOGIST",
        "NEUROSURGEON",
    }

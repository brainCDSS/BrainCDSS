from __future__ import annotations

from rest_framework.permissions import BasePermission


def get_role_code(user) -> str | None:
    if not user or not getattr(user, "is_authenticated", False):
        return None

    role = getattr(user, "role", None)
    return getattr(role, "code", None)


class IsPatientRole(BasePermission):
    message = "PATIENT role is required."

    def has_permission(self, request, view):
        return get_role_code(request.user) == "PATIENT"


class IsPatientOrNurseRole(BasePermission):
    message = "PATIENT or NURSE role is required."

    def has_permission(self, request, view):
        return get_role_code(request.user) in {"PATIENT", "NURSE"}

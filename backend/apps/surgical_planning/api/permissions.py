"""Permissions dedicated to the surgical planning API."""

from rest_framework.permissions import BasePermission


class SurgicalPlanningPermission(BasePermission):
    allowed_roles = {"NEUROLOGIST", "NEUROSURGEON", "RADIOLOGY"}

    def has_permission(self, request, view):
        role = getattr(getattr(request.user, "role", None), "code", None)
        return bool(request.user and request.user.is_authenticated and role in self.allowed_roles)

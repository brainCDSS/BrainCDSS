from __future__ import annotations

from apps.accounts.models import RolePermission


def role_code(user) -> str | None:
    if not user or not getattr(user, "is_authenticated", False):
        return None

    role = getattr(user, "role", None)
    return getattr(role, "code", None)


def has_permission_code(user, code: str) -> bool:
    if not user or not getattr(user, "is_authenticated", False):
        return False

    role_id = getattr(user, "role_id", None)

    if role_id is None:
        return False

    return RolePermission.objects.filter(
        role_id=role_id,
        permission__code=code,
    ).exists()

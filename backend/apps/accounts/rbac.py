# Shared role-gate helpers for BrainOn RBAC.

from __future__ import annotations

from collections.abc import Iterable


MASTER_ROLE_CODE = "MASTER"

MASTER_CLINICAL_ROLES = frozenset(
    {
        "NURSE",
        "NEUROLOGIST",
        "NEUROSURGEON",
        "RADIOLOGY",
    }
)


def role_allowed(
    role_code: str | None,
    allowed_roles: Iterable[str],
) -> bool:
    allowed = set(allowed_roles)

    if role_code in allowed:
        return True

    return (
        role_code == MASTER_ROLE_CODE
        and bool(allowed & MASTER_CLINICAL_ROLES)
    )

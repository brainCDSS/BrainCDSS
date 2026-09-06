from uuid import UUID

from django.db.models import Q

from apps.accounts.models import (
    Permission,
    Role,
    RolePermission,
    User,
)


def valid_uuid(value):
    try:
        return UUID(str(value))
    except (TypeError, ValueError, AttributeError):
        return None


def permission_rows_for_role(role):
    return list(
        RolePermission.objects
        .filter(role=role)
        .select_related("permission")
        .order_by("permission__domain", "permission__code")
    )


def permission_codes_for_role(role):
    return [
        row.permission.code
        for row in permission_rows_for_role(role)
    ]


def permission_payloads_for_role(role):
    return [
        {
            "code": row.permission.code,
            "name": row.permission.name,
            "domain": row.permission.domain,
        }
        for row in permission_rows_for_role(role)
    ]


def role_brief(role):
    return {
        "code": role.code,
        "name": role.name,
    }


def user_summary_payload(user):
    return {
        "id": user.id,
        "login_id": user.login_id,
        "name": user.name,
        "email": user.email,
        "role": role_brief(user.role),
        "is_active": user.is_active,
        "last_login": user.last_login,
        "created_at": user.created_at,
    }


def user_detail_payload(user):
    data = user_summary_payload(user)

    data.update({
        "permissions": permission_codes_for_role(
            user.role
        ),
        "updated_at": user.updated_at,
    })

    return data


def get_user(user_id):
    value = valid_uuid(user_id)

    if value is None:
        return None

    return (
        User.objects
        .select_related("role")
        .filter(id=value)
        .first()
    )


def get_role(role_id):
    value = valid_uuid(role_id)

    if value is None:
        return None

    return Role.objects.filter(id=value).first()


def user_list_queryset(
    *,
    role=None,
    is_active=None,
    search=None,
):
    queryset = (
        User.objects
        .select_related("role")
        .all()
        .order_by("-created_at")
    )

    if role:
        queryset = queryset.filter(
            role__code=role
        )

    if is_active is not None:
        queryset = queryset.filter(
            is_active=is_active
        )

    if search:
        queryset = queryset.filter(
            Q(login_id__icontains=search)
            | Q(name__icontains=search)
            | Q(email__icontains=search)
        )

    return queryset


def active_roles():
    return Role.objects.filter(
        is_active=True
    )


def all_active_permissions():
    return Permission.objects.all()

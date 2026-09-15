from __future__ import annotations


from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.tokens import (
    RefreshToken,
    TokenError,
)

from apps.accounts.api.errors import (
    ContractAPIException,
)
from apps.accounts.models import (
    Permission,
    Role,
    RolePermission,
    User,
)
from apps.accounts.selectors.accounts import (
    get_role,
    get_user,
    permission_codes_for_role,
    permission_payloads_for_role,
    role_brief,
    user_detail_payload,
    user_summary_payload,
)
from apps.audit.services.audit_event import (
    record_audit_event,
)


# ============================================================
# AUDIT SNAPSHOT
# ============================================================

def _user_audit_snapshot(user):
    return {
        "id": str(user.id),
        "login_id": user.login_id,
        "name": user.name,
        "email": user.email,
        "role_id": str(user.role_id),
        "role_code": user.role.code,
        "is_active": user.is_active,
    }


# ============================================================
# AUTH
# ============================================================

def login(
    *,
    login_id,
    password,
):
    user = (
        User.objects
        .select_related("role")
        .filter(login_id=login_id)
        .first()
    )

    if (
        user is None
        or not user.is_active
        or not user.check_password(password)
    ):
        raise ContractAPIException(
            "AUTH_INVALID_CREDENTIALS",
            "Invalid login credentials.",
            401,
        )

    user.last_login = timezone.now()
    user.save(
        update_fields=[
            "last_login",
        ]
    )

    refresh = RefreshToken.for_user(user)

    return {
        "access": str(refresh.access_token),
        "refresh": str(refresh),
        "user": {
            "id": user.id,
            "login_id": user.login_id,
            "name": user.name,
            "email": user.email,
            "role": role_brief(user.role),
            "permissions": permission_codes_for_role(
                user.role
            ),
        },
    }


def refresh_access_token(
    *,
    refresh_value,
):
    try:
        refresh = RefreshToken(
            refresh_value
        )
    except TokenError:
        raise ContractAPIException(
            "AUTH_REFRESH_INVALID",
            "Refresh token is invalid or blacklisted.",
            401,
        )

    return {
        "access": str(
            refresh.access_token
        ),
    }


def logout(
    *,
    request,
    refresh_value,
):
    try:
        refresh = RefreshToken(
            refresh_value
        )
    except TokenError:
        raise ContractAPIException(
            "AUTH_TOKEN_INVALID",
            "Refresh token is invalid.",
            401,
        )

    token_user_id = refresh.get(
        api_settings.USER_ID_CLAIM
    )

    if str(token_user_id) != str(
        request.user.pk
    ):
        raise ContractAPIException(
            "AUTH_TOKEN_INVALID",
            "Refresh token does not belong to the authenticated user.",
            401,
        )

    try:
        refresh.blacklist()
    except TokenError:
        raise ContractAPIException(
            "AUTH_TOKEN_INVALID",
            "Refresh token is invalid.",
            401,
        )


@transaction.atomic
def change_password(
    *,
    request,
    current_password,
    new_password,
):
    user = (
        User.objects
        .select_for_update()
        .select_related("role")
        .get(pk=request.user.pk)
    )

    if not user.check_password(
        current_password
    ):
        raise ContractAPIException(
            "CURRENT_PASSWORD_INVALID",
            "Current password is invalid.",
            400,
        )

    now = timezone.now()

    user.set_password(
        new_password
    )

    user.password_changed_at = now

    user.save(
        update_fields=[
            "password",
            "password_changed_at",
            "updated_at",
        ]
    )

    record_audit_event(
        request=request,
        actor_user=user,
        source_service="AUTH_API",
        action="CHANGE_PASSWORD",
        resource_type="User",
        resource_id=user.id,
        before_json=None,
        after_json={
            "password_changed_at": (
                now.isoformat()
            ),
        },
    )

    return {
        "changed": True,
        "password_changed_at": now,
    }


# ============================================================
# USER ADMIN
# ============================================================

@transaction.atomic
def create_user(
    *,
    request,
    login_id,
    name,
    email,
    role_id,
    temp_password,
):
    if User.objects.filter(
        login_id=login_id
    ).exists():
        raise ContractAPIException(
            "USER_DUPLICATE",
            "login_id already exists.",
            409,
        )

    if (
        email
        and User.objects.filter(
            email__iexact=email
        ).exists()
    ):
        raise ContractAPIException(
            "USER_DUPLICATE",
            "email already exists.",
            409,
        )

    role = get_role(role_id)

    if (
        role is None
        or not role.is_active
    ):
        raise ContractAPIException(
            "ROLE_NOT_FOUND",
            "Active role was not found.",
            404,
        )

    user = User(
        login_id=login_id,
        name=name,
        email=email,
        role=role,
        is_active=True,
    )

    user.set_password(
        temp_password
    )

    try:
        user.save()
    except IntegrityError:
        raise ContractAPIException(
            "USER_DUPLICATE",
            "User already exists.",
            409,
        )

    user = (
        User.objects
        .select_related("role")
        .get(pk=user.pk)
    )

    record_audit_event(
        request=request,
        actor_user=request.user,
        source_service="ADMIN_API",
        action="CREATE_USER",
        resource_type="User",
        resource_id=user.id,
        after_json=_user_audit_snapshot(
            user
        ),
    )

    return user


@transaction.atomic
def update_user(
    *,
    request,
    user_id,
    data,
):
    target = get_user(user_id)

    if target is None:
        raise ContractAPIException(
            "USER_NOT_FOUND",
            "User was not found.",
            404,
        )

    target = (
        User.objects
        .select_for_update()
        .select_related("role")
        .get(pk=target.pk)
    )

    before = _user_audit_snapshot(
        target
    )

    if (
        target.pk == request.user.pk
        and data.get(
            "is_active",
            target.is_active,
        ) is False
    ):
        raise ContractAPIException(
            "FORBIDDEN_ROLE",
            "Administrator cannot deactivate the current account.",
            403,
        )

    fields = []

    if "name" in data:
        target.name = data["name"]
        fields.append("name")

    if "email" in data:
        email = data["email"]

        if (
            email
            and User.objects
            .exclude(pk=target.pk)
            .filter(
                email__iexact=email
            )
            .exists()
        ):
            raise ContractAPIException(
                "USER_DUPLICATE",
                "email already exists.",
                409,
            )

        target.email = email
        fields.append("email")

    if "role_id" in data:
        role = get_role(
            data["role_id"]
        )

        if (
            role is None
            or not role.is_active
        ):
            raise ContractAPIException(
                "VALIDATION_ERROR",
                "Active role was not found.",
                400,
            )

        target.role = role
        fields.append("role")

    if "is_active" in data:
        target.is_active = data[
            "is_active"
        ]
        fields.append("is_active")

    if fields:
        try:
            target.save(
                update_fields=[
                    *fields,
                    "updated_at",
                ]
            )
        except IntegrityError:
            raise ContractAPIException(
                "USER_DUPLICATE",
                "User update violates a unique constraint.",
                409,
            )

    target.refresh_from_db()

    target = (
        User.objects
        .select_related("role")
        .get(pk=target.pk)
    )

    after = _user_audit_snapshot(
        target
    )

    record_audit_event(
        request=request,
        actor_user=request.user,
        source_service="ADMIN_API",
        action="UPDATE_USER",
        resource_type="User",
        resource_id=target.id,
        before_json=before,
        after_json=after,
    )

    return target


# ============================================================
# ROLE / PERMISSION ADMIN
# ============================================================

@transaction.atomic
def replace_role_permissions(
    *,
    request,
    role_id,
    permission_codes,
):
    role = get_role(role_id)

    if role is None:
        raise ContractAPIException(
            "ROLE_NOT_FOUND",
            "Role was not found.",
            404,
        )

    role = (
        Role.objects
        .select_for_update()
        .get(pk=role.pk)
    )

    before_codes = sorted(
        permission_codes_for_role(
            role
        )
    )

    permissions = list(
        Permission.objects
        .filter(
            code__in=permission_codes
        )
        .order_by("code")
    )

    found_codes = {
        permission.code
        for permission in permissions
    }

    requested_codes = set(
        permission_codes
    )

    missing = sorted(
        requested_codes
        - found_codes
    )

    if missing:
        raise ContractAPIException(
            "VALIDATION_ERROR",
            (
                "Unknown permission code(s): "
                + ", ".join(missing)
            ),
            400,
        )

    RolePermission.objects.filter(
        role=role
    ).delete()

    for permission in permissions:
        RolePermission.objects.create(
            role=role,
            permission=permission,
        )

    updated_at = timezone.now()

    after_payload = (
        permission_payloads_for_role(
            role
        )
    )

    record_audit_event(
        request=request,
        actor_user=request.user,
        source_service="ADMIN_API",
        action="UPDATE_PERMISSION",
        resource_type="Role",
        resource_id=role.id,
        before_json={
            "permission_codes": (
                before_codes
            ),
        },
        after_json={
            "permission_codes": sorted(
                found_codes
            ),
        },
    )

    return {
        "role": {
            "id": role.id,
            "code": role.code,
            "name": role.name,
        },
        "permissions": after_payload,
        # Role DB에는 updated_at 물리컬럼이 없으므로
        # 권한 변경 작업 시각을 API 응답값으로 반환한다.
        "updated_at": updated_at,
    }

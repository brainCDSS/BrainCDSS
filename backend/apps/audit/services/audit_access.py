from __future__ import annotations

import uuid

from django.utils import timezone

from apps.audit.models import AuditLog
from apps.common.tracking import build_tracking_code


SECRET_FRAGMENTS = (
    "password",
    "passwd",
    "token",
    "authorization",
    "cookie",
    "secret",
    "service_key",
    "api_key",
    "apikey",
    "pixel_data",
    "dicom_pixel",
)

PHI_KEYS = {
    "patient_name",
    "birth_date",
    "phone",
    "emergency_contact",
    "address",
    "email",
    "resident_registration_number",
    "rrn",
    "ssn",
}


def _sensitive_key(key) -> bool:
    value = str(key).lower()

    if value in PHI_KEYS:
        return True

    return any(
        fragment in value
        for fragment in SECRET_FRAGMENTS
    )


def mask_snapshot(value):
    if isinstance(value, dict):
        result = {}

        for key, item in value.items():
            if _sensitive_key(key):
                result[key] = "***"
            else:
                result[key] = (
                    mask_snapshot(item)
                )

        return result

    if isinstance(value, list):
        return [
            mask_snapshot(item)
            for item in value
        ]

    return value


def list_payload(log):
    return {
        "audit_id": log.id,
        "actor_user_id": (
            log.actor_user_id
        ),
        "actor_login_id": (
            log.actor_login
        ),
        "actor_role_code": (
            log.actor_role_code
        ),
        "source_service": (
            log.source_service
        ),
        "action": log.action,
        "patient_id": log.patient,
        "resource_type": (
            log.resource_type
        ),
        "resource_id": log.resource,
        "outcome": log.outcome,
        "request_id": log.request,
        "tracking_code": (
            build_tracking_code(
                log.request
            )
        ),
        "occurred_at": (
            log.occurred_at
        ),
    }


def detail_payload(log):
    return {
        "audit_id": log.id,
        "actor_user_id": (
            log.actor_user_id
        ),
        "actor_login_id": (
            log.actor_login
        ),
        "actor_role_code": (
            log.actor_role_code
        ),
        "source_service": (
            log.source_service
        ),
        "action": log.action,
        "resource_type": (
            log.resource_type
        ),
        "resource_id": log.resource,
        "patient_id": log.patient,
        "outcome": log.outcome,
        "reason": log.reason,
        "before_json": (
            mask_snapshot(
                log.before_json
            )
        ),
        "after_json": (
            mask_snapshot(
                log.after_json
            )
        ),
        "request_ip": (
            log.request_ip
        ),
        "user_agent": (
            log.user_agent
        ),
        "request_id": log.request,
        "tracking_code": (
            build_tracking_code(
                log.request
            )
        ),
        "occurred_at": (
            log.occurred_at
        ),
        "created_at": log.created_at,
    }


def _request_uuid(request):
    value = getattr(
        request,
        "request_id",
        None,
    )

    if value is None:
        value = request.headers.get(
            "X-Request-ID"
        )

    if value in (
        None,
        "",
    ):
        return None

    try:
        return uuid.UUID(str(value))
    except (
        ValueError,
        TypeError,
        AttributeError,
    ):
        return None


def _request_ip(request):
    forwarded = request.META.get(
        "HTTP_X_FORWARDED_FOR",
        "",
    )

    if forwarded:
        return (
            forwarded
            .split(",")[0]
            .strip()
        )

    return request.META.get(
        "REMOTE_ADDR"
    )


def record_audit_read(
    *,
    request,
    reason: str,
    action: str,
    resource_id=None,
):
    user = request.user

    role = getattr(
        user,
        "role",
        None,
    )

    AuditLog.objects.create(
        actor_user=user,
        actor_login=getattr(
            user,
            "login_id",
            None,
        ),
        actor_role_code=getattr(
            role,
            "code",
            None,
        ),
        source_service="AUDIT_API",
        action=action,
        resource_type="AuditLog",
        resource=(
            str(resource_id)
            if resource_id
            else None
        ),
        patient=None,
        outcome="SUCCESS",
        reason=reason,
        before_json=None,
        after_json=None,
        request_ip=_request_ip(
            request
        ),
        user_agent=(
            request.headers.get(
                "User-Agent"
            )
            or None
        ),
        request=_request_uuid(
            request
        ),
        occurred_at=timezone.now(),
    )

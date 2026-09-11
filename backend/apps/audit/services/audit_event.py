from __future__ import annotations

import uuid

from django.utils import timezone

from apps.audit.models import AuditLog
from apps.audit.services.audit_access import mask_snapshot


def _uuid_or_none(value):
    if value in (None, ""):
        return None

    try:
        return uuid.UUID(str(value))
    except (ValueError, TypeError, AttributeError):
        return None


def _request_ip(request):
    if request is None:
        return None

    forwarded = request.META.get(
        "HTTP_X_FORWARDED_FOR",
        "",
    )

    if forwarded:
        return forwarded.split(",")[0].strip()

    return request.META.get("REMOTE_ADDR")


def _actor_role_code(user):
    if user is None:
        return None

    role = getattr(user, "role", None)

    if role is None:
        return None

    code = getattr(role, "code", None)

    if code:
        return str(code)

    if isinstance(role, str):
        return role

    return str(role)


def record_audit_event(
    *,
    source_service,
    action,
    resource_type,
    outcome,
    request=None,
    request_id=None,
    actor_user=None,
    resource_id=None,
    patient_id=None,
    reason=None,
    before_json=None,
    after_json=None,
):
    """Persist one BrainOn AuditLog event.

    The caller controls whether audit persistence is transactionally
    mandatory for the business action.
    """

    if request is not None:
        if request_id is None:
            request_id = getattr(
                request,
                "request_id",
                None,
            )

        if actor_user is None:
            candidate = getattr(
                request,
                "user",
                None,
            )

            if (
                candidate is not None
                and getattr(
                    candidate,
                    "is_authenticated",
                    False,
                )
            ):
                actor_user = candidate

    audit_request_id = _uuid_or_none(request_id)

    if request_id not in (None, "") and audit_request_id is None:
        raise ValueError("AUDIT_REQUEST_ID_INVALID")

    audit_patient_id = _uuid_or_none(patient_id)

    if patient_id not in (None, "") and audit_patient_id is None:
        raise ValueError("AUDIT_PATIENT_ID_INVALID")

    if not source_service or len(source_service) > 64:
        raise ValueError("AUDIT_SOURCE_SERVICE_INVALID")

    if not action or len(action) > 80:
        raise ValueError("AUDIT_ACTION_INVALID")

    if not resource_type or len(resource_type) > 80:
        raise ValueError("AUDIT_RESOURCE_TYPE_INVALID")

    if not outcome or len(outcome) > 16:
        raise ValueError("AUDIT_OUTCOME_INVALID")

    if resource_id is not None:
        resource_id = str(resource_id)

        if len(resource_id) > 128:
            raise ValueError("AUDIT_RESOURCE_ID_INVALID")

    return AuditLog.objects.create(
        actor_user=actor_user,
        actor_login=(
            getattr(
                actor_user,
                "login_id",
                None,
            )
            if actor_user is not None
            else None
        ),
        actor_role_code=_actor_role_code(
            actor_user
        ),
        source_service=source_service,
        action=action,
        resource_type=resource_type,
        resource=resource_id,
        patient=audit_patient_id,
        outcome=outcome,
        reason=reason,
        before_json=(
            mask_snapshot(before_json)
            if before_json is not None
            else None
        ),
        after_json=(
            mask_snapshot(after_json)
            if after_json is not None
            else None
        ),
        request_ip=_request_ip(request),
        user_agent=(
            request.headers.get(
                "User-Agent"
            )
            if request is not None
            else None
        ),
        request=audit_request_id,
        occurred_at=timezone.now(),
    )

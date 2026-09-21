
from __future__ import annotations

import re
import uuid
from contextlib import nullcontext
from datetime import date, datetime, time, timedelta
from decimal import Decimal, InvalidOperation

from django.apps import apps
from django.conf import settings
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from django.db.models import Prefetch, Q
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime
from rest_framework.exceptions import APIException, AuthenticationFailed, NotFound, PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiResponse, extend_schema

from apps.accounts.models import RolePermission
from apps.audit.models import AuditLog
from apps.common.authentication import ServiceJWTAuthentication
from apps.common.models import OutboxEvent


READ_METHODS = {"GET", "HEAD", "OPTIONS"}

# Notification categories already used by the clinician notification UI.  These
# are response defaults only; user-specific rows still take precedence.
DEFAULT_NOTIFICATION_PREFERENCE_CATEGORIES = (
    "EMERGENCY",
    "CONSULTATION",
    "IMAGING",
    "AI_ANALYSIS",
    "APPOINTMENT",
    "SYSTEM",
)

ACTION_STATUS = {
    "accept": "ACCEPTED",
    "acknowledge": "ACKNOWLEDGED",
    "approve": "APPROVED",
    "archive": "ARCHIVED",
    "block": "BLOCKED",
    "cancel": "CANCELLED",
    "close": "CLOSED",
    "complete": "COMPLETED",
    "confirm": "CONFIRMED",
    "finalize": "FINAL",
    "identify": "ACTIVE",
    "reject": "REJECTED",
    "respond": "RESPONDED",
    "retire": "RETIRED",
    "start": "IN_PROGRESS",
    "unblock": "AVAILABLE",
    "validate": "VALIDATED",
}


class ContractError(ValidationError):
    status_code = 400


class ContractConflict(APIException):
    status_code = 409
    default_code = "CONFLICT"


def _model(spec):
    label = spec.get("primary_model")
    return apps.get_model(label) if label else None


def _field_map(model):
    if model is None:
        return {}
    result = {}
    for field in model._meta.get_fields():
        if getattr(field, "auto_created", False) and not getattr(field, "concrete", False):
            continue
        result[field.name] = field
        attname = getattr(field, "attname", None)
        if attname:
            result[attname] = field
    return result


def _safe_value(value):
    """
    AuditLog / OutboxEvent JSONField에 저장할 값을
    JSON 직렬화 가능한 형태로 재귀 변환한다.

    Django/Python 객체 중 JSON에서 직접 지원하지 않는
    Decimal, UUID, datetime/date/time, timedelta,
    bytes, Model instance 등을 처리한다.
    """
    from datetime import (
        date,
        datetime,
        time,
        timedelta,
    )
    from decimal import Decimal
    import uuid as uuid_module

    from django.db.models import Model

    if value is None:
        return None

    if isinstance(
        value,
        (
            str,
            int,
            float,
            bool,
        ),
    ):
        return value

    # Decimal은 의료 dose 등의 정밀도를 보존하기 위해
    # float가 아닌 문자열로 저장한다.
    if isinstance(value, Decimal):
        return str(value)

    if isinstance(
        value,
        uuid_module.UUID,
    ):
        return str(value)

    if isinstance(
        value,
        (
            datetime,
            date,
            time,
        ),
    ):
        return value.isoformat()

    if isinstance(
        value,
        timedelta,
    ):
        return value.total_seconds()

    if isinstance(value, bytes):
        return value.decode(
            "utf-8",
            errors="replace",
        )

    if isinstance(value, Model):
        return str(value.pk)

    if isinstance(value, dict):
        return {
            str(key): _safe_value(item)
            for key, item
            in value.items()
        }

    if isinstance(
        value,
        (
            list,
            tuple,
            set,
        ),
    ):
        return [
            _safe_value(item)
            for item in value
        ]

    # numpy 계열 scalar가 들어오는 경우도 대비
    if hasattr(value, "item"):
        try:
            return _safe_value(
                value.item()
            )
        except Exception:
            pass

    # JSONField 저장 실패로 전체 API가 500이 되는 것을
    # 방지하기 위한 최종 fallback
    return str(value)




def serialize_instance(obj):
    if obj is None:
        return None
    payload = {}
    for field in obj._meta.concrete_fields:
        if field.is_relation:
            payload[field.name + "_id"] = _safe_value(getattr(obj, field.attname))
        else:
            payload[field.name] = _safe_value(getattr(obj, field.name))
    return payload


def _role_code(user):
    role = getattr(user, "role", None)
    return getattr(role, "code", None)


def _has_permission(user, code):
    if not code:
        return True
    role_id = getattr(user, "role_id", None)
    if not role_id:
        return False
    return RolePermission.objects.filter(
        role_id=role_id,
        permission__code=code,
    ).exists()


def check_access(request, spec):
    service_scope = spec.get("service_scope")
    if service_scope:
        principal = getattr(request, "user", None)
        if not getattr(principal, "is_service", False):
            raise AuthenticationFailed({
                "code": "SERVICE_AUTH_REQUIRED",
                "detail": "Service JWT is required.",
            })
        if service_scope not in getattr(principal, "scopes", frozenset()):
            raise PermissionDenied({
                "code": "SERVICE_SCOPE_FORBIDDEN",
                "detail": f"Missing service scope: {service_scope}",
            })
        return

    user = request.user
    if not getattr(user, "is_authenticated", False):
        raise AuthenticationFailed()

    allowed_roles = set(spec.get("roles") or [])
    if allowed_roles and _role_code(user) not in allowed_roles:
        raise PermissionDenied({
            "code": "FORBIDDEN_ROLE",
            "detail": "Role is not allowed for this API.",
        })

    permission = spec.get("permission")
    if permission and not _has_permission(user, permission):
        raise PermissionDenied({
            "code": "FORBIDDEN_PERMISSION",
            "detail": f"Missing permission: {permission}",
        })


def _path_filter(model, kwargs):
    fields = _field_map(model)
    filters = {}

    for key, value in kwargs.items():
        candidates = [key]
        if key.endswith("_id"):
            candidates.extend([key[:-3], key])
        else:
            candidates.append(key + "_id")

        matched = None
        for candidate in candidates:
            field = fields.get(candidate)
            if field:
                matched = field.attname if field.is_relation else field.name
                break

        if matched is None and key.endswith("_id"):
            resource = key[:-3].replace("_", "").lower()
            model_name = model.__name__.replace("_", "").lower()
            if resource in model_name or model_name in resource:
                matched = "pk"

        if matched:
            filters[matched] = value

    return filters


def _patient_for_user(user):
    try:
        from apps.patients.models import Patient
        return Patient.objects.filter(user=user).first()
    except Exception:
        return None


def _owner_scope(qs, model, request):
    if _role_code(request.user) != "PATIENT":
        return qs

    fields = _field_map(model)
    patient = _patient_for_user(request.user)

    options = [
        ("user", request.user.id),
        ("recipient_user", request.user.id),
        ("patient", getattr(patient, "id", None)),
    ]
    for name, value in options:
        field = fields.get(name)
        if field and field.is_relation and value is not None:
            return qs.filter(**{field.attname: value})
    return qs


def _apply_query_filters(qs, model, request):
    fields = _field_map(model)

    for key, value in request.query_params.items():
        if key in {"page", "page_size", "reason", "search", "from", "to", "date"}:
            continue
        if value in ("", None):
            continue

        field = fields.get(key)
        if field is None and key.endswith("_id"):
            field = fields.get(key[:-3])

        if not field:
            continue

        lookup = field.attname if field.is_relation else field.name
        qs = qs.filter(**{lookup: value})

    search = request.query_params.get("search")
    if search:
        q = Q()
        for name in ("name", "title", "patient_no", "code", "description"):
            if name in fields:
                q |= Q(**{f"{name}__icontains": search})
        if q:
            qs = qs.filter(q)

    return qs


def _paginate(qs, request):
    try:
        page = max(int(request.query_params.get("page", 1) or 1), 1)
    except Exception:
        page = 1
    try:
        page_size = min(max(int(request.query_params.get("page_size", 50) or 50), 1), 100)
    except Exception:
        page_size = 50

    total = qs.count()
    start = (page - 1) * page_size
    end = start + page_size
    rows = list(qs[start:end])

    return {
        "count": total,
        "next": page + 1 if end < total else None,
        "previous": page - 1 if page > 1 else None,
        "results": [serialize_instance(row) for row in rows],
    }


def _get_instance(model, request, kwargs, for_update=False):
    qs = model.objects.all()
    if for_update:
        qs = qs.select_for_update()
    qs = _owner_scope(qs, model, request)
    filters = _path_filter(model, kwargs)

    if not filters:
        raise NotFound({
            "code": "RESOURCE_NOT_FOUND",
            "detail": "No resolvable resource identifier.",
        })

    try:
        return qs.get(**filters)
    except model.DoesNotExist as exc:
        raise NotFound({
            "code": "RESOURCE_NOT_FOUND",
            "detail": f"{model.__name__} was not found.",
        }) from exc


def _write_data(model, request):
    fields = _field_map(model)
    data = {}

    if not isinstance(request.data, dict):
        return data

    for key, value in request.data.items():
        if key in {"id", "pk", "created_at", "updated_at"}:
            continue

        field = fields.get(key)
        if field is None and key.endswith("_id"):
            field = fields.get(key[:-3])

        if field is None:
            continue

        if getattr(field, "primary_key", False) or not getattr(field, "editable", True):
            continue

        target = field.attname if field.is_relation else field.name
        data[target] = value

    user_id = getattr(request.user, "id", None)
    if user_id:
        for name in (
            "created_by",
            "requested_by",
            "author",
            "assessor",
            "doctor",
            "reviewer",
            "changed_by",
            "handled_by",
            "acknowledged_by",
            "recorded_by",
            "finalized_by",
            "resolved_by",
        ):
            field = fields.get(name)
            if field and field.is_relation and field.attname not in data:
                data[field.attname] = user_id

    return data


def _transition(spec, current=None):
    text = " ".join(str(spec.get(k) or "") for k in ("processing", "validation", "api_name"))
    pairs = re.findall(r"\b([A-Z][A-Z0-9_]*)\s*[→>-]+\s*([A-Z][A-Z0-9_]*)\b", text)

    if current:
        for src, dst in pairs:
            if src == current:
                return dst

    if pairs:
        return pairs[0][1]

    action = str(spec.get("endpoint") or "").rstrip("/").rsplit("/", 1)[-1].lower()
    return ACTION_STATUS.get(action)


def _history_model_for(model):
    for candidate in apps.get_models():
        if "history" not in candidate.__name__.lower():
            continue
        for field in candidate._meta.concrete_fields:
            if field.is_relation and field.related_model is model:
                return candidate, field
    return None, None


def _record_history(obj, previous, new, request, reason=None):
    history_model, relation_field = _history_model_for(obj.__class__)
    if not history_model:
        return

    fields = _field_map(history_model)
    payload = {relation_field.attname: obj.pk}

    for name, value in {
        "previous_status": previous or "",
        "from_status": previous or "",
        "new_status": new,
        "to_status": new,
        "reason": reason,
    }.items():
        if name in fields and value is not None:
            payload[name] = value

    if "changed_at" in fields:
        payload["changed_at"] = timezone.now()

    for user_field in ("changed_by", "actor", "user"):
        field = fields.get(user_field)
        if field and field.is_relation:
            payload[field.attname] = getattr(request.user, "id", None)
            break

    try:
        with transaction.atomic():
            history_model.objects.create(**payload)
    except Exception:
        # Keep the parent request transaction usable if an auxiliary
        # status-history insert fails.
        pass


def _audit(request, spec, resource=None, before=None, after=None, outcome="SUCCESS"):
    if not spec.get("audit_required"):
        return

    role = getattr(getattr(request.user, "role", None), "code", None)
    request_id = request.headers.get("X-Request-ID")
    try:
        request_uuid = uuid.UUID(str(request_id)) if request_id else None
    except Exception:
        request_uuid = None

    AuditLog.objects.create(
        actor_user=request.user if getattr(request.user, "id", None) else None,
        actor_login=getattr(request.user, "login_id", None),
        actor_role_code=role,
        source_service="DJANGO_API",
        action=spec["api_id"],
        resource_type=(resource.__class__.__name__ if resource is not None else spec.get("domain")),
        resource=(str(getattr(resource, "pk", "")) if resource is not None else None),
        patient=getattr(resource, "patient_id", None) if resource is not None else None,
        outcome=outcome,
        reason=(request.data.get("reason") if isinstance(getattr(request, "data", None), dict) else None),
        before_json=_safe_value(before),
        after_json=_safe_value(after),
        request_ip=request.META.get("REMOTE_ADDR"),
        user_agent=request.headers.get("User-Agent") or None,
        request=request_uuid,
        occurred_at=timezone.now(),
    )


def _event_type(spec):
    raw = str(spec.get("event") or "").strip()
    if (
        not raw
        or raw in {"-", "X"}
        or "없음" in raw
    ):
        return None

    match = re.search(r"\b([a-z][a-z0-9_.-]+\.v\d+)\b", raw)
    if match:
        return match.group(1)

    token = re.split(r"[\s/→,]+", raw)[0].strip()
    return token.lower() if token and token not in {"-", "O", "X"} else None


def _outbox(spec, resource=None, payload=None):
    event_type = _event_type(spec)
    if not event_type:
        return

    OutboxEvent.objects.create(
        event_type=event_type,
        aggregate_type=(resource.__class__.__name__ if resource is not None else spec.get("domain", "Resource")),
        aggregate=(str(getattr(resource, "pk", "")) if resource is not None else None),
        payload=_safe_value(payload or {}),
        status="PENDING",
        retry_count=0,
        published_at=None,
        created_at=timezone.now(),
    )


def _generic_get(request, spec, kwargs):
    model = _model(spec)
    if model is None:
        return Response({
            "api_id": spec["api_id"],
            "status": "ok",
        }, status=200)

    trailing = spec["endpoint"].rstrip("/").split("/")[-1]
    detail = bool(kwargs) and trailing.startswith("{") and trailing.endswith("}")

    if detail:
        return Response(
            serialize_instance(_get_instance(model, request, kwargs)),
            status=200,
        )

    qs = _owner_scope(model.objects.all(), model, request)
    qs = _apply_query_filters(qs, model, request)

    try:
        qs = qs.order_by("-created_at")
    except Exception:
        pass

    return Response(_paginate(qs, request), status=200)



def _apply_server_defaults(model, data):
    # Server-managed final-DB fields excluded from client request bodies.
    fields = _field_map(model)
    now = timezone.now()

    for name in ("created_at", "updated_at"):
        field = fields.get(name)
        if (
            field is not None
            and name not in data
            and not field.null
            and not field.has_default()
        ):
            data[name] = now

    return data


def _generic_create(request, spec, kwargs):
    model = _model(spec)
    if model is None:
        code = 202 if "202" in str(spec.get("success")) else 200
        return Response({
            "api_id": spec["api_id"],
            "accepted": True,
        }, status=code)

    fields = _field_map(model)
    data = _write_data(model, request)
    data = _apply_server_defaults(model, data)

    for key, value in kwargs.items():
        if key.endswith("_id"):
            base = key[:-3]
            field = fields.get(base)
            if field and field.is_relation and field.attname not in data:
                data[field.attname] = value

    try:
        obj = model.objects.create(**data)
    except (IntegrityError, TypeError, ValueError) as exc:
        raise ContractError({
            "code": "VALIDATION_ERROR",
            "detail": str(exc),
        }) from exc

    after = serialize_instance(obj)
    _audit(request, spec, obj, None, after)
    _outbox(spec, obj, after)

    code = 201 if "201" in str(spec.get("success")) else 200
    return Response(after, status=code)


def _generic_update(request, spec, kwargs):
    model = _model(spec)
    if model is None:
        return Response({"api_id": spec["api_id"], "updated": True}, status=200)

    obj = _get_instance(model, request, kwargs, for_update=True)
    before = serialize_instance(obj)
    data = _write_data(model, request)

    for key, value in data.items():
        setattr(obj, key, value)

    fields = _field_map(model)
    if "updated_at" in fields:
        obj.updated_at = timezone.now()

    obj.save()
    after = serialize_instance(obj)
    _audit(request, spec, obj, before, after)
    _outbox(spec, obj, after)
    return Response(after, status=200)


# --- Appointment response handlers ----------------------------------------

def _appointment_user_payload(user):
    if user is None:
        return None

    return {
        "id": str(user.id),
        "name": user.name,
    }


def _appointment_clinician_payload(clinician):
    return {
        "id": str(clinician.id),
        "name": clinician.user.name,
    }


def _appointment_slot_payload(slot):
    if slot is None:
        return None

    return {
        "id": str(slot.id),
        "start_at": _safe_value(slot.start_at),
        "end_at": _safe_value(slot.end_at),
        "status": slot.status,
        "held_until": _safe_value(slot.held_until),
    }


def _appointment_reschedule_history_payload(appointment):
    history_manager = getattr(appointment, "reschedule_history", None)
    if history_manager is None:
        return []

    return [
        {
            "previous_slot": _appointment_slot_payload(history.previous_slot),
            "changed_slot": _appointment_slot_payload(history.changed_slot),
            "rescheduled_at": _safe_value(history.rescheduled_at),
            "reschedule_reason": history.reschedule_reason,
        }
        for history in history_manager.all()
    ]


def _appointment_payload(appointment):
    slot = _appointment_slot_payload(appointment.slot)

    return {
        "appointment_id": str(appointment.id),
        "patient": {
            "id": str(appointment.patient_id),
            "patient_no": appointment.patient.patient_no,
            "name": appointment.patient.name,
        },
        "hospital": {
            "id": str(appointment.hospital_id),
            "name": appointment.hospital.name,
        },
        "department": {
            "id": str(appointment.department_id),
            "name": appointment.department.name,
        },
        "clinician": _appointment_clinician_payload(
            appointment.clinician
        ),
        "slot": slot,
        "current_slot": slot,
        "requested_slot": _appointment_slot_payload(
            appointment.requested_slot
        ),
        "status": appointment.status,
        "request_type": appointment.request_type,
        "scheduled_at": slot["start_at"],
        "start_at": slot["start_at"],
        "end_at": slot["end_at"],
        "rejection_reason": appointment.rejection_reason,
        "cancel_reason": appointment.cancel_reason,
        "requested_at": _safe_value(appointment.requested_at),
        "reschedule_requested_at": _safe_value(
            appointment.reschedule_requested_at
        ),
        "reschedule_history": _appointment_reschedule_history_payload(
            appointment
        ),
        "confirmed_at": _safe_value(appointment.confirmed_at),
        "cancelled_at": _safe_value(appointment.cancelled_at),
        "completed_at": _safe_value(appointment.completed_at),
        "handled_by": _appointment_user_payload(
            appointment.handled_by
        ),
    }


def _appointment_queryset(spec, request):
    model = _model(spec)
    if model is None:
        raise ContractError({
            "code": "APPOINTMENT_MODEL_NOT_CONFIGURED",
        })

    queryset = model.objects.select_related(
        "patient",
        "hospital",
        "department",
        "clinician__user",
        "slot",
        "requested_slot",
        "handled_by",
    )
    history_model = apps.get_model(
        "appointments",
        "AppointmentRescheduleHistory",
    )
    queryset = queryset.prefetch_related(
        Prefetch(
            "reschedule_history",
            queryset=history_model.objects.select_related(
                "previous_slot",
                "changed_slot",
            ).order_by("-rescheduled_at"),
        )
    )
    return _owner_scope(queryset, model, request)


def _appointment_filter_datetime(queryset, request):
    date_value = request.query_params.get("date")
    from_value = request.query_params.get("from")
    to_value = request.query_params.get("to")

    if date_value:
        parsed = parse_date(date_value)
        if parsed is None:
            raise ContractError({"date": "must be an ISO-8601 date"})
        queryset = queryset.filter(slot__start_at__date=parsed)

    for key, value, date_lookup, datetime_lookup in (
        ("from", from_value, "gte", "gte"),
        ("to", to_value, "lte", "lte"),
    ):
        if not value:
            continue

        parsed_datetime = parse_datetime(value)
        if parsed_datetime is not None:
            if timezone.is_naive(parsed_datetime):
                parsed_datetime = timezone.make_aware(parsed_datetime)
            queryset = queryset.filter(**{
                f"slot__start_at__{datetime_lookup}": parsed_datetime,
            })
            continue

        parsed_date = parse_date(value)
        if parsed_date is None:
            raise ContractError({
                key: "must be an ISO-8601 date or datetime",
            })
        queryset = queryset.filter(**{
            f"slot__start_at__date__{date_lookup}": parsed_date,
        })

    return queryset


def _appointment_filter_fields(queryset, request):
    clinician_id = request.query_params.get("clinician_id")
    department_id = request.query_params.get("department_id")
    status_value = request.query_params.get("status")

    if clinician_id:
        queryset = queryset.filter(clinician_id=clinician_id)
    if department_id:
        queryset = queryset.filter(department_id=department_id)
    if status_value:
        queryset = queryset.filter(status=status_value)

    return _appointment_filter_datetime(queryset, request)


def _slot_query_boundary(value, parameter, *, end_of_day=False):
    parsed_datetime = parse_datetime(value)
    if parsed_datetime is not None:
        if timezone.is_naive(parsed_datetime):
            return timezone.make_aware(parsed_datetime)
        return parsed_datetime

    parsed_date = parse_date(value)
    if parsed_date is None:
        raise ContractError({
            "code": "VALIDATION_ERROR",
            parameter: "must be an ISO-8601 date or datetime",
        })

    boundary_time = time.max if end_of_day else time.min
    return timezone.make_aware(datetime.combine(parsed_date, boundary_time))


def _appointment_generate_available_slots(clinician, target_date):
    """Idempotently fill a date's schedule-derived slots without touching rows."""
    schedule_model = apps.get_model("appointments", "ClinicianSchedule")
    slot_model = apps.get_model("appointments", "AppointmentSlot")
    schedules = schedule_model.objects.filter(
        clinician=clinician,
        weekday=target_date.weekday(),
        is_active=True,
        effective_from__lte=target_date,
    ).filter(
        Q(effective_to__isnull=True) | Q(effective_to__gte=target_date),
    )

    candidates = {}
    for schedule in schedules.order_by("effective_from", "id"):
        schedule_start = timezone.make_aware(
            datetime.combine(target_date, schedule.start_time),
        )
        schedule_end = timezone.make_aware(
            datetime.combine(target_date, schedule.end_time),
        )
        if schedule_end <= schedule_start:
            continue

        start_at = schedule_start
        while start_at < timezone.make_aware(datetime.combine(target_date, time(9))):
            start_at += timedelta(minutes=schedule.slot_minutes)

        while (
            timezone.localtime(start_at).time().replace(tzinfo=None) <= time(18)
            and start_at + timedelta(minutes=schedule.slot_minutes) <= schedule_end
        ):
            candidates.setdefault(start_at, schedule)
            start_at += timedelta(minutes=schedule.slot_minutes)

    if not candidates:
        return

    existing_starts = set(
        slot_model.objects.filter(
            clinician=clinician,
            start_at__in=candidates,
        ).values_list("start_at", flat=True),
    )
    slot_model.objects.bulk_create(
        [
            slot_model(
                clinician=clinician,
                schedule=schedule,
                start_at=start_at,
                end_at=start_at + timedelta(minutes=schedule.slot_minutes),
                status="AVAILABLE",
            )
            for start_at, schedule in candidates.items()
            if start_at not in existing_starts
        ],
        ignore_conflicts=True,
    )


def _appointment_available_slots(request, spec, kwargs):
    """Return only a clinician's AVAILABLE slots for an explicit time range."""
    del spec
    clinician_id = kwargs.get("clinician_id")
    clinician_model = apps.get_model("organizations", "Clinician")
    slot_model = apps.get_model("appointments", "AppointmentSlot")

    try:
        clinician = clinician_model.objects.select_related("user").get(
            pk=clinician_id,
        )
    except (
        clinician_model.DoesNotExist,
        DjangoValidationError,
        TypeError,
        ValueError,
    ) as exc:
        raise NotFound({"code": "CLINICIAN_NOT_FOUND"}) from exc

    date_value = request.query_params.get("date")
    from_value = request.query_params.get("from")
    to_value = request.query_params.get("to")

    if date_value:
        if from_value or to_value:
            raise ContractError({
                "code": "VALIDATION_ERROR",
                "detail": "Use date or the from/to range, not both.",
            })
        target_date = parse_date(date_value)
        if target_date is None:
            raise ContractError({
                "code": "VALIDATION_ERROR",
                "date": "must be an ISO-8601 date",
            })
        _appointment_generate_available_slots(clinician, target_date)
        queryset = slot_model.objects.filter(
            clinician_id=clinician.id,
            status="AVAILABLE",
            start_at__date=target_date,
        )
        payload_from = target_date.isoformat()
        payload_to = target_date.isoformat()
    else:
        if not from_value or not to_value:
            raise ContractError({
                "code": "VALIDATION_ERROR",
                "detail": "date or both from and to are required.",
            })

        range_from = _slot_query_boundary(from_value, "from")
        range_to = _slot_query_boundary(to_value, "to", end_of_day=True)
        if range_from > range_to:
            raise ContractError({
                "code": "VALIDATION_ERROR",
                "detail": "from must be earlier than or equal to to.",
            })
        queryset = slot_model.objects.filter(
            clinician_id=clinician.id,
            status="AVAILABLE",
            start_at__gte=range_from,
            start_at__lte=range_to,
        )
        payload_from = _safe_value(range_from)
        payload_to = _safe_value(range_to)

    slots = queryset.order_by("start_at")
    return Response({
        "clinician": {
            "id": str(clinician.id),
            "name": clinician.user.name,
        },
        "from": payload_from,
        "to": payload_to,
        "slots": [
            {
                "id": str(slot.id),
                "start_at": _safe_value(slot.start_at),
                "end_at": _safe_value(slot.end_at),
                "status": "AVAILABLE",
            }
            for slot in slots
        ],
    }, status=200)


def _appointment_paginated_payload(queryset, request):
    try:
        page = max(int(request.query_params.get("page", 1) or 1), 1)
    except (TypeError, ValueError):
        page = 1

    try:
        page_size = min(
            max(int(request.query_params.get("page_size", 50) or 50), 1),
            100,
        )
    except (TypeError, ValueError):
        page_size = 50

    count = queryset.count()
    start = (page - 1) * page_size
    end = start + page_size
    rows = list(queryset[start:end])

    return {
        "count": count,
        "next": page + 1 if end < count else None,
        "previous": page - 1 if page > 1 else None,
        "results": [_appointment_payload(row) for row in rows],
    }


def _appointment_list(request, spec, kwargs):
    del kwargs
    queryset = _appointment_queryset(spec, request)
    queryset = _appointment_filter_fields(queryset, request)
    queryset = queryset.order_by("-slot__start_at", "-created_at")
    return Response(
        _appointment_paginated_payload(queryset, request),
        status=200,
    )


def _appointment_detail(request, spec, kwargs):
    model = _model(spec)
    queryset = _appointment_queryset(spec, request)
    filters = _path_filter(model, kwargs)

    if not filters:
        raise NotFound({
            "code": "APPOINTMENT_NOT_FOUND",
            "detail": "No appointment identifier was provided.",
        })

    try:
        appointment = queryset.get(**filters)
    except model.DoesNotExist as exc:
        raise NotFound({
            "code": "APPOINTMENT_NOT_FOUND",
            "detail": "Appointment was not found.",
        }) from exc

    return Response(_appointment_payload(appointment), status=200)


def _appointment_request_list(request, spec, kwargs):
    del kwargs
    queryset = _appointment_queryset(spec, request).filter(
        Q(status="REQUESTED") | Q(requested_slot__isnull=False)
    )
    queryset = _appointment_filter_fields(queryset, request)
    queryset = queryset.order_by("slot__start_at", "requested_at")
    return Response(
        _appointment_paginated_payload(queryset, request),
        status=200,
    )


def _staff_appointment_list(request, spec, kwargs):
    del kwargs
    queryset = _appointment_queryset(spec, request)
    queryset = _appointment_filter_fields(queryset, request)
    queryset = queryset.order_by("slot__start_at", "created_at")
    rows = list(queryset)

    clinician = None
    clinician_ids = {row.clinician_id for row in rows}
    if len(clinician_ids) == 1:
        clinician = _appointment_clinician_payload(rows[0].clinician)

    return Response({
        "from": request.query_params.get("from"),
        "to": request.query_params.get("to"),
        "clinician": clinician,
        "appointments": [
            _appointment_payload(row)
            for row in rows
        ],
    }, status=200)

def _generic_delete(request, spec, kwargs):
    model = _model(spec)
    if model is None:
        return Response(status=204)

    obj = _get_instance(model, request, kwargs, for_update=True)
    before = serialize_instance(obj)
    fields = _field_map(model)
    processing = str(spec.get("processing") or "")

    if "비활성" in processing and "is_active" in fields:
        obj.is_active = False
        obj.save(update_fields=["is_active"])
        after = serialize_instance(obj)
    elif "비활성" in processing and "status" in fields:
        obj.status = "INACTIVE"
        obj.save(update_fields=["status"])
        after = serialize_instance(obj)
    else:
        obj.delete()
        after = None

    _audit(request, spec, obj, before, after)
    _outbox(spec, obj, {"deleted": after is None})
    return Response(status=204)


def _generic_action(request, spec, kwargs):
    model = _model(spec)
    if model is None:
        return _generic_create(request, spec, kwargs)

    obj = _get_instance(model, request, kwargs, for_update=True)
    before = serialize_instance(obj)
    fields = _field_map(model)
    action = spec["endpoint"].rstrip("/").rsplit("/", 1)[-1].lower()

    if action == "read" and "is_read" in fields:
        obj.is_read = True
        if "read_at" in fields:
            obj.read_at = timezone.now()

    elif action == "view-response":
        previous = getattr(obj, "status", None)

        if previous != "RESPONDED":
            raise ContractError({
                "code": "INVALID_CONSULTATION_STATUS",
                "detail": "view-response requires RESPONDED status.",
            })

        viewed_by = fields.get("response_viewed_by")
        if viewed_by and viewed_by.is_relation:
            setattr(obj, viewed_by.attname, request.user.id)

        if "response_viewed_at" in fields:
            obj.response_viewed_at = timezone.now()

        if "status" in fields:
            obj.status = "CLOSED"
            _record_history(
                obj,
                previous,
                "CLOSED",
                request,
                reason=(
                    request.data.get("reason")
                    if isinstance(request.data, dict)
                    else None
                ),
            )

    elif action in {"block", "unblock"} and "status" in fields:
        previous = getattr(obj, "status", None)
        obj.status = ACTION_STATUS[action]
        _record_history(obj, previous, obj.status, request)
        if "held_until" in fields:
            obj.held_until = None
    else:
        if "status" in fields:
            previous = getattr(obj, "status", None)
            new = _transition(spec, previous)
            if new:
                obj.status = new
                reason = None
                if isinstance(request.data, dict):
                    reason = (
                        request.data.get("reason")
                        or request.data.get("memo")
                        or request.data.get("rejection_reason")
                    )
                _record_history(obj, previous, new, request, reason)

        timestamp_fields = {
            "acknowledge": ("acknowledged_at",),
            "approve": ("approved_at",),
            "cancel": ("cancelled_at", "ended_at"),
            "close": ("closed_at",),
            "complete": ("completed_at", "ended_at"),
            "finalize": ("finalized_at",),
            "respond": ("responded_at",),
            "retire": ("retired_at",),
            "start": ("started_at",),
            "validate": ("validated_at",),
        }
        for name in timestamp_fields.get(action, ()):
            if name in fields:
                setattr(obj, name, timezone.now())

    write_data = _write_data(model, request)
    if model._meta.label_lower == "consultations.consultation":
        # Consultation state actions must never replace the original requester
        # or explicitly assigned clinician with the action actor/body values.
        write_data.pop("requested_by_id", None)
        write_data.pop("assigned_to_id", None)

    for key, value in write_data.items():
        setattr(obj, key, value)

    if "updated_at" in fields:
        obj.updated_at = timezone.now()

    obj.save()
    after = serialize_instance(obj)
    _audit(request, spec, obj, before, after)
    _outbox(spec, obj, after)
    return Response(after, status=200)


# --- Contract-specific handlers for high-risk endpoints ---------------------

def _schedule_put(request, spec, kwargs):
    model = _model(spec)
    clinician_id = kwargs.get("clinician_id")
    if model is None or clinician_id is None:
        raise ContractError({"clinician_id": "required"})

    rows = request.data.get("schedules") if isinstance(request.data, dict) else None
    if rows is None:
        rows = request.data if isinstance(request.data, list) else [request.data]
    if not isinstance(rows, list):
        raise ContractError({"schedules": "must be a list"})

    fields = _field_map(model)
    model.objects.filter(clinician_id=clinician_id).delete()
    created = []

    for row in rows:
        if not isinstance(row, dict):
            continue
        data = {}
        for key, value in row.items():
            field = fields.get(key)
            if field and not field.primary_key:
                data[field.attname if field.is_relation else field.name] = value
        clinician = fields.get("clinician")
        if clinician and clinician.is_relation:
            data[clinician.attname] = clinician_id
        created.append(model.objects.create(**data))

    payload = {"results": [serialize_instance(x) for x in created]}
    _audit(request, spec, created[0] if created else None, None, payload)
    return Response(payload, status=200)


def _appointment_validate_start_time(start_at):
    local_start = timezone.localtime(start_at)
    if not time(9) <= local_start.time().replace(tzinfo=None) <= time(18):
        raise ContractError({
            "code": "VALIDATION_ERROR",
            "start_at": "Appointment times must be between 09:00 and 18:00.",
        })


def _appointment_slot_for_create(request):
    """Lock an existing slot or create one from an active clinician schedule."""
    data = request.data
    slot_model = apps.get_model("appointments", "AppointmentSlot")

    if data.get("slot_id"):
        try:
            slot = (
                slot_model.objects.select_for_update()
                .select_related("clinician__department__hospital")
                .get(pk=data["slot_id"])
            )
        except (
            slot_model.DoesNotExist,
            DjangoValidationError,
            ValueError,
            TypeError,
        ) as exc:
            raise NotFound({"code": "SLOT_NOT_FOUND"}) from exc
        _appointment_validate_start_time(slot.start_at)
        return slot

    clinician_id = data.get("clinician_id")
    start_at_value = data.get("start_at") or data.get("scheduled_at")
    if not clinician_id or not start_at_value:
        raise ContractError({
            "code": "VALIDATION_ERROR",
            "slot_id": "slot_id or clinician_id and start_at are required.",
        })

    start_at = parse_datetime(str(start_at_value))
    if start_at is None:
        raise ContractError({
            "code": "VALIDATION_ERROR",
            "start_at": "must be an ISO-8601 datetime.",
        })
    if timezone.is_naive(start_at):
        start_at = timezone.make_aware(start_at)
    _appointment_validate_start_time(start_at)

    clinician_model = apps.get_model("organizations", "Clinician")
    try:
        clinician = clinician_model.objects.select_related(
            "department__hospital",
        ).get(pk=clinician_id)
    except (
        clinician_model.DoesNotExist,
        DjangoValidationError,
        ValueError,
        TypeError,
    ) as exc:
        raise NotFound({"code": "CLINICIAN_NOT_FOUND"}) from exc

    slot = (
        slot_model.objects.select_for_update()
        .select_related("clinician__department__hospital")
        .filter(clinician=clinician, start_at=start_at)
        .first()
    )
    if slot is not None:
        return slot

    local_start = timezone.localtime(start_at)
    schedule_model = apps.get_model("appointments", "ClinicianSchedule")
    schedule = (
        schedule_model.objects.filter(
            clinician=clinician,
            weekday=local_start.weekday(),
            is_active=True,
            effective_from__lte=local_start.date(),
        )
        .filter(Q(effective_to__isnull=True) | Q(effective_to__gte=local_start.date()))
        .order_by("effective_from", "id")
        .first()
    )
    if schedule is None:
        raise ContractError({
            "code": "SLOT_SCHEDULE_NOT_FOUND",
            "detail": "No active clinician schedule covers this appointment time.",
        })

    start_time = local_start.time().replace(tzinfo=None)
    end_at = start_at + timedelta(minutes=schedule.slot_minutes)
    local_end = timezone.localtime(end_at)
    minutes_from_schedule_start = (
        datetime.combine(date.min, start_time)
        - datetime.combine(date.min, schedule.start_time)
    ).total_seconds() / 60
    if (
        start_time < schedule.start_time
        or local_end.date() != local_start.date()
        or local_end.time().replace(tzinfo=None) > schedule.end_time
        or minutes_from_schedule_start % schedule.slot_minutes != 0
    ):
        raise ContractError({
            "code": "VALIDATION_ERROR",
            "start_at": "The appointment time does not match the clinician schedule.",
        })

    try:
        with transaction.atomic():
            slot = slot_model.objects.create(
                clinician=clinician,
                schedule=schedule,
                start_at=start_at,
                end_at=end_at,
                status="AVAILABLE",
            )
    except IntegrityError:
        slot = (
            slot_model.objects.select_for_update()
            .select_related("clinician__department__hospital")
            .get(clinician=clinician, start_at=start_at)
        )
    else:
        slot = (
            slot_model.objects.select_for_update()
            .select_related("clinician__department__hospital")
            .get(pk=slot.pk)
        )
    return slot


@transaction.atomic
def _appointment_create(request, spec, kwargs):
    del kwargs
    model = _model(spec)
    if model is None:
        raise ContractError({"code": "APPOINTMENT_MODEL_NOT_CONFIGURED"})
    if not isinstance(request.data, dict):
        raise ContractError({
            "code": "VALIDATION_ERROR",
            "slot_id": "slot_id or clinician_id and start_at are required.",
        })

    patient = _patient_for_user(request.user)
    if patient is None:
        raise ContractError({"code": "PATIENT_PROFILE_REQUIRED"})

    slot = _appointment_slot_for_create(request)

    if slot.status != "AVAILABLE":
        raise ContractConflict({
            "code": "SLOT_NOT_AVAILABLE",
            "detail": "The appointment slot is not available.",
        })
    if model.objects.filter(
        patient=patient,
        status__in=("REQUESTED", "CONFIRMED"),
        slot__start_at=slot.start_at,
    ).exists():
        raise ContractConflict({
            "code": "SLOT_NOT_AVAILABLE",
            "detail": "The patient already has an active appointment at this time.",
        })

    now = timezone.now()
    slot.status = "HELD"
    slot.held_until = now + timedelta(
        minutes=settings.APPOINTMENT_HOLD_TTL_MINUTES
    )
    slot.version += 1
    slot.save(update_fields=["status", "held_until", "version"])

    obj = model.objects.create(
        patient=patient,
        hospital=slot.clinician.department.hospital,
        department=slot.clinician.department,
        clinician=slot.clinician,
        slot=slot,
        status="REQUESTED",
        request_type="NEW",
        requested_at=now,
        created_at=now,
        updated_at=now,
    )
    _appointment_history(obj, None, "REQUESTED", request)
    obj = _appointment_refresh(obj)
    after = _appointment_payload(obj)
    _audit(request, spec, obj, None, after)
    _outbox(spec, obj, after)
    _create_appointment_notification(
        appointment=obj,
        recipient_user=obj.clinician.user,
        request=request,
        title="New appointment request",
        body="A new appointment request requires review.",
    )
    return Response(after, status=201)


def _appointment_locked(kwargs):
    appointment_model = apps.get_model("appointments", "Appointment")
    appointment_id = kwargs.get("appointment_id")
    if appointment_id is None:
        raise NotFound({"code": "APPOINTMENT_NOT_FOUND"})
    try:
        return (
            appointment_model.objects.select_for_update(of=("self",))
            .select_related(
                "patient", "hospital", "department", "clinician__user",
                "slot", "requested_slot", "handled_by",
            )
            .get(pk=appointment_id)
        )
    except appointment_model.DoesNotExist as exc:
        raise NotFound({"code": "APPOINTMENT_NOT_FOUND"}) from exc


def _appointment_slots_locked(appointment, *additional_slot_ids):
    slot_model = apps.get_model("appointments", "AppointmentSlot")
    slot_ids = {appointment.slot_id}
    if appointment.requested_slot_id:
        slot_ids.add(appointment.requested_slot_id)
    slot_ids.update(slot_id for slot_id in additional_slot_ids if slot_id)
    return {
        slot.pk: slot
        for slot in slot_model.objects.select_for_update()
        .filter(pk__in=slot_ids).order_by("pk")
    }


def _appointment_history(appointment, previous, new, request, reason=None):
    history_model = apps.get_model("appointments", "AppointmentStatusHistory")
    history_model.objects.create(
        appointment=appointment,
        from_status=previous,
        to_status=new,
        changed_by=request.user,
        reason=reason,
    )


def _appointment_action_reason(request, *names):
    if not isinstance(request.data, dict):
        return None
    for name in names:
        value = request.data.get(name)
        if value is not None and str(value).strip():
            return str(value).strip()
    return None


def _appointment_require_patient_owner(appointment, request):
    patient = _patient_for_user(request.user)
    if patient is None or appointment.patient_id != patient.id:
        raise PermissionDenied({
            "code": "FORBIDDEN_PERMISSION",
            "detail": "This appointment does not belong to the current patient.",
        })


def _appointment_refresh(appointment):
    return (
        appointment.__class__.objects
        .select_related(
            "patient", "hospital", "department", "clinician__user",
            "slot", "requested_slot", "handled_by",
        )
        .get(pk=appointment.pk)
    )


def _create_appointment_notification(*, appointment, recipient_user, request, title, body):
    """Notify only a concrete appointment owner; never infer a role-wide recipient."""
    from apps.notifications.services.notifications import create_notification_for_user

    return create_notification_for_user(
        recipient_user=recipient_user,
        category="APPOINTMENT",
        severity="INFO",
        title=title,
        body=body,
        data_json={
            "patient_id": str(appointment.patient_id),
            "resource_type": "Appointment",
            "resource_id": str(appointment.id),
            "actor_user_id": str(request.user.id),
        },
    )


@transaction.atomic
def _appointment_accept(request, spec, kwargs):
    appointment = _appointment_locked(kwargs)
    is_new_request = appointment.status == "REQUESTED"
    is_reschedule = (
        appointment.status == "CONFIRMED"
        and appointment.requested_slot_id is not None
    )
    if not is_new_request and not is_reschedule:
        raise ContractConflict({
            "code": "APPOINTMENT_ALREADY_PROCESSED",
            "detail": "The appointment has no request that can be accepted.",
        })
    slots = _appointment_slots_locked(appointment)
    current_slot = slots[appointment.slot_id]
    requested_slot = (
        slots[appointment.requested_slot_id]
        if is_reschedule
        else None
    )
    slot_to_book = requested_slot or current_slot
    now = timezone.now()
    if (
        slot_to_book.status != "HELD"
        or slot_to_book.held_until is None
        or slot_to_book.held_until <= now
        or (is_reschedule and current_slot.status != "BOOKED")
    ):
        raise ContractConflict({
            "code": "APPOINTMENT_SLOT_CONFLICT",
            "detail": "The appointment slot is not actively held.",
        })

    previous = appointment.status
    before = serialize_instance(appointment)
    reason = _appointment_action_reason(request, "memo", "reason")
    if requested_slot is not None:
        current_slot.status = "AVAILABLE"
        current_slot.held_until = None
        current_slot.version += 1
        current_slot.save(update_fields=["status", "held_until", "version"])
    slot_to_book.status = "BOOKED"
    slot_to_book.held_until = None
    slot_to_book.version += 1
    slot_to_book.save(update_fields=["status", "held_until", "version"])
    appointment.status = "CONFIRMED"
    if requested_slot is not None:
        appointment.slot = requested_slot
        appointment.requested_slot = None
    appointment.confirmed_at = now
    appointment.handled_by = request.user
    appointment.reschedule_requested_at = None
    appointment.updated_at = now
    appointment.save(update_fields=[
        "status", "slot", "requested_slot", "confirmed_at", "handled_by",
        "reschedule_requested_at", "updated_at",
    ])
    if requested_slot is not None:
        reschedule_history_model = apps.get_model(
            "appointments",
            "AppointmentRescheduleHistory",
        )
        reschedule_history_model.objects.create(
            appointment=appointment,
            previous_slot=current_slot,
            changed_slot=requested_slot,
            rescheduled_at=now,
            reschedule_reason=reason,
            changed_by=request.user,
        )
    _appointment_history(appointment, previous, "CONFIRMED", request, reason)
    appointment = _appointment_refresh(appointment)
    after = _appointment_payload(appointment)
    after["confirmed_by"] = _appointment_user_payload(request.user)
    _audit(request, spec, appointment, before, after)
    _outbox(spec, appointment, after)
    return Response(after, status=200)


@transaction.atomic
def _appointment_reject(request, spec, kwargs):
    reason = _appointment_action_reason(request, "rejection_reason")
    if reason is None:
        raise ContractError({
            "code": "VALIDATION_ERROR",
            "rejection_reason": "This field is required.",
        })
    appointment = _appointment_locked(kwargs)
    is_new_request = appointment.status == "REQUESTED"
    is_reschedule = (
        appointment.status == "CONFIRMED"
        and appointment.requested_slot_id is not None
    )
    if not is_new_request and not is_reschedule:
        raise ContractConflict({
            "code": "APPOINTMENT_INVALID_STATE",
            "detail": "The appointment has no request that can be rejected.",
        })
    slots = _appointment_slots_locked(appointment)
    current_slot = slots[appointment.slot_id]
    slot_to_release = (
        slots[appointment.requested_slot_id]
        if is_reschedule
        else current_slot
    )
    now = timezone.now()
    if (
        slot_to_release.status != "HELD"
        or slot_to_release.held_until is None
        or slot_to_release.held_until <= now
        or (is_reschedule and current_slot.status != "BOOKED")
    ):
        raise ContractConflict({
            "code": "APPOINTMENT_SLOT_CONFLICT",
            "detail": "The appointment slot is not actively held.",
        })

    previous = appointment.status
    before = serialize_instance(appointment)
    slot_to_release.status = "AVAILABLE"
    slot_to_release.held_until = None
    slot_to_release.version += 1
    slot_to_release.save(update_fields=["status", "held_until", "version"])
    appointment.status = "CONFIRMED" if is_reschedule else "REJECTED"
    appointment.rejection_reason = reason
    appointment.handled_by = request.user
    appointment.requested_slot = None
    appointment.reschedule_requested_at = None
    appointment.updated_at = now
    appointment.save(update_fields=[
        "status", "rejection_reason", "handled_by", "requested_slot",
        "reschedule_requested_at", "updated_at",
    ])
    _appointment_history(appointment, previous, appointment.status, request, reason)
    appointment = _appointment_refresh(appointment)
    after = _appointment_payload(appointment)
    after["rejected_by"] = _appointment_user_payload(request.user)
    after["rejected_at"] = _safe_value(now)
    after["released_slot"] = _appointment_slot_payload(slot_to_release)
    _audit(request, spec, appointment, before, after)
    _outbox(spec, appointment, after)
    return Response(after, status=200)


@transaction.atomic
def _appointment_cancel(request, spec, kwargs):
    appointment = _appointment_locked(kwargs)
    _appointment_require_patient_owner(appointment, request)
    if appointment.status not in {"REQUESTED", "CONFIRMED"}:
        raise ContractConflict({
            "code": "APPOINTMENT_INVALID_STATE",
            "detail": "Only a requested or confirmed appointment can be cancelled.",
        })
    slots = _appointment_slots_locked(appointment)
    current_slot = slots[appointment.slot_id]
    expected_status = "HELD" if appointment.status == "REQUESTED" else "BOOKED"
    if current_slot.status != expected_status:
        raise ContractConflict({
            "code": "APPOINTMENT_SLOT_CONFLICT",
            "detail": "The current appointment slot has an invalid state.",
        })
    requested_slot = slots.get(appointment.requested_slot_id) if appointment.requested_slot_id else None
    if requested_slot is not None and requested_slot.status != "HELD":
        raise ContractConflict({
            "code": "APPOINTMENT_SLOT_CONFLICT",
            "detail": "The requested appointment slot has an invalid state.",
        })

    previous = appointment.status
    before = serialize_instance(appointment)
    released_slots = []
    for slot in (current_slot, requested_slot):
        if slot is None:
            continue
        slot.status = "AVAILABLE"
        slot.held_until = None
        slot.version += 1
        slot.save(update_fields=["status", "held_until", "version"])
        released_slots.append(_appointment_slot_payload(slot))
    now = timezone.now()
    reason = _appointment_action_reason(request, "reason", "cancel_reason")
    appointment.status = "CANCELLED"
    appointment.cancel_reason = reason
    appointment.cancelled_at = now
    appointment.requested_slot = None
    appointment.reschedule_requested_at = None
    appointment.updated_at = now
    appointment.save(update_fields=[
        "status", "cancel_reason", "cancelled_at", "requested_slot",
        "reschedule_requested_at", "updated_at",
    ])
    _appointment_history(appointment, previous, "CANCELLED", request, reason)
    appointment = _appointment_refresh(appointment)
    after = _appointment_payload(appointment)
    after["released_slots"] = released_slots
    _audit(request, spec, appointment, before, after)
    _outbox(spec, appointment, after)
    _create_appointment_notification(
        appointment=appointment,
        recipient_user=appointment.handled_by or appointment.clinician.user,
        request=request,
        title="Appointment cancelled",
        body="An appointment has been cancelled.",
    )
    return Response(after, status=200)


@transaction.atomic
def _appointment_reschedule(request, spec, kwargs):
    if not isinstance(request.data, dict) or not request.data.get("new_slot_id"):
        raise ContractError({
            "code": "VALIDATION_ERROR",
            "new_slot_id": "This field is required.",
        })
    appointment = _appointment_locked(kwargs)
    _appointment_require_patient_owner(appointment, request)
    if appointment.status not in {"REQUESTED", "CONFIRMED"}:
        raise ContractConflict({
            "code": "APPOINTMENT_INVALID_STATE",
            "detail": "Only a requested or confirmed appointment can be rescheduled.",
        })
    if appointment.status == "REQUESTED" and appointment.request_type != "NEW":
        raise ContractConflict({
            "code": "APPOINTMENT_RESCHEDULE_CONFLICT",
            "detail": "The requested appointment already has a reschedule request.",
        })
    if appointment.status == "CONFIRMED" and appointment.requested_slot_id:
        raise ContractConflict({
            "code": "APPOINTMENT_RESCHEDULE_CONFLICT",
            "detail": "The confirmed appointment already has a requested slot.",
        })

    new_slot_id = request.data["new_slot_id"]
    if str(new_slot_id) == str(appointment.slot_id):
        raise ContractConflict({
            "code": "APPOINTMENT_RESCHEDULE_CONFLICT",
            "detail": "The new slot must differ from the current slot.",
        })
    try:
        slots = _appointment_slots_locked(appointment, new_slot_id)
        new_slot = next(
            slot for slot_id, slot in slots.items()
            if str(slot_id) == str(new_slot_id)
        )
    except (StopIteration, DjangoValidationError, ValueError, TypeError) as exc:
        raise NotFound({"code": "SLOT_NOT_FOUND"}) from exc

    current_slot = slots[appointment.slot_id]
    if new_slot.status != "AVAILABLE":
        raise ContractConflict({
            "code": "SLOT_NOT_AVAILABLE",
            "detail": "The requested new slot is not available.",
        })
    if new_slot.clinician_id != appointment.clinician_id:
        raise ContractConflict({
            "code": "APPOINTMENT_RESCHEDULE_CONFLICT",
            "detail": "The new slot must belong to the appointment clinician.",
        })

    now = timezone.now()
    held_until = now + timedelta(
        minutes=settings.APPOINTMENT_HOLD_TTL_MINUTES
    )
    before = serialize_instance(appointment)
    if appointment.status == "REQUESTED":
        if current_slot.status != "HELD":
            raise ContractConflict({
                "code": "APPOINTMENT_SLOT_CONFLICT",
                "detail": "The current appointment slot is not held.",
            })
        current_slot.status = "AVAILABLE"
        current_slot.held_until = None
        current_slot.version += 1
        current_slot.save(update_fields=["status", "held_until", "version"])
        new_slot.status = "HELD"
        new_slot.held_until = held_until
        new_slot.version += 1
        new_slot.save(update_fields=["status", "held_until", "version"])
        appointment.slot = new_slot
    else:
        if current_slot.status != "BOOKED":
            raise ContractConflict({
                "code": "APPOINTMENT_SLOT_CONFLICT",
                "detail": "The current appointment slot is not booked.",
            })
        new_slot.status = "HELD"
        new_slot.held_until = held_until
        new_slot.version += 1
        new_slot.save(update_fields=["status", "held_until", "version"])
        appointment.requested_slot = new_slot

    appointment.request_type = "RESCHEDULE"
    appointment.reschedule_requested_at = now
    appointment.updated_at = now
    update_fields = ["request_type", "reschedule_requested_at", "updated_at"]
    update_fields.append("slot" if appointment.status == "REQUESTED" else "requested_slot")
    appointment.save(update_fields=update_fields)
    appointment = _appointment_refresh(appointment)
    after = _appointment_payload(appointment)
    _audit(request, spec, appointment, before, after)
    _outbox(spec, appointment, after)
    _create_appointment_notification(
        appointment=appointment,
        recipient_user=appointment.handled_by or appointment.clinician.user,
        request=request,
        title="Appointment change requested",
        body="An appointment change request requires review.",
    )
    return Response(after, status=200)


@transaction.atomic
def _appointment_complete(request, spec, kwargs):
    appointment = _appointment_locked(kwargs)
    if (
        _role_code(request.user) in {"NEUROLOGIST", "NEUROSURGEON"}
        and appointment.clinician.user_id != request.user.id
    ):
        raise PermissionDenied({
            "code": "FORBIDDEN_PERMISSION",
            "detail": "Clinicians may complete only their own appointments.",
        })
    if appointment.status != "CONFIRMED":
        raise ContractConflict({
            "code": "APPOINTMENT_INVALID_STATE",
            "detail": "Only a confirmed appointment can be completed.",
        })
    previous = appointment.status
    before = serialize_instance(appointment)
    now = timezone.now()
    appointment.status = "COMPLETED"
    appointment.completed_at = now
    appointment.updated_at = now
    appointment.save(update_fields=["status", "completed_at", "updated_at"])
    _appointment_history(appointment, previous, "COMPLETED", request)
    appointment = _appointment_refresh(appointment)
    after = _appointment_payload(appointment)
    after["completed_by"] = _appointment_user_payload(request.user)
    _audit(request, spec, appointment, before, after)
    _outbox(spec, appointment, after)
    return Response(after, status=200)


@transaction.atomic
def _appointment_correct(request, spec, kwargs):
    target_status = (
        request.data.get("target_status")
        if isinstance(request.data, dict)
        else None
    )
    reason = _appointment_action_reason(request, "reason")
    if target_status != "REQUESTED":
        raise ContractError({
            "code": "VALIDATION_ERROR",
            "target_status": "Only REQUESTED is supported.",
        })
    if reason is None:
        raise ContractError({
            "code": "VALIDATION_ERROR",
            "reason": "This field is required.",
        })

    appointment = _appointment_locked(kwargs)
    if appointment.status not in {"REJECTED", "CONFIRMED"}:
        raise ContractConflict({
            "code": "APPOINTMENT_CORRECTION_INVALID_STATE",
            "detail": "Only a rejected or confirmed appointment can be corrected.",
        })
    if appointment.requested_slot_id is not None:
        raise ContractConflict({
            "code": "APPOINTMENT_CORRECTION_CONFLICT",
            "detail": "An appointment with a pending reschedule cannot be corrected.",
        })

    slot = _appointment_slots_locked(appointment)[appointment.slot_id]
    expected_slot_status = (
        "AVAILABLE" if appointment.status == "REJECTED" else "BOOKED"
    )
    if slot.status != expected_slot_status:
        raise ContractConflict({
            "code": "APPOINTMENT_SLOT_CONFLICT",
            "detail": "The appointment slot has an invalid state for correction.",
        })

    previous = appointment.status
    before = serialize_instance(appointment)
    now = timezone.now()
    slot.status = "HELD"
    slot.held_until = now + timedelta(
        minutes=settings.APPOINTMENT_HOLD_TTL_MINUTES
    )
    slot.version += 1
    slot.save(update_fields=["status", "held_until", "version"])

    appointment.status = "REQUESTED"
    appointment.rejection_reason = None
    appointment.confirmed_at = None
    appointment.handled_by = None
    appointment.updated_at = now
    appointment.save(update_fields=[
        "status", "rejection_reason", "confirmed_at", "handled_by",
        "updated_at",
    ])
    _appointment_history(
        appointment,
        previous,
        "REQUESTED",
        request,
        reason,
    )
    appointment = _appointment_refresh(appointment)
    after = _appointment_payload(appointment)
    after["previous_status"] = previous
    after["correction_reason"] = reason
    _audit(request, spec, appointment, before, after)
    return Response(after, status=200)


def _notification_preferences_get(request, spec, kwargs):
    setting_model = apps.get_model("notifications", "NotificationSetting")
    pref_model = apps.get_model("notifications", "NotificationCategoryPreference")

    setting = setting_model.objects.filter(user=request.user).first()
    preferences_by_category = {
        preference.category: preference
        for preference in pref_model.objects.filter(user=request.user)
    }
    def preference_payload(category, preference=None):
        required = str(category).upper() == "CRITICAL"
        return {
            "category": category,
            "enabled": True if required else (
                preference.enabled if preference is not None else True
            ),
            "required": required,
        }

    categories = []
    for category in DEFAULT_NOTIFICATION_PREFERENCE_CATEGORIES:
        preference = preferences_by_category.pop(category, None)
        categories.append(preference_payload(category, preference))
    return Response({
        "dnd": serialize_instance(setting) if setting else {
            "dnd_enabled": False,
            "dnd_start": None,
            "dnd_end": None,
            "timezone": "Asia/Seoul",
        },
        "categories": categories,
    }, status=200)


def _notification_preferences_patch(request, spec, kwargs):
    setting_model = apps.get_model("notifications", "NotificationSetting")
    pref_model = apps.get_model("notifications", "NotificationCategoryPreference")
    fields = _field_map(setting_model)

    defaults = {}
    for key in ("dnd_enabled", "dnd_start", "dnd_end", "timezone"):
        if key in request.data and key in fields:
            defaults[key] = request.data[key]

    setting_model.objects.update_or_create(
        user=request.user,
        defaults=defaults,
    )

    categories = request.data.get("categories") or {}
    if isinstance(categories, dict):
        for category, enabled in categories.items():
            if category not in DEFAULT_NOTIFICATION_PREFERENCE_CATEGORIES:
                continue
            required = str(category).upper() == "CRITICAL"
            pref_model.objects.update_or_create(
                user=request.user,
                category=category,
                defaults={"enabled": True if required else bool(enabled)},
            )

    return _notification_preferences_get(request, spec, kwargs)


INITIAL_SCREENING_ITEM_CODES = (
    "BALANCE",
    "EYES",
    "FACE",
    "ARM",
    "SPEECH",
    "CONSCIOUSNESS",
)


def _assessment_item_group(item_code):
    if item_code in INITIAL_SCREENING_ITEM_CODES:
        return "INITIAL_SCREENING"
    if item_code.startswith("FAST_"):
        return "FAST"
    if item_code in {"BP_SYS", "BP_DIA", "HEART_RATE", "RESP_RATE", "BODY_TEMP", "SPO2"}:
        return "VITAL"
    if item_code in {"HEIGHT_CM", "WEIGHT_KG"}:
        return "MEASUREMENT"
    return "ASSESSMENT"


def _assessment_item_payload(item):
    return {
        "item_code": item.item_code,
        "value_text": item.value_text,
        "value_numeric": item.value_numeric,
        "unit": item.unit,
        "score": item.score,
        "is_red_flag": item.is_red_flag,
        "note": item.note,
    }


def _initial_screening_score(value, item_code):
    if isinstance(value, bool) or value is None:
        raise ContractError({item_code: "value_numeric must be an integer from 1 to 5."})
    try:
        decimal_value = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ContractError({item_code: "value_numeric must be an integer from 1 to 5."}) from exc

    if decimal_value != decimal_value.to_integral_value() or not 1 <= decimal_value <= 5:
        raise ContractError({item_code: "value_numeric must be an integer from 1 to 5."})
    return int(decimal_value)


def _assessment_start(request, spec, kwargs):
    del kwargs
    assessment_model = apps.get_model("assessments", "InitialAssessment")
    encounter_model = apps.get_model("clinical_records", "Encounter")

    if not isinstance(request.data, dict):
        raise ContractError({
            "code": "VALIDATION_ERROR",
            "detail": "A JSON object is required.",
        })

    encounter_id = request.data.get("encounter_id")
    if not encounter_id:
        raise ContractError({
            "code": "ENCOUNTER_ID_REQUIRED",
            "detail": "encounter_id is required.",
        })

    try:
        encounter = (
            encounter_model.objects
            .select_for_update()
            .get(pk=encounter_id)
        )
    except (
        encounter_model.DoesNotExist,
        DjangoValidationError,
        TypeError,
        ValueError,
    ) as exc:
        raise NotFound({
            "code": "ENCOUNTER_NOT_FOUND",
            "detail": "Encounter was not found.",
        }) from exc

    if (
        encounter.status in {"COMPLETED", "CANCELLED"}
        or encounter.ended_at is not None
    ):
        raise ContractConflict({
            "code": "ENCOUNTER_NOT_ACTIVE",
            "detail": "Only active encounters can start an assessment.",
        })

    existing_draft = (
        assessment_model.objects
        .filter(
            encounter=encounter,
            status="DRAFT",
        )
        .order_by("-created_at", "-id")
        .first()
    )
    if existing_draft is not None:
        raise ContractConflict({
            "code": "ASSESSMENT_ALREADY_IN_PROGRESS",
            "detail": "A DRAFT assessment already exists for this encounter.",
        })

    now = timezone.now()
    assessment = assessment_model.objects.create(
        encounter=encounter,
        assessor=request.user,
        status="DRAFT",
        created_at=now,
        updated_at=now,
    )

    payload = {
        "assessment_id": str(assessment.id),
        "encounter_id": str(encounter.id),
        "status": assessment.status,
        "assessor_id": str(request.user.id),
        "created_at": assessment.created_at,
    }
    _audit(request, spec, assessment, None, payload)
    _outbox(spec, assessment, payload)
    return Response(payload, status=201)


def _assessment_detail_payload(assessment):
    item_model = apps.get_model("assessments", "AssessmentItem")
    items = item_model.objects.filter(assessment=assessment).order_by("recorded_at", "id")
    return {
        "assessment_id": str(assessment.id),
        "encounter_id": str(assessment.encounter_id),
        "status": assessment.status,
        "total_score": assessment.total_score,
        "triage_priority": assessment.triage_priority,
        "onset_at": assessment.onset_at,
        "lkw_at": assessment.lkw_at,
        "symptom_note": assessment.symptom_note,
        "assigned_neurologist": (
            {"id": str(assessment.assigned_neurologist_id), "name": assessment.assigned_neurologist.name}
            if assessment.assigned_neurologist_id else None
        ),
        "items": [_assessment_item_payload(item) for item in items],
        "created_at": assessment.created_at,
        "updated_at": assessment.updated_at,
    }


def _assessment_detail(request, spec, kwargs):
    del spec
    assessment_model = apps.get_model("assessments", "InitialAssessment")
    assessment = _get_instance(assessment_model, request, kwargs)
    return Response(_assessment_detail_payload(assessment), status=200)


def _assessment_patch(request, spec, kwargs):
    assessment_model = apps.get_model("assessments", "InitialAssessment")
    item_model = apps.get_model("assessments", "AssessmentItem")
    assessment = _get_instance(assessment_model, request, kwargs, for_update=True)

    if assessment.status != "DRAFT":
        raise ContractConflict({
            "code": "ASSESSMENT_INVALID_STATE",
            "detail": "Only DRAFT assessments can be updated.",
        })
    if not isinstance(request.data, dict):
        raise ContractError({"detail": "A JSON object is required."})

    before = serialize_instance(assessment)
    for field_name in ("onset_at", "lkw_at", "symptom_note"):
        if field_name in request.data:
            setattr(assessment, field_name, request.data[field_name])

    items = request.data.get("items", [])
    if not isinstance(items, list):
        raise ContractError({"items": "must be a list."})

    now = timezone.now()
    for payload in items:
        if not isinstance(payload, dict):
            raise ContractError({"items": "each item must be an object."})
        item_code = payload.get("item_code")
        if not isinstance(item_code, str) or not item_code:
            raise ContractError({"item_code": "is required."})

        existing = item_model.objects.filter(
            assessment=assessment,
            item_code=item_code,
        ).order_by("id").first()
        if existing is None:
            existing = item_model(
                assessment=assessment,
                item_code=item_code,
                item_group=_assessment_item_group(item_code),
                is_red_flag=False,
                recorded_at=now,
            )

        if item_code in INITIAL_SCREENING_ITEM_CODES:
            score = _initial_screening_score(payload.get("value_numeric"), item_code)
            existing.item_group = "INITIAL_SCREENING"
            existing.value_numeric = score
            existing.score = score
        else:
            for field_name in ("value_text", "value_numeric", "unit", "score", "is_red_flag", "note"):
                if field_name in payload:
                    setattr(existing, field_name, payload[field_name])
            if not existing.item_group:
                existing.item_group = _assessment_item_group(item_code)

        existing.recorded_at = now
        existing.save()

    assessment.updated_at = now
    assessment.save(update_fields=["onset_at", "lkw_at", "symptom_note", "updated_at"])
    after = _assessment_detail_payload(assessment)
    _audit(request, spec, assessment, before, after)
    _outbox(spec, assessment, after)
    if (
        assessment.encounter.encounter_type == "EMERGENCY"
        and assessment.assigned_neurologist_id
    ):
        from apps.notifications.services.notifications import create_notification_for_user

        create_notification_for_user(
            recipient_user=assessment.assigned_neurologist,
            category="EMERGENCY",
            severity=(
                "CRITICAL"
                if assessment.triage_priority == "EMERGENCY"
                else "WARNING"
            ),
            title="Emergency assessment completed",
            body="An assigned emergency encounter assessment has been completed.",
            data_json={
                "patient_id": str(assessment.encounter.patient_id),
                "encounter_id": str(assessment.encounter_id),
                "resource_type": "InitialAssessment",
                "resource_id": str(assessment.id),
                "actor_user_id": str(request.user.id),
            },
        )
    return Response({
        "assessment_id": str(assessment.id),
        "status": assessment.status,
        "updated_at": assessment.updated_at,
        "items": after["items"],
    }, status=200)


def _assessment_complete(request, spec, kwargs):
    assessment_model = apps.get_model("assessments", "InitialAssessment")
    item_model = apps.get_model("assessments", "AssessmentItem")
    emergency_event_model = apps.get_model("assessments", "EmergencyEvent")
    user_model = apps.get_model("accounts", "User")
    assessment = _get_instance(assessment_model, request, kwargs, for_update=True)

    if assessment.status != "DRAFT":
        raise ContractConflict({
            "code": "ASSESSMENT_INVALID_STATE",
            "detail": "Only DRAFT assessments can be completed.",
        })

    if not isinstance(request.data, dict):
        raise ContractError({"detail": "A JSON object is required."})

    assigned_neurologist_id = request.data.get("assigned_neurologist_id")
    if not assigned_neurologist_id:
        raise ContractError({
            "code": "NEUROLOGIST_REQUIRED",
            "assigned_neurologist_id": "is required.",
        })

    neurologist = (
        user_model.objects
        .select_related("role")
        .filter(pk=assigned_neurologist_id)
        .first()
    )
    if neurologist is None:
        raise NotFound({
            "code": "NEUROLOGIST_NOT_FOUND",
            "detail": "The selected neurologist was not found.",
        })
    if not neurologist.is_active or getattr(neurologist.role, "code", None) != "NEUROLOGIST":
        raise ContractConflict({
            "code": "NEUROLOGIST_NOT_AVAILABLE",
            "detail": "The selected user is not an active neurologist.",
        })

    assessment_items = {
        item.item_code: item
        for item in item_model.objects.filter(assessment=assessment)
    }

    missing = [
        code
        for code in INITIAL_SCREENING_ITEM_CODES
        if code not in assessment_items
    ]
    required_fast = ("FAST_FACE", "FAST_ARM", "FAST_SPEECH")
    missing.extend(
        code
        for code in required_fast
        if code not in assessment_items
        or not str(assessment_items[code].value_text or "").strip()
    )
    required_vital = ("BP_SYS", "BP_DIA", "HEART_RATE", "BODY_TEMP")
    missing.extend(
        code
        for code in required_vital
        if code not in assessment_items
        or assessment_items[code].value_numeric is None
    )
    if assessment.lkw_at is None:
        missing.append("LKW_AT")

    if missing:
        raise ContractError({
            "code": "ASSESSMENT_INCOMPLETE",
            "items": missing,
        })

    screening_items = {
        code: assessment_items[code]
        for code in INITIAL_SCREENING_ITEM_CODES
    }
    total_score = sum(
        _initial_screening_score(screening_items[code].value_numeric, code)
        for code in INITIAL_SCREENING_ITEM_CODES
    )
    if not 6 <= total_score <= 30:
        raise ContractError({"total_score": "must be between 6 and 30."})

    # The system does not infer clinical urgency from the screening score.
    # The nurse explicitly records the initial triage priority after reviewing
    # FAST, screening score and LKW.  This uses the existing DB column and
    # keeps the clinical decision attributable to the assessor.
    triage_priority = str(request.data.get("triage_priority") or "").upper()
    if triage_priority not in {
        "URGENT",
        "EMERGENCY",
        "NON_EMERGENCY",
    }:
        raise ContractError({
            "code": "TRIAGE_PRIORITY_REQUIRED",
            "triage_priority": (
                "must be one of EMERGENCY, URGENT, or NON_EMERGENCY."
            ),
        })

    before = serialize_instance(assessment)
    now = timezone.now()
    assessment.assigned_neurologist = neurologist
    assessment.total_score = total_score
    assessment.triage_priority = triage_priority
    assessment.status = "COMPLETED"
    assessment.completed_at = now
    assessment.updated_at = now
    assessment.save(update_fields=[
        "assigned_neurologist",
        "total_score",
        "triage_priority",
        "status",
        "completed_at",
        "updated_at",
    ])

    emergency_event = None
    if assessment.triage_priority in {"URGENT", "EMERGENCY"}:
        emergency_event = emergency_event_model.objects.create(
            assessment=assessment,
            encounter=assessment.encounter,
            assigned_neurologist=neurologist,
            event_type="EMERGENCY_DETECTED",
            priority=assessment.triage_priority,
            status="NOTIFIED",
            occurred_at=now,
            notified_at=now,
            created_at=now,
        )

    notification_data = {
        "event_type": "NEUROLOGIST_ASSIGNED",
        "patient_id": str(
            assessment.encounter.patient_id
        ),
        "encounter_id": str(
            assessment.encounter_id
        ),
        "assessment_id": str(
            assessment.id
        ),
        "emergency_event_id": (
            str(emergency_event.id)
            if emergency_event is not None
            else None
        ),
        "triage_priority": (
            assessment.triage_priority
        ),
        "resource_type": "InitialAssessment",
        "resource_id": str(
            assessment.id
        ),
        "actor_user_id": str(
            request.user.id
        ),
    }

    severity = (
        "CRITICAL"
        if assessment.triage_priority == "EMERGENCY"
        else "WARNING"
        if assessment.triage_priority == "URGENT"
        else "INFO"
    )

    title = (
        "Emergency assessment assigned"
        if emergency_event is not None
        else "Initial assessment assigned"
    )

    body = (
        "A completed initial assessment "
        "has been assigned to you."
    )

    if emergency_event is not None:
        # URGENT / EMERGENCY is a mandatory clinical alert.
        # Create it directly so an ordinary notification
        # preference cannot suppress the alert.
        notification_model = apps.get_model(
            "notifications",
            "Notification",
        )
        notification_model.objects.create(
            recipient_user=neurologist,
            category="EMERGENCY",
            severity=severity,
            title=title,
            body=body,
            data_json=notification_data,
        )
    else:
        from apps.notifications.services.notifications import (
            create_notification_for_user,
        )

        create_notification_for_user(
            recipient_user=neurologist,
            category="SYSTEM",
            severity=severity,
            title=title,
            body=body,
            data_json=notification_data,
        )

    after = _assessment_detail_payload(assessment)
    _audit(request, spec, assessment, before, after)
    _outbox(spec, assessment, after)

    if emergency_event is not None:
        OutboxEvent.objects.create(
            event_type="emergency_detected",
            aggregate_type="EmergencyEvent",
            aggregate=str(emergency_event.id),
            payload={
                "emergency_event_id": str(emergency_event.id),
                "assessment_id": str(assessment.id),
                "encounter_id": str(assessment.encounter_id),
                "assigned_neurologist_id": str(neurologist.id),
                "triage_priority": assessment.triage_priority,
                "status": emergency_event.status,
            },
            status="PENDING",
            retry_count=0,
            published_at=None,
            created_at=now,
        )

    return Response({
        "assessment_id": str(assessment.id),
        "status": assessment.status,
        "total_score": assessment.total_score,
        "triage_priority": assessment.triage_priority,
        "assigned_neurologist_id": str(assessment.assigned_neurologist_id),
        "emergency_event_id": (
            str(emergency_event.id) if emergency_event is not None else None
        ),
        "completed_at": assessment.completed_at,
    }, status=200)


def _fcm_create(request, spec, kwargs):
    model = apps.get_model("notifications", "FCMDeviceToken")
    fields = _field_map(model)
    token = request.data.get("token")
    if not token:
        raise ContractError({"token": "required"})

    defaults = {}
    for key, value in request.data.items():
        field = fields.get(key)
        if field and key != "token":
            defaults[field.attname if field.is_relation else field.name] = value

    user_field = fields.get("user")
    if user_field and user_field.is_relation:
        defaults[user_field.attname] = request.user.id
    if "is_active" in fields:
        defaults["is_active"] = True

    obj, created = model.objects.update_or_create(
        token=token,
        defaults=defaults,
    )
    return Response(serialize_instance(obj), status=201 if created else 200)


def _cds_discovery(request, spec, kwargs):
    return Response({
        "services": [
            {
                "id": "medication-safety-order-select",
                "hook": "order-select",
                "title": "BrainOn Medication Safety",
                "description": "Medication safety decision support.",
            },
            {
                "id": "medication-safety-order-sign",
                "hook": "order-sign",
                "title": "BrainOn Medication Safety Sign",
                "description": "Medication safety decision support before signing.",
            },
            {
                "id": "stroke-patient-view",
                "hook": "patient-view",
                "title": "BrainOn Stroke Patient View",
                "description": "Cerebrovascular CDSS patient context.",
            },
        ]
    }, status=200)


def _medication_safety_check(request, spec, kwargs):
    from apps.medication_safety.models import (
        DURAgeRule,
        DURDoseRule,
        DURDuplicateRule,
        DURElderlyRule,
        DURInteractionRule,
        DURPregnancyRule,
        PatientAllergy,
    )

    patient_id = request.data.get("patient_id")
    ingredient_ids = request.data.get("ingredient_ids") or []

    if not patient_id:
        raise ContractError({"patient_id": "required"})

    alerts = []

    allergies = PatientAllergy.objects.filter(
        patient_id=patient_id,
        status="ACTIVE",
    )
    if ingredient_ids:
        allergies = allergies.filter(
            Q(ingredient_id__in=ingredient_ids) | Q(ingredient_id__isnull=True)
        )

    for item in allergies:
        alerts.append({
            "type": "ALLERGY",
            "severity": getattr(item, "severity", "HIGH"),
            "rule_id": str(item.id),
            "message": getattr(item, "reaction", None) or getattr(item, "substance", None),
        })

    if ingredient_ids:
        for rule in DURInteractionRule.objects.filter(
            is_active=True,
            ingredient_a_id__in=ingredient_ids,
            ingredient_b_id__in=ingredient_ids,
        ):
            alerts.append({
                "type": "INTERACTION",
                "severity": "HIGH",
                "rule_id": str(rule.id),
                "message": getattr(rule, "description", None),
            })

        for type_code, rule_model in [
            ("DOSE", DURDoseRule),
            ("DUPLICATE", DURDuplicateRule),
            ("AGE", DURAgeRule),
            ("ELDERLY", DURElderlyRule),
            ("PREGNANCY", DURPregnancyRule),
        ]:
            for rule in rule_model.objects.filter(
                ingredient_id__in=ingredient_ids,
                is_active=True,
            ):
                alerts.append({
                    "type": type_code,
                    "severity": "WARNING",
                    "rule_id": str(rule.id),
                    "message": getattr(rule, "description", None),
                })

    return Response({
        "patient_id": str(patient_id),
        "safe": len(alerts) == 0,
        "alerts": alerts,
    }, status=200)


# === BATCH_B_LOCAL_HANDLERS_START ===

def _batchb_prescription_payload(prescription):
    item_model = apps.get_model(
        "prescriptions",
        "PrescriptionItem",
    )

    data = serialize_instance(prescription)
    data["prescription_id"] = str(prescription.pk)

    prescriber = getattr(
        prescription,
        "prescribed_by",
        None,
    )

    data["doctor"] = (
        str(prescriber)
        if prescriber is not None
        else None
    )

    department = getattr(
        prescriber,
        "department",
        None,
    ) if prescriber is not None else None

    data["department"] = (
        str(department)
        if department is not None
        else None
    )

    items = []

    for item in (
        item_model.objects
        .filter(
            prescription_id=prescription.pk
        )
        .order_by("created_at")
    ):
        row = serialize_instance(item)
        row["item_id"] = str(item.pk)
        items.append(row)

    data["items"] = items

    return data


def _batchb_prescriber_scope(
    request,
    prescription,
):
    from rest_framework.exceptions import (
        PermissionDenied,
    )

    prescriber = getattr(
        prescription,
        "prescribed_by",
        None,
    )

    if prescriber is None:
        return

    # prescribed_by -> accounts.User
    try:
        if (
            prescriber._meta.label_lower
            == request.user._meta.label_lower
        ):
            if (
                str(prescriber.pk)
                != str(request.user.pk)
            ):
                raise PermissionDenied({
                    "code":
                        "PRESCRIPTION_VIEW_FORBIDDEN",
                    "detail":
                        "Prescription is outside "
                        "the clinician scope.",
                })

            return
    except AttributeError:
        pass

    # prescribed_by -> Clinician -> user
    user_id = getattr(
        prescriber,
        "user_id",
        None,
    )

    if (
        user_id is not None
        and str(user_id)
        != str(request.user.pk)
    ):
        raise PermissionDenied({
            "code":
                "PRESCRIPTION_VIEW_FORBIDDEN",
            "detail":
                "Prescription is outside "
                "the clinician scope.",
        })



def _batchb_rx_create(
    request,
    spec,
    kwargs,
):
    from decimal import (
        Decimal,
        InvalidOperation,
    )
    from django.utils.dateparse import (
        parse_date,
    )
    from apps.medication_safety.services.medication_safety import (
        UNIT_ALIASES,
    )

    del kwargs

    prescription_model = apps.get_model(
        "prescriptions",
        "Prescription",
    )

    item_model = apps.get_model(
        "prescriptions",
        "PrescriptionItem",
    )

    encounter_model = apps.get_model(
        "clinical_records",
        "Encounter",
    )

    if not isinstance(
        request.data,
        dict,
    ):
        raise ContractError({
            "code":
                "PRESCRIPTION_INVALID_ITEM",
            "detail":
                "Request body must be an object.",
        })

    encounter_id = request.data.get(
        "encounter_id"
    )

    items = request.data.get(
        "items"
    )

    if not encounter_id:
        raise ContractError({
            "code":
                "ENCOUNTER_ID_REQUIRED",
            "detail":
                "encounter_id is required.",
        })

    if (
        not isinstance(items, list)
        or not items
    ):
        raise ContractError({
            "code":
                "PRESCRIPTION_INVALID_ITEM",
            "detail":
                "At least one prescription "
                "item is required.",
        })

    try:
        encounter = (
            encounter_model.objects
            .get(pk=encounter_id)
        )
    except (
        encounter_model.DoesNotExist,
        ValueError,
        TypeError,
    ) as exc:
        raise NotFound({
            "code":
                "ENCOUNTER_NOT_FOUND",
        }) from exc

    now = timezone.now()

    prescription = (
        prescription_model.objects.create(
            encounter=encounter,
            prescribed_by=request.user,
            status="DRAFT",
            finalized_at=None,
            created_at=now,
            updated_at=now,
        )
    )

    required_fields = (
        "medication_id",
        "dose",
        "dose_unit",
        "frequency_per_day",
        "start_date",
        "duration_days",
    )

    for index, raw_payload in enumerate(
        items,
        start=1,
    ):
        if not isinstance(
            raw_payload,
            dict,
        ):
            raise ContractError({
                "code":
                    "PRESCRIPTION_INVALID_ITEM",
                "detail":
                    f"Item {index} must be "
                    "an object.",
            })

        payload = dict(
            raw_payload
        )

        missing = [
            field_name
            for field_name
            in required_fields
            if payload.get(
                field_name
            ) in (
                None,
                "",
            )
        ]

        if missing:
            raise ContractError({
                "code":
                    "PRESCRIPTION_INVALID_ITEM",
                "detail":
                    f"Item {index} has "
                    "missing required fields.",
                "fields":
                    missing,
            })

        raw_dose_unit = str(
            payload["dose_unit"]
        ).strip()

        normalized_dose_unit = (
            UNIT_ALIASES.get(
                raw_dose_unit.lower()
            )
            or UNIT_ALIASES.get(
                raw_dose_unit
            )
        )

        if normalized_dose_unit is None:
            raise ContractError({
                "code":
                    "PRESCRIPTION_INVALID_ITEM",
                "detail":
                    "Unsupported dose_unit. "
                    "Supported units are "
                    "mg, g, mcg and their "
                    "configured aliases.",
            })

        payload["dose_unit"] = (
            normalized_dose_unit
        )

        try:
            dose = Decimal(
                str(
                    payload["dose"]
                )
            )

            frequency = int(
                payload[
                    "frequency_per_day"
                ]
            )

            duration = int(
                payload[
                    "duration_days"
                ]
            )

        except (
            InvalidOperation,
            TypeError,
            ValueError,
        ) as exc:
            raise ContractError({
                "code":
                    "PRESCRIPTION_INVALID_ITEM",
                "detail":
                    f"Item {index} contains "
                    "invalid numeric values.",
            }) from exc

        if (
            dose <= 0
            or frequency <= 0
            or duration <= 0
        ):
            raise ContractError({
                "code":
                    "PRESCRIPTION_INVALID_ITEM",
                "detail":
                    "dose, frequency_per_day, "
                    "and duration_days must "
                    "be greater than zero.",
            })

        start_date = payload[
            "start_date"
        ]

        if isinstance(
            start_date,
            str,
        ):
            start_date = parse_date(
                start_date
            )

        if start_date is None:
            raise ContractError({
                "code":
                    "PRESCRIPTION_INVALID_ITEM",
                "detail":
                    f"Item {index} has an "
                    "invalid start_date.",
            })

        medication = (
            _batchb_active_medication(
                payload[
                    "medication_id"
                ]
            )
        )

        payload["dose"] = dose
        payload[
            "frequency_per_day"
        ] = frequency
        payload[
            "duration_days"
        ] = duration
        payload[
            "start_date"
        ] = start_date

        item = item_model(
            prescription_id=
                prescription.pk
        )

        _batchb_apply_item(
            item,
            payload,
            medication,
        )

        item.created_at = now
        item.updated_at = now

        item.save()

    response_payload = (
        _batchb_prescription_payload(
            prescription
        )
    )

    _outbox(
        spec,
        prescription,
        response_payload,
    )

    return Response(
        response_payload,
        status=201,
    )



def _batchb_rx_detail(
    request,
    spec,
    kwargs,
):
    from rest_framework.exceptions import (
        PermissionDenied,
    )

    prescription_model = apps.get_model(
        "prescriptions",
        "Prescription",
    )

    prescription = _get_instance(
        prescription_model,
        request,
        kwargs,
    )

    if _role_code(request.user) == "PATIENT":
        patient = _patient_for_user(
            request.user
        )

        encounter = getattr(
            prescription,
            "encounter",
            None,
        )

        valid = (
            patient is not None
            and encounter is not None
            and str(
                getattr(
                    encounter,
                    "patient_id",
                    "",
                )
            ) == str(patient.pk)
            and getattr(
                prescription,
                "status",
                None,
            ) == "FINAL"
        )

        if not valid:
            raise PermissionDenied({
                "code":
                    "PRESCRIPTION_VIEW_FORBIDDEN",
                "detail":
                    "Prescription access denied.",
            })

    else:
        _batchb_prescriber_scope(
            request,
            prescription,
        )

    return Response(
        _batchb_prescription_payload(
            prescription
        ),
        status=200,
    )


def _batchb_active_medication(
    medication_id,
):
    medication_model = apps.get_model(
        "medications",
        "Medication",
    )

    try:
        return medication_model.objects.get(
            pk=medication_id,
            is_active=True,
        )
    except (
        medication_model.DoesNotExist
    ) as exc:
        raise NotFound({
            "code":
                "MEDICATION_NOT_FOUND",
            "detail":
                "Active medication was not found.",
        }) from exc


def _batchb_apply_item(
    item,
    payload,
    medication,
):
    item.medication_id = medication.pk

    if hasattr(
        item,
        "medication_code",
    ):
        item.medication_code = getattr(
            medication,
            "medication_code",
            None,
        )

    if hasattr(
        item,
        "medication_name",
    ):
        item.medication_name = getattr(
            medication,
            "medication_name",
            None,
        )

    for name in (
        "dose",
        "dose_unit",
        "route",
        "frequency_per_day",
        "timing",
        "start_date",
        "duration_days",
        "instructions",
    ):
        if name in payload:
            setattr(
                item,
                name,
                payload[name],
            )


def _batchb_rx_patch(
    request,
    spec,
    kwargs,
):
    prescription_model = apps.get_model(
        "prescriptions",
        "Prescription",
    )

    item_model = apps.get_model(
        "prescriptions",
        "PrescriptionItem",
    )

    prescription = _get_instance(
        prescription_model,
        request,
        kwargs,
        for_update=True,
    )

    _batchb_prescriber_scope(
        request,
        prescription,
    )

    if getattr(
        prescription,
        "status",
        None,
    ) != "DRAFT":
        raise ContractError({
            "code":
                "PRESCRIPTION_FINAL_LOCKED",
            "detail":
                "Only DRAFT prescriptions "
                "may be modified.",
        })

    before = _batchb_prescription_payload(
        prescription
    )

    items = request.data.get("items")

    if items is not None:
        if not isinstance(items, list):
            raise ContractError({
                "code":
                    "PRESCRIPTION_INVALID_ITEM",
                "detail":
                    "items must be an array.",
            })

        for payload in items:
            if not isinstance(
                payload,
                dict,
            ):
                raise ContractError({
                    "code":
                        "PRESCRIPTION_INVALID_ITEM",
                    "detail":
                        "Invalid prescription item.",
                })

            item_id = payload.get(
                "item_id"
            )

            medication_id = payload.get(
                "medication_id"
            )

            if item_id:
                try:
                    item = (
                        item_model.objects
                        .select_for_update()
                        .get(
                            pk=item_id,
                            prescription_id=
                                prescription.pk,
                        )
                    )
                except (
                    item_model.DoesNotExist
                ) as exc:
                    raise NotFound({
                        "code":
                            "PRESCRIPTION_ITEM_NOT_FOUND",
                        "detail":
                            "Prescription item "
                            "was not found.",
                    }) from exc

                if medication_id:
                    medication = (
                        _batchb_active_medication(
                            medication_id
                        )
                    )
                else:
                    medication = (
                        item.medication
                    )

            else:
                if not medication_id:
                    raise ContractError({
                        "code":
                            "PRESCRIPTION_INVALID_ITEM",
                        "detail":
                            "medication_id is required "
                            "for a new item.",
                    })

                medication = (
                    _batchb_active_medication(
                        medication_id
                    )
                )

                item = item_model(
                    prescription_id=
                        prescription.pk
                )

            _batchb_apply_item(
                item,
                payload,
                medication,
            )

            item.save()

    fields = _field_map(
        prescription_model
    )

    if "updated_at" in fields:
        prescription.updated_at = (
            timezone.now()
        )

    prescription.save()

    after = _batchb_prescription_payload(
        prescription
    )

    _audit(
        request,
        spec,
        prescription,
        before,
        after,
    )

    _outbox(
        spec,
        prescription,
        after,
    )

    return Response(
        after,
        status=200,
    )


def _batchb_ingredient_ids(
    prescription,
):
    item_model = apps.get_model(
        "prescriptions",
        "PrescriptionItem",
    )

    medication_ids = list(
        item_model.objects
        .filter(
            prescription_id=
                prescription.pk
        )
        .exclude(
            medication_id__isnull=True
        )
        .values_list(
            "medication_id",
            flat=True,
        )
    )

    if not medication_ids:
        return []

    try:
        link_model = apps.get_model(
            "medication_safety",
            "MedicationIngredient",
        )
    except LookupError:
        return []

    fields = _field_map(link_model)

    medication_field = fields.get(
        "medication"
    )

    ingredient_field = fields.get(
        "ingredient"
    )

    if (
        medication_field is None
        or ingredient_field is None
    ):
        return []

    return list(
        link_model.objects
        .filter(
            **{
                f"{medication_field.attname}__in":
                    medication_ids
            }
        )
        .values_list(
            ingredient_field.attname,
            flat=True,
        )
    )


def _batchb_safety_alerts(
    patient_id,
    ingredient_ids,
):
    from apps.medication_safety.models import (
        DURAgeRule,
        DURDoseRule,
        DURDuplicateRule,
        DURElderlyRule,
        DURInteractionRule,
        DURPregnancyRule,
        PatientAllergy,
    )

    alerts = []

    allergies = (
        PatientAllergy.objects
        .filter(
            patient_id=patient_id,
            status="ACTIVE",
        )
    )

    if ingredient_ids:
        allergies = allergies.filter(
            Q(
                ingredient_id__in=
                    ingredient_ids
            )
            |
            Q(
                ingredient_id__isnull=True
            )
        )
    else:
        allergies = allergies.filter(
            ingredient_id__isnull=True
        )

    for allergy in allergies:
        severity = str(
            getattr(
                allergy,
                "severity",
                None,
            )
            or "WARNING"
        ).upper()

        severity = {
            "HIGH": "MAJOR",
            "SEVERE": "MAJOR",
            "CRITICAL": "BLOCK",
        }.get(
            severity,
            severity,
        )

        alerts.append({
            "type": "ALLERGY",
            "rule_type": "ALLERGY",
            "rule_id": str(
                allergy.pk
            ),
            "severity": severity,
            "message": (
                getattr(
                    allergy,
                    "reaction",
                    None,
                )
                or getattr(
                    allergy,
                    "substance",
                    None,
                )
            ),
            "_rule_obj": allergy,
        })

    if ingredient_ids:
        for rule in (
            DURInteractionRule.objects
            .filter(
                is_active=True,
                ingredient_a_id__in=
                    ingredient_ids,
                ingredient_b_id__in=
                    ingredient_ids,
            )
        ):
            alerts.append({
                "type":
                    "INTERACTION",
                "rule_type":
                    "INTERACTION",
                "rule_id":
                    str(rule.pk),
                "severity":
                    "MAJOR",
                "message":
                    getattr(
                        rule,
                        "description",
                        None,
                    ),
                "_rule_obj": rule,
            })

        for code, model in (
            ("DOSE", DURDoseRule),
            (
                "DUPLICATE",
                DURDuplicateRule,
            ),
            ("AGE", DURAgeRule),
            (
                "ELDERLY",
                DURElderlyRule,
            ),
            (
                "PREGNANCY",
                DURPregnancyRule,
            ),
        ):
            for rule in (
                model.objects.filter(
                    ingredient_id__in=
                        ingredient_ids,
                    is_active=True,
                )
            ):
                alerts.append({
                    "type": code,
                    "rule_type": code,
                    "rule_id":
                        str(rule.pk),
                    "severity":
                        "WARNING",
                    "message":
                        getattr(
                            rule,
                            "description",
                            None,
                        ),
                    "_rule_obj": rule,
                })

    return alerts


def _batchb_public_alert(
    alert,
):
    return {
        key: value
        for key, value in alert.items()
        if not key.startswith("_")
    }


def _batchb_create_override(
    prescription,
    patient_id,
    alert,
    payload,
):
    model = apps.get_model(
        "medication_safety",
        "MedicationSafetyOverride",
    )

    fields = _field_map(model)

    reason = str(
        payload.get("reason")
        or ""
    ).strip()

    if not reason:
        raise ContractError({
            "code":
                "OVERRIDE_REASON_REQUIRED",
            "detail":
                "Override reason is required.",
        })

    data = {
        "alert_type":
            alert["type"],
        "severity":
            alert["severity"],
        "rule_type":
            alert["rule_type"],
        "reason":
            reason,
    }

    if "patient" in fields:
        data[
            fields[
                "patient"
            ].attname
        ] = patient_id

    if "prescription" in fields:
        data[
            fields[
                "prescription"
            ].attname
        ] = prescription.pk

    if (
        "doctor" in fields
        and getattr(
            prescription,
            "prescribed_by_id",
            None,
        ) is not None
    ):
        data[
            fields[
                "doctor"
            ].attname
        ] = (
            prescription
            .prescribed_by_id
        )

    rule_field = fields.get("rule")
    rule_obj = alert.get("_rule_obj")

    if (
        rule_field is not None
        and rule_obj is not None
    ):
        if rule_field.is_relation:
            target_model = (
                rule_field
                .remote_field
                .model
            )

            if isinstance(
                rule_obj,
                target_model,
            ):
                data[
                    rule_field.attname
                ] = rule_obj.pk
        else:
            data[
                rule_field.name
            ] = str(rule_obj.pk)

    return model.objects.create(
        **data
    )


def _batchb_create_schedules(
    prescription,
):
    item_model = apps.get_model(
        "prescriptions",
        "PrescriptionItem",
    )

    schedule_model = apps.get_model(
        "medications",
        "MedicationSchedule",
    )

    created = 0

    for item in (
        item_model.objects
        .filter(
            prescription_id=
                prescription.pk
        )
    ):
        exists = (
            schedule_model.objects
            .filter(
                prescription_item_id=
                    item.pk
            )
            .exists()
        )

        if exists:
            continue

        create_data = {
            "prescription_item_id":
                item.pk,
            "scheduled_at":
                timezone.now(),
            "time_slot": (
                getattr(
                    item,
                    "timing",
                    None,
                )
                or "DEFAULT"
            ),
            "dose": getattr(
                item,
                "dose",
                None,
            ),
        }

        schedule_fields = _field_map(
            schedule_model
        )

        if "created_at" in schedule_fields:
            create_data["created_at"] = (
                timezone.now()
            )

        schedule_model.objects.create(
            **create_data
        )

        created += 1

    return created


def _batchb_rx_finalize(
    request,
    spec,
    kwargs,
):
    prescription_model = apps.get_model(
        "prescriptions",
        "Prescription",
    )

    item_model = apps.get_model(
        "prescriptions",
        "PrescriptionItem",
    )

    prescription = _get_instance(
        prescription_model,
        request,
        kwargs,
        for_update=True,
    )

    _batchb_prescriber_scope(
        request,
        prescription,
    )

    if getattr(
        prescription,
        "status",
        None,
    ) != "DRAFT":
        raise ContractError({
            "code":
                "PRESCRIPTION_INVALID_STATE",
            "detail":
                "Prescription must be DRAFT.",
        })

    items = list(
        item_model.objects
        .filter(
            prescription_id=
                prescription.pk
        )
    )

    if not items:
        raise ContractError({
            "code":
                "PRESCRIPTION_EMPTY",
            "detail":
                "Prescription has no items.",
        })

    for item in items:
        medication = getattr(
            item,
            "medication",
            None,
        )

        if (
            medication is None
            or not getattr(
                medication,
                "is_active",
                False,
            )
        ):
            raise ContractError({
                "code":
                    "PRESCRIPTION_INVALID_ITEM",
                "detail":
                    "Inactive medication exists.",
            })

    encounter = getattr(
        prescription,
        "encounter",
        None,
    )

    patient_id = getattr(
        encounter,
        "patient_id",
        None,
    )

    if patient_id is None:
        raise ContractError({
            "code":
                "PRESCRIPTION_PATIENT_MISMATCH",
            "detail":
                "Patient could not be resolved.",
        })

    ingredient_ids = (
        _batchb_ingredient_ids(
            prescription
        )
    )

    alerts = _batchb_safety_alerts(
        patient_id,
        ingredient_ids,
    )

    blocking = [
        alert
        for alert in alerts
        if str(
            alert.get(
                "severity"
            )
            or ""
        ).upper()
        in {"MAJOR", "BLOCK"}
    ]

    requested_overrides = (
        request.data.get(
            "overrides"
        )
        or []
    )

    created_overrides = []

    for alert in blocking:
        matched = None

        for candidate in (
            requested_overrides
        ):
            if not isinstance(
                candidate,
                dict,
            ):
                continue

            if (
                str(
                    candidate.get(
                        "alert_type"
                    )
                )
                ==
                str(alert["type"])
                and
                str(
                    candidate.get(
                        "rule_id"
                    )
                )
                ==
                str(alert["rule_id"])
            ):
                matched = candidate
                break

        if matched is None:
            raise ContractError({
                "code":
                    "MEDICATION_SAFETY_BLOCKED",
                "detail":
                    "Blocking safety alert "
                    "requires override.",
                "alerts": [
                    _batchb_public_alert(
                        item
                    )
                    for item in blocking
                ],
            })

        override = (
            _batchb_create_override(
                prescription,
                patient_id,
                alert,
                matched,
            )
        )

        created_overrides.append({
            "override_id":
                str(override.pk),
            "alert_type":
                alert["type"],
            "severity":
                alert["severity"],
            "reason":
                matched["reason"],
        })

    before = (
        _batchb_prescription_payload(
            prescription
        )
    )

    prescription.status = "FINAL"
    prescription.finalized_at = (
        timezone.now()
    )

    fields = _field_map(
        prescription_model
    )

    if "updated_at" in fields:
        prescription.updated_at = (
            timezone.now()
        )

    prescription.save()

    schedules_created = (
        _batchb_create_schedules(
            prescription
        )
    )

    after = (
        _batchb_prescription_payload(
            prescription
        )
    )

    audit_after = {
        **after,
        "safety": {
            "alerts": [
                _batchb_public_alert(
                    alert
                )
                for alert in alerts
            ],
            "overrides":
                created_overrides,
        },
    }

    _audit(
        request,
        spec,
        prescription,
        before,
        audit_after,
    )

    # Outbox DB 저장까지는 Backend 내부 검증 대상.
    # 실제 RabbitMQ publish는 외부연동 후 검증한다.
    _outbox(
        spec,
        prescription,
        {
            "prescription_id":
                str(prescription.pk),
            "status":
                "FINAL",
            "schedules_created":
                schedules_created,
        },
    )

    return Response({
        "prescription_id":
            str(prescription.pk),
        "status":
            "FINAL",
        "finalized_at":
            prescription.finalized_at,
        "safety": {
            "safe":
                len(alerts) == 0,
            "alerts": [
                _batchb_public_alert(
                    alert
                )
                for alert in alerts
            ],
            "overrides":
                created_overrides,
        },
        "schedules_created":
            schedules_created,
    }, status=200)


def _batchb_allergy_list(
    request,
    spec,
    kwargs,
):
    allergy_model = apps.get_model("medication_safety", "PatientAllergy")
    patient_model = apps.get_model("patients", "Patient")
    patient_id = kwargs.get("patient_id")

    if not patient_model.objects.filter(pk=patient_id).exists():
        raise NotFound({
            "code": "PATIENT_NOT_FOUND",
            "detail": "Patient was not found.",
        })

    queryset = allergy_model.objects.filter(patient_id=patient_id)
    status = request.query_params.get("status")
    queryset = queryset.filter(status=status or "ACTIVE")
    queryset = _owner_scope(queryset, allergy_model, request).order_by("-created_at")
    return Response(_paginate(queryset, request), status=200)


def _batchb_allergy_create(
    request,
    spec,
    kwargs,
):
    """Create an allergy and refresh the patient-chart summary atomically."""
    allergy_model = apps.get_model("medication_safety", "PatientAllergy")
    patient_model = apps.get_model("patients", "Patient")
    patient_id = kwargs.get("patient_id")

    if not patient_id:
        raise ContractError({"patient_id": "required"})

    try:
        patient = patient_model.objects.select_for_update().get(pk=patient_id)
    except patient_model.DoesNotExist as exc:
        raise NotFound({
            "code": "PATIENT_NOT_FOUND",
            "detail": "Patient was not found.",
        }) from exc

    data = _write_data(allergy_model, request)
    substance = str(data.get("substance") or "").strip()
    ingredient_id = data.get("ingredient_id")
    if not substance and not ingredient_id:
        raise ContractError({
            "code": "VALIDATION_ERROR",
            "detail": "ingredient_id or substance is required.",
        })

    data["patient_id"] = patient.id
    data["substance"] = substance or None
    data["status"] = "ACTIVE"
    data.setdefault("severity", "MODERATE")
    if getattr(request.user, "id", None):
        data["recorded_by_id"] = request.user.id

    try:
        allergy = allergy_model.objects.create(**data)
    except (IntegrityError, TypeError, ValueError) as exc:
        raise ContractError({
            "code": "VALIDATION_ERROR",
            "detail": str(exc),
        }) from exc

    from apps.patients.services.patients import rebuild_allergy_info

    rebuild_allergy_info(patient=patient)
    after = serialize_instance(allergy)
    _audit(request, spec, allergy, None, after)
    _outbox(spec, allergy, after)
    return Response(after, status=201)


def _batchb_allergy_deactivate(
    request,
    spec,
    kwargs,
):
    allergy_model = apps.get_model(
        "medication_safety",
        "PatientAllergy",
    )

    patient_id = kwargs.get(
        "patient_id"
    )

    allergy_id = kwargs.get(
        "allergy_id"
    )

    qs = (
        allergy_model.objects
        .select_for_update()
        .filter(
            pk=allergy_id,
            patient_id=patient_id,
            status="ACTIVE",
        )
    )

    qs = _owner_scope(
        qs,
        allergy_model,
        request,
    )

    allergy = qs.first()

    if allergy is None:
        raise NotFound({
            "code":
                "PATIENT_ALLERGY_NOT_FOUND",
            "detail":
                "Active patient allergy "
                "was not found.",
        })

    before = serialize_instance(
        allergy
    )

    allergy.status = "INACTIVE"

    fields = _field_map(
        allergy_model
    )

    if "updated_at" in fields:
        allergy.updated_at = (
            timezone.now()
        )

    update_fields = ["status"]

    if "updated_at" in fields:
        update_fields.append(
            "updated_at"
        )

    allergy.save(
        update_fields=update_fields
    )

    patient_model = apps.get_model(
        "patients",
        "Patient",
    )

    patient_fields = _field_map(
        patient_model
    )

    if "allergy_info" in patient_fields:
        try:
            patient = (
                patient_model.objects
                .select_for_update()
                .get(pk=patient_id)
            )
        except (
            patient_model.DoesNotExist
        ) as exc:
            raise NotFound({
                "code":
                    "PATIENT_NOT_FOUND",
                "detail":
                    "Patient was not found.",
            }) from exc

        active = (
            allergy_model.objects
            .filter(
                patient_id=patient_id,
                status="ACTIVE",
            )
            .select_related(
                "ingredient"
            )
            .order_by("created_at")
        )

        labels = []

        for item in active:
            label = getattr(
                item,
                "substance",
                None,
            )

            if not label:
                ingredient = getattr(
                    item,
                    "ingredient",
                    None,
                )

                if ingredient is not None:
                    label = str(
                        ingredient
                    )

            if (
                label
                and str(label)
                not in labels
            ):
                labels.append(
                    str(label)
                )

        patient.allergy_info = (
            ", ".join(labels)
            if labels
            else None
        )

        patient_update = [
            "allergy_info"
        ]

        if "updated_at" in patient_fields:
            patient.updated_at = (
                timezone.now()
            )

            patient_update.append(
                "updated_at"
            )

        patient.save(
            update_fields=
                patient_update
        )

    after = serialize_instance(
        allergy
    )

    _audit(
        request,
        spec,
        allergy,
        before,
        after,
    )

    _outbox(
        spec,
        allergy,
        after,
    )

    return Response(status=204)


# === BATCH_B_LOCAL_HANDLERS_END ===


# --- Clinical note write handlers -----------------------------------------

_CLINICAL_NOTE_FIELDS = (
    "subjective",
    "objective",
    "assessment",
    "plan",
    "clinical_opinion",
)


def _clinical_note_payload(note, *, include_created_at=False):
    payload = {
        "note_id": str(note.id),
        "encounter_id": str(note.encounter_id),
        "author_id": str(note.author_id),
        "status": note.status,
        "subjective": note.subjective,
        "objective": note.objective,
        "assessment": note.assessment,
        "plan": note.plan,
        "clinical_opinion": note.clinical_opinion,
        "finalized_at": _safe_value(note.finalized_at),
        "updated_at": _safe_value(note.updated_at),
    }
    if include_created_at:
        payload["created_at"] = _safe_value(note.created_at)
    return payload


def _clinical_note_get_for_update(note_id):
    ClinicalNote = apps.get_model("clinical_records", "ClinicalNote")
    try:
        return ClinicalNote.objects.select_for_update().get(pk=note_id)
    except (ClinicalNote.DoesNotExist, ValueError, TypeError) as exc:
        raise NotFound({
            "code": "CLINICAL_NOTE_NOT_FOUND",
            "detail": "Clinical note was not found.",
        }) from exc


def _clinical_note_require_author(request, note):
    if note.author_id != request.user.id:
        raise PermissionDenied({
            "code": "CLINICAL_NOTE_FORBIDDEN",
            "detail": "Only the author can modify this clinical note.",
        })


def _clinical_note_require_draft(note):
    if note.status != "DRAFT":
        raise ContractConflict({
            "code": "CLINICAL_NOTE_INVALID_STATE",
            "detail": "Only a DRAFT clinical note can be changed.",
        })


def _clinical_note_create(request, spec, kwargs):
    ClinicalNote = apps.get_model("clinical_records", "ClinicalNote")
    Encounter = apps.get_model("clinical_records", "Encounter")
    encounter_id = request.data.get("encounter_id")

    if not encounter_id:
        raise ContractError({
            "code": "ENCOUNTER_ID_REQUIRED",
            "detail": "encounter_id is required.",
        })

    try:
        # Lock the encounter so concurrent creates cannot both pass the
        # per-encounter/author DRAFT check within this transaction.
        encounter = Encounter.objects.select_for_update().get(pk=encounter_id)
    except (Encounter.DoesNotExist, ValueError, TypeError) as exc:
        raise NotFound({
            "code": "ENCOUNTER_NOT_FOUND",
            "detail": "Encounter was not found.",
        }) from exc

    if ClinicalNote.objects.filter(
        encounter=encounter,
        author=request.user,
        status="DRAFT",
    ).exists():
        raise ContractConflict({
            "code": "CLINICAL_NOTE_ALREADY_IN_PROGRESS",
            "detail": "A DRAFT clinical note already exists for this encounter and author.",
        })

    now = timezone.now()
    note = ClinicalNote.objects.create(
        encounter=encounter,
        author=request.user,
        status="DRAFT",
        subjective=request.data.get("subjective"),
        objective=request.data.get("objective"),
        assessment=request.data.get("assessment"),
        plan=request.data.get("plan"),
        created_at=now,
        updated_at=now,
    )
    payload = _clinical_note_payload(note, include_created_at=True)
    _outbox(spec, note, payload)
    return Response(payload, status=201)


def _clinical_note_update(request, spec, kwargs):
    note = _clinical_note_get_for_update(kwargs.get("note_id"))
    _clinical_note_require_author(request, note)
    _clinical_note_require_draft(note)

    supplied_fields = set(request.data.keys())
    invalid_fields = supplied_fields.difference(_CLINICAL_NOTE_FIELDS)
    if invalid_fields:
        raise ContractError({
            "code": "CLINICAL_NOTE_FIELDS_INVALID",
            "detail": "Only SOAP and clinical_opinion fields can be updated.",
            "fields": sorted(invalid_fields),
        })
    if not supplied_fields:
        raise ContractError({
            "code": "CLINICAL_NOTE_FIELDS_REQUIRED",
            "detail": "At least one editable clinical note field is required.",
        })

    for field_name in supplied_fields:
        setattr(note, field_name, request.data.get(field_name))
    note.updated_at = timezone.now()
    note.save(update_fields=[*sorted(supplied_fields), "updated_at"])

    payload = _clinical_note_payload(note)
    _outbox(spec, note, payload)
    return Response(payload, status=200)


def _clinical_note_finalize(request, spec, kwargs):
    note = _clinical_note_get_for_update(kwargs.get("note_id"))
    _clinical_note_require_author(request, note)
    _clinical_note_require_draft(note)

    missing_fields = [
        field_name
        for field_name in ("assessment", "plan", "clinical_opinion")
        if not str(getattr(note, field_name) or "").strip()
    ]
    if missing_fields:
        raise ContractError({
            "code": "CLINICAL_NOTE_INCOMPLETE",
            "detail": "assessment, plan, and clinical_opinion are required to finalize.",
            "fields": missing_fields,
        })

    before = serialize_instance(note)
    now = timezone.now()
    note.status = "FINAL"
    note.finalized_at = now
    note.updated_at = now
    note.save(update_fields=["status", "finalized_at", "updated_at"])

    payload = _clinical_note_payload(note)
    _audit(request, spec, note, before, serialize_instance(note))
    _outbox(spec, note, payload)
    return Response(payload, status=200)



# --- Consultation minimal workflow fix ---

def _consultation_action_locked(
    kwargs,
):
    model = apps.get_model(
        "consultations",
        "Consultation",
    )

    consultation_id = kwargs.get(
        "consultation_id"
    )

    if consultation_id is None:
        raise NotFound({
            "code":
                "CONSULTATION_NOT_FOUND",
        })

    try:
        # IMPORTANT:
        # Consultation.assigned_to is nullable.
        # Do not select_related(nullable FK) together
        # with FOR UPDATE because PostgreSQL rejects
        # locking the nullable side of an outer join.
        return (
            model.objects
            .select_for_update()
            .get(
                pk=consultation_id
            )
        )

    except model.DoesNotExist as exc:
        raise NotFound({
            "code":
                "CONSULTATION_NOT_FOUND",
        }) from exc


def _consultation_accept_strict(
    request,
    spec,
    kwargs,
):
    consultation = (
        _consultation_action_locked(
            kwargs
        )
    )

    expected_role = {
        "NEUROSURGERY":
            "NEUROSURGEON",
        "RADIOLOGY":
            "RADIOLOGY",
    }.get(
        consultation.consultation_type
    )

    if (
        expected_role is None
        or _role_code(request.user)
        != expected_role
    ):
        raise PermissionDenied({
            "code":
                "CONSULTATION_FORBIDDEN",
        })

    if (
        consultation.status
        != "REQUESTED"
        or (
            consultation.assigned_to_id
            is not None
            and consultation.assigned_to_id
            != request.user.id
        )
    ):
        raise ContractConflict({
            "code":
                "CONSULTATION_INVALID_STATE",
        })

    before = serialize_instance(
        consultation
    )

    now = timezone.now()

    consultation.status = "ACCEPTED"
    consultation.assigned_to_id = (
        request.user.id
    )
    consultation.accepted_at = now

    fields = _field_map(
        consultation.__class__
    )

    update_fields = [
        "status",
        "assigned_to",
        "accepted_at",
    ]

    if "updated_at" in fields:
        consultation.updated_at = now
        update_fields.append(
            "updated_at"
        )

    consultation.save(
        update_fields=update_fields
    )

    _record_history(
        consultation,
        "REQUESTED",
        "ACCEPTED",
        request,
    )

    after = serialize_instance(
        consultation
    )

    _audit(
        request,
        spec,
        consultation,
        before,
        after,
    )

    return Response(
        after,
        status=200,
    )


def _consultation_respond_strict(
    request,
    spec,
    kwargs,
):
    consultation = (
        _consultation_action_locked(
            kwargs
        )
    )

    if (
        consultation.assigned_to_id
        != request.user.id
    ):
        raise PermissionDenied({
            "code":
                "CONSULTATION_FORBIDDEN",
        })

    if (
        consultation.status
        != "IN_PROGRESS"
    ):
        raise ContractConflict({
            "code":
                "CONSULTATION_INVALID_STATE",
        })

    final_opinion = str(
        request.data.get(
            "final_opinion"
        )
        or ""
    ).strip()

    if not final_opinion:
        raise ContractError({
            "code":
                "FINAL_OPINION_REQUIRED",
        })

    before = serialize_instance(
        consultation
    )

    now = timezone.now()

    consultation.status = "RESPONDED"
    consultation.final_opinion = (
        final_opinion
    )
    consultation.treatment_plan = (
        request.data.get(
            "treatment_plan"
        )
    )
    consultation.completed_at = now

    fields = _field_map(
        consultation.__class__
    )

    update_fields = [
        "status",
        "final_opinion",
        "treatment_plan",
        "completed_at",
    ]

    if "updated_at" in fields:
        consultation.updated_at = now
        update_fields.append(
            "updated_at"
        )

    consultation.save(
        update_fields=update_fields
    )

    _record_history(
        consultation,
        "IN_PROGRESS",
        "RESPONDED",
        request,
    )

    after = serialize_instance(
        consultation
    )

    _audit(
        request,
        spec,
        consultation,
        before,
        after,
    )

    _outbox(
        spec,
        consultation,
        after,
    )

    return Response(
        after,
        status=200,
    )


def _ensure_consultation_action_scope(request, kwargs, action):
    """Enforce requester/assignee scope for generic consultation actions."""
    consultation = _consultation_action_locked(kwargs)

    if action in {"start", "reject"}:
        allowed = consultation.assigned_to_id == request.user.id
    elif action == "view-response":
        allowed = consultation.requested_by_id == request.user.id
    elif action == "cancel":
        allowed = request.user.id in {
            consultation.requested_by_id,
            consultation.assigned_to_id,
        }
    else:
        allowed = True

    if not allowed:
        raise PermissionDenied({
            "code": "CONSULTATION_FORBIDDEN",
        })


def _medication_schedule_payload(schedule, intake=None):
    item = schedule.prescription_item
    return {
        "schedule_id": str(schedule.id),
        "prescription_id": str(item.prescription_id),
        "medication_name": item.medication_name,
        "scheduled_at": _safe_value(schedule.scheduled_at),
        "time_slot": schedule.time_slot,
        "dose": _safe_value(schedule.dose),
        "status": intake.status if intake is not None else "PENDING",
        "intake_id": str(intake.id) if intake is not None else None,
        "taken_at": _safe_value(intake.taken_at) if intake is not None else None,
    }


def _patient_medication_schedules(request):
    patient = _patient_for_user(request.user)
    if patient is None:
        raise PermissionDenied({"code": "FORBIDDEN_ROLE"})

    schedule_model = apps.get_model("medications", "MedicationSchedule")
    return schedule_model.objects.filter(
        prescription_item__prescription__encounter__patient_id=patient.id,
        prescription_item__prescription__status="FINAL",
    ).select_related("prescription_item__prescription")


def _patient_medication_schedules_get(request, spec, kwargs):
    del spec, kwargs
    date_value = request.query_params.get("date")
    if not date_value:
        raise ContractError({"code": "VALIDATION_ERROR", "date": "is required"})

    target_date = parse_date(date_value)
    if target_date is None:
        raise ContractError({"code": "VALIDATION_ERROR", "date": "must be an ISO-8601 date"})

    schedules = list(
        _patient_medication_schedules(request)
        .filter(scheduled_at__date=target_date)
        .order_by("scheduled_at")
    )
    intake_model = apps.get_model("medications", "MedicationIntake")
    intakes = {
        intake.schedule_id: intake
        for intake in intake_model.objects.filter(schedule_id__in=[row.id for row in schedules])
    }
    taken_count = sum(1 for intake in intakes.values() if intake.status == "TAKEN")

    return Response({
        "summary": {
            "scheduled_count": len(schedules),
            "taken_count": taken_count,
            "adherence_rate": (taken_count / len(schedules) * 100) if schedules else 0,
        },
        "items": [
            _medication_schedule_payload(row, intakes.get(row.id))
            for row in schedules
        ],
    }, status=200)


def _patient_medication_intake_create(request, spec, kwargs):
    del spec, kwargs
    schedule_id = request.data.get("medication_schedule_id")
    status_value = request.data.get("status")
    if not schedule_id or status_value not in {"TAKEN", "SKIPPED"}:
        raise ContractError({"code": "VALIDATION_ERROR"})

    try:
        schedule = _patient_medication_schedules(request).get(pk=schedule_id)
    except apps.get_model("medications", "MedicationSchedule").DoesNotExist as exc:
        raise NotFound({"code": "MEDICATION_SCHEDULE_NOT_FOUND"}) from exc

    intake_model = apps.get_model("medications", "MedicationIntake")
    if intake_model.objects.filter(schedule_id=schedule.id).exists():
        raise ContractConflict({"code": "MEDICATION_INTAKE_DUPLICATED"})

    now = timezone.now()
    intake = intake_model.objects.create(
        schedule_id=schedule.id,
        recorded_by_id=request.user.id,
        status=status_value,
        taken_at=now if status_value == "TAKEN" else None,
        note=request.data.get("note") or None,
        created_at=now,
        updated_at=now,
    )
    return Response({
        "intake_id": str(intake.id),
        "schedule_id": str(schedule.id),
        "status": intake.status,
        "taken_at": _safe_value(intake.taken_at),
        "note": intake.note,
    }, status=201)


def _patient_medication_intake_update(request, spec, kwargs):
    del spec
    intake_id = kwargs.get("intake_id")
    status_value = request.data.get("status")
    if status_value not in {"TAKEN", "SKIPPED"}:
        raise ContractError({"code": "VALIDATION_ERROR"})

    intake_model = apps.get_model("medications", "MedicationIntake")
    try:
        intake = intake_model.objects.select_for_update().get(pk=intake_id)
    except intake_model.DoesNotExist as exc:
        raise NotFound({"code": "MEDICATION_INTAKE_NOT_FOUND"}) from exc

    allowed_schedule_ids = _patient_medication_schedules(request).filter(
        pk=intake.schedule_id,
    ).values_list("id", flat=True)
    if not allowed_schedule_ids:
        raise NotFound({"code": "MEDICATION_INTAKE_NOT_FOUND"})

    intake.status = status_value
    intake.taken_at = timezone.now() if status_value == "TAKEN" else None
    intake.updated_at = timezone.now()
    intake.save(update_fields=["status", "taken_at", "updated_at"])
    return Response({
        "intake_id": str(intake.id),
        "schedule_id": str(intake.schedule_id),
        "status": intake.status,
        "taken_at": _safe_value(intake.taken_at),
        "note": intake.note,
        "updated_at": _safe_value(intake.updated_at),
    }, status=200)


CUSTOM_HANDLERS = {
    "API-RX-001": _batchb_rx_create,
    "API-CON-004": _consultation_accept_strict,
    "API-CON-006": _consultation_respond_strict,
    "API-ALLERGY-001": _batchb_allergy_list,
    "API-ALLERGY-002": _batchb_allergy_create,
    "API-ALLERGY-003": _batchb_allergy_deactivate,
    "API-RX-002": _batchb_rx_detail,
    "API-RX-003": _batchb_rx_patch,
    "API-RX-004": _batchb_rx_finalize,
    "API-SCH-002": _schedule_put,
    "API-SLOT-001": _appointment_available_slots,
    "API-APP-001": _appointment_create,
    "API-APP-002": _appointment_list,
    "API-APP-003": _appointment_detail,
    "API-APP-004": _appointment_reschedule,
    "API-APP-005": _appointment_cancel,
    "API-APP-006": _appointment_request_list,
    "API-APP-007": _appointment_accept,
    "API-APP-008": _appointment_reject,
    "API-APP-009": _staff_appointment_list,
    "API-APP-010": _appointment_complete,
    "API-APP-011": _appointment_correct,
    "API-NOTI-003": _notification_preferences_get,
    "API-NOTI-004": _notification_preferences_patch,
    "API-ASM-002": _assessment_start,
    "API-ASM-003": _assessment_detail,
    "API-ASM-004": _assessment_patch,
    "API-ASM-005": _assessment_complete,
    "API-FCM-001": _fcm_create,
    "API-MEDSAFE-001": _medication_safety_check,
    "API-MED-001": _patient_medication_schedules_get,
    "API-MED-002": _patient_medication_intake_create,
    "API-MED-003": _patient_medication_intake_update,
    "API-CDS-001": _cds_discovery,
    "API-NOTE-001": _clinical_note_create,
    "API-NOTE-004": _clinical_note_update,
    "API-NOTE-005": _clinical_note_finalize,
}


def execute_contract(request, spec, **kwargs):
    check_access(request, spec)

    model = _model(spec)
    handler = CUSTOM_HANDLERS.get(spec["api_id"])
    context = transaction.atomic() if spec.get("transactional") or request.method not in READ_METHODS else nullcontext()

    with context:
        if handler:
            return handler(request, spec, kwargs)

        method = request.method.upper()
        action = spec["endpoint"].rstrip("/").rsplit("/", 1)[-1].lower()

        if method == "GET":
            return _generic_get(request, spec, kwargs)
        if method == "DELETE":
            return _generic_delete(request, spec, kwargs)
        if method in {"PATCH", "PUT"}:
            if method == "PUT" and not kwargs:
                return _generic_create(request, spec, kwargs)
            return _generic_update(request, spec, kwargs)
        if method == "POST":
            is_action = bool(kwargs) and (
                action in ACTION_STATUS
                or any(token in action for token in (
                    "acknowledge", "accept", "approve", "archive", "block",
                    "cancel", "close", "complete", "final", "read", "reject",
                    "respond", "retry", "start", "unblock", "validate",
                    "view-response",
                ))
            )
            if is_action:
                if (
                    model is not None
                    and model._meta.label_lower == "consultations.consultation"
                ):
                    _ensure_consultation_action_scope(
                        request,
                        kwargs,
                        action,
                    )
                return _generic_action(request, spec, kwargs)
            return _generic_create(request, spec, kwargs)

    raise ContractError({"detail": "Unsupported HTTP method."})



def _openapi_success_status(spec):
    text = str(spec.get("success") or "")
    match = re.search(r"\b(20[0-9])\b", text)

    if match:
        return int(match.group(1))

    method = str(spec.get("method") or "").upper()

    if method == "POST":
        return 200

    if method == "DELETE":
        return 204

    return 200


def _openapi_operation_id(spec):
    api_id = str(spec.get("api_id") or "generated")
    return "brainon_" + api_id.lower().replace("-", "_")


def _decorate_contract_method(method, spec):
    http_method = str(spec.get("method") or "").upper()
    status_code = _openapi_success_status(spec)

    schema_kwargs = {
        "operation_id": _openapi_operation_id(spec),
        "summary": (
            f"{spec.get('api_id', '')} "
            f"{spec.get('api_name', '')}"
        ).strip(),
        "responses": {
            status_code: (
                OpenApiResponse(description="Success")
                if status_code == 204
                else OpenApiTypes.OBJECT
            )
        },
    }

    if http_method in {"POST", "PUT", "PATCH"}:
        schema_kwargs["request"] = OpenApiTypes.OBJECT
    else:
        schema_kwargs["request"] = None

    return extend_schema(**schema_kwargs)(method)


def build_contract_view(specs):
    service_specs = [s for s in specs if s.get("service_scope")]
    user_specs = [s for s in specs if not s.get("service_scope")]

    attrs = {"__module__": "apps.common.remaining149_runtime"}

    if service_specs and not user_specs:
        attrs["authentication_classes"] = [ServiceJWTAuthentication]
        attrs["permission_classes"] = []
    else:
        attrs["permission_classes"] = [IsAuthenticated]

    for spec in specs:
        method_name = spec["method"].lower()

        def make_method(current_spec):
            def method(self, request, **kwargs):
                return execute_contract(request, current_spec, **kwargs)

            method.__name__ = current_spec["method"].lower()
            method.__doc__ = (
                f"{current_spec['api_id']} "
                f"{current_spec.get('api_name', '')}"
            )

            return _decorate_contract_method(
                method,
                current_spec,
            )

        attrs[method_name] = make_method(spec)

    name = "GeneratedReal_" + "_".join(
        spec["api_id"].replace("-", "_")
        for spec in specs
    )
    return type(name, (APIView,), attrs)

# === BATCH_C_CDS_RAD_FINAL_START ===


# ============================================================
# Shared Radiology helpers
# ============================================================

def _batchc_rad_model(name):
    return apps.get_model(
        "radiology",
        name,
    )


def _batchc_rad_get_report(
    request,
    kwargs,
    *,
    for_update=True,
):
    report_model = _batchc_rad_model(
        "RadiologyReport"
    )

    qs = report_model.objects.all()

    if for_update:
        qs = qs.select_for_update()

    report_id = kwargs.get(
        "report_id"
    )

    if not report_id:
        raise ContractError({
            "code": "REPORT_ID_REQUIRED",
            "detail": "report_id is required.",
        })

    try:
        return qs.get(
            pk=report_id
        )

    except report_model.DoesNotExist as exc:
        raise NotFound({
            "code": "RESOURCE_NOT_FOUND",
            "detail": (
                "RadiologyReport was not found."
            ),
        }) from exc


def _batchc_user_relation_id(
    field,
    user,
):
    """
    User FK 또는 User profile FK에
    현재 로그인 사용자를 안전하게 연결한다.
    """

    if (
        field is None
        or not field.is_relation
        or not getattr(
            user,
            "pk",
            None,
        )
    ):
        return None

    related_model = (
        field.remote_field.model
    )

    try:
        if isinstance(
            user,
            related_model,
        ):
            return user.pk
    except TypeError:
        pass

    related_fields = _field_map(
        related_model
    )

    user_field = (
        related_fields.get("user")
    )

    if (
        user_field is not None
        and user_field.is_relation
    ):
        obj = (
            related_model.objects
            .filter(
                **{
                    user_field.attname:
                        user.pk
                }
            )
            .first()
        )

        if obj is not None:
            return obj.pk

    return None


def _batchc_rad_snapshot(report):
    """
    Revision snapshot은 반드시 JSON-safe 값으로 저장한다.
    """
    return _safe_value(
        serialize_instance(
            report
        )
    )


def _batchc_rad_revision(
    request,
    report,
    *,
    previous_snapshot,
    new_snapshot,
    reason=None,
    version=None,
):
    revision_model = _batchc_rad_model(
        "RadiologyReportRevision"
    )

    fields = _field_map(
        revision_model
    )

    data = {}

    # Report FK
    for name in (
        "report",
        "radiology_report",
    ):
        field = fields.get(name)

        if (
            field is not None
            and field.is_relation
        ):
            data[field.attname] = (
                report.pk
            )
            break

    # version
    if "version" in fields:
        data["version"] = (
            version
            if version is not None
            else getattr(
                report,
                "version",
                1,
            )
        )

    # Snapshot
    if "previous_snapshot" in fields:
        data["previous_snapshot"] = (
            _safe_value(
                previous_snapshot
                or {}
            )
        )

    if "new_snapshot" in fields:
        data["new_snapshot"] = (
            _safe_value(
                new_snapshot
                or {}
            )
        )

    # 변경 사유
    if "change_reason" in fields:
        data["change_reason"] = (
            reason or ""
        )

    # 변경자
    for name in (
        "changed_by",
        "created_by",
    ):
        field = fields.get(name)

        if (
            field is not None
            and field.is_relation
        ):
            relation_id = (
                _batchc_user_relation_id(
                    field,
                    request.user,
                )
            )

            if relation_id is not None:
                data[field.attname] = (
                    relation_id
                )
            break

    # 생성시각
    for name in (
        "created_at",
        "changed_at",
    ):
        if name in fields:
            data[name] = timezone.now()

    # 아직 남은 NOT NULL / no default 필드 탐지
    unresolved = []

    for field in (
        revision_model._meta.fields
    ):
        if field.primary_key:
            continue

        if (
            field.name in data
            or field.attname in data
        ):
            continue

        if (
            field.null
            or field.has_default()
            or getattr(
                field,
                "auto_now",
                False,
            )
            or getattr(
                field,
                "auto_now_add",
                False,
            )
        ):
            continue

        # 의미가 명확한 안전한 fallback만 허용
        if isinstance(
            field,
            models.JSONField,
        ):
            data[field.name] = {}

        elif isinstance(
            field,
            (
                models.CharField,
                models.TextField,
            ),
        ):
            data[field.name] = ""

        elif isinstance(
            field,
            models.DateTimeField,
        ):
            data[field.name] = (
                timezone.now()
            )

        elif (
            field.name == "version"
            and isinstance(
                field,
                (
                    models.IntegerField,
                    models.BigIntegerField,
                    models.SmallIntegerField,
                ),
            )
        ):
            data[field.name] = (
                version
                or getattr(
                    report,
                    "version",
                    1,
                )
                or 1
            )

        else:
            unresolved.append(
                field.name
            )

    if unresolved:
        raise ContractError({
            "code":
                "RADIOLOGY_REVISION_SCHEMA_ERROR",

            "detail":
                (
                    "Required Revision fields "
                    "could not be resolved: "
                    + ", ".join(
                        unresolved
                    )
                ),
        })

    return (
        revision_model.objects.create(
            **data
        )
    )


def _batchc_rad_check_version(
    request,
    report,
):
    if not isinstance(
        request.data,
        dict,
    ):
        return

    requested = (
        request.data.get(
            "version"
        )
    )

    if requested in (
        None,
        "",
    ):
        return

    actual = getattr(
        report,
        "version",
        None,
    )

    if (
        actual is not None
        and int(requested)
        != int(actual)
    ):
        raise ContractError({
            "code":
                "RADIOLOGY_VERSION_CONFLICT",

            "detail":
                (
                    f"version mismatch: "
                    f"request={requested}, "
                    f"current={actual}"
                ),
        })


def _batchc_rad_require_confirmation(
    request,
):
    if (
        not isinstance(
            request.data,
            dict,
        )
        or request.data.get(
            "confirmation"
        )
        is not True
    ):
        raise ContractError({
            "code":
                "CONFIRMATION_REQUIRED",

            "detail":
                "confirmation=true is required.",
        })


def _batchc_rad_apply_content(
    report,
    request,
):
    fields = _field_map(
        report.__class__
    )

    allowed = (
        "findings",
        "impression",
        "recommendation",
        "structured_findings",
        "critical_finding",
        "critical_level",
    )

    for name in allowed:
        if (
            name in fields
            and name in request.data
        ):
            setattr(
                report,
                name,
                request.data[name],
            )


def _batchc_rad_increment_version(
    report,
):
    fields = _field_map(
        report.__class__
    )

    if "version" in fields:
        report.version = (
            int(
                getattr(
                    report,
                    "version",
                    0,
                )
                or 0
            )
            + 1
        )


def _batchc_rad_set_actor(
    report,
    request,
    field_name,
):
    fields = _field_map(
        report.__class__
    )

    field = fields.get(
        field_name
    )

    if (
        field is None
        or not field.is_relation
    ):
        return

    relation_id = (
        _batchc_user_relation_id(
            field,
            request.user,
        )
    )

    if relation_id is not None:
        setattr(
            report,
            field.attname,
            relation_id,
        )


# ============================================================
# RAD-002 : 판독문 생성
# ============================================================

def _batchc_rad_create(
    request,
    spec,
    kwargs,
):
    report_model = _batchc_rad_model(
        "RadiologyReport"
    )

    fields = _field_map(
        report_model
    )

    data = _write_data(
        report_model,
        request,
    )

    data = _apply_server_defaults(
        report_model,
        data,
    )

    # study_id
    study_id = (
        request.data.get("study_id")
        if isinstance(
            request.data,
            dict,
        )
        else None
    )

    study_field = (
        fields.get("study")
    )

    if (
        study_id
        and study_field is not None
        and study_field.is_relation
    ):
        data[
            study_field.attname
        ] = study_id

    if "version" in fields:
        data["version"] = 1

    if "status" in fields:
        data["status"] = "DRAFT"

    if "is_current" in fields:
        data["is_current"] = True

    for name in (
        "created_at",
        "updated_at",
    ):
        if name in fields:
            data[name] = timezone.now()

    for actor_name in (
        "author",
        "created_by",
        "radiologist",
    ):
        field = fields.get(
            actor_name
        )

        if (
            field is not None
            and field.is_relation
        ):
            actor_id = (
                _batchc_user_relation_id(
                    field,
                    request.user,
                )
            )

            if actor_id is not None:
                data[
                    field.attname
                ] = actor_id

            break

    try:
        report = (
            report_model.objects
            .create(
                **data
            )
        )

    except (
        IntegrityError,
        TypeError,
        ValueError,
    ) as exc:
        raise ContractError({
            "code":
                "VALIDATION_ERROR",

            "detail":
                str(exc),
        }) from exc

    after = _batchc_rad_snapshot(
        report
    )

    _batchc_rad_revision(
        request,
        report,
        previous_snapshot={},
        new_snapshot=after,
        reason="initial report created",
        version=getattr(
            report,
            "version",
            1,
        ),
    )

    _audit(
        request,
        spec,
        report,
        None,
        after,
    )

    _outbox(
        spec,
        report,
        after,
    )

    return Response(
        after,
        status=201,
    )


# ============================================================
# RAD-004 : 판독문 수정
# ============================================================

def _batchc_rad_update(
    request,
    spec,
    kwargs,
):
    report = (
        _batchc_rad_get_report(
            request,
            kwargs,
            for_update=True,
        )
    )

    if getattr(
        report,
        "status",
        None,
    ) not in {
        "DRAFT",
        "PRELIMINARY",
    }:
        raise ContractError({
            "code":
                "RADIOLOGY_INVALID_STATE",

            "detail":
                "Only DRAFT/PRELIMINARY report can be edited.",
        })

    _batchc_rad_check_version(
        request,
        report,
    )

    before = _batchc_rad_snapshot(
        report
    )

    _batchc_rad_apply_content(
        report,
        request,
    )

    _batchc_rad_increment_version(
        report
    )

    fields = _field_map(
        report.__class__
    )

    if "updated_at" in fields:
        report.updated_at = (
            timezone.now()
        )

    report.save()

    after = _batchc_rad_snapshot(
        report
    )

    _batchc_rad_revision(
        request,
        report,
        previous_snapshot=before,
        new_snapshot=after,
        reason=(
            request.data.get(
                "reason",
                "report updated",
            )
            if isinstance(
                request.data,
                dict,
            )
            else "report updated"
        ),
        version=getattr(
            report,
            "version",
            None,
        ),
    )

    _audit(
        request,
        spec,
        report,
        before,
        after,
    )

    _outbox(
        spec,
        report,
        after,
    )

    return Response(
        after,
        status=200,
    )


# ============================================================
# RAD-005 : Preliminary
# ============================================================

def _batchc_rad_preliminary(
    request,
    spec,
    kwargs,
):
    report = (
        _batchc_rad_get_report(
            request,
            kwargs,
            for_update=True,
        )
    )

    if getattr(
        report,
        "status",
        None,
    ) != "DRAFT":
        raise ContractError({
            "code":
                "RADIOLOGY_INVALID_STATE",

            "detail":
                "submit-preliminary requires DRAFT.",
        })

    _batchc_rad_check_version(
        request,
        report,
    )

    _batchc_rad_require_confirmation(
        request
    )

    before = _batchc_rad_snapshot(
        report
    )

    _batchc_rad_apply_content(
        report,
        request,
    )

    report.status = "PRELIMINARY"

    fields = _field_map(
        report.__class__
    )

    if "preliminary_at" in fields:
        report.preliminary_at = (
            timezone.now()
        )

    _batchc_rad_increment_version(
        report
    )

    if "updated_at" in fields:
        report.updated_at = (
            timezone.now()
        )

    report.save()

    after = _batchc_rad_snapshot(
        report
    )

    _batchc_rad_revision(
        request,
        report,
        previous_snapshot=before,
        new_snapshot=after,
        reason="submit preliminary",
        version=getattr(
            report,
            "version",
            None,
        ),
    )

    _audit(
        request,
        spec,
        report,
        before,
        after,
    )

    _outbox(
        spec,
        report,
        after,
    )

    return Response(
        after,
        status=200,
    )


# ============================================================
# Radiology notification recipient
# ============================================================

def _batchc_rad_notify_order_requester(report, request, *, title, body):
    """Notify the concrete ImagingOrder requester after a final report change."""
    study = report.study
    order = getattr(study, "imaging_order", None)
    recipient = getattr(order, "requested_by", None)
    if order is None or recipient is None:
        return None

    from apps.notifications.services.notifications import create_notification_for_user

    return create_notification_for_user(
        recipient_user=recipient,
        category="IMAGING",
        severity="CRITICAL" if report.critical_finding else "INFO",
        title=title,
        body=body,
        data_json={
            "patient_id": str(order.patient_id),
            "encounter_id": str(order.encounter_id),
            "resource_type": "RadiologyReport",
            "resource_id": str(report.id),
            "actor_user_id": str(request.user.id),
        },
    )


# ============================================================
# RAD-006 : Finalize
# ============================================================

def _batchc_rad_finalize(
    request,
    spec,
    kwargs,
):
    report = (
        _batchc_rad_get_report(
            request,
            kwargs,
            for_update=True,
        )
    )

    if getattr(
        report,
        "status",
        None,
    ) not in {
        "DRAFT",
        "PRELIMINARY",
    }:
        raise ContractError({
            "code":
                "RADIOLOGY_INVALID_STATE",

            "detail":
                "finalize requires DRAFT/PRELIMINARY.",
        })

    _batchc_rad_check_version(
        request,
        report,
    )

    _batchc_rad_require_confirmation(
        request
    )

    findings = (
        getattr(
            report,
            "findings",
            None,
        )
    )

    impression = (
        getattr(
            report,
            "impression",
            None,
        )
    )

    if not findings or not impression:
        raise ContractError({
            "code":
                "RADIOLOGY_CONTENT_REQUIRED",

            "detail":
                "findings and impression are required.",
        })

    before = _batchc_rad_snapshot(
        report
    )

    report.status = "FINAL"

    fields = _field_map(
        report.__class__
    )

    if "finalized_at" in fields:
        report.finalized_at = (
            timezone.now()
        )

    _batchc_rad_set_actor(
        report,
        request,
        "finalized_by",
    )

    _batchc_rad_increment_version(
        report
    )

    if "updated_at" in fields:
        report.updated_at = (
            timezone.now()
        )

    report.save()

    after = _batchc_rad_snapshot(
        report
    )

    _batchc_rad_revision(
        request,
        report,
        previous_snapshot=before,
        new_snapshot=after,
        reason="finalized",
        version=getattr(
            report,
            "version",
            None,
        ),
    )

    _audit(
        request,
        spec,
        report,
        before,
        after,
    )

    _outbox(
        spec,
        report,
        after,
    )

    _batchc_rad_notify_order_requester(
        report,
        request,
        title="Final imaging report available",
        body="The final imaging report is available.",
    )

    return Response(
        after,
        status=200,
    )


# ============================================================
# RAD-007 : Amend
# ============================================================

def _batchc_rad_amend(
    request,
    spec,
    kwargs,
):
    old = (
        _batchc_rad_get_report(
            request,
            kwargs,
            for_update=True,
        )
    )

    if (
        getattr(
            old,
            "status",
            None,
        )
        not in {
            "FINAL",
            "AMENDED",
        }
        or (
            hasattr(
                old,
                "is_current",
            )
            and old.is_current
            is not True
        )
    ):
        raise ContractError({
            "code":
                "RADIOLOGY_INVALID_STATE",

            "detail":
                (
                    "amend requires current "
                    "FINAL/AMENDED report."
                ),
        })

    _batchc_rad_require_confirmation(
        request
    )

    reason = (
        request.data.get(
            "change_reason"
        )
        if isinstance(
            request.data,
            dict,
        )
        else None
    )

    if (
        not reason
        or len(
            str(reason)
        ) < 10
    ):
        raise ContractError({
            "code":
                "CHANGE_REASON_REQUIRED",

            "detail":
                "change_reason must be at least 10 characters.",
        })

    old_before = (
        _batchc_rad_snapshot(
            old
        )
    )

    report_model = (
        old.__class__
    )

    fields = _field_map(
        report_model
    )

    # 기존 Report 값 복제
    clone = {}

    for field in (
        report_model._meta.fields
    ):
        if field.primary_key:
            continue

        if field.name in {
            "created_at",
            "updated_at",
        }:
            continue

        if field.is_relation:
            clone[
                field.attname
            ] = getattr(
                old,
                field.attname,
            )

        else:
            clone[
                field.name
            ] = getattr(
                old,
                field.name,
            )

    # 기존 current 해제
    if "is_current" in fields:
        old.is_current = False

    if "updated_at" in fields:
        old.updated_at = (
            timezone.now()
        )

    old.save()

    clone["status"] = "AMENDED"

    if "is_current" in fields:
        clone["is_current"] = True

    if "version" in fields:
        clone["version"] = (
            int(
                getattr(
                    old,
                    "version",
                    0,
                )
                or 0
            )
            + 1
        )

    if "created_at" in fields:
        clone["created_at"] = (
            timezone.now()
        )

    if "updated_at" in fields:
        clone["updated_at"] = (
            timezone.now()
        )

    # 요청의 정정 내용 적용
    for name in (
        "findings",
        "impression",
        "recommendation",
        "structured_findings",
        "critical_finding",
        "critical_level",
    ):
        if (
            name in fields
            and name in request.data
        ):
            clone[name] = (
                request.data[name]
            )

    new = report_model.objects.create(
        **clone
    )

    new_after = (
        _batchc_rad_snapshot(
            new
        )
    )

    _batchc_rad_revision(
        request,
        new,
        previous_snapshot=old_before,
        new_snapshot=new_after,
        reason=str(reason),
        version=getattr(
            new,
            "version",
            None,
        ),
    )

    _audit(
        request,
        spec,
        new,
        old_before,
        new_after,
    )

    _outbox(
        spec,
        new,
        new_after,
    )

    _batchc_rad_notify_order_requester(
        new,
        request,
        title="Imaging report amended",
        body="A finalized imaging report has been amended.",
    )

    return Response(
        new_after,
        status=201,
    )


# ============================================================
# RAD-009 : Measurement Create
# ============================================================

def _batchc_rad_measurement_create(
    request,
    spec,
    kwargs,
):
    report = (
        _batchc_rad_get_report(
            request,
            kwargs,
            for_update=True,
        )
    )

    if getattr(
        report,
        "status",
        None,
    ) not in {
        "DRAFT",
        "PRELIMINARY",
    }:
        raise ContractError({
            "code":
                "RADIOLOGY_INVALID_STATE",

            "detail":
                (
                    "measurement creation requires "
                    "DRAFT/PRELIMINARY."
                ),
        })

    model = _batchc_rad_model(
        "RadiologyMeasurement"
    )

    fields = _field_map(
        model
    )

    data = _write_data(
        model,
        request,
    )

    # report FK
    for name in (
        "report",
        "radiology_report",
    ):
        field = fields.get(name)

        if (
            field is not None
            and field.is_relation
        ):
            data[
                field.attname
            ] = report.pk
            break

    # created_by
    field = fields.get(
        "created_by"
    )

    if (
        field is not None
        and field.is_relation
    ):
        actor_id = (
            _batchc_user_relation_id(
                field,
                request.user,
            )
        )

        if actor_id is not None:
            data[
                field.attname
            ] = actor_id

    if "created_at" in fields:
        data["created_at"] = (
            timezone.now()
        )

    try:
        obj = model.objects.create(
            **data
        )

    except (
        IntegrityError,
        TypeError,
        ValueError,
    ) as exc:
        raise ContractError({
            "code":
                "VALIDATION_ERROR",

            "detail":
                str(exc),
        }) from exc

    after = serialize_instance(
        obj
    )

    _audit(
        request,
        spec,
        obj,
        None,
        after,
    )

    return Response(
        after,
        status=201,
    )


# ============================================================
# RAD-011 : Cancel
# ============================================================

def _batchc_rad_cancel(
    request,
    spec,
    kwargs,
):
    report = (
        _batchc_rad_get_report(
            request,
            kwargs,
            for_update=True,
        )
    )

    if getattr(
        report,
        "status",
        None,
    ) not in {
        "DRAFT",
        "PRELIMINARY",
    }:
        raise ContractError({
            "code":
                "RADIOLOGY_INVALID_STATE",

            "detail":
                (
                    "Only DRAFT/PRELIMINARY "
                    "report can be cancelled."
                ),
        })

    if (
        hasattr(
            report,
            "is_current",
        )
        and report.is_current
        is not True
    ):
        raise ContractError({
            "code":
                "RADIOLOGY_NOT_CURRENT",

            "detail":
                "Only current report can be cancelled.",
        })

    _batchc_rad_check_version(
        request,
        report,
    )

    reason = (
        request.data.get(
            "reason"
        )
        if isinstance(
            request.data,
            dict,
        )
        else None
    )

    if not reason:
        raise ContractError({
            "code":
                "CANCEL_REASON_REQUIRED",

            "detail":
                "reason is required.",
        })

    before = _batchc_rad_snapshot(
        report
    )

    report.status = "CANCELLED"

    fields = _field_map(
        report.__class__
    )

    if "is_current" in fields:
        report.is_current = False

    _batchc_rad_increment_version(
        report
    )

    if "updated_at" in fields:
        report.updated_at = (
            timezone.now()
        )

    report.save()

    after = _batchc_rad_snapshot(
        report
    )

    _batchc_rad_revision(
        request,
        report,
        previous_snapshot=before,
        new_snapshot=after,
        reason=str(reason),
        version=getattr(
            report,
            "version",
            None,
        ),
    )

    _audit(
        request,
        spec,
        report,
        before,
        after,
    )

    _outbox(
        spec,
        report,
        after,
    )

    return Response(
        after,
        status=200,
    )


# ============================================================
# CDS helpers
# ============================================================

def _batchc_cds_uuid(value):
    if not value:
        return None

    value = str(value)

    if "/" in value:
        value = value.rsplit(
            "/",
            1,
        )[-1]

    try:
        return uuid.UUID(
            value
        )
    except Exception:
        return None


def _batchc_cds_validate_hook(
    request,
    expected_hook,
):
    if not isinstance(
        request.data,
        dict,
    ):
        raise ContractError({
            "code":
                "INVALID_CDS_REQUEST",

            "detail":
                "JSON object is required.",
        })

    if (
        request.data.get("hook")
        != expected_hook
    ):
        raise ContractError({
            "code":
                "INVALID_CDS_HOOK",

            "detail":
                (
                    f"hook must be "
                    f"{expected_hook}."
                ),
        })

    context = (
        request.data.get(
            "context"
        )
        or {}
    )

    return context


def _batchc_cds_patient(
    context,
):
    patient_id = (
        _batchc_cds_uuid(
            context.get(
                "patientId"
            )
        )
    )

    if patient_id is None:
        raise ContractError({
            "code":
                "CDS_PATIENT_REQUIRED",

            "detail":
                "context.patientId is required.",
        })

    patient_model = apps.get_model(
        "patients",
        "Patient",
    )

    try:
        return (
            patient_model.objects
            .get(
                pk=patient_id
            )
        )

    except patient_model.DoesNotExist as exc:
        raise NotFound({
            "code":
                "PATIENT_NOT_FOUND",

            "detail":
                "Patient was not found.",
        }) from exc


def _batchc_cds_cards_from_alerts(
    alerts,
):
    cards = []

    for alert in alerts:
        severity = str(
            alert.get(
                "severity",
                "WARNING",
            )
        ).upper()

        indicator = (
            "critical"
            if severity in {
                "HIGH",
                "MAJOR",
                "BLOCK",
                "CRITICAL",
            }
            else "warning"
        )

        cards.append({
            "summary":
                (
                    alert.get("message")
                    or alert.get("type")
                    or "Medication safety alert"
                ),

            "indicator":
                indicator,

            "source": {
                "label":
                    "BrainOn Medication Safety"
            },

            "detail":
                str(
                    alert.get("type")
                    or ""
                ),
        })

    return cards


def _batchc_cds_medication(
    request,
    spec,
    kwargs,
    expected_hook,
):
    context = (
        _batchc_cds_validate_hook(
            request,
            expected_hook,
        )
    )

    patient = (
        _batchc_cds_patient(
            context
        )
    )

    # 기존 실제 Medication Safety 로직 재사용
    class SafetyRequest:
        pass

    safety_request = (
        SafetyRequest()
    )

    safety_request.data = {
        "patient_id":
            str(patient.pk),

        # 현재 CDS FHIR Adapter 상세 매핑 전에는
        # Patient Allergy + Local DUR 기반 검사 수행
        "ingredient_ids":
            [],
    }

    safety_request.user = (
        request.user
    )

    response = (
        _medication_safety_check(
            safety_request,
            spec,
            {},
        )
    )

    body = (
        response.data
        if hasattr(
            response,
            "data",
        )
        else {}
    )

    cards = (
        _batchc_cds_cards_from_alerts(
            body.get(
                "alerts",
                [],
            )
        )
    )

    return Response({
        "cards":
            cards,
    }, status=200)


def _batchc_cds_002(
    request,
    spec,
    kwargs,
):
    return _batchc_cds_medication(
        request,
        spec,
        kwargs,
        "order-select",
    )


def _batchc_cds_003(
    request,
    spec,
    kwargs,
):
    return _batchc_cds_medication(
        request,
        spec,
        kwargs,
        "order-sign",
    )


def _batchc_cds_004(
    request,
    spec,
    kwargs,
):
    context = (
        _batchc_cds_validate_hook(
            request,
            "patient-view",
        )
    )

    patient = (
        _batchc_cds_patient(
            context
        )
    )

    encounter_id = (
        _batchc_cds_uuid(
            context.get(
                "encounterId"
            )
        )
    )

    if encounter_id is None:
        raise ContractError({
            "code":
                "CDS_ENCOUNTER_REQUIRED",

            "detail":
                "context.encounterId is required.",
        })

    encounter_model = apps.get_model(
        "clinical_records",
        "Encounter",
    )

    encounter = (
        encounter_model.objects
        .filter(
            pk=encounter_id,
            patient_id=patient.pk,
        )
        .first()
    )

    if encounter is None:
        raise NotFound({
            "code":
                "ENCOUNTER_NOT_FOUND",

            "detail":
                "Encounter was not found.",
        })

    # 현재 Final/Amended 판독 존재 여부
    report_model = apps.get_model(
        "radiology",
        "RadiologyReport",
    )

    report_qs = (
        report_model.objects
        .filter(
            status__in=[
                "FINAL",
                "AMENDED",
            ]
        )
    )

    report_fields = (
        _field_map(
            report_model
        )
    )

    if "is_current" in report_fields:
        report_qs = (
            report_qs.filter(
                is_current=True
            )
        )

    cards = []

    current_report = (
        report_qs
        .order_by("-created_at")
        .first()
    )

    if current_report is not None:
        cards.append({
            "summary":
                "Current radiology report available",

            "indicator":
                "info",

            "source": {
                "label":
                    "BrainOn Stroke CDSS"
            },

            "detail":
                (
                    getattr(
                        current_report,
                        "impression",
                        None,
                    )
                    or ""
                ),
        })

    # IntegrationTransaction 저장
    try:
        tx_model = apps.get_model(
            "integrations",
            "IntegrationTransaction",
        )

        tx_fields = _field_map(
            tx_model
        )

        tx_data = {}

        candidates = {
            "direction":
                "INBOUND",

            "interface_type":
                "CDS_HOOK",

            "status":
                "COMPLETED",

            "request_payload":
                _safe_value(
                    request.data
                ),

            "response_payload":
                {
                    "cards":
                        cards
                },

            "created_at":
                timezone.now(),

            "updated_at":
                timezone.now(),

            "completed_at":
                timezone.now(),
        }

        for name, value in (
            candidates.items()
        ):
            if name in tx_fields:
                tx_data[name] = value

        # required fields 중 안전한 값만 보완
        for field in (
            tx_model._meta.fields
        ):
            if field.primary_key:
                continue

            if (
                field.name in tx_data
                or field.attname in tx_data
                or field.null
                or field.has_default()
                or getattr(
                    field,
                    "auto_now",
                    False,
                )
                or getattr(
                    field,
                    "auto_now_add",
                    False,
                )
            ):
                continue

            if isinstance(
                field,
                models.JSONField,
            ):
                tx_data[
                    field.name
                ] = {}

            elif isinstance(
                field,
                (
                    models.CharField,
                    models.TextField,
                ),
            ):
                tx_data[
                    field.name
                ] = (
                    "CDS_HOOK"
                )

            elif isinstance(
                field,
                models.DateTimeField,
            ):
                tx_data[
                    field.name
                ] = (
                    timezone.now()
                )

        tx_model.objects.create(
            **tx_data
        )

    except LookupError:
        pass

    return Response({
        "cards":
            cards,
    }, status=200)


# ============================================================
# Register
# ============================================================

CUSTOM_HANDLERS.update({
    "API-CDS-002":
        _batchc_cds_002,

    "API-CDS-003":
        _batchc_cds_003,

    "API-CDS-004":
        _batchc_cds_004,

    "API-RAD-002":
        _batchc_rad_create,

    "API-RAD-004":
        _batchc_rad_update,

    "API-RAD-005":
        _batchc_rad_preliminary,

    "API-RAD-006":
        _batchc_rad_finalize,

    "API-RAD-007":
        _batchc_rad_amend,

    "API-RAD-009":
        _batchc_rad_measurement_create,

    "API-RAD-011":
        _batchc_rad_cancel,
})


# === BATCH_C_CDS_RAD_FINAL_END ===

# BEGIN BRAINON MEDM DB CONTRACT OVERRIDE
#
# Medication Master API source of truth:
#   Django Medication / MedicationIngredient / DrugIngredient DB models.
#
# Frontend contract follows this Backend response shape.
#

from django.db.models import Q as _medm_Q
from rest_framework.response import Response as _medm_Response

from apps.medications.models import (
    Medication as _MEDMMedication,
)

from apps.medication_safety.models import (
    MedicationIngredient as _MEDMMedicationIngredient,
)


_execute_contract_before_medm_db_contract = execute_contract


def _medm_error(
    code,
    detail,
    status_code=400,
):
    return _medm_Response(
        {
            "code": code,
            "detail": detail,
        },
        status=status_code,
    )


def _medm_bool(
    value,
    *,
    default=True,
):
    if value is None:
        return default

    value = str(value).strip().lower()

    if value in (
        "true",
        "1",
        "yes",
    ):
        return True

    if value in (
        "false",
        "0",
        "no",
    ):
        return False

    raise ValueError(
        "is_active must be true or false."
    )


def _medm_positive_int(
    value,
    *,
    default,
    maximum=None,
):
    if value in (
        None,
        "",
    ):
        return default

    try:
        result = int(value)
    except (
        TypeError,
        ValueError,
    ):
        raise ValueError(
            "must be an integer."
        )

    if result < 1:
        raise ValueError(
            "must be >= 1."
        )

    if (
        maximum is not None
        and result > maximum
    ):
        raise ValueError(
            f"must be <= {maximum}."
        )

    return result


def _medm_datetime(
    value,
):
    if value is None:
        return None

    return value.isoformat()


def _medm_medication_payload(
    medication,
):
    return {
        "id": str(medication.id),
        "medication_code": (
            medication.medication_code
        ),
        "medication_name": (
            medication.medication_name
        ),
        "dosage_form": (
            medication.dosage_form
        ),
        "strength": (
            medication.strength
        ),
        "manufacturer": (
            medication.manufacturer
        ),
        "is_active": (
            medication.is_active
        ),
        "created_at": _medm_datetime(
            medication.created_at
        ),
        "updated_at": _medm_datetime(
            medication.updated_at
        ),
    }


def _medm_page_url(
    request,
    page_number,
):
    query = request.GET.copy()

    query["page"] = str(
        page_number
    )

    query_string = query.urlencode()

    if query_string:
        relative = (
            f"{request.path}"
            f"?{query_string}"
        )
    else:
        relative = request.path

    return request.build_absolute_uri(
        relative
    )


def _medm_list(
    request,
):
    search = str(
        request.query_params.get(
            "search",
            ""
        )
        or ""
    ).strip()

    dosage_form = str(
        request.query_params.get(
            "dosage_form",
            ""
        )
        or ""
    ).strip()

    if len(search) > 200:
        return _medm_error(
            "INVALID_QUERY",
            "search must be <= 200 characters.",
        )

    if len(dosage_form) > 50:
        return _medm_error(
            "INVALID_QUERY",
            "dosage_form must be <= 50 characters.",
        )

    try:
        is_active = _medm_bool(
            request.query_params.get(
                "is_active"
            ),
            default=True,
        )

        page = _medm_positive_int(
            request.query_params.get(
                "page"
            ),
            default=1,
        )

        page_size = (
            _medm_positive_int(
                request.query_params.get(
                    "page_size"
                ),
                default=20,
                maximum=100,
            )
        )

    except ValueError as exc:
        return _medm_error(
            "INVALID_QUERY",
            str(exc),
        )

    queryset = (
        _MEDMMedication.objects
        .filter(
            is_active=is_active
        )
    )

    if search:
        queryset = queryset.filter(
            _medm_Q(
                medication_code__icontains=
                    search
            )
            |
            _medm_Q(
                medication_name__icontains=
                    search
            )
        )

    if dosage_form:
        queryset = queryset.filter(
            dosage_form__iexact=
                dosage_form
        )

    queryset = queryset.order_by(
        "medication_name",
        "medication_code",
        "id",
    )

    count = queryset.count()

    start = (
        (page - 1)
        * page_size
    )

    end = (
        start
        + page_size
    )

    rows = list(
        queryset[
            start:end
        ]
    )

    has_previous = (
        page > 1
    )

    has_next = (
        end < count
    )

    return _medm_Response(
        {
            "count": count,
            "next": (
                _medm_page_url(
                    request,
                    page + 1,
                )
                if has_next
                else None
            ),
            "previous": (
                _medm_page_url(
                    request,
                    page - 1,
                )
                if has_previous
                else None
            ),
            "results": [
                _medm_medication_payload(
                    medication
                )
                for medication
                in rows
            ],
        },
        status=200,
    )


def _medm_detail(
    request,
    **kwargs,
):
    medication_id = (
        kwargs.get(
            "medication_id"
        )
        or kwargs.get(
            "id"
        )
    )

    medication = (
        _MEDMMedication.objects
        .filter(
            id=medication_id
        )
        .first()
    )

    if medication is None:
        return _medm_error(
            "MEDICATION_NOT_FOUND",
            "Medication was not found.",
            404,
        )

    payload = (
        _medm_medication_payload(
            medication
        )
    )

    mappings = (
        _MEDMMedicationIngredient.objects
        .filter(
            medication=medication
        )
        .select_related(
            "ingredient"
        )
        .order_by(
            "created_at",
            "id",
        )
    )

    payload["ingredients"] = [
        {
            "id": str(
                mapping.id
            ),
            "ingredient_id": str(
                mapping.ingredient_id
            ),
            "dur_ingredient_code": (
                mapping.ingredient
                .dur_ingredient_code
            ),
            "name_ko": (
                mapping.ingredient
                .name_ko
            ),
            "name_en": (
                mapping.ingredient
                .name_en
            ),
            "amount": (
                str(mapping.amount)
                if mapping.amount
                is not None
                else None
            ),
            "unit": (
                mapping.unit
            ),
            "is_active": (
                mapping.is_active
            ),
            "created_at": (
                _medm_datetime(
                    mapping.created_at
                )
            ),
        }
        for mapping in mappings
    ]

    return _medm_Response(
        payload,
        status=200,
    )


def execute_contract(
    request,
    spec,
    **kwargs,
):
    api_id = spec.get(
        "api_id"
    )

    if api_id not in {
        "API-MEDM-001",
        "API-MEDM-002",
    }:
        return (
            _execute_contract_before_medm_db_contract(
                request,
                spec,
                **kwargs,
            )
        )

    # 기존 execute_contract를 먼저 호출하여
    # 프로젝트 공통 인증/권한 정책을 그대로 통과시킨다.
    gate_response = (
        _execute_contract_before_medm_db_contract(
            request,
            spec,
            **kwargs,
        )
    )

    if (
        getattr(
            gate_response,
            "status_code",
            500,
        )
        != 200
    ):
        return gate_response

    if api_id == "API-MEDM-001":
        return _medm_list(
            request
        )

    return _medm_detail(
        request,
        **kwargs,
    )


# END BRAINON MEDM DB CONTRACT OVERRIDE

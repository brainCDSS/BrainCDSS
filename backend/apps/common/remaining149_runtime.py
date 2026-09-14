
from __future__ import annotations

import re
import uuid
from contextlib import nullcontext
from datetime import date, datetime, timedelta

from django.apps import apps
from django.conf import settings
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from django.db.models import Q
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
    if not raw or raw in {"-", "X"}:
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

    for key, value in _write_data(model, request).items():
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


@transaction.atomic
def _appointment_create(request, spec, kwargs):
    del kwargs
    model = _model(spec)
    if model is None:
        raise ContractError({"code": "APPOINTMENT_MODEL_NOT_CONFIGURED"})
    if not isinstance(request.data, dict) or not request.data.get("slot_id"):
        raise ContractError({
            "code": "VALIDATION_ERROR",
            "slot_id": "This field is required.",
        })

    patient = _patient_for_user(request.user)
    if patient is None:
        raise ContractError({"code": "PATIENT_PROFILE_REQUIRED"})

    slot_model = apps.get_model("appointments", "AppointmentSlot")
    try:
        slot = (
            slot_model.objects.select_for_update()
            .select_related("clinician__department__hospital")
            .get(pk=request.data["slot_id"])
        )
    except (slot_model.DoesNotExist, DjangoValidationError, ValueError, TypeError) as exc:
        raise NotFound({"code": "SLOT_NOT_FOUND"}) from exc

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
    reason = _appointment_action_reason(request, "memo", "reason")
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
    prefs = pref_model.objects.filter(user=request.user).order_by("category")

    return Response({
        "dnd": serialize_instance(setting) if setting else {
            "dnd_enabled": False,
            "dnd_start": None,
            "dnd_end": None,
            "timezone": "Asia/Seoul",
        },
        "categories": [serialize_instance(x) for x in prefs],
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
            required = str(category).upper() == "CRITICAL"
            pref_model.objects.update_or_create(
                user=request.user,
                category=category,
                defaults={"enabled": True if required else bool(enabled)},
            )

    return _notification_preferences_get(request, spec, kwargs)


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


CUSTOM_HANDLERS = {
    "API-ALLERGY-003": _batchb_allergy_deactivate,
    "API-RX-002": _batchb_rx_detail,
    "API-RX-003": _batchb_rx_patch,
    "API-RX-004": _batchb_rx_finalize,
    "API-SCH-002": _schedule_put,
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
    "API-FCM-001": _fcm_create,
    "API-MEDSAFE-001": _medication_safety_check,
    "API-CDS-001": _cds_discovery,
    "API-NOTE-001": _clinical_note_create,
    "API-NOTE-004": _clinical_note_update,
    "API-NOTE-005": _clinical_note_finalize,
}


def execute_contract(request, spec, **kwargs):
    check_access(request, spec)

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

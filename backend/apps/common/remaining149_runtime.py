
from __future__ import annotations

import re
import uuid
from contextlib import nullcontext
from datetime import date, datetime

from django.apps import apps
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework.exceptions import AuthenticationFailed, NotFound, PermissionDenied, ValidationError
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
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, dict):
        return {str(k): _safe_value(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_safe_value(v) for v in value]
    return value


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


def _appointment_create(request, spec, kwargs):
    model = _model(spec)
    if model is None:
        return _generic_create(request, spec, kwargs)

    fields = _field_map(model)
    data = _write_data(model, request)
    data = _apply_server_defaults(model, data)

    if _role_code(request.user) == "PATIENT" and "patient" in fields:
        patient = _patient_for_user(request.user)
        if patient is None:
            raise ContractError({"code": "PATIENT_PROFILE_REQUIRED"})
        data[fields["patient"].attname] = patient.id

    if "status" in fields and "status" not in data:
        data["status"] = "REQUESTED"
    if "request_type" in fields and "request_type" not in data:
        data["request_type"] = "NEW"

    try:
        obj = model.objects.create(**data)
    except Exception as exc:
        raise ContractError({"code": "VALIDATION_ERROR", "detail": str(exc)}) from exc

    after = serialize_instance(obj)
    _audit(request, spec, obj, None, after)
    _outbox(spec, obj, after)
    return Response(after, status=201)


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


CUSTOM_HANDLERS = {
    "API-SCH-002": _schedule_put,
    "API-APP-001": _appointment_create,
    "API-NOTI-003": _notification_preferences_get,
    "API-NOTI-004": _notification_preferences_patch,
    "API-FCM-001": _fcm_create,
    "API-MEDSAFE-001": _medication_safety_check,
    "API-CDS-001": _cds_discovery,
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

from __future__ import annotations

import hashlib
import json
import uuid
from collections import OrderedDict
from typing import Any

from django.apps import apps
from django.core.serializers.json import DjangoJSONEncoder
from django.db import connection, models, transaction
from django.utils import timezone

from apps.audit.models import AuditLog
from apps.common.services.outbox import (
    create_outbox_event,
    enqueue_outbox_event_on_commit,
)
from apps.medication_safety.models import PatientAllergy
from apps.patients.models import (
    FavoriteHospital,
    Patient,
    PatientMergeHistory,
)


FORMAL_PATIENT_NO_PREFIX = "P"
TEMP_PATIENT_NO_PREFIX = "TMP"

PATIENT_STATUS_ACTIVE = "ACTIVE"
PATIENT_STATUS_TEMP = "TEMP"
PATIENT_STATUS_MERGED = "MERGED"

PREGNANCY_STATUS_UNKNOWN = "UNKNOWN"

# Immutable/lineage relations must not be rewritten by a merge.
# New patient FK tables are migrated automatically unless intentionally
# added here.
PATIENT_MERGE_RELATION_EXCLUDES = {
    ("patients.Patient", "merged_into_patient"),
    ("patients.PatientMergeHistory", "source_patient"),
    ("patients.PatientMergeHistory", "target_patient"),
}


class PatientServiceError(Exception):
    def __init__(
        self,
        *,
        code: str,
        detail: str,
        status_code: int,
    ):
        self.code = code
        self.detail = detail
        self.status_code = status_code
        super().__init__(detail)


def normalize_patient_name(value: str) -> str:
    return " ".join(value.split())


def _identity_lock_key(
    *,
    name: str,
    birth_date,
) -> int:
    identity = (
        f"{normalize_patient_name(name).casefold()}"
        f"|{birth_date.isoformat()}"
    )

    raw = hashlib.sha256(
        identity.encode("utf-8")
    ).digest()[:8]

    return int.from_bytes(
        raw,
        byteorder="big",
        signed=True,
    )


def lock_identity_candidate(
    *,
    name: str,
    birth_date,
) -> None:
    """
    PostgreSQL transaction-scoped advisory lock.

    This closes the race between duplicate-candidate check and insert
    without changing the current 66-table DB contract.
    """
    key = _identity_lock_key(
        name=name,
        birth_date=birth_date,
    )

    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT pg_advisory_xact_lock(%s)",
            [key],
        )


def find_active_duplicate_candidate(
    *,
    name: str,
    birth_date,
    exclude_patient_id=None,
    for_update: bool = False,
):
    qs = Patient.objects.filter(
        status=PATIENT_STATUS_ACTIVE,
        name__iexact=normalize_patient_name(name),
        birth_date=birth_date,
    )

    if exclude_patient_id is not None:
        qs = qs.exclude(id=exclude_patient_id)

    if for_update:
        qs = qs.select_for_update()

    return qs.order_by("created_at", "id").first()


def _patient_no_year_lock_key(year: int) -> int:
    raw = hashlib.sha256(
        f"brainon:patient_no:{year}".encode("utf-8")
    ).digest()[:8]

    return int.from_bytes(
        raw,
        byteorder="big",
        signed=True,
    )


def _next_formal_patient_no() -> str:
    """
    Formal BrainOn patient number policy.

    Format:
        P + YYYY + yearly sequence(minimum 5 digits)

    Example:
        P202600001

    PostgreSQL advisory_xact_lock serializes number allocation per year,
    so multiple Cloud Run instances can create patients concurrently
    without adding a sequence table to the current DB contract.
    """
    year = timezone.localdate().year

    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT pg_advisory_xact_lock(%s)",
            [_patient_no_year_lock_key(year)],
        )

    prefix = f"{FORMAL_PATIENT_NO_PREFIX}{year}"

    max_sequence = 0

    for value in Patient.objects.filter(
        patient_no__startswith=prefix
    ).values_list("patient_no", flat=True):
        suffix = value[len(prefix):]

        if suffix.isdigit():
            max_sequence = max(
                max_sequence,
                int(suffix),
            )

    next_sequence = max_sequence + 1
    candidate = f"{prefix}{next_sequence:05d}"

    if len(candidate) > 30:
        raise RuntimeError(
            "Generated formal patient_no exceeds "
            "DB max_length=30."
        )

    if Patient.objects.filter(
        patient_no=candidate
    ).exists():
        raise RuntimeError(
            "Formal patient_no collision after advisory lock."
        )

    return candidate


def _next_temporary_patient_no() -> str:
    date_part = timezone.localdate().strftime("%Y%m%d")

    for _ in range(10):
        random_part = uuid.uuid4().hex[:12].upper()
        value = (
            f"{TEMP_PATIENT_NO_PREFIX}-"
            f"{date_part}-{random_part}"
        )

        if len(value) > 30:
            raise RuntimeError(
                "Generated temporary patient_no exceeds "
                "DB max_length=30."
            )

        if not Patient.objects.filter(
            patient_no=value
        ).exists():
            return value

    raise RuntimeError(
        "Could not generate a unique temporary patient_no."
    )


def generate_patient_no(*, temporary: bool) -> str:
    if temporary:
        return _next_temporary_patient_no()

    return _next_formal_patient_no()
def generate_temporary_name() -> str:
    return f"UNKNOWN-{uuid.uuid4().hex[:8].upper()}"


def _jsonable(value: Any):
    return json.loads(
        json.dumps(
            value,
            cls=DjangoJSONEncoder,
        )
    )


def _request_id(request):
    candidates = [
        getattr(request, "request_id", None),
        request.headers.get("X-Request-ID")
        if request is not None
        else None,
    ]

    for value in candidates:
        if not value:
            continue

        try:
            return uuid.UUID(str(value))
        except (TypeError, ValueError):
            continue

    return None


def _request_ip(request):
    if request is None:
        return None

    forwarded = request.META.get(
        "HTTP_X_FORWARDED_FOR"
    )

    if forwarded:
        return forwarded.split(",")[0].strip()

    return request.META.get("REMOTE_ADDR")


def create_audit_log(
    *,
    request,
    actor,
    action: str,
    patient_id=None,
    resource_id=None,
    before=None,
    after=None,
    reason: str | None = None,
):
    role = getattr(actor, "role", None)

    return AuditLog.objects.create(
        actor_user=actor,
        actor_login=getattr(
            actor,
            "login_id",
            None,
        ),
        actor_role_code=getattr(
            role,
            "code",
            None,
        ),
        source_service="backend",
        action=action,
        resource_type="Patient",
        resource=(
            str(resource_id)
            if resource_id is not None
            else (
                str(patient_id)
                if patient_id is not None
                else None
            )
        ),
        patient=patient_id,
        outcome="SUCCESS",
        reason=reason,
        before_json=(
            _jsonable(before)
            if before is not None
            else None
        ),
        after_json=(
            _jsonable(after)
            if after is not None
            else None
        ),
        request_ip=_request_ip(request),
        user_agent=(
            request.META.get(
                "HTTP_USER_AGENT"
            )
            if request is not None
            else None
        ),
        request=_request_id(request),
        occurred_at=timezone.now(),
    )


def patient_snapshot(patient: Patient) -> dict[str, Any]:
    return {
        "id": str(patient.id),
        "patient_no": patient.patient_no,
        "name": patient.name,
        "birth_date": patient.birth_date,
        "estimated_age": patient.estimated_age,
        "sex": patient.sex,
        "phone": patient.phone,
        "emergency_contact": patient.emergency_contact,
        "status": patient.status,
        "pregnancy_status": patient.pregnancy_status,
        "pregnancy_status_updated_at": (
            patient.pregnancy_status_updated_at
        ),
        "merged_into_patient_id": (
            str(patient.merged_into_patient_id)
            if patient.merged_into_patient_id
            else None
        ),
        "merged_at": patient.merged_at,
    }


@transaction.atomic
def create_patient(
    *,
    actor,
    request,
    name: str,
    birth_date,
    sex: str,
    phone=None,
    emergency_contact=None,
) -> Patient:
    normalized_name = normalize_patient_name(name)

    lock_identity_candidate(
        name=normalized_name,
        birth_date=birth_date,
    )

    duplicate = find_active_duplicate_candidate(
        name=normalized_name,
        birth_date=birth_date,
        for_update=True,
    )

    if duplicate is not None:
        raise PatientServiceError(
            code="PATIENT_DUPLICATE",
            detail=(
                "An ACTIVE patient with the same normalized "
                f"name and birth_date already exists: "
                f"{duplicate.patient_no}"
            ),
            status_code=409,
        )

    now = timezone.now()

    patient = Patient.objects.create(
        patient_no=generate_patient_no(
            temporary=False
        ),
        name=normalized_name,
        birth_date=birth_date,
        estimated_age=None,
        sex=sex,
        phone=phone,
        emergency_contact=emergency_contact,
        status=PATIENT_STATUS_ACTIVE,
        merged_into_patient=None,
        merged_at=None,
        merged_by=None,
        created_by=actor,
        created_at=now,
        updated_at=now,
        pregnancy_status=PREGNANCY_STATUS_UNKNOWN,
        pregnancy_status_updated_at=None,
    )

    create_audit_log(
        request=request,
        actor=actor,
        action="CREATE_PATIENT",
        patient_id=patient.id,
        after=patient_snapshot(patient),
    )

    return patient


@transaction.atomic
def create_temporary_patient(
    *,
    actor,
    request,
    sex=None,
    estimated_age=None,
) -> Patient:
    now = timezone.now()

    patient = Patient.objects.create(
        patient_no=generate_patient_no(
            temporary=True
        ),
        name=generate_temporary_name(),
        birth_date=None,
        estimated_age=estimated_age,
        sex=sex,
        phone=None,
        emergency_contact=None,
        status=PATIENT_STATUS_TEMP,
        merged_into_patient=None,
        merged_at=None,
        merged_by=None,
        created_by=actor,
        created_at=now,
        updated_at=now,
        pregnancy_status=PREGNANCY_STATUS_UNKNOWN,
        pregnancy_status_updated_at=None,
    )

    create_audit_log(
        request=request,
        actor=actor,
        action="CREATE_TEMP_PATIENT",
        patient_id=patient.id,
        after=patient_snapshot(patient),
    )

    return patient


@transaction.atomic
def update_patient(
    *,
    patient_id,
    actor,
    request,
    changes: dict[str, Any],
) -> Patient:
    patient = (
        Patient.objects.select_for_update()
        .filter(id=patient_id)
        .first()
    )

    if (
        patient is None
        or patient.status
        not in {
            PATIENT_STATUS_ACTIVE,
            PATIENT_STATUS_TEMP,
        }
    ):
        raise PatientServiceError(
            code="PATIENT_NOT_FOUND",
            detail=(
                "ACTIVE/TEMP patient was not found."
            ),
            status_code=404,
        )

    before = patient_snapshot(patient)
    now = timezone.now()

    if "phone" in changes:
        patient.phone = changes["phone"]

    if "emergency_contact" in changes:
        patient.emergency_contact = (
            changes["emergency_contact"]
        )

    if "pregnancy_status" in changes:
        new_status = changes[
            "pregnancy_status"
        ]

        if new_status != patient.pregnancy_status:
            patient.pregnancy_status = new_status
            patient.pregnancy_status_updated_at = now

    patient.updated_at = now

    patient.save(
        update_fields=[
            "phone",
            "emergency_contact",
            "pregnancy_status",
            "pregnancy_status_updated_at",
            "updated_at",
        ]
    )

    create_audit_log(
        request=request,
        actor=actor,
        action="UPDATE_PATIENT",
        patient_id=patient.id,
        before=before,
        after=patient_snapshot(patient),
    )

    return patient


def _patient_relation_fields():
    relations = []
    patient_model = Patient

    for model in apps.get_models():
        for field in model._meta.fields:
            remote = getattr(
                field,
                "remote_field",
                None,
            )

            if (
                remote is None
                or getattr(
                    remote,
                    "model",
                    None,
                )
                is not patient_model
            ):
                continue

            label = (
                f"{model._meta.app_label}."
                f"{model.__name__}"
            )

            if (
                label,
                field.name,
            ) in PATIENT_MERGE_RELATION_EXCLUDES:
                continue

            relations.append(
                (model, field)
            )

    relations.sort(
        key=lambda item: (
            item[0]._meta.app_label,
            item[0]._meta.db_table,
            item[1].name,
        )
    )

    return relations


def _value_for_field(instance, field_name):
    field = instance._meta.get_field(
        field_name
    )
    return getattr(
        instance,
        field.attname,
    )


def _check_unique_constraint_conflicts(
    *,
    model,
    patient_field,
    source,
    target,
) -> list[str]:
    conflicts = []

    source_qs = model.objects.filter(
        **{
            patient_field.attname: source.pk
        }
    )

    if not source_qs.exists():
        return conflicts

    if patient_field.unique:
        if model.objects.filter(
            **{
                patient_field.attname:
                target.pk
            }
        ).exists():
            conflicts.append(
                f"{model._meta.db_table}."
                f"{patient_field.name}:"
                " unique relation conflict"
            )

    groups = []

    for constraint in model._meta.constraints:
        if (
            isinstance(
                constraint,
                models.UniqueConstraint,
            )
            and constraint.fields
            and patient_field.name
            in constraint.fields
        ):
            groups.append(
                tuple(constraint.fields)
            )

    for unique_group in (
        model._meta.unique_together or ()
    ):
        if (
            patient_field.name
            in unique_group
        ):
            groups.append(
                tuple(unique_group)
            )

    seen_groups = set()

    for fields in groups:
        if fields in seen_groups:
            continue

        seen_groups.add(fields)

        other_fields = [
            value
            for value in fields
            if value != patient_field.name
        ]

        for row in source_qs:
            filters = {
                patient_field.attname:
                target.pk
            }

            for field_name in other_fields:
                related_field = (
                    model._meta.get_field(
                        field_name
                    )
                )

                filters[
                    related_field.attname
                ] = getattr(
                    row,
                    related_field.attname,
                )

            if model.objects.filter(
                **filters
            ).exists():
                conflicts.append(
                    f"{model._meta.db_table}: "
                    f"unique{fields} conflict"
                )
                break

    return conflicts


def _preflight_merge_conflicts(
    *,
    source: Patient,
    target: Patient,
):
    conflicts = []

    for model, field in _patient_relation_fields():
        conflicts.extend(
            _check_unique_constraint_conflicts(
                model=model,
                patient_field=field,
                source=source,
                target=target,
            )
        )

    if conflicts:
        raise PatientServiceError(
            code="PATIENT_MERGE_CONFLICT",
            detail="; ".join(conflicts),
            status_code=409,
        )


def _migrate_patient_relations(
    *,
    source: Patient,
    target: Patient,
) -> dict[str, int]:
    summary: OrderedDict[str, int] = OrderedDict()

    for model, field in _patient_relation_fields():
        key = (
            f"{model._meta.db_table}."
            f"{field.name}"
        )

        count = model.objects.filter(
            **{
                field.attname:
                source.pk
            }
        ).update(
            **{
                field.attname:
                target.pk
            }
        )

        if count:
            summary[key] = count

    return dict(summary)


def rebuild_allergy_info(
    *,
    patient: Patient,
) -> str | None:
    allergies = list(
        PatientAllergy.objects.filter(
            patient=patient,
            status="ACTIVE",
        ).order_by(
            "substance",
            "ingredient_id",
            "created_at",
            "id",
        )
    )

    parts = []

    for allergy in allergies:
        label = (
            allergy.substance.strip()
            if allergy.substance
            else None
        )

        if not label and allergy.ingredient_id:
            label = (
                f"ingredient:{allergy.ingredient_id}"
            )

        if not label:
            label = "unspecified-allergen"

        metadata = []

        if allergy.reaction:
            metadata.append(
                f"reaction={allergy.reaction}"
            )

        if allergy.severity:
            metadata.append(
                f"severity={allergy.severity}"
            )

        if metadata:
            parts.append(
                f"{label} [{', '.join(metadata)}]"
            )
        else:
            parts.append(label)

    summary = (
        "; ".join(parts)
        if parts
        else None
    )

    Patient.objects.filter(
        id=patient.id
    ).update(
        allergy_info=summary,
        updated_at=timezone.now(),
    )

    patient.allergy_info = summary
    return summary


@transaction.atomic
def merge_temporary_patient(
    *,
    source_patient_id,
    target_patient_id,
    actor,
    request,
) -> dict[str, Any]:
    source = (
        Patient.objects.select_for_update()
        .filter(id=source_patient_id)
        .first()
    )
    target = (
        Patient.objects.select_for_update()
        .filter(id=target_patient_id)
        .first()
    )

    if source is None or target is None:
        raise PatientServiceError(
            code="PATIENT_NOT_FOUND",
            detail="Source or target patient was not found.",
            status_code=404,
        )

    if source.id == target.id:
        raise PatientServiceError(
            code="VALIDATION_ERROR",
            detail="source and target patient must differ.",
            status_code=400,
        )

    if source.status != PATIENT_STATUS_TEMP:
        raise PatientServiceError(
            code="PATIENT_MERGE_CONFLICT",
            detail="Source patient must be TEMP.",
            status_code=409,
        )

    if target.status != PATIENT_STATUS_ACTIVE:
        raise PatientServiceError(
            code="PATIENT_MERGE_CONFLICT",
            detail="Target patient must be ACTIVE.",
            status_code=409,
        )

    _preflight_merge_conflicts(
        source=source,
        target=target,
    )

    before_source = patient_snapshot(source)
    before_target = patient_snapshot(target)

    migrated_summary = (
        _migrate_patient_relations(
            source=source,
            target=target,
        )
    )

    merged_at = timezone.now()

    merge_history = (
        PatientMergeHistory.objects.create(
            source_patient=source,
            target_patient=target,
            merged_by=actor,
            reason=(
                "Temporary patient merged into "
                "confirmed ACTIVE patient."
            ),
            merged_at=merged_at,
        )
    )

    source.status = PATIENT_STATUS_MERGED
    source.merged_into_patient = target
    source.merged_by = actor
    source.merged_at = merged_at
    source.updated_at = merged_at
    source.save(
        update_fields=[
            "status",
            "merged_into_patient",
            "merged_by",
            "merged_at",
            "updated_at",
        ]
    )

    allergy_info = rebuild_allergy_info(
        patient=target
    )

    target.refresh_from_db()

    audit_after = {
        "source": patient_snapshot(source),
        "target": patient_snapshot(target),
        "merge_history_id": str(
            merge_history.id
        ),
        "migrated_fk_summary": migrated_summary,
        "target_allergy_info": allergy_info,
    }

    create_audit_log(
        request=request,
        actor=actor,
        action="MERGE_PATIENT",
        patient_id=target.id,
        resource_id=source.id,
        before={
            "source": before_source,
            "target": before_target,
        },
        after=audit_after,
    )

    outbox = create_outbox_event(
        event_type="patient.merged.v1",
        aggregate_type="Patient",
        aggregate_id=str(target.id),
        payload=_jsonable({
            "merge_history_id": str(
                merge_history.id
            ),
            "source_patient_id": str(
                source.id
            ),
            "source_patient_no":
                source.patient_no,
            "target_patient_id": str(
                target.id
            ),
            "target_patient_no":
                target.patient_no,
            "migrated_fk_summary":
                migrated_summary,
            "merged_by_id": str(actor.id),
            "merged_at":
                merged_at.isoformat(),
        }),
    )

    enqueue_outbox_event_on_commit(
        str(outbox.id)
    )

    return {
        "merge_history_id": str(
            merge_history.id
        ),
        "source_patient": {
            "id": str(source.id),
            "patient_no": source.patient_no,
            "status": source.status,
            "merged_into_patient_id": str(
                target.id
            ),
        },
        "target_patient": {
            "id": str(target.id),
            "patient_no": target.patient_no,
            "status": target.status,
        },
        "migrated_fk_summary":
            migrated_summary,
        "merged_by": {
            "id": str(actor.id),
            "name": actor.name,
        },
        "merged_at": merged_at,
        "outbox_event_id": str(outbox.id),
    }


@transaction.atomic
def identify_temporary_patient(
    *,
    patient_id,
    actor,
    request,
    name: str,
    birth_date,
    sex: str,
    phone=None,
    emergency_contact=None,
) -> Patient:
    patient = (
        Patient.objects.select_for_update()
        .filter(id=patient_id)
        .first()
    )

    if patient is None:
        raise PatientServiceError(
            code="PATIENT_NOT_FOUND",
            detail="Patient was not found.",
            status_code=404,
        )

    if patient.status != PATIENT_STATUS_TEMP:
        raise PatientServiceError(
            code="VALIDATION_ERROR",
            detail="Only TEMP patient can be identified.",
            status_code=400,
        )

    normalized_name = normalize_patient_name(
        name
    )

    lock_identity_candidate(
        name=normalized_name,
        birth_date=birth_date,
    )

    duplicate = find_active_duplicate_candidate(
        name=normalized_name,
        birth_date=birth_date,
        exclude_patient_id=patient.id,
        for_update=True,
    )

    if duplicate is not None:
        raise PatientServiceError(
            code="PATIENT_IDENTIFY_CONFLICT",
            detail=(
                "Existing ACTIVE duplicate candidate "
                f"{duplicate.patient_no} found. "
                "Use the merge API instead."
            ),
            status_code=409,
        )

    before = patient_snapshot(patient)
    now = timezone.now()

    patient.patient_no = generate_patient_no(
        temporary=False
    )
    patient.name = normalized_name
    patient.birth_date = birth_date
    patient.estimated_age = None
    patient.sex = sex
    patient.phone = phone
    patient.emergency_contact = (
        emergency_contact
    )
    patient.status = PATIENT_STATUS_ACTIVE
    patient.updated_at = now

    patient.save(
        update_fields=[
            "patient_no",
            "name",
            "birth_date",
            "estimated_age",
            "sex",
            "phone",
            "emergency_contact",
            "status",
            "updated_at",
        ]
    )

    create_audit_log(
        request=request,
        actor=actor,
        action="PATIENT_IDENTIFIED",
        patient_id=patient.id,
        before=before,
        after=patient_snapshot(patient),
    )

    return patient


@transaction.atomic
def add_favorite_hospital(
    *,
    patient: Patient,
    hospital,
):
    relation, created = (
        FavoriteHospital.objects.get_or_create(
            patient=patient,
            hospital=hospital,
            defaults={
                "created_at":
                    timezone.now(),
            },
        )
    )

    return relation, created


@transaction.atomic
def remove_favorite_hospital(
    *,
    patient: Patient,
    hospital,
) -> bool:
    deleted, _ = (
        FavoriteHospital.objects.filter(
            patient=patient,
            hospital=hospital,
        ).delete()
    )

    return bool(deleted)

from __future__ import annotations

import re
import uuid
from datetime import datetime, timedelta

from django.db import transaction
from django.utils import timezone

from apps.accounts.models import RolePermission
from apps.audit.services.audit_event import record_audit_event
from apps.common.models import OutboxEvent
from apps.common.outbox_tasks import publish_outbox_event
from apps.medications.models import MedicationSchedule
from apps.medication_safety.models import (
    MedicationSafetyOverride,
)
from apps.medication_safety.services.medication_safety import (
    MedicationSafetyError,
    check_medication_safety,
)
from apps.notifications.models import Notification
from apps.notifications.services.notifications import create_notification_for_user
from apps.prescriptions.models import (
    Prescription,
    PrescriptionItem,
)


BLOCKING_SEVERITIES = {
    "MAJOR",
    "BLOCK",
}


def _create_finalized_prescription_notification(*, prescription, patient):
    """Create one post-finalization inbox row for the prescription owner."""
    recipient_user = patient.user
    if recipient_user is None:
        return None

    dedupe_key = f"prescription-finalized:{prescription.id}"
    if Notification.objects.filter(
        recipient_user=recipient_user,
        category="PRESCRIPTION",
        data_json__dedupe_key=dedupe_key,
    ).exists():
        return None

    return create_notification_for_user(
        recipient_user=recipient_user,
        category="PRESCRIPTION",
        severity="INFO",
        title="새 처방이 등록되었어요",
        body="새로운 처방이 등록되었습니다. 복약 일정을 확인해 주세요.",
        data_json={
            "event_type": "PRESCRIPTION_FINALIZED",
            "prescription_id": str(prescription.id),
            "patient_id": str(patient.id),
            "encounter_id": str(prescription.encounter_id),
            "dedupe_key": dedupe_key,
        },
    )


class PrescriptionFinalizeError(Exception):
    def __init__(
        self,
        code,
        detail,
        status_code,
    ):
        self.code = code
        self.detail = detail
        self.status_code = status_code
        super().__init__(detail)


def _has_permission(
    user,
    permission_code,
):
    role_id = getattr(
        user,
        "role_id",
        None,
    )

    if not role_id:
        return False

    return (
        RolePermission.objects
        .filter(
            role_id=role_id,
            permission__code=permission_code,
        )
        .exists()
    )


def _validate_overrides(overrides):
    if overrides is None:
        return []

    if not isinstance(overrides, list):
        raise PrescriptionFinalizeError(
            "PRESCRIPTION_FINALIZE_INVALID",
            "overrides must be a list.",
            400,
        )

    validated = []
    seen = set()

    for index, item in enumerate(overrides):
        if not isinstance(item, dict):
            raise PrescriptionFinalizeError(
                "PRESCRIPTION_FINALIZE_INVALID",
                f"overrides[{index}] must be an object.",
                400,
            )

        alert_type = str(
            item.get("alert_type", "")
        ).strip().upper()

        if not alert_type:
            raise PrescriptionFinalizeError(
                "PRESCRIPTION_FINALIZE_INVALID",
                (
                    f"overrides[{index}].alert_type "
                    "is required."
                ),
                400,
            )

        try:
            rule_id = uuid.UUID(
                str(item.get("rule_id"))
            )
        except (
            ValueError,
            TypeError,
            AttributeError,
        ):
            raise PrescriptionFinalizeError(
                "PRESCRIPTION_FINALIZE_INVALID",
                (
                    f"overrides[{index}].rule_id "
                    "must be UUID."
                ),
                400,
            )

        reason = str(
            item.get("reason", "")
        ).strip()

        if len(reason) < 5:
            raise PrescriptionFinalizeError(
                "OVERRIDE_REASON_REQUIRED",
                (
                    "Override reason must contain "
                    "at least 5 characters."
                ),
                422,
            )

        key = (
            alert_type,
            str(rule_id),
        )

        if key in seen:
            raise PrescriptionFinalizeError(
                "PRESCRIPTION_OVERRIDE_DUPLICATE",
                (
                    "Duplicate override for "
                    f"{alert_type}/{rule_id}"
                ),
                400,
            )

        seen.add(key)

        validated.append(
            {
                "alert_type": alert_type,
                "rule_type": (
                    str(
                        item.get(
                            "rule_type",
                            alert_type,
                        )
                    ).strip()
                    or alert_type
                ),
                "rule_id": rule_id,
                "reason": reason,
            }
        )

    return validated


def _extract_times(timing):
    values = re.findall(
        r"(?<!\d)"
        r"([01]\d|2[0-3]):([0-5]\d)"
        r"(?!\d)",
        str(timing or ""),
    )

    result = []

    for hour, minute in values:
        value = (
            int(hour),
            int(minute),
        )

        if value not in result:
            result.append(value)

    return result


def _create_schedules(items):
    """
    timing에 명시적인 HH:MM이 있는 경우만
    MedicationSchedule을 생성한다.

    임상 투약 시간을 Backend에서 임의로 만들지 않는다.
    """

    created = 0
    tz = timezone.get_current_timezone()

    for item in items:
        times = _extract_times(
            item.timing
        )

        if not times:
            continue

        times = times[
            : item.frequency_per_day
        ]

        duration_days = max(
            int(item.duration_days),
            1,
        )

        for day_offset in range(
            duration_days
        ):
            day = (
                item.start_date
                + timedelta(
                    days=day_offset
                )
            )

            for hour, minute in times:
                naive = datetime(
                    day.year,
                    day.month,
                    day.day,
                    hour,
                    minute,
                )

                scheduled_at = (
                    timezone.make_aware(
                        naive,
                        tz,
                    )
                )

                MedicationSchedule.objects.create(
                    prescription_item=item,
                    scheduled_at=scheduled_at,
                    time_slot=(
                        f"{hour:02d}:{minute:02d}"
                    ),
                    dose=item.dose,
                    created_at=timezone.now(),
                )

                created += 1

    return created


def _send_outbox_after_commit(
    event_id,
):
    try:
        publish_outbox_event.delay(
            str(event_id)
        )
    except Exception:
        # DB Commit 이후 RabbitMQ 장애가 발생해도
        # Outbox row는 PENDING으로 남아 재시도 가능.
        pass


def finalize_prescription(
    *,
    prescription_id,
    actor_user,
    overrides=None,
    request=None,
):
    overrides = _validate_overrides(
        overrides
    )

    supplied = {
        (
            item["alert_type"],
            str(item["rule_id"]),
        ): item
        for item in overrides
    }

    with transaction.atomic():
        try:
            prescription = (
                Prescription.objects
                # `encounter__patient__user` is nullable and therefore
                # becomes an OUTER JOIN. PostgreSQL rejects FOR UPDATE when
                # it tries to lock that nullable join target. The
                # prescription row is the workflow aggregate and the only
                # row that must be locked for finalization.
                .select_for_update(of=("self",))
                .select_related(
                    "encounter",
                    "encounter__patient",
                    "encounter__patient__user",
                    "prescribed_by",
                )
                .get(
                    pk=prescription_id
                )
            )

        except Prescription.DoesNotExist:
            raise PrescriptionFinalizeError(
                "PRESCRIPTION_NOT_FOUND",
                "Prescription was not found.",
                404,
            )

        if (
            prescription.prescribed_by_id
            != actor_user.id
        ):
            raise PrescriptionFinalizeError(
                "PRESCRIPTION_FINALIZE_FORBIDDEN",
                (
                    "Only the prescribing doctor "
                    "may finalize this prescription."
                ),
                403,
            )

        if prescription.status != "DRAFT":
            raise PrescriptionFinalizeError(
                "PRESCRIPTION_INVALID_STATE",
                (
                    "Only DRAFT prescriptions "
                    "may be finalized."
                ),
                409,
            )

        items = list(
            PrescriptionItem.objects
            .filter(
                prescription=prescription
            )
            .select_related("medication")
            .order_by("created_at")
        )

        if not items:
            raise PrescriptionFinalizeError(
                "PRESCRIPTION_EMPTY",
                "Prescription has no items.",
                400,
            )

        patient = (
            prescription.encounter.patient
        )

        safety_input = [
            {
                "medication_id": (
                    item.medication_id
                ),
                "dose": item.dose,
                "unit": item.dose_unit,
                "frequency_per_day": (
                    item.frequency_per_day
                ),
                "duration_days": (
                    item.duration_days
                ),
                "route": item.route,
            }
            for item in items
        ]

        try:
            safety = check_medication_safety(
                medications=safety_input,
                patient=patient,
            )

        except MedicationSafetyError as exc:
            raise PrescriptionFinalizeError(
                "MEDICATION_SAFETY_UNAVAILABLE",
                (
                    f"{exc.code}: "
                    f"{exc.detail}"
                ),
                503,
            )

        blocking_alerts = [
            alert
            for alert in safety["alerts"]
            if alert.get("severity")
            in BLOCKING_SEVERITIES
        ]

        unresolved = []

        for alert in blocking_alerts:
            if not alert.get(
                "override_allowed",
                False,
            ):
                unresolved.append(alert)
                continue

            key = (
                str(
                    alert["alert_type"]
                ).upper(),
                str(
                    alert["rule_id"]
                ),
            )

            if key not in supplied:
                unresolved.append(alert)

        if unresolved:
            raise PrescriptionFinalizeError(
                "MEDICATION_SAFETY_BLOCKED",
                (
                    "Prescription contains "
                    f"{len(unresolved)} unresolved "
                    "MAJOR/BLOCK safety alert(s)."
                ),
                409,
            )

        if (
            blocking_alerts
            and not _has_permission(
                actor_user,
                "medication_safety.override",
            )
        ):
            raise PrescriptionFinalizeError(
                "FORBIDDEN_PERMISSION",
                (
                    "Permission "
                    "'medication_safety.override' "
                    "is required."
                ),
                403,
            )

        saved_overrides = []

        for alert in blocking_alerts:
            key = (
                str(
                    alert["alert_type"]
                ).upper(),
                str(
                    alert["rule_id"]
                ),
            )

            supplied_override = (
                supplied[key]
            )

            override = (
                MedicationSafetyOverride
                .objects
                .create(
                    patient=patient,
                    prescription=prescription,
                    doctor=actor_user,
                    alert_type=(
                        alert["alert_type"]
                    ),
                    severity=(
                        alert["severity"]
                    ),
                    rule_type=(
                        supplied_override[
                            "rule_type"
                        ]
                    ),
                    rule=(
                        supplied_override[
                            "rule_id"
                        ]
                    ),
                    reason=(
                        supplied_override[
                            "reason"
                        ]
                    ),
                    created_at=(
                        timezone.now()
                    ),
                )
            )

            saved_overrides.append(
                override
            )

        finalized_at = timezone.now()

        prescription.status = "FINAL"
        prescription.finalized_at = (
            finalized_at
        )
        prescription.updated_at = (
            finalized_at
        )

        prescription.save(
            update_fields=[
                "status",
                "finalized_at",
                "updated_at",
            ]
        )

        schedules_created = (
            _create_schedules(items)
        )

        _create_finalized_prescription_notification(
            prescription=prescription,
            patient=patient,
        )

        record_audit_event(
            source_service="BACKEND",
            action="PRESCRIPTION_FINALIZED",
            resource_type="Prescription",
            resource_id=prescription.id,
            outcome="SUCCESS",
            request=request,
            actor_user=actor_user,
            after_json={
                "patient_id": str(
                    patient.id
                ),
                "status": "FINAL",
                "finalized_at": (
                    finalized_at.isoformat()
                ),
                "safety": safety,
                "override_count": len(
                    saved_overrides
                ),
                "schedules_created": (
                    schedules_created
                ),
            },
        )

        outbox = OutboxEvent.objects.create(
            event_type=(
                "prescription.finalized.v1"
            ),
            aggregate_type="Prescription",
            aggregate=str(
                prescription.id
            ),
            payload={
                "prescription_id": str(
                    prescription.id
                ),
                "patient_id": str(
                    patient.id
                ),
                "doctor_id": str(
                    actor_user.id
                ),
                "finalized_at": (
                    finalized_at.isoformat()
                ),
                "schedules_created": (
                    schedules_created
                ),
            },
            status="PENDING",
            retry_count=0,
            published_at=None,
            created_at=finalized_at,
        )

        transaction.on_commit(
            lambda event_id=outbox.id:
            _send_outbox_after_commit(
                event_id
            )
        )

        return {
            "prescription_id": str(
                prescription.id
            ),
            "status": "FINAL",
            "finalized_at": finalized_at,
            "safety": {
                **safety,
                "overrides": [
                    {
                        "override_id": str(
                            override.id
                        ),
                        "alert_type": (
                            override.alert_type
                        ),
                        "severity": (
                            override.severity
                        ),
                        "reason": (
                            override.reason
                        ),
                    }
                    for override
                    in saved_overrides
                ],
            },
            "schedules_created": (
                schedules_created
            ),
        }

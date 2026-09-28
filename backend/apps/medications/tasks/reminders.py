"""Celery tasks for patient medication reminders."""

from __future__ import annotations

from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.db import transaction
from django.db.models.functions import TruncMinute
from django.utils import timezone

from apps.medications.models import MedicationIntake, MedicationSchedule
from apps.notifications.models import Notification
from apps.notifications.services.notifications import create_notification_for_user


def _scheduled_minute_window(now):
    """Return the minute containing ``now`` in the active timezone."""
    start = now.replace(second=0, microsecond=0)
    return start, start + timedelta(minutes=1)


def _reminder_item(schedule):
    item = schedule.prescription_item
    return {
        "medication_schedule_id": str(schedule.id),
        "prescription_id": str(item.prescription_id),
        "prescription_item_id": str(item.id),
        "medication_name": item.medication_name or "처방약",
        "dose": str(schedule.dose),
        "dose_unit": item.dose_unit or "",
        "time_slot": schedule.time_slot,
    }


@shared_task(name="apps.medications.tasks.send_medication_reminders")
def send_medication_reminders():
    """Create one reminder for each patient's schedules in the current minute."""
    batch_size = int(getattr(settings, "MEDICATION_REMINDER_BATCH_SIZE", 300))
    reminder_start, reminder_end = _scheduled_minute_window(timezone.now())
    user_path = "prescription_item__prescription__encounter__patient__user_id"
    group_rows = list(
        MedicationSchedule.objects.filter(
            scheduled_at__gte=reminder_start,
            scheduled_at__lt=reminder_end,
            prescription_item__prescription__status="FINAL",
            prescription_item__prescription__encounter__patient__user__isnull=False,
        )
        .annotate(reminder_minute=TruncMinute("scheduled_at"))
        .order_by(user_path, "reminder_minute")
        .values(user_path, "reminder_minute")
        .distinct()[:batch_size]
    )

    created_count = 0
    skipped_count = 0

    for group in group_rows:
        recipient_user_id = group[user_path]
        scheduled_at = group["reminder_minute"]

        with transaction.atomic():
            schedules = list(
                MedicationSchedule.objects.select_for_update(of=("self",))
                .select_related(
                    "prescription_item",
                    "prescription_item__prescription",
                    "prescription_item__prescription__encounter",
                    "prescription_item__prescription__encounter__patient",
                    "prescription_item__prescription__encounter__patient__user",
                )
                .filter(
                    scheduled_at__gte=scheduled_at,
                    scheduled_at__lt=scheduled_at + timedelta(minutes=1),
                    prescription_item__prescription__status="FINAL",
                    prescription_item__prescription__encounter__patient__user_id=recipient_user_id,
                )
                .order_by("id")
            )
            current_start, current_end = _scheduled_minute_window(timezone.now())
            if scheduled_at < current_start or scheduled_at >= current_end:
                skipped_count += 1
                continue

            pending_schedules = [
                schedule
                for schedule in schedules
                if not MedicationIntake.objects.filter(schedule_id=schedule.id).exists()
            ]
            if not pending_schedules:
                skipped_count += 1
                continue

            first_schedule = pending_schedules[0]
            patient = first_schedule.prescription_item.prescription.encounter.patient
            recipient_user = patient.user
            if recipient_user is None:
                skipped_count += 1
                continue

            dedupe_key = (
                "medication-reminder:"
                f"{patient.id}:"
                f"{scheduled_at.isoformat()}"
            )
            if Notification.objects.filter(
                recipient_user=recipient_user,
                category="MEDICATION",
                data_json__dedupe_key=dedupe_key,
            ).exists():
                skipped_count += 1
                continue

            reminder_items = [_reminder_item(schedule) for schedule in pending_schedules]
            first_item = reminder_items[0]
            count = len(reminder_items)
            if count == 1:
                body = "지금 복용할 약이 있어요. 복약 일정을 확인해 주세요."
            else:
                body = f"지금 복용할 약이 {count}개 있어요. 복약 일정을 확인해 주세요."

            notification = create_notification_for_user(
                recipient_user=recipient_user,
                category="MEDICATION",
                severity="INFO",
                title="복약 시간이에요",
                body=body,
                data_json={
                    "event_type": "MEDICATION_REMINDER",
                    "patient_id": str(patient.id),
                    # Keep the pre-existing scalar fields for compatibility.
                    "resource_type": "MedicationSchedule",
                    "resource_id": first_item["medication_schedule_id"],
                    "medication_schedule_id": first_item["medication_schedule_id"],
                    "prescription_id": first_item["prescription_id"],
                    "prescription_item_id": first_item["prescription_item_id"],
                    "medication_name": first_item["medication_name"],
                    "scheduled_at": scheduled_at.isoformat(),
                    "time_slot": first_item["time_slot"],
                    "dose": first_item["dose"],
                    "dose_unit": first_item["dose_unit"],
                    "medication_schedules": reminder_items,
                    "dedupe_key": dedupe_key,
                },
            )
            if notification is None:
                skipped_count += 1
                continue
            created_count += 1

    return {
        "checked": len(group_rows),
        "created": created_count,
        "skipped": skipped_count,
        "reminder_minute": reminder_start.isoformat(),
    }

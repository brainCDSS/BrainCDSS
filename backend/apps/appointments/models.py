"""appointments persistence models; TODO after domain schema approval."""

import uuid

from django.db import models
from django.utils import timezone

# === FINAL_DB_GENERATED_IMPORTS_START ===
from .models_generated import ClinicianSchedule, AppointmentSlot, Appointment, AppointmentStatusHistory
# === FINAL_DB_GENERATED_IMPORTS_END ===


class AppointmentRescheduleHistory(models.Model):
    """Approved appointment reschedules retained for patient-facing history."""

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        db_column="id",
    )
    appointment = models.ForeignKey(
        Appointment,
        on_delete=models.CASCADE,
        db_column="appointment_id",
        related_name="reschedule_history",
        db_index=True,
    )
    previous_slot = models.ForeignKey(
        AppointmentSlot,
        on_delete=models.PROTECT,
        db_column="previous_slot_id",
        related_name="+",
        db_index=True,
    )
    changed_slot = models.ForeignKey(
        AppointmentSlot,
        on_delete=models.PROTECT,
        db_column="changed_slot_id",
        related_name="+",
        db_index=True,
    )
    rescheduled_at = models.DateTimeField(
        default=timezone.now,
        db_column="rescheduled_at",
        db_index=True,
    )
    reschedule_reason = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        db_column="reschedule_reason",
    )
    changed_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        db_column="changed_by_id",
        related_name="+",
        null=True,
        blank=True,
        db_index=True,
    )

    class Meta:
        db_table = "appointment_reschedule_history"
        ordering = ["-rescheduled_at"]

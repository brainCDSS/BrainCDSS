"""Celery tasks for patient appointment reminders."""

from __future__ import annotations

from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.appointments.models import Appointment
from apps.notifications.models import Notification
from apps.notifications.services.notifications import (
    create_notification_for_user,
)


@shared_task(
    name="apps.appointments.tasks.send_appointment_reminders",
)
def send_appointment_reminders():
    """
    Create one patient reminder notification for confirmed appointments
    whose scheduled time is within the configured reminder window.

    Delivery flow:
        Celery Beat
        -> this task
        -> Notification row
        -> existing notification signal
        -> FCM Celery task
        -> patient mobile app

    Duplicate prevention:
        appointment UUID + current slot start_at

    Therefore:
    - repeated Beat runs do not create duplicate reminders;
    - if an appointment is rescheduled, the changed start_at produces
      a new dedupe key and the new appointment time can be reminded.
    """

    reminder_hours = int(
        getattr(
            settings,
            "APPOINTMENT_REMINDER_HOURS",
            24,
        )
    )

    batch_size = int(
        getattr(
            settings,
            "APPOINTMENT_REMINDER_BATCH_SIZE",
            200,
        )
    )

    now = timezone.now()

    reminder_until = (
        now
        + timedelta(hours=reminder_hours)
    )

    # ---------------------------------------------------------
    # Candidate 조회
    # ---------------------------------------------------------
    #
    # 실제 알림 생성 전 각 Appointment를 다시 lock하고 상태/시간을
    # 재확인하므로 여기서는 candidate id만 가져온다.
    # ---------------------------------------------------------

    appointment_ids = list(
        Appointment.objects.filter(
            status="CONFIRMED",
            slot__start_at__gt=now,
            slot__start_at__lte=reminder_until,
            patient__user__isnull=False,
        )
        .order_by(
            "slot__start_at",
            "id",
        )
        .values_list(
            "id",
            flat=True,
        )[:batch_size]
    )

    created_count = 0
    skipped_count = 0

    # ---------------------------------------------------------
    # Appointment 단위 처리
    # ---------------------------------------------------------

    for appointment_id in appointment_ids:

        with transaction.atomic():

            # -------------------------------------------------
            # 동일 예약을 여러 Worker가 동시에 처리하더라도
            # duplicate Notification이 생기지 않도록
            # Appointment row를 잠근다.
            # -------------------------------------------------

            try:
                appointment = (
                    Appointment.objects
                    .select_for_update(
                        of=("self",),
                    )
                    .select_related(
                        "patient__user",
                        "slot",
                    )
                    .get(
                        pk=appointment_id,
                    )
                )

            except Appointment.DoesNotExist:
                skipped_count += 1
                continue

            current_now = timezone.now()

            current_until = (
                current_now
                + timedelta(
                    hours=reminder_hours
                )
            )

            # -------------------------------------------------
            # Candidate 조회 이후 상태가 바뀌었을 수 있으므로
            # lock 후 다시 검증한다.
            # -------------------------------------------------

            if (
                appointment.status
                != "CONFIRMED"
            ):
                skipped_count += 1
                continue

            if (
                appointment.slot is None
                or appointment.slot.start_at
                is None
            ):
                skipped_count += 1
                continue

            scheduled_at = (
                appointment.slot.start_at
            )

            if (
                scheduled_at
                <= current_now
                or scheduled_at
                > current_until
            ):
                skipped_count += 1
                continue

            patient = appointment.patient

            if patient is None:
                skipped_count += 1
                continue

            recipient_user = (
                patient.user
            )

            if recipient_user is None:
                skipped_count += 1
                continue

            # =================================================
            # Duplicate key
            # =================================================
            #
            # appointment id뿐 아니라 start_at까지 포함한다.
            #
            # 예)
            #
            # 기존:
            # appointment-reminder:
            #   <appointment_uuid>:2026-09-22T10:00...
            #
            # 변경:
            # appointment-reminder:
            #   <appointment_uuid>:2026-09-23T14:00...
            #
            # 예약 시간이 바뀌면 새 reminder가 가능하다.
            # =================================================

            dedupe_key = (
                "appointment-reminder:"
                f"{appointment.id}:"
                f"{scheduled_at.isoformat()}"
            )

            already_exists = (
                Notification.objects
                .filter(
                    recipient_user=recipient_user,
                    category="APPOINTMENT",
                    data_json__dedupe_key=(
                        dedupe_key
                    ),
                )
                .exists()
            )

            if already_exists:
                skipped_count += 1
                continue

            # -------------------------------------------------
            # 환자에게 표시할 예약 시간
            # -------------------------------------------------

            local_scheduled_at = (
                timezone.localtime(
                    scheduled_at
                )
            )

            scheduled_text = (
                local_scheduled_at.strftime(
                    "%Y-%m-%d %H:%M"
                )
            )

            # =================================================
            # Notification 생성
            # =================================================

            notification = (
                create_notification_for_user(
                    recipient_user=(
                        recipient_user
                    ),
                    category="APPOINTMENT",
                    severity="INFO",
                    title=(
                        "예약 일정이 예정되어 있습니다"
                    ),
                    body=(
                        f"{scheduled_text} 예약이 "
                        "예정되어 있습니다. "
                        "예약 일정을 확인해 주세요."
                    ),
                    data_json={
                        "event_type":
                            "APPOINTMENT_REMINDER",

                        "patient_id":
                            str(
                                appointment.patient_id
                            ),

                        "resource_type":
                            "Appointment",

                        "resource_id":
                            str(
                                appointment.id
                            ),

                        "appointment_status":
                            str(
                                appointment.status
                            ),

                        "scheduled_at":
                            scheduled_at.isoformat(),

                        "reminder_hours":
                            reminder_hours,

                        "dedupe_key":
                            dedupe_key,
                    },
                )
            )

            if notification is None:
                # 사용자 Notification Preference에서
                # APPOINTMENT category가 disabled인 경우 등.
                skipped_count += 1
                continue

            created_count += 1

    return {
        "checked": len(
            appointment_ids
        ),
        "created": created_count,
        "skipped": skipped_count,
        "reminder_hours": (
            reminder_hours
        ),
    }
"""Celery tasks for patient medication reminders."""

from __future__ import annotations

from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.medications.models import (
    MedicationIntake,
    MedicationSchedule,
)
from apps.notifications.models import Notification
from apps.notifications.services.notifications import (
    create_notification_for_user,
)


@shared_task(
    name="apps.medications.tasks.send_medication_reminders",
)
def send_medication_reminders():
    """
    Create one medication reminder notification for each upcoming
    MedicationSchedule.

    Conditions:
    - prescription status must be FINAL;
    - scheduled_at must be in the upcoming reminder window;
    - patient must have a linked user account;
    - no MedicationIntake may exist for the schedule;
    - the same schedule/time reminder must not already exist.

    Delivery flow:
        Celery Beat
        -> this task
        -> Notification row
        -> existing Notification signal
        -> FCM Celery task
        -> patient mobile app
    """

    reminder_minutes = int(
        getattr(
            settings,
            "MEDICATION_REMINDER_MINUTES",
            10,
        )
    )

    batch_size = int(
        getattr(
            settings,
            "MEDICATION_REMINDER_BATCH_SIZE",
            300,
        )
    )

    now = timezone.now()

    reminder_until = (
        now
        + timedelta(
            minutes=reminder_minutes
        )
    )

    # =========================================================
    # Candidate 조회
    # =========================================================
    #
    # MedicationSchedule.scheduled_at을 복약 예정시간의
    # 단일 기준으로 사용한다.
    #
    # FINAL 처방만 대상으로 한다.
    #
    # 실제 생성 직전에는 select_for_update() 후
    # 상태를 다시 확인한다.
    # =========================================================

    schedule_ids = list(
        MedicationSchedule.objects
        .filter(
            scheduled_at__gt=now,
            scheduled_at__lte=reminder_until,
            prescription_item__prescription__status="FINAL",
            prescription_item__prescription__encounter__patient__user__isnull=False,
        )
        .order_by(
            "scheduled_at",
            "id",
        )
        .values_list(
            "id",
            flat=True,
        )[:batch_size]
    )

    created_count = 0
    skipped_count = 0

    # =========================================================
    # Schedule 단위 처리
    # =========================================================

    for schedule_id in schedule_ids:

        with transaction.atomic():

            try:
                schedule = (
                    MedicationSchedule.objects
                    .select_for_update(
                        of=("self",),
                    )
                    .select_related(
                        "prescription_item",
                        "prescription_item__prescription",
                        "prescription_item__prescription__encounter",
                        "prescription_item__prescription__encounter__patient",
                        "prescription_item__prescription__encounter__patient__user",
                    )
                    .get(
                        pk=schedule_id
                    )
                )

            except MedicationSchedule.DoesNotExist:
                skipped_count += 1
                continue

            prescription_item = (
                schedule.prescription_item
            )

            prescription = (
                prescription_item.prescription
            )

            # -------------------------------------------------
            # Candidate 조회 이후 처방 상태가 바뀌었을 수 있으므로
            # lock 이후 다시 검증한다.
            # -------------------------------------------------

            if prescription.status != "FINAL":
                skipped_count += 1
                continue

            current_now = timezone.now()

            current_until = (
                current_now
                + timedelta(
                    minutes=reminder_minutes
                )
            )

            scheduled_at = (
                schedule.scheduled_at
            )

            if (
                scheduled_at <= current_now
                or scheduled_at > current_until
            ):
                skipped_count += 1
                continue

            # =================================================
            # 이미 복약 기록이 존재하는 경우 알림 제외
            # =================================================
            #
            # MedicationIntake.schedule은 OneToOne.
            #
            # TAKEN / SKIPPED 등 어떤 상태든 이미 환자 또는
            # 의료진이 해당 Schedule에 대해 기록을 만들었다면
            # 다시 복약 알림을 보내지 않는다.
            # =================================================

            intake_exists = (
                MedicationIntake.objects
                .filter(
                    schedule_id=schedule.id
                )
                .exists()
            )

            if intake_exists:
                skipped_count += 1
                continue

            encounter = (
                prescription.encounter
            )

            patient = (
                encounter.patient
            )

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
            # MedicationSchedule 자체가 하나의 실제 복약시점을
            # 나타내므로 schedule UUID와 scheduled_at을 묶는다.
            #
            # Beat가 5분마다 반복되어도 같은 Schedule에 대해
            # Notification은 한 번만 생성된다.
            # =================================================

            dedupe_key = (
                "medication-reminder:"
                f"{schedule.id}:"
                f"{scheduled_at.isoformat()}"
            )

            already_exists = (
                Notification.objects
                .filter(
                    recipient_user=recipient_user,
                    category="MEDICATION",
                    data_json__dedupe_key=(
                        dedupe_key
                    ),
                )
                .exists()
            )

            if already_exists:
                skipped_count += 1
                continue

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

            medication_name = (
                prescription_item.medication_name
                or "처방약"
            )

            dose = schedule.dose

            dose_unit = (
                prescription_item.dose_unit
                or ""
            )

            dose_text = (
                f"{dose}{dose_unit}"
                if dose_unit
                else str(dose)
            )

            # =================================================
            # Notification 생성
            # =================================================

            notification = (
                create_notification_for_user(
                    recipient_user=(
                        recipient_user
                    ),
                    category="MEDICATION",
                    severity="INFO",
                    title="복약 시간이 곧 예정되어 있습니다",
                    body=(
                        f"{scheduled_text} "
                        f"{medication_name} "
                        f"{dose_text} 복약이 예정되어 있습니다."
                    ),
                    data_json={
                        "event_type":
                            "MEDICATION_REMINDER",

                        "patient_id":
                            str(
                                patient.id
                            ),

                        "resource_type":
                            "MedicationSchedule",

                        "resource_id":
                            str(
                                schedule.id
                            ),

                        "medication_schedule_id":
                            str(
                                schedule.id
                            ),

                        "prescription_id":
                            str(
                                prescription.id
                            ),

                        "prescription_item_id":
                            str(
                                prescription_item.id
                            ),

                        "medication_name":
                            medication_name,

                        "scheduled_at":
                            scheduled_at.isoformat(),

                        "time_slot":
                            schedule.time_slot,

                        "dose":
                            str(
                                schedule.dose
                            ),

                        "dose_unit":
                            dose_unit,

                        "reminder_minutes":
                            reminder_minutes,

                        "dedupe_key":
                            dedupe_key,
                    },
                )
            )

            if notification is None:
                # MEDICATION 알림 카테고리를 사용자가
                # 비활성화한 경우 등.
                skipped_count += 1
                continue

            created_count += 1

    return {
        "checked": len(
            schedule_ids
        ),
        "created": created_count,
        "skipped": skipped_count,
        "reminder_minutes": (
            reminder_minutes
        ),
    }
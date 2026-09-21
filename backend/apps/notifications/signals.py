"""Notification delivery and clinical workflow signals."""

import logging

from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.consultations.models import (
    Consultation,
    ConsultationHistory,
)
from apps.notifications.models import (
    Notification,
)
from apps.notifications.services.notifications import (
    create_notification_for_user,
)
from apps.notifications.tasks.fcm import (
    send_notification_fcm,
)


logger = logging.getLogger(__name__)


@receiver(post_save, sender=Consultation, dispatch_uid="brainon_consultation_request_notification")
def notify_consultation_request(sender, instance, created, **kwargs):
    if not created or instance.assigned_to_id is None:
        return
    from apps.notifications.services.consultations import create_assigned_consultation_notification
    consultation = Consultation.objects.select_related(
        "encounter__patient", "assigned_to", "requested_by"
    ).get(pk=instance.pk)
    create_assigned_consultation_notification(consultation=consultation)


@receiver(
    post_save,
    sender=Notification,
    dispatch_uid="brainon_notification_common_fcm",
)
def queue_notification_fcm(
    sender,
    instance,
    created,
    **kwargs,
):
    """
    새로 생성된 모든 Notification을
    DB commit 이후 공통 FCM task로 전달한다.
    """

    if not created:
        return

    notification_id = str(
        instance.id
    )

    def enqueue():
        try:
            send_notification_fcm.delay(
                notification_id
            )
        except Exception:
            logger.exception(
                "FCM_ENQUEUE_FAILED "
                "notification=%s",
                notification_id,
            )

    transaction.on_commit(
        enqueue
    )


@receiver(
    post_save,
    sender=ConsultationHistory,
    dispatch_uid=(
        "brainon_consultation_decision_notification"
    ),
)
def notify_consultation_decision(
    sender,
    instance,
    created,
    **kwargs,
):
    """
    협진 요청이 ACCEPTED 또는 REJECTED 되면
    최초 요청자에게 Notification을 생성한다.
    """

    if not created:
        return

    if instance.to_status not in {
        "ACCEPTED",
        "REJECTED",
        "RESPONDED",
    }:
        return

    history = (
        ConsultationHistory.objects
        .select_related(
            "consultation__requested_by",
            "consultation__encounter__patient",
            "changed_by",
        )
        .get(
            pk=instance.pk
        )
    )

    consultation = history.consultation
    recipient = consultation.requested_by

    if recipient is None:
        return

    actor = history.changed_by

    actor_name = (
        getattr(
            actor,
            "name",
            None,
        )
        or "담당 의료진"
    )

    patient = (
        consultation.encounter.patient
    )

    if history.to_status == "ACCEPTED":
        event_type = (
            "CONSULTATION_ACCEPTED"
        )

        title = "협진 요청 수락"
        severity = "INFO"

        body = (
            f"{actor_name} 의료진이 "
            f"{patient.name} 환자의 "
            "협진 요청을 수락했습니다."
        )

    elif history.to_status == "REJECTED":
        event_type = (
            "CONSULTATION_REJECTED"
        )

        title = "협진 요청 거절"
        severity = "WARNING"

        body = (
            f"{actor_name} 의료진이 "
            f"{patient.name} 환자의 "
            "협진 요청을 거절했습니다."
        )

        reason = str(
            history.reason or ""
        ).strip()

        if reason:
            body += (
                f" 사유: {reason}"
            )

    else:
        event_type = "CONSULTATION_RESPONDED"
        title = "Consultation response available"
        severity = "INFO"
        body = "The requested consultation has a response ready for review."

    create_notification_for_user(
        recipient_user=recipient,
        category="CONSULTATION",
        severity=severity,
        title=title,
        body=body,
        data_json={
            "event_type": event_type,

            "consultation_id": str(
                consultation.id
            ),

            "encounter_id": str(
                consultation.encounter_id
            ),

            "patient_id": str(
                patient.id
            ),

            "consultation_type": (
                consultation.consultation_type
            ),

            "status": (
                history.to_status
            ),

            "changed_by_id": (
                str(actor.id)
                if actor is not None
                else None
            ),
        },
    )

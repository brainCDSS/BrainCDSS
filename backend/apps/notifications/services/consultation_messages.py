"""Consultation message notification service."""

from datetime import timedelta

from django.utils import timezone

from apps.consultations.models import (
    ConsultationChatPresence,
)
from apps.notifications.models import Notification


PRESENCE_ACTIVE_SECONDS = 5


def recipient_is_active_in_consultation(
    *,
    consultation,
    recipient,
):
    """
    상대 사용자가 현재 같은 협진 채팅에 접속 중인지 판단한다.

    Frontend heartbeat는 2초 간격으로 갱신하며,
    마지막 heartbeat가 최근 5초 이내인 경우에만
    현재 같은 consultation을 보고 있다고 판단한다.
    """

    cutoff = (
        timezone.now()
        - timedelta(
            seconds=PRESENCE_ACTIVE_SECONDS,
        )
    )

    return (
        ConsultationChatPresence.objects
        .filter(
            consultation_id=consultation.id,
            user_id=recipient.id,
            last_seen_at__gte=cutoff,
        )
        .exists()
    )


def create_consultation_message_notification(
    *,
    consultation,
    message,
    recipient,
):
    """
    협진 메시지용 Notification을 생성한다.

    수신자가 현재 같은 consultation 채팅을 보고 있으면
    실시간 메시지만 표시하고 Notification / FCM Push는
    생성하지 않는다.
    """

    if recipient_is_active_in_consultation(
        consultation=consultation,
        recipient=recipient,
    ):
        return None

    preview = message.content.strip()

    if len(preview) > 80:
        preview = preview[:77] + "..."

    return Notification.objects.create(
        recipient_user=recipient,
        category="CONSULTATION",
        severity="INFO",
        title="새 협진 메시지",
        body=(
            f"{message.sender.name}: "
            f"{preview}"
        ),
        data_json={
            "event_type": "CONSULTATION_MESSAGE",
            "consultation_id": str(
                consultation.id
            ),
            "message_id": str(
                message.id
            ),
            "sender_id": str(
                message.sender_id
            ),
            "sender_name": (
                message.sender.name
            ),
            "encounter_id": str(
                consultation.encounter_id
            ),
        },
    )

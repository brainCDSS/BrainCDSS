"""FCM delivery tasks."""

import logging

from celery import shared_task
from firebase_admin import messaging

from apps.notifications.models import (
    FCMDeviceToken,
    Notification,
)
from apps.notifications.services.fcm import (
    send_fcm_message,
)


logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={
        "max_retries": 3,
    },
)
def send_notification_fcm(
    self,
    notification_id: str,
):
    """
    Notification 한 건을 수신자의 모든 활성 FCM device로 발송한다.
    """

    notification = (
        Notification.objects
        .select_related(
            "recipient_user",
        )
        .get(
            pk=notification_id,
        )
    )

    tokens = list(
        FCMDeviceToken.objects
        .filter(
            user=notification.recipient_user,
            is_active=True,
        )
        .only(
            "id",
            "token",
            "is_active",
        )
    )

    if not tokens:
        logger.info(
            "FCM_SKIP_NO_ACTIVE_TOKEN "
            "notification=%s recipient=%s",
            notification.id,
            notification.recipient_user_id,
        )

        return {
            "sent": 0,
            "failed": 0,
        }

    sent = 0
    failed = 0

    for device in tokens:
        try:
            send_fcm_message(
                token=device.token,
                title=notification.title,
                body=notification.body,
                data={
                    **(
                        notification.data_json
                        or {}
                    ),
                    "notification_id": str(
                        notification.id
                    ),
                    "category": (
                        notification.category
                    ),
                },
            )

            sent += 1

        except (
            messaging.UnregisteredError,
            messaging.SenderIdMismatchError,
        ):
            device.is_active = False

            device.save(
                update_fields=[
                    "is_active",
                ]
            )

            failed += 1

            logger.warning(
                "FCM_TOKEN_DEACTIVATED "
                "token_id=%s",
                device.id,
            )

        except Exception:
            logger.exception(
                "FCM_SEND_FAILED "
                "notification=%s "
                "token_id=%s",
                notification.id,
                device.id,
            )

            # shared_task의
            # autoretry_for=(Exception,)가
            # 실제로 재시도할 수 있도록 다시 raise.
            raise

    return {
        "sent": sent,
        "failed": failed,
    }

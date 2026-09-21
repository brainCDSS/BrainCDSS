"""Preference-aware, per-device FCM delivery tasks."""

import logging
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from celery import shared_task
from firebase_admin import messaging
from firebase_admin import exceptions as firebase_exceptions

from apps.notifications.models import FCMDeviceToken, Notification, NotificationCategoryPreference, NotificationSetting
from apps.notifications.services.fcm import send_fcm_message

logger = logging.getLogger(__name__)


def _safe_push_text(notification):
    if notification.severity == "CRITICAL":
        return "Urgent BrainOn alert", "Open BrainOn to review the alert."
    labels = {
        "CONSULTATION": "Consultation update",
        "AI_ANALYSIS": "AI analysis update",
        "PRESCRIPTION": "Prescription update",
        "MEDICATION_SAFETY": "Medication safety update",
        "APPOINTMENT": "Appointment update",
        "IMAGING": "Imaging update",
    }
    return labels.get(notification.category, "BrainOn notification"), "Open BrainOn to view details."


def _push_is_suppressed(notification):
    """DND and category preferences suppress Push, never the inbox row."""
    if notification.severity == "CRITICAL":
        return False
    preference = NotificationCategoryPreference.objects.filter(
        user=notification.recipient_user, category=notification.category,
    ).first()
    if preference is not None and not preference.enabled:
        return True
    setting = NotificationSetting.objects.filter(user=notification.recipient_user).first()
    if not setting or not setting.dnd_enabled or not setting.dnd_start or not setting.dnd_end:
        return False
    try:
        local_time = datetime.now(ZoneInfo(setting.timezone)).time().replace(tzinfo=None)
    except ZoneInfoNotFoundError:
        logger.warning("FCM_DND_TIMEZONE_INVALID recipient=%s", notification.recipient_user_id)
        return False
    if setting.dnd_start <= setting.dnd_end:
        return setting.dnd_start <= local_time < setting.dnd_end
    return local_time >= setting.dnd_start or local_time < setting.dnd_end


@shared_task(ignore_result=True)
def send_notification_fcm(notification_id: str):
    """Fan out once; each device owns its retry lifecycle."""
    notification = Notification.objects.select_related("recipient_user").get(pk=notification_id)
    if _push_is_suppressed(notification):
        logger.info("FCM_SKIP_PREFERENCE notification=%s", notification.id)
        return {"queued": 0}
    token_ids = list(FCMDeviceToken.objects.filter(
        user=notification.recipient_user, is_active=True,
    ).values_list("id", flat=True))
    for token_id in token_ids:
        send_notification_device_fcm.delay(str(notification.id), str(token_id))
    return {"queued": len(token_ids)}


@shared_task(bind=True, ignore_result=True, max_retries=3)
def send_notification_device_fcm(self, notification_id: str, token_id: str):
    """Send to one device so retry cannot repeat successful sibling devices."""
    notification = Notification.objects.select_related("recipient_user").get(pk=notification_id)
    device = FCMDeviceToken.objects.filter(
        pk=token_id, user=notification.recipient_user, is_active=True,
    ).first()
    if device is None or _push_is_suppressed(notification):
        return {"sent": 0}
    try:
        data = notification.data_json or {}
        title, body = _safe_push_text(notification)
        send_fcm_message(
            token=device.token, title=title, body=body,
            data={**data, "notification_id": str(notification.id),
                  "event_type": str(data.get("event_type") or ""),
                  "category": notification.category},
        )
        return {"sent": 1}
    except (messaging.UnregisteredError, messaging.SenderIdMismatchError):
        FCMDeviceToken.objects.filter(pk=device.pk).update(is_active=False)
        logger.warning("FCM_TOKEN_DEACTIVATED token_id=%s", device.id)
        return {"sent": 0, "deactivated": 1}
    except (
        messaging.QuotaExceededError,
        firebase_exceptions.UnavailableError,
        firebase_exceptions.DeadlineExceededError,
    ) as exc:
        raise self.retry(exc=exc, countdown=min(60, 2 ** self.request.retries))
    except Exception as exc:
        if isinstance(exc, (TimeoutError, ConnectionError)):
            raise self.retry(exc=exc, countdown=min(60, 2 ** self.request.retries))
        logger.exception("FCM_SEND_FAILED notification=%s token_id=%s", notification.id, device.id)
        raise

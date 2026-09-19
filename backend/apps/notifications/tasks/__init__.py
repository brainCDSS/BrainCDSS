"""Notification Celery tasks."""

from .fcm import send_notification_fcm

__all__ = [
    "send_notification_fcm",
]

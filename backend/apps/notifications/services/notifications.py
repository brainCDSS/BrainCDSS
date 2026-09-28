"""Shared, preference-aware notification creation helpers."""

from __future__ import annotations

from typing import Any

from apps.notifications.models import Notification, NotificationCategoryPreference


def create_notification_for_user(
    *,
    recipient_user: Any,
    category: str,
    severity: str,
    title: str,
    body: str,
    data_json: dict[str, Any] | None = None,
) -> Notification | None:
    """Create one user notification unless its ordinary category is disabled.

    CRITICAL notifications retain the existing forced-delivery policy used by
    notification-preferences PATCH; no recipient is inferred by this helper.
    """
    if recipient_user is None or not getattr(recipient_user, "pk", None):
        return None

    preference = NotificationCategoryPreference.objects.filter(
        user=recipient_user,
        category=category,
    ).first()
    if severity != "CRITICAL" and preference is not None and not preference.enabled:
        return None

    return Notification.objects.create(
        recipient_user=recipient_user,
        category=category,
        severity=severity,
        title=title,
        body=body,
        data_json=data_json or {},
    )


def create_notifications_for_role(*, role_code: str, **notification_kwargs: Any) -> list[Notification]:
    """Create preference-aware notifications for active users in one role."""
    from apps.accounts.models import User

    notifications = []
    for user in User.objects.filter(role__code=role_code, is_active=True):
        notification = create_notification_for_user(
            recipient_user=user,
            **notification_kwargs,
        )
        if notification is not None:
            notifications.append(notification)
    return notifications

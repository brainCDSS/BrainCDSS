from __future__ import annotations

from typing import Mapping

from firebase_admin import messaging

from .firebase import get_firebase_app


def _normalize_data(
    data: Mapping[str, object] | None,
) -> dict[str, str]:
    if not data:
        return {}

    return {
        str(key): str(value)
        for key, value in data.items()
        if value is not None
    }


def send_fcm_message(
    *,
    token: str,
    title: str,
    body: str,
    data: Mapping[str, object] | None = None,
) -> str:
    """
    단일 FCM registration token으로 Push를 발송한다.
    성공하면 Firebase message ID를 반환한다.
    """
    registration_token = token.strip()

    if not registration_token:
        raise ValueError(
            "FCM_TOKEN_REQUIRED"
        )

    message = messaging.Message(
        token=registration_token,
        notification=messaging.Notification(
            title=title,
            body=body,
        ),
        data=_normalize_data(data),
    )

    return messaging.send(
        message,
        app=get_firebase_app(),
    )

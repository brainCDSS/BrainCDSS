from __future__ import annotations

import logging
from typing import Any

from django.db import transaction
from django.utils import timezone

from apps.common.models import OutboxEvent

logger = logging.getLogger(__name__)


OUTBOX_PENDING = "PENDING"
OUTBOX_PUBLISHED = "PUBLISHED"
OUTBOX_FAILED = "FAILED"


def create_outbox_event(
    *,
    event_type: str,
    aggregate_type: str,
    aggregate_id: str,
    payload: dict[str, Any],
) -> OutboxEvent:
    return OutboxEvent.objects.create(
        event_type=event_type,
        aggregate_type=aggregate_type,
        aggregate=str(aggregate_id),
        payload=payload,
        status=OUTBOX_PENDING,
        retry_count=0,
        published_at=None,
        created_at=timezone.now(),
    )


def enqueue_outbox_event(event_id: str) -> None:
    """
    Best-effort enqueue after the surrounding DB transaction commits.
    If RabbitMQ/Celery is temporarily unavailable, the DB outbox row remains
    PENDING and can be picked up later by publish_pending_outbox_events.
    """
    try:
        from apps.common.tasks import publish_outbox_event
        publish_outbox_event.delay(str(event_id))
    except Exception:
        logger.exception(
            "Could not enqueue outbox event %s; leaving it PENDING.",
            event_id,
        )


def enqueue_outbox_event_on_commit(event_id: str) -> None:
    transaction.on_commit(
        lambda: enqueue_outbox_event(str(event_id)),
        robust=True,
    )

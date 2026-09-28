"""Celery autodiscovery entry point for common tasks."""

from .broker import broker_ping
from apps.common.outbox_tasks import (
    publish_outbox_event,
    publish_pending_outbox_events,
)


__all__ = [
    "broker_ping",
    "publish_outbox_event",
    "publish_pending_outbox_events",
]

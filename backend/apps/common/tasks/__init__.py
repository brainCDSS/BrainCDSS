"""Autodiscovered common tasks; keep a single tasks package."""
from celery import shared_task

from apps.common.outbox_tasks import publish_outbox_event, publish_pending_outbox_events


@shared_task(name="apps.common.tasks.broker_ping", ignore_result=True)
def broker_ping():
    """Check broker delivery without patient data or a result backend."""
    return "ok"

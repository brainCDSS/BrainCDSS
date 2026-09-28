from __future__ import annotations

from celery import current_app, shared_task
from django.db import transaction
from django.db.models import F
from django.utils import timezone
from kombu import Exchange, Producer, Queue

from apps.common.models import OutboxEvent


DOMAIN_EXCHANGE_NAME = "brainon.events"
DOMAIN_QUEUE_NAME = "brainon.domain.events"


@shared_task(bind=True, max_retries=5, default_retry_delay=30)
def publish_outbox_event(self, event_id: str):
    exchange = Exchange(
        DOMAIN_EXCHANGE_NAME,
        type="topic",
        durable=True,
    )
    queue = Queue(
        DOMAIN_QUEUE_NAME,
        exchange=exchange,
        routing_key="#",
        durable=True,
    )

    try:
        # Keep the row lock until broker publish + PUBLISHED update finish.
        # This prevents two workers from publishing the same outbox row
        # concurrently.
        with transaction.atomic():
            event = (
                OutboxEvent.objects.select_for_update()
                .get(pk=event_id)
            )

            if event.status == "PUBLISHED":
                return {
                    "event_id": str(event.id),
                    "status": "ALREADY_PUBLISHED",
                }

            message = {
                "event_id": str(event.id),
                "event_type": event.event_type,
                "aggregate_type": event.aggregate_type,
                "aggregate_id": event.aggregate,
                "payload": event.payload,
                "created_at": event.created_at.isoformat(),
            }

            with current_app.connection_for_write() as connection:
                producer = Producer(connection)
                producer.publish(
                    message,
                    exchange=exchange,
                    routing_key=event.event_type,
                    serializer="json",
                    delivery_mode=2,
                    declare=[exchange, queue],
                    retry=True,
                    retry_policy={
                        "max_retries": 3,
                        "interval_start": 0,
                        "interval_step": 1,
                        "interval_max": 3,
                    },
                )

            event.status = "PUBLISHED"
            event.published_at = timezone.now()
            event.save(
                update_fields=[
                    "status",
                    "published_at",
                ]
            )

        return {
            "event_id": str(event_id),
            "status": "PUBLISHED",
        }

    except Exception as exc:
        OutboxEvent.objects.filter(pk=event_id).update(
            status="FAILED",
            retry_count=F("retry_count") + 1,
        )
        raise self.retry(exc=exc)


@shared_task
def publish_pending_outbox_events(limit: int = 100):
    ids = list(
        OutboxEvent.objects.filter(
            status__in=["PENDING", "FAILED"],
            retry_count__lt=5,
        )
        .order_by("created_at")
        .values_list("id", flat=True)[:limit]
    )

    for event_id in ids:
        publish_outbox_event.delay(str(event_id))

    return {
        "queued": len(ids),
        "event_ids": [str(value) for value in ids],
    }

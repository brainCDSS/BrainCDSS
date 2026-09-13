"""Central Celery queue names and task routing for the modular monolith."""

import os

from kombu import Exchange, Queue


def _queue_name(suffix: str) -> str:
    prefix = os.getenv("CELERY_QUEUE_PREFIX", "brainon").strip(".")
    return f"{prefix}.{suffix}" if prefix else suffix


DEFAULT_QUEUE = os.getenv("CELERY_QUEUE_DEFAULT", _queue_name("default"))
INFERENCE_QUEUE = os.getenv("CELERY_QUEUE_INFERENCE", _queue_name("inference"))
NOTIFICATIONS_QUEUE = os.getenv(
    "CELERY_QUEUE_NOTIFICATIONS", _queue_name("notifications")
)
INTEGRATIONS_QUEUE = os.getenv(
    "CELERY_QUEUE_INTEGRATIONS", _queue_name("integrations")
)


def _direct_queue(name: str) -> Queue:
    return Queue(
        name,
        exchange=Exchange(name, type="direct", durable=True),
        routing_key=name,
        durable=True,
    )


TASK_QUEUES = tuple(
    _direct_queue(name)
    for name in {
        DEFAULT_QUEUE,
        INFERENCE_QUEUE,
        NOTIFICATIONS_QUEUE,
        INTEGRATIONS_QUEUE,
    }
)

# Add a domain route here when a new asynchronous feature is introduced.
# Celery evaluates these patterns in order.
TASK_ROUTES = {
    "apps.ai_analysis.tasks.*": {"queue": INFERENCE_QUEUE},
    "apps.ai_analysis.run_*": {"queue": INFERENCE_QUEUE},
    "apps.notifications.tasks.*": {"queue": NOTIFICATIONS_QUEUE},
    "apps.common.outbox_tasks.*": {"queue": INTEGRATIONS_QUEUE},
    "apps.common.tasks.broker_ping": {"queue": INTEGRATIONS_QUEUE},
}

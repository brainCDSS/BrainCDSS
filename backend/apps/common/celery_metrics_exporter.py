"""Prometheus exporter for BrainOn Celery worker/task events."""

from __future__ import annotations

import logging
import time

import django

django.setup()

from celery.events.state import State
from prometheus_client import (
    Counter,
    Gauge,
    Histogram,
    start_http_server,
)

from config.celery import app


logger = logging.getLogger(
    "brainon.celery.metrics"
)


BROKER_CONNECTED = Gauge(
    "brainon_celery_monitor_broker_connected",
    "Whether the Celery event monitor is connected to RabbitMQ.",
)


WORKERS_ONLINE = Gauge(
    "brainon_celery_workers_online",
    "Number of Celery workers considered alive.",
)


TASKS_ACTIVE = Gauge(
    "brainon_celery_tasks_active",
    "Number of Celery tasks currently in STARTED state.",
)


TASKS_PENDING = Gauge(
    "brainon_celery_tasks_received_current",
    "Tasks received and not yet terminal.",
)


TASK_EVENTS = Counter(
    "brainon_celery_task_events",
    "Celery task lifecycle events by task name.",
    [
        "event",
        "task",
    ],
)


# BRAINON_WORKER_METRICS_V2
#
# Worker identity:
#   worker = full Celery node name, e.g. general@host
#   role   = general / inference / other
#   host   = actual hostname part after "@"
#
# Do not use request_id / task UUID as labels.
# These metrics intentionally remain low-cardinality.

WORKER_ONLINE = Gauge(
    "brainon_celery_worker_online",
    "Whether an individual BrainOn Celery worker is alive.",
    [
        "worker",
        "role",
        "host",
    ],
)


WORKER_TASKS_ACTIVE = Gauge(
    "brainon_celery_worker_tasks_active",
    "Current active tasks by BrainOn Celery worker.",
    [
        "worker",
        "role",
        "host",
    ],
)


WORKER_TASKS_PENDING = Gauge(
    "brainon_celery_worker_tasks_pending",
    "Current received/started/retry tasks by BrainOn Celery worker.",
    [
        "worker",
        "role",
        "host",
    ],
)


WORKER_TASK_EVENTS = Counter(
    "brainon_celery_worker_task_events",
    "Celery task lifecycle events by worker and task.",
    [
        "worker",
        "role",
        "host",
        "event",
        "task",
    ],
)



TASK_RUNTIME = Histogram(
    "brainon_celery_task_runtime_seconds",
    "Runtime of successfully completed Celery tasks.",
    [
        "task",
    ],
    buckets=(
        0.01,
        0.05,
        0.1,
        0.25,
        0.5,
        1.0,
        2.5,
        5.0,
        10.0,
        30.0,
        60.0,
        300.0,
        900.0,
    ),
)


EVENT_NAMES = {
    "task-sent":
        "sent",

    "task-received":
        "received",

    "task-started":
        "started",

    "task-succeeded":
        "succeeded",

    "task-failed":
        "failed",

    "task-retried":
        "retried",

    "task-revoked":
        "revoked",

    "task-rejected":
        "rejected",
}


state = State(
    max_tasks_in_memory=10000,
)


def _task_name(
    event,
):
    name = event.get(
        "name"
    )

    uuid = event.get(
        "uuid"
    )

    if (
        not name
        and uuid
    ):
        task = state.tasks.get(
            uuid
        )

        name = getattr(
            task,
            "name",
            None,
        )

    return str(
        name
        or "unknown"
    )[:160]


def _worker_labels(
    worker_name,
):
    raw = str(
        worker_name
        or "unknown"
    )[:160]

    if "@" in raw:
        prefix, host = raw.split(
            "@",
            1,
        )
    else:
        prefix = raw
        host = "unknown"

    normalized = (
        prefix
        .strip()
        .lower()
    )

    if normalized.startswith(
        "general"
    ):
        role = "general"

    elif normalized.startswith(
        "inference"
    ):
        role = "inference"

    else:
        role = "other"

    return (
        raw,
        role,
        str(
            host
            or "unknown"
        )[:128],
    )


def _task_worker_name(
    task,
):
    worker = getattr(
        task,
        "worker",
        None,
    )

    hostname = getattr(
        worker,
        "hostname",
        None,
    )

    if hostname:
        return str(
            hostname
        )

    return "unknown"


def _event_worker_name(
    event,
):
    hostname = event.get(
        "hostname"
    )

    if hostname:
        return str(
            hostname
        )

    uuid = event.get(
        "uuid"
    )

    if uuid:
        task = state.tasks.get(
            uuid
        )

        if task is not None:
            return (
                _task_worker_name(
                    task
                )
            )

    return "unknown"



def refresh_gauges():
    workers = 0

    active = 0
    pending = 0

    worker_identities = {}

    active_by_worker = {}
    pending_by_worker = {}


    # Gauges are rebuilt from current Celery State.
    # This prevents stale workers from remaining at 1.
    WORKER_ONLINE.clear()
    WORKER_TASKS_ACTIVE.clear()
    WORKER_TASKS_PENDING.clear()


    for worker in state.workers.values():

        hostname = (
            getattr(
                worker,
                "hostname",
                None,
            )
            or getattr(
                worker,
                "id",
                None,
            )
            or "unknown"
        )

        labels = (
            _worker_labels(
                hostname
            )
        )

        worker_identities[
            labels
        ] = True


        try:
            alive = bool(
                worker.alive
            )

        except Exception:
            alive = False


        if alive:
            workers += 1


        WORKER_ONLINE.labels(
            worker=labels[0],
            role=labels[1],
            host=labels[2],
        ).set(
            1 if alive else 0
        )


    WORKERS_ONLINE.set(
        workers
    )


    for task in state.tasks.values():

        task_state = str(
            getattr(
                task,
                "state",
                "",
            )
            or ""
        ).upper()


        worker_name = (
            _task_worker_name(
                task
            )
        )

        labels = (
            _worker_labels(
                worker_name
            )
        )


        if worker_name != "unknown":
            worker_identities[
                labels
            ] = True


        if task_state == "STARTED":
            active += 1

            if worker_name != "unknown":
                active_by_worker[
                    labels
                ] = (
                    active_by_worker.get(
                        labels,
                        0,
                    )
                    + 1
                )


        if task_state in {
            "RECEIVED",
            "STARTED",
            "RETRY",
        }:
            pending += 1

            if worker_name != "unknown":
                pending_by_worker[
                    labels
                ] = (
                    pending_by_worker.get(
                        labels,
                        0,
                    )
                    + 1
                )


    TASKS_ACTIVE.set(
        active
    )

    TASKS_PENDING.set(
        pending
    )


    for labels in worker_identities:

        WORKER_TASKS_ACTIVE.labels(
            worker=labels[0],
            role=labels[1],
            host=labels[2],
        ).set(
            active_by_worker.get(
                labels,
                0,
            )
        )


        WORKER_TASKS_PENDING.labels(
            worker=labels[0],
            role=labels[1],
            host=labels[2],
        ).set(
            pending_by_worker.get(
                labels,
                0,
            )
        )


def process_event(
    event,
):
    # State first, so later lifecycle events can recover
    # the task name from the UUID.
    state.event(
        event
    )

    event_type = str(
        event.get(
            "type",
            "",
        )
    )

    normalized = (
        EVENT_NAMES.get(
            event_type
        )
    )

    task_name = (
        _task_name(
            event
        )
    )


    if normalized:
        TASK_EVENTS.labels(
            event=normalized,
            task=task_name,
        ).inc()


        worker_name = (
            _event_worker_name(
                event
            )
        )

        worker, role, host = (
            _worker_labels(
                worker_name
            )
        )


        WORKER_TASK_EVENTS.labels(
            worker=worker,
            role=role,
            host=host,
            event=normalized,
            task=task_name,
        ).inc()


    if event_type == "task-succeeded":

        runtime = event.get(
            "runtime"
        )

        if isinstance(
            runtime,
            (
                int,
                float,
            ),
        ):
            TASK_RUNTIME.labels(
                task=task_name
            ).observe(
                float(runtime)
            )


    refresh_gauges()


def main():
    start_http_server(
        9808,
        addr="0.0.0.0",
    )

    logger.info(
        "BrainOn Celery metrics exporter "
        "listening on :9808"
    )


    while True:
        try:
            BROKER_CONNECTED.set(
                0
            )

            with app.connection() as connection:

                BROKER_CONNECTED.set(
                    1
                )

                receiver = (
                    app.events.Receiver(
                        connection,
                        handlers={
                            "*": process_event,
                        },
                    )
                )

                receiver.capture(
                    limit=None,
                    timeout=None,
                    wakeup=True,
                )


        except KeyboardInterrupt:
            raise


        except Exception:
            BROKER_CONNECTED.set(
                0
            )

            logger.exception(
                "Celery event monitor "
                "connection failed"
            )

            time.sleep(
                5
            )


if __name__ == "__main__":
    main()

from __future__ import annotations

import uuid
from datetime import timedelta

from django.db import connection, transaction
from django.utils import timezone

from apps.audit.models import AuditLog
from apps.audit.services.audit_event import (
    record_audit_event,
)
from apps.medication_safety.tasks import (
    sync_mfds_dur_data,
)
from apps.medication_safety.services.dur_rules import (
    SUPPORTED_RULE_KINDS,
)


DUR_SYNC_ACCEPT_LOCK_ID = 2026091101
DUR_SYNC_STALE_MINUTES = 60

TERMINAL_ACTIONS = {
    "DUR_SYNC_COMPLETED",
    "DUR_SYNC_FAILED",
}


class DurSyncInProgress(Exception):
    def __init__(self, task_id):
        self.task_id = task_id
        super().__init__(
            f"DUR sync already in progress: {task_id}"
        )


def _acquire_accept_lock():
    # PostgreSQL transaction-scoped advisory lock.
    # 동시에 들어온 DUR sync 요청의 acceptance 구간을 직렬화한다.
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT pg_advisory_xact_lock(%s)",
            [DUR_SYNC_ACCEPT_LOCK_ID],
        )


def _current_sync():
    cutoff = (
        timezone.now()
        - timedelta(
            minutes=DUR_SYNC_STALE_MINUTES,
        )
    )

    requested = (
        AuditLog.objects
        .filter(
            action="DUR_SYNC_REQUESTED",
            occurred_at__gte=cutoff,
        )
        .exclude(resource__isnull=True)
        .order_by("-occurred_at")
    )

    for log in requested:
        terminal_exists = (
            AuditLog.objects
            .filter(
                resource=log.resource,
                action__in=TERMINAL_ACTIONS,
            )
            .exists()
        )

        if not terminal_exists:
            return log

    return None


def _normalize_sync_types(sync_types):
    if not isinstance(
        sync_types,
        (list, tuple),
    ):
        raise ValueError(
            "DUR_SYNC_TYPES_INVALID"
        )

    normalized = list(
        dict.fromkeys(
            sync_types
        )
    )

    if not normalized:
        raise ValueError(
            "DUR_SYNC_TYPES_INVALID"
        )

    supported = set(
        SUPPORTED_RULE_KINDS
    )

    if any(
        value not in supported
        for value in normalized
    ):
        raise ValueError(
            "DUR_SYNC_TYPES_INVALID"
        )

    return normalized


def enqueue_dur_sync(
    *,
    request,
    sync_types,
):
    task_id = str(uuid.uuid4())
    requested_at = timezone.now()

    sync_types = _normalize_sync_types(
        sync_types
    )

    try:
        with transaction.atomic():
            _acquire_accept_lock()

            current = _current_sync()

            if current is not None:
                raise DurSyncInProgress(
                    current.resource
                )

            record_audit_event(
                source_service="BACKEND",
                action="DUR_SYNC_REQUESTED",
                resource_type="DURSync",
                resource_id=task_id,
                outcome="SUCCESS",
                request=request,
                after_json={
                    "task_id": task_id,
                    "sync_types": sync_types,
                },
            )

            sync_mfds_dur_data.apply_async(
                kwargs={
                    "sync_types": sync_types,
                    "dry_run": False,
                    "page_size": 100,
                    "request_id": (
                        request.request_id
                    ),
                    "actor_user_id": (
                        str(request.user.id)
                    ),
                },
                task_id=task_id,
            )

    except DurSyncInProgress:
        raise

    except Exception as exc:
        # Broker publish 등 acceptance 실패 기록.
        record_audit_event(
            source_service="BACKEND",
            action="DUR_SYNC_FAILED",
            resource_type="DURSync",
            resource_id=task_id,
            outcome="FAILURE",
            request=request,
            reason=type(exc).__name__,
            after_json={
                "task_id": task_id,
                "sync_types": sync_types,
                "phase": "ENQUEUE",
            },
        )

        raise

    return {
        "task_id": task_id,
        "status": "ACCEPTED",
        "requested_sync_types": (
            sync_types
        ),
        "requested_at": requested_at,
    }

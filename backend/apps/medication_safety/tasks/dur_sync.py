"""Celery tasks for MFDS DUR synchronization."""

import uuid
from io import StringIO

from celery import shared_task
from django.core.management import call_command
from django.contrib.auth import get_user_model

from apps.audit.services.audit_event import record_audit_event
from apps.medication_safety.models import (
    DrugIngredient,
    DURInteractionRule,
    DURDoseRule,
)


def _actor(actor_user_id):
    if not actor_user_id:
        return None

    try:
        user_id = uuid.UUID(str(actor_user_id))
    except (ValueError, TypeError, AttributeError):
        return None

    User = get_user_model()

    return User.objects.filter(
        pk=user_id
    ).first()


@shared_task(
    bind=True,
    name="medication_safety.sync_mfds_dur_data",
    ignore_result=True,
)
def sync_mfds_dur_data(
    self,
    *,
    kind="BOTH",
    dry_run=False,
    page_size=100,
    request_id=None,
    actor_user_id=None,
):
    """Run the already-validated sync_dur_rules command asynchronously."""

    if kind not in {
        "BOTH",
        "INTERACTION",
        "DOSE",
    }:
        raise ValueError("DUR_KIND_INVALID")

    if (
        type(page_size) is not int
        or not 1 <= page_size <= 100
    ):
        raise ValueError("DUR_PAGE_SIZE_INVALID")

    actor_user = _actor(actor_user_id)

    output = StringIO()

    try:
        call_command(
            "sync_dur_rules",
            kind=kind,
            dry_run=bool(dry_run),
            page_size=page_size,
            stdout=output,
        )

        if not dry_run:
            record_audit_event(
                source_service="CELERY",
                action="DUR_SYNC_COMPLETED",
                resource_type="DURSync",
                resource_id=self.request.id,
                outcome="SUCCESS",
                request_id=request_id,
                actor_user=actor_user,
                after_json={
                    "task_id": self.request.id,
                    "kind": kind,
                    "ingredient_count": (
                        DrugIngredient.objects.count()
                    ),
                    "interaction_rule_count": (
                        DURInteractionRule.objects.count()
                    ),
                    "dose_rule_count": (
                        DURDoseRule.objects.count()
                    ),
                },
            )

        return {
            "task_id": self.request.id,
            "status": "SUCCESS",
            "kind": kind,
            "dry_run": bool(dry_run),
        }

    except Exception as exc:
        if not dry_run:
            record_audit_event(
                source_service="CELERY",
                action="DUR_SYNC_FAILED",
                resource_type="DURSync",
                resource_id=self.request.id,
                outcome="FAILURE",
                request_id=request_id,
                actor_user=actor_user,
                reason=type(exc).__name__,
                after_json={
                    "task_id": self.request.id,
                    "kind": kind,
                },
            )

        raise

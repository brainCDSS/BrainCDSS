"""Celery tasks for MFDS DUR synchronization."""

import uuid
from io import StringIO

from celery import shared_task
from django.contrib.auth import get_user_model
from django.core.management import call_command

from apps.audit.services.audit_event import (
    record_audit_event,
)
from apps.medication_safety.models import (
    DrugIngredient,
    DURInteractionRule,
    DURDoseRule,
    DURDuplicateRule,
    DURAgeRule,
    DURElderlyRule,
    DURPregnancyRule,
    DURDurationRule,
)
from apps.medication_safety.services.dur_rules import (
    SUPPORTED_RULE_KINDS,
)


RULE_MODELS = {
    "INTERACTION": DURInteractionRule,
    "DOSE": DURDoseRule,
    "DUPLICATE": DURDuplicateRule,
    "AGE": DURAgeRule,
    "ELDERLY": DURElderlyRule,
    "PREGNANCY": DURPregnancyRule,
    "DURATION": DURDurationRule,
}


def _actor(actor_user_id):
    if not actor_user_id:
        return None

    try:
        user_id = uuid.UUID(
            str(actor_user_id)
        )
    except (
        ValueError,
        TypeError,
        AttributeError,
    ):
        return None

    User = get_user_model()

    return User.objects.filter(
        pk=user_id
    ).first()


def _normalize_sync_types(
    *,
    kind,
    sync_types,
):
    # New API path.
    if sync_types is not None:
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

        if any(
            value not in SUPPORTED_RULE_KINDS
            for value in normalized
        ):
            raise ValueError(
                "DUR_SYNC_TYPES_INVALID"
            )

        return normalized

    # Legacy task-call compatibility.
    if kind == "ALL":
        return list(
            SUPPORTED_RULE_KINDS
        )

    if kind == "BOTH":
        return [
            "INTERACTION",
            "DOSE",
        ]

    if kind in SUPPORTED_RULE_KINDS:
        return [kind]

    raise ValueError(
        "DUR_KIND_INVALID"
    )


def _command_options(sync_types):
    selected = set(
        sync_types
    )

    if selected == set(
        SUPPORTED_RULE_KINDS
    ):
        return {
            "kind": "ALL",
        }

    if selected == {
        "INTERACTION",
        "DOSE",
    }:
        return {
            "kind": "BOTH",
        }

    if len(sync_types) == 1:
        return {
            "kind": sync_types[0],
        }

    return {
        "kinds": sync_types,
    }


@shared_task(
    bind=True,
    name="medication_safety.sync_mfds_dur_data",
    ignore_result=True,
)
def sync_mfds_dur_data(
    self,
    *,
    kind="BOTH",
    sync_types=None,
    dry_run=False,
    page_size=100,
    request_id=None,
    actor_user_id=None,
):
    """Run validated MFDS DUR synchronization asynchronously."""

    if (
        type(page_size) is not int
        or not 1 <= page_size <= 100
    ):
        raise ValueError(
            "DUR_PAGE_SIZE_INVALID"
        )

    normalized_types = (
        _normalize_sync_types(
            kind=kind,
            sync_types=sync_types,
        )
    )

    command_options = (
        _command_options(
            normalized_types
        )
    )

    actor_user = _actor(
        actor_user_id
    )

    output = StringIO()

    try:
        call_command(
            "sync_dur_rules",
            dry_run=bool(dry_run),
            page_size=page_size,
            stdout=output,
            **command_options,
        )

        if not dry_run:
            rule_counts = {
                rule_kind: (
                    model.objects.count()
                )
                for rule_kind, model
                in RULE_MODELS.items()
            }

            record_audit_event(
                source_service="CELERY",
                action="DUR_SYNC_COMPLETED",
                resource_type="DURSync",
                resource_id=self.request.id,
                outcome="SUCCESS",
                request_id=request_id,
                actor_user=actor_user,
                after_json={
                    "task_id": (
                        self.request.id
                    ),
                    "sync_types": (
                        normalized_types
                    ),
                    "ingredient_count": (
                        DrugIngredient
                        .objects
                        .count()
                    ),
                    # Legacy fields retained.
                    "interaction_rule_count": (
                        rule_counts[
                            "INTERACTION"
                        ]
                    ),
                    "dose_rule_count": (
                        rule_counts[
                            "DOSE"
                        ]
                    ),
                    "rule_counts": (
                        rule_counts
                    ),
                },
            )

        return {
            "task_id": (
                self.request.id
            ),
            "status": "SUCCESS",
            "kind": kind,
            "sync_types": (
                normalized_types
            ),
            "dry_run": bool(
                dry_run
            ),
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
                    "task_id": (
                        self.request.id
                    ),
                    "sync_types": (
                        normalized_types
                    ),
                },
            )

        raise

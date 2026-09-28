from __future__ import annotations

from django.db.models import (
    CharField,
    Value,
)
from django.db.models.functions import (
    Cast,
    Replace,
)

from apps.audit.models import AuditLog
from apps.common.tracking import (
    tracking_code_prefix,
)


def audit_log_queryset(
    filters: dict,
):
    qs = (
        AuditLog.objects
        .select_related("actor_user")
        .all()
        .order_by(
            "-occurred_at",
            "-created_at",
        )
    )

    mapping = {
        "actor_user_id":
            "actor_user_id",
        "actor_login_id":
            "actor_login",
        "actor_role_code":
            "actor_role_code",
        "patient_id":
            "patient",
        "resource_type":
            "resource_type",
        "resource_id":
            "resource",
        "action":
            "action",
        "outcome":
            "outcome",
        "request_id":
            "request",
    }

    for (
        api_name,
        orm_name,
    ) in mapping.items():

        value = filters.get(
            api_name
        )

        if value not in (
            None,
            "",
        ):
            qs = qs.filter(
                **{
                    orm_name:
                        value,
                }
            )

    tracking_code = filters.get(
        "tracking_code"
    )

    if tracking_code:
        prefix = (
            tracking_code_prefix(
                tracking_code
            )
        )

        if prefix:
            qs = (
                qs.annotate(
                    _request_compact=Replace(
                        Cast(
                            "request",
                            output_field=CharField(),
                        ),
                        Value("-"),
                        Value(""),
                    )
                )
                .filter(
                    _request_compact__istartswith=(
                        prefix
                    )
                )
            )

    occurred_from = filters.get(
        "occurred_from"
    )

    occurred_to = filters.get(
        "occurred_to"
    )

    if occurred_from is not None:
        qs = qs.filter(
            occurred_at__gte=(
                occurred_from
            )
        )

    if occurred_to is not None:
        qs = qs.filter(
            occurred_at__lte=(
                occurred_to
            )
        )

    return qs


def get_audit_log(
    audit_id,
):
    try:
        return (
            AuditLog.objects
            .select_related(
                "actor_user"
            )
            .get(
                pk=audit_id
            )
        )

    except AuditLog.DoesNotExist:
        return None

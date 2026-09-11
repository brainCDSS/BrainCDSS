from django.db import transaction
from django.utils import timezone

from apps.audit.services.audit_event import (
    record_audit_event,
)
from apps.common.models import OutboxEvent
from apps.imaging.models import (
    ImagingOrder,
    ImagingOrderStatusHistory,
)


def _outbox(
    *,
    event_type,
    order,
    payload,
):
    return OutboxEvent.objects.create(
        event_type=event_type,
        aggregate_type="ImagingOrder",
        aggregate=str(order.id),
        payload=payload,
        status="PENDING",
        retry_count=0,
        published_at=None,
        created_at=timezone.now(),
    )


@transaction.atomic
def create_imaging_order(
    *,
    encounter,
    user,
    data,
    request,
):
    now = timezone.now()

    order = ImagingOrder.objects.create(
        patient=encounter.patient,
        encounter=encounter,
        accession_number=None,
        procedure_code=data["procedure_code"],
        procedure_name=data["procedure_name"],
        modality=data["modality"],
        priority=data["priority"],
        status="PLACED",
        reason=data["reason"],
        requested_by=user,
        requested_at=now,
        scheduled_at=None,
        created_at=now,
        updated_at=now,
    )

    ImagingOrderStatusHistory.objects.create(
        imaging_order=order,
        previous_status=None,
        status="PLACED",
        occurred_at=now,
        reason=data["reason"],
        recorded_by=user,
    )

    record_audit_event(
        source_service="imaging",
        action="CREATE_IMAGING_ORDER",
        resource_type="ImagingOrder",
        resource_id=order.id,
        patient_id=order.patient_id,
        outcome="SUCCESS",
        request=request,
        after_json={
            "encounter_id":
                str(order.encounter_id),
            "status": "PLACED",
            "modality": order.modality,
            "priority": order.priority,
        },
    )

    _outbox(
        event_type="imaging.order.placed.v1",
        order=order,
        payload={
            "order_id": str(order.id),
            "encounter_id":
                str(order.encounter_id),
            "patient_id":
                str(order.patient_id),
            "status": order.status,
        },
    )

    return order


@transaction.atomic
def update_imaging_order(
    *,
    order_id,
    user,
    data,
    request,
):
    order = (
        ImagingOrder.objects
        .select_for_update()
        .select_related("patient")
        .get(pk=order_id)
    )

    before = {
        "priority": order.priority,
        "reason": order.reason,
        "scheduled_at": (
            order.scheduled_at.isoformat()
            if order.scheduled_at
            else None
        ),
        "status": order.status,
    }

    previous_status = order.status

    if "priority" in data:
        order.priority = data["priority"]

    if "reason" in data:
        order.reason = data["reason"]

    if "scheduled_at" in data:
        order.scheduled_at = data["scheduled_at"]

        if (
            previous_status == "PLACED"
            and data["scheduled_at"] is not None
        ):
            order.status = "SCHEDULED"

    order.updated_at = timezone.now()

    order.save(
        update_fields=[
            "priority",
            "reason",
            "scheduled_at",
            "status",
            "updated_at",
        ]
    )

    if order.status != previous_status:
        ImagingOrderStatusHistory.objects.create(
            imaging_order=order,
            previous_status=previous_status,
            status=order.status,
            occurred_at=order.updated_at,
            reason=order.reason,
            recorded_by=user,
        )

    record_audit_event(
        source_service="imaging",
        action="UPDATE_IMAGING_ORDER",
        resource_type="ImagingOrder",
        resource_id=order.id,
        patient_id=order.patient_id,
        outcome="SUCCESS",
        request=request,
        before_json=before,
        after_json={
            "priority": order.priority,
            "reason": order.reason,
            "scheduled_at": (
                order.scheduled_at.isoformat()
                if order.scheduled_at
                else None
            ),
            "status": order.status,
        },
    )

    _outbox(
        event_type="imaging.order.updated.v1",
        order=order,
        payload={
            "order_id": str(order.id),
            "status": order.status,
            "priority": order.priority,
        },
    )

    return order


@transaction.atomic
def cancel_imaging_order(
    *,
    order_id,
    user,
    reason,
    request,
):
    order = (
        ImagingOrder.objects
        .select_for_update()
        .select_related("patient")
        .get(pk=order_id)
    )

    previous_status = order.status
    now = timezone.now()

    order.status = "CANCELLED"
    order.updated_at = now

    order.save(
        update_fields=[
            "status",
            "updated_at",
        ]
    )

    history = (
        ImagingOrderStatusHistory.objects.create(
            imaging_order=order,
            previous_status=previous_status,
            status="CANCELLED",
            occurred_at=now,
            reason=reason,
            recorded_by=user,
        )
    )

    record_audit_event(
        source_service="imaging",
        action="CANCEL_IMAGING_ORDER",
        resource_type="ImagingOrder",
        resource_id=order.id,
        patient_id=order.patient_id,
        outcome="SUCCESS",
        request=request,
        before_json={
            "status": previous_status,
        },
        after_json={
            "status": "CANCELLED",
            "reason": reason,
        },
    )

    _outbox(
        event_type="imaging.order.cancelled.v1",
        order=order,
        payload={
            "order_id": str(order.id),
            "status": "CANCELLED",
            "reason": reason,
        },
    )

    return order, history

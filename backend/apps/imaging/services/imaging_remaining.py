from __future__ import annotations

import uuid

from django.db import transaction
from django.utils import timezone

from apps.ai_analysis.models import (
    AIAnalysis,
    AIAnalysisResult,
    AIResultArtifact,
)
from apps.audit.services.audit_event import (
    record_audit_event,
)
from apps.common.models import OutboxEvent
from apps.imaging.models import (
    DicomObjectReference,
    DicomTransferJob,
    ImagingOrder,
    ImagingOrderStatusHistory,
    ImagingReconciliationTask,
    ImagingStudy,
    SeriesReference,
)
from apps.integrations.models import (
    IntegrationTransaction,
)
from apps.patients.models import Patient


def _outbox(
    event_type,
    aggregate_type,
    aggregate_id,
    payload,
):
    return OutboxEvent.objects.create(
        event_type=event_type,
        aggregate_type=aggregate_type,
        aggregate=str(aggregate_id),
        payload=payload,
        status="PENDING",
        retry_count=0,
        published_at=None,
        created_at=timezone.now(),
    )


def _integration(
    *,
    direction,
    source,
    target,
    message_type,
    external_message,
    trace,
    status,
    error_code=None,
):
    now = timezone.now()

    return IntegrationTransaction.objects.create(
        direction=direction,
        standard="REST",
        source_system=source,
        target_system=target,
        message_type=message_type,
        external_message=str(
            external_message
        ),
        trace=str(trace)[:64],
        status=status,
        attempt_count=1,
        error_code=error_code,
        started_at=now,
        completed_at=(
            now
            if status
            in {"SUCCESS", "FAILED"}
            else None
        ),
    )


def apply_orthanc_snapshot(
    *,
    snapshot,
    existing_study=None,
):
    uid = snapshot[
        "study_instance_uid"
    ]

    if not uid:
        raise ValueError(
            "STUDY_INSTANCE_UID_MISSING"
        )

    accession = snapshot[
        "accession_number"
    ]

    patient_no = snapshot[
        "patient_no"
    ]

    order = None

    if accession:
        order = (
            ImagingOrder.objects
            .select_related("patient")
            .filter(
                accession_number=accession
            )
            .order_by(
                "-requested_at"
            )
            .first()
        )

    patient = None

    if patient_no:
        patient = (
            Patient.objects
            .filter(
                patient_no=patient_no
            )
            .first()
        )

    if (
        order is not None
        and patient is None
    ):
        patient = order.patient

    match_ok = bool(
        order is not None
        and patient is not None
        and order.patient_id
        == patient.id
    )

    study = existing_study

    if study is None:
        study = (
            ImagingStudy.objects
            .filter(
                study_instance_uid=uid
            )
            .first()
        )

    if study is None:
        study = (
            ImagingStudy.objects
            .filter(
                orthanc_study=
                    snapshot[
                        "orthanc_study_id"
                    ]
            )
            .first()
        )

    now = timezone.now()

    if study is None:
        study = ImagingStudy(
            study_instance_uid=uid,
            created_at=now,
        )

    study.orthanc_study = (
        snapshot[
            "orthanc_study_id"
        ]
    )

    study.accession_number = (
        accession
        or study.accession_number
        or ""
    )

    study.study_datetime = (
        snapshot["study_datetime"]
        or study.study_datetime
    )

    study.study_description = (
        snapshot[
            "study_description"
        ]
        or study.study_description
        or ""
    )

    modalities = sorted({
        row["modality"]
        for row in snapshot["series"]
        if row["modality"]
    })

    study.modalities = modalities

    study.series_count = len(
        snapshot["series"]
    )

    study.instance_count = sum(
        row["instance_count"]
        for row in snapshot["series"]
    )

    all_complete = bool(
        snapshot["series"]
    ) and all(
        row["is_complete"]
        for row in snapshot["series"]
    )

    if match_ok:
        study.patient = patient
        study.imaging_order = order

        study.status = (
            "AVAILABLE"
            if all_complete
            else "INCOMPLETE"
        )

    else:
        study.patient = patient
        study.imaging_order = None
        study.status = "UNMATCHED"

    study.last_synced_at = now
    study.updated_at = now
    study.save()

    for row in snapshot["series"]:
        if not row[
            "series_instance_uid"
        ]:
            continue

        SeriesReference.objects.update_or_create(
            series_instance_uid=
                row[
                    "series_instance_uid"
                ],
            defaults={
                "study": study,
                "orthanc_series":
                    row[
                        "orthanc_series_id"
                    ],
                "series_number":
                    row[
                        "series_number"
                    ],
                "modality":
                    row["modality"],
                "series_description":
                    row[
                        "series_description"
                    ],
                "protocol_name":
                    row[
                        "protocol_name"
                    ],
                "instance_count":
                    row[
                        "instance_count"
                    ],
                "frame_count":
                    row[
                        "frame_count"
                    ],
                "rows":
                    row["rows"],
                "columns":
                    row["columns"],
                "slice_thickness":
                    row[
                        "slice_thickness"
                    ],
                "is_complete":
                    row[
                        "is_complete"
                    ],
                "is_ai_eligible":
                    row[
                        "is_ai_eligible"
                    ],
                "ai_exclusion_reason":
                    row[
                        "ai_exclusion_reason"
                    ],
                "updated_at": now,
                "created_at": now,
            },
        )

    if study.status == "UNMATCHED":
        ImagingReconciliationTask.objects.get_or_create(
            study=study,
            issue_code="UNMATCHED_STUDY",
            status="OPEN",
            defaults={
                "imaging_order": order,
                "resolved_patient": None,
                "resolution_note": "",
                "resolved_by": None,
                "detected_at": now,
                "resolved_at": None,
            },
        )

    return study


ALLOWED_TRANSITIONS = {
    "PLACED": {
        "SCHEDULED",
        "IN_PROGRESS",
        "HELD",
        "CANCELLED",
    },
    "SCHEDULED": {
        "IN_PROGRESS",
        "HELD",
        "CANCELLED",
    },
    "HELD": {
        "SCHEDULED",
        "IN_PROGRESS",
        "CANCELLED",
    },
    "IN_PROGRESS": {
        "HELD",
        "COMPLETED",
    },
    "COMPLETED": set(),
    "CANCELLED": set(),
}


@transaction.atomic
def apply_status_event(
    *,
    order_id,
    data,
    idempotency_key,
    service_name,
):
    existing = (
        IntegrationTransaction.objects
        .filter(
            message_type=
                "IMAGING_ORDER_STATUS_EVENT",
            external_message=
                idempotency_key,
            status="SUCCESS",
        )
        .first()
    )

    order = (
        ImagingOrder.objects
        .select_for_update()
        .select_related("patient")
        .filter(pk=order_id)
        .first()
    )

    if order is None:
        return None, None, False

    if existing is not None:
        study = (
            ImagingStudy.objects
            .filter(
                imaging_order=order
            )
            .first()
        )

        return (
            order,
            study,
            True,
        )

    previous = order.status
    new_status = data["status"]

    if new_status not in (
        ALLOWED_TRANSITIONS.get(
            previous,
            set(),
        )
    ):
        raise ValueError(
            "INVALID_STATUS_TRANSITION"
        )

    accession = data.get(
        "accession_number"
    )

    if accession:
        order.accession_number = (
            accession
        )

    if new_status == "SCHEDULED":
        order.scheduled_at = (
            data["occurred_at"]
        )

    order.status = new_status
    order.updated_at = timezone.now()

    order.save(
        update_fields=[
            "accession_number",
            "scheduled_at",
            "status",
            "updated_at",
        ]
    )

    ImagingOrderStatusHistory.objects.create(
        imaging_order=order,
        previous_status=previous,
        status=new_status,
        occurred_at=data["occurred_at"],
        reason=data["reason"],
        recorded_by=None,
    )

    study = None

    uid = data.get(
        "study_instance_uid"
    )

    if uid:
        study = (
            ImagingStudy.objects
            .select_for_update()
            .filter(
                study_instance_uid=uid
            )
            .first()
        )

        if study is not None:
            if (
                study.patient_id
                not in (
                    None,
                    order.patient_id,
                )
                or study.imaging_order_id
                not in (
                    None,
                    order.id,
                )
            ):
                raise ValueError(
                    "STUDY_ORDER_MISMATCH"
                )

            study.patient = (
                order.patient
            )
            study.imaging_order = order
            study.accession_number = (
                accession
                or order.accession_number
                or study.accession_number
            )
            study.updated_at = timezone.now()
            study.save(
                update_fields=[
                    "patient",
                    "imaging_order",
                    "accession_number",
                    "updated_at",
                ]
            )

        elif new_status == "COMPLETED":
            now = timezone.now()

            study = ImagingStudy.objects.create(
                patient=order.patient,
                imaging_order=order,
                study_instance_uid=uid,
                accession_number=(
                    accession
                    or order.accession_number
                    or ""
                ),
                orthanc_study=None,
                study_datetime=
                    data["occurred_at"],
                modalities=[
                    order.modality
                ],
                study_description=
                    order.procedure_name,
                series_count=0,
                instance_count=0,
                status="RECEIVING",
                last_synced_at=None,
                created_at=now,
                updated_at=now,
            )

    if (
        new_status == "COMPLETED"
        and study is None
    ):
        study = (
            ImagingStudy.objects
            .filter(
                imaging_order=order
            )
            .first()
        )

        if study is None:
            raise ValueError(
                "COMPLETED_STUDY_REQUIRED"
            )

    _integration(
        direction="INBOUND",
        source=service_name,
        target="BrainOn",
        message_type=
            "IMAGING_ORDER_STATUS_EVENT",
        external_message=
            idempotency_key,
        trace=idempotency_key,
        status="SUCCESS",
    )

    _outbox(
        "imaging.order.status_changed.v1",
        "ImagingOrder",
        order.id,
        {
            "order_id":
                str(order.id),
            "previous_status":
                previous,
            "status":
                new_status,
            "study_id": (
                str(study.id)
                if study
                else None
            ),
        },
    )

    return order, study, False


@transaction.atomic
def resolve_reconciliation(
    *,
    task_id,
    data,
    user,
    request,
):
    task = (
        ImagingReconciliationTask.objects
        .select_for_update()
        .select_related("study")
        .filter(pk=task_id)
        .first()
    )

    if task is None:
        return None

    if task.status not in {
        "OPEN",
        "IN_REVIEW",
    }:
        raise ValueError(
            "TASK_INVALID_STATE"
        )

    now = timezone.now()

    if data["action"] == "IGNORE":
        task.status = "IGNORED"
        task.resolution_note = (
            data["resolution_note"]
        )
        task.resolved_by = user
        task.resolved_at = now

    else:
        patient = (
            Patient.objects
            .filter(
                pk=data["patient_id"]
            )
            .first()
        )

        order = (
            ImagingOrder.objects
            .select_related("patient")
            .filter(
                pk=data[
                    "imaging_order_id"
                ]
            )
            .first()
        )

        if (
            patient is None
            or order is None
            or order.patient_id
            != patient.id
        ):
            raise ValueError(
                "RECONCILIATION_MISMATCH"
            )

        study = task.study

        if (
            study.accession_number
            and order.accession_number
            and study.accession_number
            != order.accession_number
        ):
            raise ValueError(
                "RECONCILIATION_MISMATCH"
            )

        study.patient = patient
        study.imaging_order = order

        series = list(
            SeriesReference.objects
            .filter(study=study)
        )

        study.status = (
            "AVAILABLE"
            if (
                series
                and all(
                    item.is_complete
                    for item in series
                )
            )
            else "INCOMPLETE"
        )

        study.updated_at = now

        study.save(
            update_fields=[
                "patient",
                "imaging_order",
                "status",
                "updated_at",
            ]
        )

        task.imaging_order = order
        task.resolved_patient = patient
        task.status = "RESOLVED"
        task.resolution_note = (
            data["resolution_note"]
        )
        task.resolved_by = user
        task.resolved_at = now

    task.save(
        update_fields=[
            "imaging_order",
            "resolved_patient",
            "status",
            "resolution_note",
            "resolved_by",
            "resolved_at",
        ]
    )

    record_audit_event(
        source_service="imaging",
        action="RESOLVE_IMAGING_RECONCILIATION",
        resource_type=
            "ImagingReconciliationTask",
        resource_id=task.id,
        patient_id=(
            task.resolved_patient_id
            or task.study.patient_id
        ),
        outcome="SUCCESS",
        request=request,
        after_json={
            "action":
                data["action"],
            "status":
                task.status,
        },
    )

    _outbox(
        "imaging.reconciliation.resolved.v1",
        "ImagingReconciliationTask",
        task.id,
        {
            "task_id":
                str(task.id),
            "study_id":
                str(task.study_id),
            "status":
                task.status,
        },
    )

    return task


@transaction.atomic
def retry_transfer_job(
    *,
    job_id,
    reason,
    user,
    request,
):
    job = (
        DicomTransferJob.objects
        .select_for_update()
        .filter(pk=job_id)
        .first()
    )

    if job is None:
        return None

    if job.status != "FAILED":
        raise ValueError(
            "TRANSFER_JOB_NOT_RETRYABLE"
        )

    job.status = "RETRYING"
    job.attempt_count += 1
    job.last_error_code = None
    job.started_at = None
    job.completed_at = None
    job.trace = str(uuid.uuid4())

    job.save(
        update_fields=[
            "status",
            "attempt_count",
            "last_error_code",
            "started_at",
            "completed_at",
            "trace",
        ]
    )

    record_audit_event(
        source_service="imaging",
        action="RETRY_DICOM_TRANSFER",
        resource_type="DicomTransferJob",
        resource_id=job.id,
        patient_id=job.study.patient_id,
        outcome="SUCCESS",
        request=request,
        reason=reason,
        after_json={
            "status": "RETRYING",
            "attempt_count":
                job.attempt_count,
        },
    )

    _outbox(
        "dicom.transfer.retry_requested.v1",
        "DicomTransferJob",
        job.id,
        {
            "job_id": str(job.id),
            "trace_id": job.trace,
            "reason": reason,
        },
    )

    return job


@transaction.atomic
def register_dicom_stow(
    *,
    data,
    service_name,
    trace,
):
    analysis = (
        AIAnalysis.objects
        .select_related("study")
        .filter(
            pk=data["analysis_id"]
        )
        .first()
    )

    result = (
        AIAnalysisResult.objects
        .filter(
            pk=data["result_id"]
        )
        .first()
    )

    if (
        analysis is None
        or result is None
        or result.analysis_id
        != analysis.id
        or analysis.status
        != "COMPLETED"
    ):
        raise ValueError(
            "DICOM_CONTRACT_INVALID"
        )

    if DicomObjectReference.objects.filter(
        sop_instance_uid=
            data["sop_instance_uid"]
    ).exists():
        raise ValueError(
            "SOP_INSTANCE_DUPLICATE"
        )

    series = None

    if data.get("series_id"):
        series = (
            SeriesReference.objects
            .filter(
                pk=data["series_id"]
            )
            .first()
        )

        if (
            series is None
            or series.study_id
            != analysis.study_id
            or not series.is_complete
        ):
            raise ValueError(
                "SPATIAL_METADATA_INVALID"
            )

    object_type = (
        "SEG"
        if data["artifact_type"]
        == "DICOM_SEG"
        else "SR"
    )

    now = timezone.now()

    dicom = DicomObjectReference.objects.create(
        study=analysis.study,
        series=series,
        object_type=object_type,
        sop_instance_uid=
            data["sop_instance_uid"],
        orthanc_instance=None,
        storage_status="PENDING",
        created_at=now,
    )

    artifact = AIResultArtifact.objects.create(
        result=result,
        artifact_type=
            data["artifact_type"],
        uri=data["artifact_uri"],
        dicom_object_reference=dicom,
        status="PENDING",
        created_at=now,
    )

    job = DicomTransferJob.objects.create(
        study=analysis.study,
        analysis=analysis,
        transfer_type="STOW",
        target_system=
            data["target_system"],
        status="QUEUED",
        attempt_count=0,
        last_error_code=None,
        started_at=None,
        completed_at=None,
        trace=str(trace)[:64],
    )

    _integration(
        direction="OUTBOUND",
        source="BrainOn-AI",
        target=data[
            "target_system"
        ],
        message_type="DICOM_STOW",
        external_message=
            data["sop_instance_uid"],
        trace=trace,
        status="SUCCESS",
    )

    _outbox(
        "dicom.artifact.stow_requested.v1",
        "DicomTransferJob",
        job.id,
        {
            "transfer_job_id":
                str(job.id),
            "artifact_id":
                str(artifact.id),
            "dicom_object_reference_id":
                str(dicom.id),
            "target_system":
                data["target_system"],
        },
    )

    return job, artifact, dicom

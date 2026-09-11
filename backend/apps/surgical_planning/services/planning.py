"""Transactional write services for surgical planning."""

from django.db import transaction
from django.utils import timezone

from apps.ai_analysis.models import AIAnalysis
from apps.audit.services.audit_event import (
    record_audit_event,
)
from apps.clinical_records.models import Encounter
from apps.imaging.models import ImagingStudy
from apps.patients.models import Patient
from apps.surgical_planning.models import (
    SurgicalPlan,
    SurgicalPlanClip,
    SurgicalPlanMessage,
    SurgicalPlanStatus,
)


class SurgicalPlanningError(Exception):
    def __init__(
        self,
        code,
        detail,
        status_code=400,
    ):
        super().__init__(detail)
        self.code = code
        self.detail = detail
        self.status_code = status_code


TERMINAL_STATUSES = {
    SurgicalPlanStatus.CONFIRMED,
    SurgicalPlanStatus.CANCELLED,
}


def _plan_audit_snapshot(plan):
    return {
        "status": plan.status,
        "version": plan.version,
        "study_id": str(plan.study_id),
        "encounter_id": (
            str(plan.encounter_id)
            if plan.encounter_id
            else None
        ),
        "ai_analysis_id": (
            str(plan.ai_analysis_id)
            if plan.ai_analysis_id
            else None
        ),
    }


def _ensure_editable(plan):
    if plan.status in TERMINAL_STATUSES:
        raise SurgicalPlanningError(
            "SURGICAL_PLAN_NOT_EDITABLE",
            (
                "CONFIRMED or CANCELLED surgical "
                "plan is not editable."
            ),
            409,
        )


def _load_related_objects(
    *,
    patient_id,
    encounter_id,
    study_id,
    ai_analysis_id,
):
    try:
        patient = Patient.objects.get(
            pk=patient_id
        )
    except Patient.DoesNotExist as exc:
        raise SurgicalPlanningError(
            "PATIENT_NOT_FOUND",
            "Patient not found.",
            404,
        ) from exc

    try:
        # The Study row is locked so concurrent create requests
        # for the same study cannot create two active plans.
        study = (
            ImagingStudy.objects
            .select_for_update()
            .select_related("imaging_order")
            .get(pk=study_id)
        )
    except ImagingStudy.DoesNotExist as exc:
        raise SurgicalPlanningError(
            "IMAGING_STUDY_NOT_FOUND",
            "Imaging study not found.",
            404,
        ) from exc

    if study.patient_id is None:
        raise SurgicalPlanningError(
            "SURGICAL_PLAN_STUDY_PATIENT_UNRESOLVED",
            (
                "Imaging study is not mapped "
                "to a patient."
            ),
            409,
        )

    if study.patient_id != patient.id:
        raise SurgicalPlanningError(
            "SURGICAL_PLAN_PATIENT_STUDY_MISMATCH",
            (
                "Imaging study does not belong "
                "to the selected patient."
            ),
            400,
        )

    encounter = None

    if encounter_id:
        try:
            encounter = Encounter.objects.get(
                pk=encounter_id
            )
        except Encounter.DoesNotExist as exc:
            raise SurgicalPlanningError(
                "ENCOUNTER_NOT_FOUND",
                "Encounter not found.",
                404,
            ) from exc

        if encounter.patient_id != patient.id:
            raise SurgicalPlanningError(
                "SURGICAL_PLAN_PATIENT_ENCOUNTER_MISMATCH",
                (
                    "Encounter does not belong "
                    "to the selected patient."
                ),
                400,
            )

        if (
            study.imaging_order_id
            and study.imaging_order.encounter_id
            != encounter.id
        ):
            raise SurgicalPlanningError(
                "SURGICAL_PLAN_STUDY_ENCOUNTER_MISMATCH",
                (
                    "Imaging study order does not "
                    "belong to the selected encounter."
                ),
                400,
            )

    analysis = None

    if ai_analysis_id:
        try:
            analysis = AIAnalysis.objects.get(
                pk=ai_analysis_id
            )
        except AIAnalysis.DoesNotExist as exc:
            raise SurgicalPlanningError(
                "AI_ANALYSIS_NOT_FOUND",
                "AI analysis not found.",
                404,
            ) from exc

        if analysis.study_id != study.id:
            raise SurgicalPlanningError(
                "SURGICAL_PLAN_AI_STUDY_MISMATCH",
                (
                    "AI analysis does not belong "
                    "to the selected study."
                ),
                400,
            )

    return (
        patient,
        encounter,
        study,
        analysis,
    )


@transaction.atomic
def create_surgical_plan(
    *,
    user,
    patient_id,
    study_id,
    encounter_id=None,
    ai_analysis_id=None,
    treatment_type="",
    memo="",
    request=None,
):
    (
        patient,
        encounter,
        study,
        analysis,
    ) = _load_related_objects(
        patient_id=patient_id,
        encounter_id=encounter_id,
        study_id=study_id,
        ai_analysis_id=ai_analysis_id,
    )

    existing = (
        SurgicalPlan.objects
        .filter(
            patient_id=patient.id,
            study_id=study.id,
        )
        .exclude(
            status=SurgicalPlanStatus.CANCELLED
        )
        .order_by("-updated_at")
        .first()
    )

    if existing is not None:
        raise SurgicalPlanningError(
            "SURGICAL_PLAN_ALREADY_EXISTS",
            (
                "An active surgical plan already "
                "exists for this patient and study."
            ),
            409,
        )

    plan = SurgicalPlan.objects.create(
        patient=patient,
        encounter=encounter,
        study=study,
        ai_analysis=analysis,
        treatment_type=treatment_type,
        memo=memo,
        created_by=user,
    )

    record_audit_event(
        source_service="surgical_planning",
        action="SURGICAL_PLAN_CREATED",
        resource_type="SurgicalPlan",
        resource_id=plan.id,
        patient_id=plan.patient_id,
        outcome="SUCCESS",
        request=request,
        after_json=_plan_audit_snapshot(plan),
    )

    return plan


@transaction.atomic
def update_surgical_plan(
    *,
    planning_id,
    expected_version,
    values,
    status=None,
    user=None,
    request=None,
    audit_action="SURGICAL_PLAN_UPDATED",
):
    try:
        plan = (
            SurgicalPlan.objects
            .select_for_update()
            .get(pk=planning_id)
        )
    except SurgicalPlan.DoesNotExist as exc:
        raise SurgicalPlanningError(
            "SURGICAL_PLAN_NOT_FOUND",
            "Surgical plan not found.",
            404,
        ) from exc

    if plan.version != expected_version:
        raise SurgicalPlanningError(
            "SURGICAL_PLAN_VERSION_CONFLICT",
            (
                "Surgical plan was modified by "
                "another request."
            ),
            409,
        )

    _ensure_editable(plan)

    before = _plan_audit_snapshot(plan)

    for field in (
        "treatment_type",
        "memo",
    ):
        if field in values:
            setattr(
                plan,
                field,
                values[field],
            )

    if status is not None:
        plan.status = status

    if status == SurgicalPlanStatus.CONFIRMED:
        plan.finalized_by = user
        plan.finalized_at = timezone.now()

    plan.version += 1
    plan.save()

    record_audit_event(
        source_service="surgical_planning",
        action=audit_action,
        resource_type="SurgicalPlan",
        resource_id=plan.id,
        patient_id=plan.patient_id,
        outcome="SUCCESS",
        request=request,
        before_json=before,
        after_json=_plan_audit_snapshot(plan),
    )

    return plan


@transaction.atomic
def create_surgical_plan_clip(
    *,
    planning_id,
    values,
    request=None,
):
    try:
        plan = (
            SurgicalPlan.objects
            .select_for_update()
            .get(pk=planning_id)
        )
    except SurgicalPlan.DoesNotExist as exc:
        raise SurgicalPlanningError(
            "SURGICAL_PLAN_NOT_FOUND",
            "Surgical plan not found.",
            404,
        ) from exc

    _ensure_editable(plan)

    clip = SurgicalPlanClip.objects.create(
        planning=plan,
        **values,
    )

    record_audit_event(
        source_service="surgical_planning",
        action="SURGICAL_PLAN_CLIP_CREATED",
        resource_type="SurgicalPlanClip",
        resource_id=clip.id,
        patient_id=plan.patient_id,
        outcome="SUCCESS",
        request=request,
        after_json={
            "planning_id": str(plan.id),
            "clip_id": clip.clip_id,
        },
    )

    return clip


@transaction.atomic
def update_surgical_plan_clip(
    *,
    planning_id,
    clip_id,
    values,
    request=None,
):
    try:
        clip = (
            SurgicalPlanClip.objects
            .select_for_update()
            .select_related("planning")
            .get(
                pk=clip_id,
                planning_id=planning_id,
            )
        )
    except SurgicalPlanClip.DoesNotExist as exc:
        raise SurgicalPlanningError(
            "SURGICAL_PLAN_CLIP_NOT_FOUND",
            "Surgical plan clip not found.",
            404,
        ) from exc

    _ensure_editable(clip.planning)

    changed_fields = []

    for field, value in values.items():
        setattr(clip, field, value)
        changed_fields.append(field)

    if changed_fields:
        clip.save()

    record_audit_event(
        source_service="surgical_planning",
        action="SURGICAL_PLAN_CLIP_UPDATED",
        resource_type="SurgicalPlanClip",
        resource_id=clip.id,
        patient_id=clip.planning.patient_id,
        outcome="SUCCESS",
        request=request,
        after_json={
            "planning_id": str(clip.planning_id),
        },
    )

    return clip


@transaction.atomic
def delete_surgical_plan_clip(
    *,
    planning_id,
    clip_id,
    request=None,
):
    try:
        clip = (
            SurgicalPlanClip.objects
            .select_for_update()
            .select_related("planning")
            .get(
                pk=clip_id,
                planning_id=planning_id,
            )
        )
    except SurgicalPlanClip.DoesNotExist as exc:
        raise SurgicalPlanningError(
            "SURGICAL_PLAN_CLIP_NOT_FOUND",
            "Surgical plan clip not found.",
            404,
        ) from exc

    plan = clip.planning

    _ensure_editable(plan)

    resource_id = clip.id
    clip_code = clip.clip_id

    record_audit_event(
        source_service="surgical_planning",
        action="SURGICAL_PLAN_CLIP_DELETED",
        resource_type="SurgicalPlanClip",
        resource_id=resource_id,
        patient_id=plan.patient_id,
        outcome="SUCCESS",
        request=request,
        before_json={
            "planning_id": str(plan.id),
            "clip_id": clip_code,
        },
    )

    clip.delete()


@transaction.atomic
def create_surgical_plan_message(
    *,
    planning_id,
    sender,
    values,
    request=None,
):
    try:
        plan = (
            SurgicalPlan.objects
            .select_for_update()
            .get(pk=planning_id)
        )
    except SurgicalPlan.DoesNotExist as exc:
        raise SurgicalPlanningError(
            "SURGICAL_PLAN_NOT_FOUND",
            "Surgical plan not found.",
            404,
        ) from exc

    message = SurgicalPlanMessage.objects.create(
        planning=plan,
        sender=sender,
        **values,
    )

    # Do not put clinical message content or viewer_state
    # into AuditLog snapshot.
    record_audit_event(
        source_service="surgical_planning",
        action="SURGICAL_PLAN_MESSAGE_CREATED",
        resource_type="SurgicalPlanMessage",
        resource_id=message.id,
        patient_id=plan.patient_id,
        outcome="SUCCESS",
        request=request,
        after_json={
            "planning_id": str(plan.id),
            "sender_id": str(sender.id),
        },
    )

    return message

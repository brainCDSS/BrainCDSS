"""Transactional write services for surgical planning."""

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.ai_analysis.models import AIAnalysis
from apps.clinical_records.models import Encounter
from apps.imaging.models import ImagingStudy
from apps.patients.models import Patient
from apps.surgical_planning.models import SurgicalPlan, SurgicalPlanStatus


def _related_objects(*, patient_id, encounter_id, study_id, ai_analysis_id):
    patient = Patient.objects.get(pk=patient_id)
    encounter = Encounter.objects.get(pk=encounter_id) if encounter_id else None
    study = ImagingStudy.objects.get(pk=study_id)
    analysis = AIAnalysis.objects.get(pk=ai_analysis_id) if ai_analysis_id else None
    if encounter and encounter.patient_id != patient.id:
        raise ValidationError("Encounter does not belong to the selected patient.")
    if study.patient_id and study.patient_id != patient.id:
        raise ValidationError("Imaging study does not belong to the selected patient.")
    if analysis and analysis.study_id != study.id:
        raise ValidationError("AI analysis does not belong to the selected study.")
    return patient, encounter, study, analysis


@transaction.atomic
def create_surgical_plan(*, user, patient_id, study_id, encounter_id=None, ai_analysis_id=None, treatment_type="", memo=""):
    patient, encounter, study, analysis = _related_objects(
        patient_id=patient_id,
        encounter_id=encounter_id,
        study_id=study_id,
        ai_analysis_id=ai_analysis_id,
    )
    return SurgicalPlan.objects.create(
        patient=patient,
        encounter=encounter,
        study=study,
        ai_analysis=analysis,
        treatment_type=treatment_type,
        memo=memo,
        created_by=user,
    )


@transaction.atomic
def update_surgical_plan(*, planning_id, expected_version, values, status=None, user=None):
    plan = SurgicalPlan.objects.select_for_update().get(pk=planning_id)
    if plan.version != expected_version:
        raise ValidationError("Surgical plan version conflict.")
    if plan.status in {SurgicalPlanStatus.CONFIRMED, SurgicalPlanStatus.CANCELLED}:
        raise ValidationError("The surgical plan is no longer editable.")
    for field in ("treatment_type", "memo"):
        if field in values:
            setattr(plan, field, values[field])
    if status is not None:
        plan.status = status
    if status == SurgicalPlanStatus.CONFIRMED:
        plan.finalized_by = user
        plan.finalized_at = timezone.now()
    plan.version += 1
    plan.save()
    return plan

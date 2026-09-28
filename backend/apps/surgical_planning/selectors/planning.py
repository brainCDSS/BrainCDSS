"""Read queries for surgical planning."""

from apps.surgical_planning.models import (
    SurgicalPlan,
    SurgicalPlanStatus,
)


def surgical_plan_queryset():
    return (
        SurgicalPlan.objects
        .select_related(
            "patient",
            "encounter",
            "study",
            "ai_analysis",
            "created_by",
            "created_by__role",
            "finalized_by",
        )
        .prefetch_related("clips")
        .order_by("-updated_at")
    )


def list_surgical_plans(
    *,
    user,
    patient_id=None,
    study_id=None,
    status=None,
):
    from apps.patients.selectors.patients import accessible_patient_ids

    queryset = surgical_plan_queryset().filter(
        patient_id__in=accessible_patient_ids(user),
    )

    if patient_id:
        queryset = queryset.filter(
            patient_id=patient_id
        )

    if study_id:
        queryset = queryset.filter(
            study_id=study_id
        )

    if status:
        queryset = queryset.filter(
            status=status
        )
    else:
        # Frontend restore query means "current usable plan".
        queryset = queryset.exclude(
            status=SurgicalPlanStatus.CANCELLED
        )

    return queryset


def get_surgical_plan(*, user, planning_id):
    return list_surgical_plans(user=user).get(
        pk=planning_id,
    )

from __future__ import annotations

from django.db.models import Q

from apps.assessments.models import InitialAssessment
from apps.clinical_records.models import Encounter
from apps.consultations.models import Consultation
from apps.organizations.models import Hospital
from apps.patients.models import (
    FavoriteHospital,
    Patient,
    PatientCareAssignment,
)


def list_patients(
    *,
    actor=None,
    search: str | None = None,
    patient_no: str | None = None,
    birth_date=None,
    status: str | None = None,
    scope: str = "all",
    user=None,
):
    qs = Patient.objects.all()

    if actor is not None:
        qs = qs.filter(id__in=accessible_patient_ids(actor))

    if scope == "mine":
        if user is None:
            return qs.none()

        active_encounter_statuses = {
            "REGISTERED",
            "IN_PROGRESS",
        }

        active_consultation_statuses = {
            "REQUESTED",
            "ACCEPTED",
            "IN_PROGRESS",
            "RESPONDED",
        }

        appointment_patient_ids = (
            Encounter.objects
            .filter(
                status__in=active_encounter_statuses,
                appointment__clinician__user_id=user.id,
            )
            .values("patient_id")
        )

        assigned_patient_ids = (
            InitialAssessment.objects
            .filter(
                assigned_neurologist_id=user.id,
                encounter__status__in=active_encounter_statuses,
            )
            .values("encounter__patient_id")
        )

        consultation_patient_ids = (
            Consultation.objects
            .filter(
                Q(requested_by_id=user.id)
                | Q(assigned_to_id=user.id),
                status__in=active_consultation_statuses,
            )
            .values("encounter__patient_id")
        )

        qs = (
            qs.filter(
                Q(id__in=appointment_patient_ids)
                | Q(id__in=assigned_patient_ids)
                | Q(id__in=consultation_patient_ids)
            )
            .distinct()
        )

    if search:
        search = search.strip()
        qs = qs.filter(
            Q(name__icontains=search)
            | Q(patient_no__icontains=search)
            | Q(phone__icontains=search)
        )

    if patient_no:
        qs = qs.filter(
            patient_no__iexact=patient_no.strip()
        )

    if birth_date:
        qs = qs.filter(birth_date=birth_date)

    if status:
        qs = qs.filter(status=status)

    return qs.order_by("-created_at", "id")


def get_patient(patient_id):
    return Patient.objects.filter(id=patient_id).first()


def accessible_patient_ids(actor):
    """
    Return patient IDs the actor may access.

    Clinical access is fail-closed, but all legitimate BrainOn
    clinician-patient relationships are included:

    - ACTIVE PatientCareAssignment
    - active Encounter appointment clinician
    - InitialAssessment assigned neurologist
    - Consultation requester / assignee
    """
    if (
        actor is None
        or not getattr(actor, "is_authenticated", False)
    ):
        return Patient.objects.none().values("id")

    role_code = getattr(
        getattr(actor, "role", None),
        "code",
        None,
    )

    if role_code == "SYSTEM_ADMIN":
        return Patient.objects.all().values("id")

    if role_code == "PATIENT":
        return Patient.objects.filter(
            user_id=actor.id
        ).values("id")

    active_encounter_statuses = {
        "REGISTERED",
        "IN_PROGRESS",
    }

    # Latest DEV:
    # 명시적 ACTIVE care assignment
    care_assignment_patient_ids = (
        PatientCareAssignment.objects
        .filter(
            clinician_id=actor.id,
            status=PatientCareAssignment.Status.ACTIVE,
        )
        .values("patient_id")
    )

    # Existing YR:
    # active Encounter의 appointment 담당의
    appointment_patient_ids = (
        Encounter.objects
        .filter(
            status__in=active_encounter_statuses,
            appointment__clinician__user_id=actor.id,
        )
        .values("patient_id")
    )

    # Existing YR:
    # 초기평가에서 배정된 신경과 담당의
    assessment_patient_ids = (
        InitialAssessment.objects
        .filter(
            assigned_neurologist_id=actor.id,
            encounter__status__in=active_encounter_statuses,
        )
        .values("encounter__patient_id")
    )

    # Latest DEV behavior preserved:
    # consultation participant이면 접근 가능.
    # 여기서는 기존 DEV와 동일하게 status 전체를 허용하고,
    # scope="mine"에서만 active consultation으로 더 좁힌다.
    consultation_patient_ids = (
        Consultation.objects
        .filter(
            Q(requested_by_id=actor.id)
            | Q(assigned_to_id=actor.id)
        )
        .values("encounter__patient_id")
    )

    return (
        Patient.objects
        .filter(
            Q(id__in=care_assignment_patient_ids)
            | Q(id__in=appointment_patient_ids)
            | Q(id__in=assessment_patient_ids)
            | Q(id__in=consultation_patient_ids)
        )
        .distinct()
        .values("id")
    )

def patient_access_queryset(actor):
    return Patient.objects.filter(id__in=accessible_patient_ids(actor))


def can_view_patient(actor, patient_id):
    return patient_access_queryset(actor).filter(pk=patient_id).exists()


def resolve_patient(patient: Patient):
    """
    Resolve MERGED -> merged_into_patient until a non-MERGED patient.
    Returns (resolved_patient, resolved_from_patient_id).
    """
    original_id = patient.id
    current = patient
    seen = set()

    while current.status == "MERGED":
        if current.id in seen:
            return None, original_id

        seen.add(current.id)

        if current.merged_into_patient_id is None:
            return None, original_id

        current = Patient.objects.filter(
            id=current.merged_into_patient_id
        ).first()

        if current is None:
            return None, original_id

    return (
        current,
        original_id
        if current.id != original_id
        else None,
    )


def patient_profile_for_user(user):
    return Patient.objects.filter(
        user_id=user.id
    ).first()


def list_favorite_hospitals(patient):
    return (
        FavoriteHospital.objects.select_related("hospital")
        .filter(
            patient=patient,
            hospital__is_active=True,
        )
        .order_by("-created_at", "id")
    )


def get_active_hospital(hospital_id):
    return Hospital.objects.filter(
        id=hospital_id,
        is_active=True,
    ).first()

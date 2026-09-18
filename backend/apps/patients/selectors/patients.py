from __future__ import annotations

from django.db.models import Q

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
):
    qs = Patient.objects.all()

    if actor is not None:
        qs = qs.filter(id__in=accessible_patient_ids(actor))

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
    """Return the patient IDs the actor may access.

    Access is fail-closed for clinical users.  A patient becomes visible only
    through an active care assignment or a consultation in which the actor is
    the requester or assignee.  Importing Consultation lazily keeps the
    patient app independent during Django app loading.
    """
    if actor is None or not getattr(actor, "is_authenticated", False):
        return Patient.objects.none().values("id")

    role_code = getattr(getattr(actor, "role", None), "code", None)
    if role_code == "SYSTEM_ADMIN":
        return Patient.objects.all().values("id")
    if role_code == "PATIENT":
        return Patient.objects.filter(user_id=actor.id).values("id")
    if role_code == "NURSE":
        # Nurses must be able to find an existing patient before an
        # assignment or consultation exists (registration/triage workflow).
        # The current product runs as a single-hospital deployment, so expose
        # every non-merged patient here. When hospital ownership is persisted
        # on the patient/encounter boundary, narrow this branch to the nurse's
        # hospital without changing the clinician assignment rules below.
        return Patient.objects.exclude(status="MERGED").values("id")

    assigned_patient_ids = PatientCareAssignment.objects.filter(
        clinician_id=actor.id,
        status=PatientCareAssignment.Status.ACTIVE,
    ).values("patient_id")

    from apps.consultations.models import Consultation

    consultation_patient_ids = Consultation.objects.filter(
        Q(requested_by_id=actor.id) | Q(assigned_to_id=actor.id),
    ).values("encounter__patient_id")

    return Patient.objects.filter(
        Q(id__in=assigned_patient_ids) | Q(id__in=consultation_patient_ids),
    ).values("id")


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

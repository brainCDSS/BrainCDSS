from __future__ import annotations

from django.db.models import Q

from apps.organizations.models import Hospital
from apps.patients.models import (
    FavoriteHospital,
    Patient,
)


def list_patients(
    *,
    search: str | None = None,
    patient_no: str | None = None,
    birth_date=None,
    status: str | None = None,
):
    qs = Patient.objects.all()

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

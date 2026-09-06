from __future__ import annotations

from math import atan2, cos, radians, sin, sqrt

from django.db.models import Q

from apps.organizations.models import Clinician, Department, Hospital
from apps.patients.models import FavoriteHospital, Patient


def list_active_hospitals(*, search: str | None = None):
    qs = Hospital.objects.filter(is_active=True)

    if search:
        search = search.strip()
        qs = qs.filter(
            Q(name__icontains=search)
            | Q(address__icontains=search)
        )

    return qs.order_by("name", "id")


def get_active_hospital(hospital_id):
    return (
        Hospital.objects.filter(
            id=hospital_id,
            is_active=True,
        )
        .first()
    )


def list_active_departments(hospital):
    return (
        Department.objects.filter(
            hospital=hospital,
            is_active=True,
        )
        .order_by("name", "code", "id")
    )


def get_active_department(department_id):
    return (
        Department.objects.select_related("hospital")
        .filter(
            id=department_id,
            is_active=True,
            hospital__is_active=True,
        )
        .first()
    )


def list_active_clinicians(department):
    return (
        Clinician.objects.select_related("user")
        .filter(
            department=department,
            is_active=True,
            user__is_active=True,
        )
        .order_by("user__name", "id")
    )


def patient_profile_for_user(user):
    if not user or not getattr(user, "is_authenticated", False):
        return None

    return Patient.objects.filter(user_id=user.id).first()


def favorite_hospital_ids_for_user(user) -> set[str]:
    patient = patient_profile_for_user(user)

    if patient is None:
        return set()

    return {
        str(value)
        for value in FavoriteHospital.objects.filter(
            patient=patient
        ).values_list("hospital_id", flat=True)
    }


def haversine_km(
    lat1: float,
    lng1: float,
    lat2: float,
    lng2: float,
) -> float:
    earth_radius_km = 6371.0088

    phi1 = radians(lat1)
    phi2 = radians(lat2)
    d_phi = radians(lat2 - lat1)
    d_lambda = radians(lng2 - lng1)

    a = (
        sin(d_phi / 2) ** 2
        + cos(phi1)
        * cos(phi2)
        * sin(d_lambda / 2) ** 2
    )

    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return earth_radius_km * c

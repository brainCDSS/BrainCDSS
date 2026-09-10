from django.db.models import Q

from apps.consultations.models import Consultation
from apps.imaging.models import (
    ImagingOrder,
    ImagingOrderStatusHistory,
    ImagingStudy,
)
from apps.organizations.models import Clinician


def _role_code(user):
    role = getattr(user, "role", None)
    return getattr(role, "code", None)


def user_can_access_encounter(
    *,
    user,
    encounter,
):
    if not getattr(user, "is_active", False):
        return False

    role = _role_code(user)

    if role not in {
        "NEUROLOGIST",
        "NEUROSURGEON",
        "NURSE",
        "RADIOLOGY",
    }:
        return False

    # 현재 최종 DB에는 Nurse의 별도
    # Hospital/Department 소속 FK가 없다.
    if role == "NURSE":
        return True

    appointment = encounter.appointment

    if (
        appointment is not None
        and appointment.clinician.user_id
        == user.id
    ):
        return True

    if Consultation.objects.filter(
        encounter=encounter
    ).filter(
        Q(requested_by=user)
        | Q(assigned_to=user)
    ).exists():
        return True

    if role == "RADIOLOGY":
        clinician = (
            Clinician.objects
            .select_related(
                "department__hospital"
            )
            .filter(
                user=user,
                is_active=True,
            )
            .first()
        )

        if clinician is None:
            # 현재 DB에 별도 Radiology Worklist
            # 배정 테이블이 없어 Role 기준 조회 허용.
            return True

        if appointment is None:
            return True

        return (
            appointment.hospital_id
            == clinician.department.hospital_id
        )

    return False


def scoped_imaging_orders(user):
    role = _role_code(user)

    base = (
        ImagingOrder.objects
        .select_related(
            "patient",
            "encounter",
            "encounter__appointment",
            "encounter__appointment__clinician",
            "encounter__appointment__clinician__user",
            "requested_by",
            "requested_by__role",
        )
    )

    if role == "NURSE":
        return base

    if role == "RADIOLOGY":
        clinician = (
            Clinician.objects
            .select_related(
                "department__hospital"
            )
            .filter(
                user=user,
                is_active=True,
            )
            .first()
        )

        if clinician is None:
            return base

        return base.filter(
            Q(
                encounter__appointment__hospital_id=
                    clinician.department.hospital_id
            )
            | Q(encounter__appointment__isnull=True)
        )

    if role in {
        "NEUROLOGIST",
        "NEUROSURGEON",
    }:
        consult_encounters = (
            Consultation.objects
            .filter(
                Q(requested_by=user)
                | Q(assigned_to=user)
            )
            .values("encounter_id")
        )

        return base.filter(
            Q(requested_by=user)
            | Q(
                encounter__appointment__clinician__user=user
            )
            | Q(
                encounter_id__in=consult_encounters
            )
        ).distinct()

    return base.none()


def get_scoped_imaging_order(
    *,
    user,
    order_id,
):
    return (
        scoped_imaging_orders(user)
        .filter(pk=order_id)
        .first()
    )


def get_order_study(order):
    return (
        ImagingStudy.objects
        .filter(imaging_order=order)
        .order_by(
            "-study_datetime",
            "-created_at",
            "-id",
        )
        .first()
    )


def get_order_history(order):
    return (
        ImagingOrderStatusHistory.objects
        .filter(imaging_order=order)
        .order_by(
            "occurred_at",
            "id",
        )
    )

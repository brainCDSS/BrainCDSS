import uuid

from django.apps import apps
from django.db import transaction
from django.utils import timezone


class EncounterRegistrationError(Exception):
    def __init__(self, code, detail, status_code):
        self.code = code
        self.detail = detail
        self.status_code = status_code
        super().__init__(detail)


@transaction.atomic
def register_encounter(
    *,
    patient_id,
    encounter_type,
    appointment_id=None,
    actor_user=None,
    request_ip=None,
    user_agent=None,
):
    patient_model = apps.get_model("patients", "Patient")
    encounter_model = apps.get_model("clinical_records", "Encounter")
    appointment_model = apps.get_model("appointments", "Appointment")

    patient = patient_model.objects.filter(pk=patient_id).first()
    if patient is None or patient.status not in {"ACTIVE", "TEMP"}:
        raise EncounterRegistrationError(
            "PATIENT_OR_APPOINTMENT_NOT_FOUND",
            "An active patient was not found.",
            404,
        )

    appointment = None
    if encounter_type == "EMERGENCY" and appointment_id is not None:
        raise EncounterRegistrationError(
            "ENCOUNTER_INPUT_INVALID",
            "Emergency encounters cannot have an appointment.",
            400,
        )

    if appointment_id is not None:
        appointment = appointment_model.objects.select_for_update().filter(
            pk=appointment_id,
            patient_id=patient.pk,
            status="CONFIRMED",
        ).first()
        if appointment is None:
            raise EncounterRegistrationError(
                "PATIENT_OR_APPOINTMENT_NOT_FOUND",
                "A confirmed appointment for the patient was not found.",
                404,
            )

    active = encounter_model.objects.select_for_update().filter(
        status__in=("REGISTERED", "IN_PROGRESS"),
    )
    duplicate = (
        active.filter(appointment_id=appointment.pk).exists()
        if appointment is not None
        else active.filter(
            patient_id=patient.pk,
            encounter_type=encounter_type,
            appointment_id__isnull=True,
        ).exists()
    )
    if duplicate:
        raise EncounterRegistrationError(
            "ACTIVE_ENCOUNTER_DUPLICATE",
            "An active encounter already exists.",
            409,
        )

    now = timezone.now()
    encounter = encounter_model.objects.create(
        patient=patient,
        appointment=appointment,
        encounter_no=f"ENC-{now:%Y%m%d}-{uuid.uuid4().hex[:12].upper()}",
        encounter_type=encounter_type,
        status="REGISTERED",
        arrived_at=now,
        created_at=now,
        updated_at=now,
    )

    result = {
        "encounter_id": encounter.pk,
        "encounter_no": encounter.encounter_no,
        "patient_id": patient.pk,
        "appointment_id": appointment.pk if appointment else None,
        "encounter_type": encounter.encounter_type,
        "status": encounter.status,
        "arrived_at": encounter.arrived_at,
    }

    audit_model = apps.get_model("audit", "AuditLog")
    audit_model.objects.create(
        actor_user=actor_user,
        actor_login=getattr(actor_user, "login_id", None),
        actor_role_code=getattr(getattr(actor_user, "role", None), "code", None),
        source_service="DJANGO_API",
        action="API-ENC-001",
        resource_type="Encounter",
        resource=str(encounter.pk),
        patient=patient.pk,
        outcome="SUCCESS",
        before_json=None,
        after_json={
            **result,
            "encounter_id": str(result["encounter_id"]),
            "patient_id": str(result["patient_id"]),
            "appointment_id": (
                str(result["appointment_id"])
                if result["appointment_id"] is not None
                else None
            ),
            "arrived_at": result["arrived_at"].isoformat(),
        },
        request_ip=request_ip,
        user_agent=user_agent,
        occurred_at=now,
    )

    outbox_model = apps.get_model("common", "OutboxEvent")
    outbox_model.objects.create(
        event_type="encounter.registered.v1",
        aggregate_type="Encounter",
        aggregate=str(encounter.pk),
        payload={
            "encounter_id": str(encounter.pk),
            "patient_id": str(patient.pk),
            "appointment_id": str(appointment.pk) if appointment else None,
            "encounter_type": encounter.encounter_type,
            "status": encounter.status,
            "arrived_at": encounter.arrived_at.isoformat(),
        },
        status="PENDING",
        retry_count=0,
        published_at=None,
        created_at=now,
    )

    return result

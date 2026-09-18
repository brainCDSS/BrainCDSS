"""Consultation notification creation service."""

from apps.notifications.services.notifications import create_notification_for_user


def create_assigned_consultation_notification(*, consultation):
    severity = {
        "STAT": "CRITICAL",
        "URGENT": "WARNING",
    }.get(consultation.priority, "INFO")
    patient = consultation.encounter.patient

    return create_notification_for_user(
        recipient_user=consultation.assigned_to,
        category="CONSULTATION",
        severity=severity,
        title="새 협진 요청",
        body=(
            f"{consultation.requested_by.name} 요청: "
            f"{patient.name} 환자 {consultation.reason}"
        ),
        data_json={
            "event_type": "CONSULTATION_REQUESTED",
            "consultation_id": str(consultation.id),
            "encounter_id": str(consultation.encounter_id),
            "patient_id": str(patient.id),
            "consultation_type": consultation.consultation_type,
            "priority": consultation.priority,
        },
    )

"""Consultation notification creation service."""

from apps.notifications.models import Notification


def create_assigned_consultation_notification(*, consultation):
    severity = {
        "STAT": "CRITICAL",
        "URGENT": "WARNING",
    }.get(consultation.priority, "INFO")
    patient = consultation.encounter.patient

    return Notification.objects.create(
        recipient_user=consultation.assigned_to,
        category="CONSULTATION",
        severity=severity,
        title="새 협진 요청",
        body=(
            f"{consultation.requested_by.name} 요청: "
            f"{patient.name} 환자 {consultation.reason}"
        ),
        data_json={
            "consultation_id": str(consultation.id),
            "encounter_id": str(consultation.encounter_id),
            "consultation_type": consultation.consultation_type,
            "priority": consultation.priority,
        },
    )

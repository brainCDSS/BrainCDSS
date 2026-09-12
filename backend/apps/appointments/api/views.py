"""Hand-written appointment API extensions registered before generated routes."""

from apps.common.remaining149_runtime import build_contract_view


APPOINTMENT_CORRECT_SPEC = {
    "api_id": "API-APP-011",
    "app": "appointments",
    "domain": "Appointment",
    "api_name": "예약 상태 정정",
    "method": "POST",
    "endpoint": "/api/v1/appointments/{appointment_id}/correct",
    "django_path": "api/v1/appointments/<uuid:appointment_id>/correct",
    "roles": ["NURSE"],
    "permission": "appointment.correct",
    "service_scope": None,
    "request_contract": "Body: target_status='REQUESTED', reason(required)",
    "validation": "NURSE + appointment.correct; REJECTED|CONFIRMED only; reason required",
    "related_db": (
        "Appointment, AppointmentSlot, AppointmentStatusHistory, AuditLog"
    ),
    "processing": (
        "REJECTED|CONFIRMED->REQUESTED; slot AVAILABLE|BOOKED->HELD; "
        "held_until=now+HOLD_TTL; status history and audit"
    ),
    "response_contract": (
        "appointment_id, previous_status, status='REQUESTED', slot, "
        "correction_reason"
    ),
    "success": "200 OK",
    "error_contract": (
        "400 VALIDATION_ERROR / 404 APPOINTMENT_NOT_FOUND / "
        "409 APPOINTMENT_CORRECTION_INVALID_STATE|"
        "APPOINTMENT_CORRECTION_CONFLICT|APPOINTMENT_SLOT_CONFLICT"
    ),
    "transaction": "O(필수)",
    "transactional": True,
    "event": "-",
    "note": "Permission: appointment.correct",
    "primary_model": "appointments.Appointment",
    "audit_required": True,
}


AppointmentCorrectView = build_contract_view([APPOINTMENT_CORRECT_SPEC])

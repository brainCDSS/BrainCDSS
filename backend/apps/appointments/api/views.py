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


APPOINTMENT_SLOT_LIST_SPEC = {
    "api_id": "API-SLOT-001",
    "app": "appointments",
    "domain": "Schedule",
    "api_name": "예약 가능 시간 조회",
    "method": "GET",
    "endpoint": "/api/v1/clinicians/{clinician_id}/slots",
    "django_path": "api/v1/clinicians/<uuid:clinician_id>/slots",
    "roles": ["PATIENT", "NURSE", "NEUROLOGIST", "NEUROSURGEON"],
    "permission": None,
    "service_scope": None,
    "primary_model": "appointments.AppointmentSlot",
    "transactional": False,
    "success": "200 OK",
}

STAFF_APPOINTMENT_CREATE_SPEC = {
    "api_id": "API-APP-012",
    "app": "appointments",
    "domain": "Appointment",
    "api_name": "간호사 예약 등록",
    "method": "POST",
    "endpoint": "/api/v1/staff/appointment-bookings",
    "django_path": "api/v1/staff/appointment-bookings",
    "roles": ["NURSE"],
    "permission": "appointment.read.staff",
    "service_scope": None,
    "request_contract": "Body: patient_id, slot_id",
    "primary_model": "appointments.Appointment",
    "transactional": True,
    "audit_required": True,
    "success": "201 Created",
}

AppointmentSlotListView = build_contract_view([APPOINTMENT_SLOT_LIST_SPEC])
StaffAppointmentCreateView = build_contract_view([STAFF_APPOINTMENT_CREATE_SPEC])

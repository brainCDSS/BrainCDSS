# Appointment booking extensions

## Available slots

`GET /api/v1/clinicians/{clinician_id}/slots?date=YYYY-MM-DD`

The server materializes slots from the clinician's active schedule rule. Only
future `AVAILABLE` slots are returned. Schedule rules support `slot_minutes` of
`15` or `30`; `(clinician_id, start_at)` is unique, so one clinician can see at
most one patient in each slot.

## Staff booking

`POST /api/v1/staff/appointment-bookings`

Allowed role: `NURSE` with `appointment.read.staff`.

```json
{
  "patient_id": "uuid",
  "slot_id": "uuid"
}
```

The operation locks the selected slot and atomically changes it from
`AVAILABLE` to `BOOKED` while creating a `CONFIRMED` appointment. Concurrent
requests for the same slot return `409 SLOT_NOT_AVAILABLE`.

Possible errors: `400 VALIDATION_ERROR`, `404 PATIENT_NOT_FOUND`,
`404 SLOT_NOT_FOUND`, `409 SLOT_NOT_AVAILABLE`, and
`409 PATIENT_APPOINTMENT_CONFLICT`.

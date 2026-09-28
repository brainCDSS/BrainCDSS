from django.urls import path

from apps.appointments.api.views import (
    AppointmentCorrectView,
    AppointmentSlotListView,
    StaffAppointmentCreateView,
)


urlpatterns = [
    path(
        "api/v1/clinicians/<uuid:clinician_id>/slots",
        AppointmentSlotListView.as_view(),
        name="api_slot_available",
    ),
    path(
        "api/v1/staff/appointment-bookings",
        StaffAppointmentCreateView.as_view(),
        name="api_staff_appointment_create",
    ),
    path(
        "api/v1/appointments/<uuid:appointment_id>/correct",
        AppointmentCorrectView.as_view(),
        name="api_app_011",
    ),
]

from django.urls import path

from apps.appointments.api.views import AppointmentCorrectView


urlpatterns = [
    path(
        "api/v1/appointments/<uuid:appointment_id>/correct",
        AppointmentCorrectView.as_view(),
        name="api_app_011",
    ),
]

from django.urls import path

from apps.prescriptions.api.prescription_finalize_views import (
    PrescriptionFinalizeView,
)
from apps.prescriptions.api.current_medications_views import (
    CurrentMedicationsView,
)
from apps.prescriptions.api.patient_prescription_views import (
    PatientPrescriptionsView,
)


urlpatterns = [
    path(
        "api/v1/me/prescriptions",
        PatientPrescriptionsView.as_view(),
        name="patient_prescriptions",
    ),
    path(
        "api/v1/patients/<uuid:patient_id>/current-medications",
        CurrentMedicationsView.as_view(),
        name="api-current-medications",
    ),
    path(
        (
            "api/v1/prescriptions/"
            "<uuid:prescription_id>/finalize"
        ),
        PrescriptionFinalizeView.as_view(),
        name="api-rx-004-real",
    ),
]

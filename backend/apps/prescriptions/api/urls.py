from django.urls import path

from apps.prescriptions.api.prescription_finalize_views import (
    PrescriptionFinalizeView,
)


urlpatterns = [
    path(
        (
            "api/v1/prescriptions/"
            "<uuid:prescription_id>/finalize"
        ),
        PrescriptionFinalizeView.as_view(),
        name="api-rx-004-real",
    ),
]

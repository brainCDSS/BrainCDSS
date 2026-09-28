from django.urls import path

from apps.cdss.api.cds_hooks_views import (
    CDSServiceDiscoveryView,
    MedicationSafetyOrderSelectView,
    MedicationSafetyOrderSignView,
    StrokePatientView,
)


urlpatterns = [
    path(
        "cds-services",
        CDSServiceDiscoveryView.as_view(),
        name="api-cds-001-real",
    ),
    path(
        (
            "cds-services/"
            "medication-safety-order-select"
        ),
        MedicationSafetyOrderSelectView.as_view(),
        name="api-cds-002-real",
    ),
    path(
        (
            "cds-services/"
            "medication-safety-order-sign"
        ),
        MedicationSafetyOrderSignView.as_view(),
        name="api-cds-003-real",
    ),
    path(
        "cds-services/stroke-patient-view",
        StrokePatientView.as_view(),
        name="api-cds-004-real",
    ),
]

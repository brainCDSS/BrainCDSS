from django.urls import path

from apps.medication_safety.api.dur_views import (
    DurSyncView,
)
from apps.medication_safety.api.safety_views import (
    MedicationSafetyCheckView,
)


urlpatterns = [
    path(
        "api/v1/admin/dur/sync",
        DurSyncView.as_view(),
        name="api-dur-001-real",
    ),
    path(
        "api/v1/prescriptions/safety-check",
        MedicationSafetyCheckView.as_view(),
        name="api-medsafe-001-real",
    ),
]

from django.urls import path

from apps.clinical_records.api.encounter_views import EncounterCreateView


urlpatterns = [
    path(
        "api/v1/encounters",
        EncounterCreateView.as_view(),
        name="api-enc-001-real",
    ),
]

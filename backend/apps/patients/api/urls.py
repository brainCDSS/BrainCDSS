from django.urls import path

from apps.patients.api.views import (
    FavoriteHospitalDetailView,
    FavoriteHospitalListView,
    PatientDetailUpdateView,
    PatientIdentifyView,
    PatientListCreateView,
    PatientMergeView,
    TemporaryPatientCreateView,
)


urlpatterns = [
    path(
        "patients",
        PatientListCreateView.as_view(),
        name="patient-list-create",
    ),
    path(
        "patients/temporary",
        TemporaryPatientCreateView.as_view(),
        name="patient-temporary-create",
    ),
    path(
        "patients/<uuid:patient_id>",
        PatientDetailUpdateView.as_view(),
        name="patient-detail-update",
    ),
    path(
        "patients/<uuid:temp_patient_id>/merge",
        PatientMergeView.as_view(),
        name="patient-merge",
    ),
    path(
        "patients/<uuid:patient_id>/identify",
        PatientIdentifyView.as_view(),
        name="patient-identify",
    ),
    path(
        "me/favorite-hospitals",
        FavoriteHospitalListView.as_view(),
        name="favorite-hospital-list",
    ),
    path(
        "me/favorite-hospitals/<uuid:hospital_id>",
        FavoriteHospitalDetailView.as_view(),
        name="favorite-hospital-detail",
    ),
]

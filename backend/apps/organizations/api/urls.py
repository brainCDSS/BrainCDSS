from django.urls import path

from apps.organizations.api.views import (
    DepartmentClinicianListView,
    HospitalDepartmentListView,
    HospitalDetailView,
    HospitalListView,
)


urlpatterns = [
    path(
        "hospitals",
        HospitalListView.as_view(),
        name="hospital-list",
    ),
    path(
        "hospitals/<uuid:hospital_id>",
        HospitalDetailView.as_view(),
        name="hospital-detail",
    ),
    path(
        "hospitals/<uuid:hospital_id>/departments",
        HospitalDepartmentListView.as_view(),
        name="hospital-departments",
    ),
    path(
        "departments/<uuid:department_id>/clinicians",
        DepartmentClinicianListView.as_view(),
        name="department-clinicians",
    ),
]

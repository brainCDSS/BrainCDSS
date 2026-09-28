from django.urls import path
from apps.medication_safety.api import generated_real_149 as views

urlpatterns = [
    path(
        'api/v1/admin/dur/sync',
        views.ContractView000.as_view(),
        name='api_dur_001',
    ),
    path(
        'api/v1/patients/<uuid:patient_id>/allergies',
        views.ContractView001.as_view(),
        name='api_allergy_001_api_allergy_002',
    ),
    path(
        'api/v1/patients/<uuid:patient_id>/allergies/<uuid:allergy_id>',
        views.ContractView002.as_view(),
        name='api_allergy_003',
    ),
    path(
        'api/v1/prescriptions/safety-check',
        views.ContractView003.as_view(),
        name='api_medsafe_001',
    ),
]


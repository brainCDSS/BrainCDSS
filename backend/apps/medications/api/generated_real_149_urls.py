from django.urls import path
from apps.medications.api import generated_real_149 as views

urlpatterns = [
    path(
        'api/v1/medication-intakes',
        views.ContractView000.as_view(),
        name='api_med_002',
    ),
    path(
        'api/v1/medication-intakes/<uuid:intake_id>',
        views.ContractView001.as_view(),
        name='api_med_003',
    ),
    path(
        'api/v1/medication-schedules',
        views.ContractView002.as_view(),
        name='api_med_001',
    ),
    path(
        'api/v1/medications',
        views.ContractView003.as_view(),
        name='api_medm_001',
    ),
    path(
        'api/v1/medications/<uuid:medication_id>',
        views.ContractView004.as_view(),
        name='api_medm_002',
    ),
]


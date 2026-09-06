from django.urls import path
from apps.cdss.api import generated_real_149 as views

urlpatterns = [
    path(
        'cds-services',
        views.ContractView000.as_view(),
        name='api_cds_001',
    ),
    path(
        'cds-services/medication-safety-order-select',
        views.ContractView001.as_view(),
        name='api_cds_002',
    ),
    path(
        'cds-services/medication-safety-order-sign',
        views.ContractView002.as_view(),
        name='api_cds_003',
    ),
    path(
        'cds-services/stroke-patient-view',
        views.ContractView003.as_view(),
        name='api_cds_004',
    ),
]


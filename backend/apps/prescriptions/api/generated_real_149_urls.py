from django.urls import path
from apps.prescriptions.api import generated_real_149 as views

urlpatterns = [
    path(
        'api/v1/prescriptions',
        views.ContractView000.as_view(),
        name='api_rx_001_api_rx_005',
    ),
    path(
        'api/v1/prescriptions/<uuid:prescription_id>',
        views.ContractView001.as_view(),
        name='api_rx_002_api_rx_003',
    ),
    path(
        'api/v1/prescriptions/<uuid:prescription_id>/finalize',
        views.ContractView002.as_view(),
        name='api_rx_004',
    ),
]


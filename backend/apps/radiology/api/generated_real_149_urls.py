from django.urls import path
from apps.radiology.api import generated_real_149 as views

urlpatterns = [
    path(
        'api/v1/radiology-reports',
        views.ContractView000.as_view(),
        name='api_rad_002',
    ),
    path(
        'api/v1/radiology-reports/<uuid:report_id>',
        views.ContractView001.as_view(),
        name='api_rad_003_api_rad_004',
    ),
    path(
        'api/v1/radiology-reports/<uuid:report_id>/amend',
        views.ContractView002.as_view(),
        name='api_rad_007',
    ),
    path(
        'api/v1/radiology-reports/<uuid:report_id>/cancel',
        views.ContractView003.as_view(),
        name='api_rad_011',
    ),
    path(
        'api/v1/radiology-reports/<uuid:report_id>/finalize',
        views.ContractView004.as_view(),
        name='api_rad_006',
    ),
    path(
        'api/v1/radiology-reports/<uuid:report_id>/measurements',
        views.ContractView005.as_view(),
        name='api_rad_009_api_rad_010',
    ),
    path(
        'api/v1/radiology-reports/<uuid:report_id>/revisions',
        views.ContractView006.as_view(),
        name='api_rad_008',
    ),
    path(
        'api/v1/radiology-reports/<uuid:report_id>/submit-preliminary',
        views.ContractView007.as_view(),
        name='api_rad_005',
    ),
    path(
        'api/v1/radiology/worklist',
        views.ContractView008.as_view(),
        name='api_rad_001',
    ),
]


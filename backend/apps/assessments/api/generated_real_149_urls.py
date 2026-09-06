from django.urls import path
from apps.assessments.api import generated_real_149 as views

urlpatterns = [
    path(
        'api/v1/assessments',
        views.ContractView000.as_view(),
        name='api_asm_002',
    ),
    path(
        'api/v1/assessments/worklist',
        views.ContractView001.as_view(),
        name='api_asm_001',
    ),
    path(
        'api/v1/assessments/<uuid:assessment_id>',
        views.ContractView002.as_view(),
        name='api_asm_003_api_asm_004',
    ),
    path(
        'api/v1/assessments/<uuid:assessment_id>/complete',
        views.ContractView003.as_view(),
        name='api_asm_005',
    ),
    path(
        'api/v1/emergency-events/<uuid:event_id>/acknowledge',
        views.ContractView004.as_view(),
        name='api_evt_001',
    ),
    path(
        'api/v1/neurology/emergency-worklist',
        views.ContractView005.as_view(),
        name='api_asm_006',
    ),
]


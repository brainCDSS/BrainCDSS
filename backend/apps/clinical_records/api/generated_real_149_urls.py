from django.urls import path
from apps.clinical_records.api import generated_real_149 as views

urlpatterns = [
    path(
        'api/v1/clinical-notes',
        views.ContractView000.as_view(),
        name='api_note_001_api_note_002',
    ),
    path(
        'api/v1/clinical-notes/<uuid:note_id>',
        views.ContractView001.as_view(),
        name='api_note_003_api_note_004',
    ),
    path(
        'api/v1/clinical-notes/<uuid:note_id>/finalize',
        views.ContractView002.as_view(),
        name='api_note_005',
    ),
    path(
        'api/v1/encounters',
        views.ContractView003.as_view(),
        name='api_enc_001',
    ),
    path(
        'api/v1/encounters/<uuid:encounter_id>/cancel',
        views.ContractView004.as_view(),
        name='api_enc_004',
    ),
    path(
        'api/v1/encounters/<uuid:encounter_id>/complete',
        views.ContractView005.as_view(),
        name='api_enc_003',
    ),
    path(
        'api/v1/encounters/<uuid:encounter_id>/start',
        views.ContractView006.as_view(),
        name='api_enc_002',
    ),
]


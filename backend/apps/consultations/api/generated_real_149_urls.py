from django.urls import path
from apps.consultations.api import generated_real_149 as views
from apps.consultations.api.consultation_list_view import ConsultationListCreateView
from apps.consultations.api.consultation_detail_view import ConsultationDetailView
from apps.consultations.api.consultation_message_view import (
    ConsultationMessageCollectionView,
)

urlpatterns = [
    path(
        'api/v1/consultations',
        ConsultationListCreateView.as_view(),
        name='api_con_001_api_con_002',
    ),
    path(
        'api/v1/consultations/<uuid:consultation_id>',
        ConsultationDetailView.as_view(),
        name='api_con_003',
    ),
    path(
        'api/v1/consultations/<uuid:consultation_id>/messages',
        ConsultationMessageCollectionView.as_view(),
        name='consultation_messages',
    ),
    path(
        'api/v1/consultations/<uuid:consultation_id>/accept',
        views.ContractView002.as_view(),
        name='api_con_004',
    ),
    path(
        'api/v1/consultations/<uuid:consultation_id>/cancel',
        views.ContractView003.as_view(),
        name='api_con_009',
    ),
    path(
        'api/v1/consultations/<uuid:consultation_id>/reject',
        views.ContractView004.as_view(),
        name='api_con_008',
    ),
    path(
        'api/v1/consultations/<uuid:consultation_id>/respond',
        views.ContractView005.as_view(),
        name='api_con_006',
    ),
    path(
        'api/v1/consultations/<uuid:consultation_id>/start',
        views.ContractView006.as_view(),
        name='api_con_005',
    ),
    path(
        'api/v1/consultations/<uuid:consultation_id>/view-response',
        views.ContractView007.as_view(),
        name='api_con_007',
    ),
]

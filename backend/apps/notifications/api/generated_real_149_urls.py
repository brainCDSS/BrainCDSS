from django.urls import path
from apps.notifications.api import generated_real_149 as views

urlpatterns = [
    path(
        'api/v1/devices/fcm-tokens',
        views.ContractView000.as_view(),
        name='api_fcm_001',
    ),
    path(
        'api/v1/devices/fcm-tokens/<uuid:token_id>',
        views.ContractView001.as_view(),
        name='api_fcm_002',
    ),
    path(
        'api/v1/notification-preferences',
        views.ContractView002.as_view(),
        name='api_noti_003_api_noti_004',
    ),
    path(
        'api/v1/notifications',
        views.ContractView003.as_view(),
        name='api_noti_001',
    ),
    path(
        'api/v1/notifications/<uuid:notification_id>/read',
        views.ContractView004.as_view(),
        name='api_noti_002',
    ),
]


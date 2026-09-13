from django.urls import path

from apps.notifications.api.fcm_views import (
    FCMTokenCollectionView,
    FCMTokenDetailView,
)


urlpatterns = [
    path(
        "api/v1/devices/fcm-tokens",
        FCMTokenCollectionView.as_view(),
        name="api_fcm_001_real",
    ),
    path(
        "api/v1/devices/fcm-tokens/<uuid:token_id>",
        FCMTokenDetailView.as_view(),
        name="api_fcm_002_real",
    ),
]

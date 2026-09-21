from django.urls import path

from apps.notifications.api.fcm_views import (
    FCMTokenCollectionView,
    FCMTokenDetailView,
)
from apps.notifications.api.views import (
    NotificationCollectionView,
    NotificationPreferenceView,
    NotificationReadView,
)


urlpatterns = [
    path("api/v1/notifications", NotificationCollectionView.as_view(), name="api_noti_001_real"),
    path(
        "api/v1/notifications/<uuid:notification_id>/read",
        NotificationReadView.as_view(),
        name="api_noti_002_real",
    ),
    path(
        "api/v1/notification-preferences",
        NotificationPreferenceView.as_view(),
        name="api_noti_003_004_real",
    ),
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

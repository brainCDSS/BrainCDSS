from django.urls import path

from apps.common.api.views import (
    MetricsView,
)


urlpatterns = [
    path(
        "internal/metrics",
        MetricsView.as_view(),
        name="api-ops-005",
    ),
]

"""Root HTTP routes for the BrainOn backend."""

from django.urls import path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
)

from apps.common.views import health


urlpatterns = [
    path(
        "api/v1/health/",
        health,
        name="health",
    ),

    path(
        "api/schema/",
        SpectacularAPIView.as_view(),
        name="openapi-schema",
    ),

    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(
            url_name="openapi-schema"
        ),
        name="swagger-ui",
    ),
]
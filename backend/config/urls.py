"""Root HTTP routes; domain APIs will be versioned below /api/v1/."""
from django.urls import path
from apps.common.views import health
urlpatterns=[path("api/v1/health/", health, name="health")]


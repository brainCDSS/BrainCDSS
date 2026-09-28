from django.urls import path

from apps.audit.api.views import (
    AuditLogDetailView,
    AuditLogListView,
)


urlpatterns = [
    path(
        "api/v1/operations/audit-logs",
        AuditLogListView.as_view(),
        name="api-ops-003",
    ),
    path(
        (
            "api/v1/operations/"
            "audit-logs/<uuid:audit_id>"
        ),
        AuditLogDetailView.as_view(),
        name="api-ops-004",
    ),
]

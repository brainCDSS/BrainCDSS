"""Service-to-service authentication for internal MCP APIs."""

from hmac import compare_digest

from django.conf import settings
from rest_framework.permissions import BasePermission


class MCPBackendTokenPermission(BasePermission):
    """Allow only the configured BrainOn MCP service token."""

    message = "Invalid MCP service credential."

    def has_permission(self, request, view):
        expected = getattr(
            settings,
            "MCP_BACKEND_TOKEN",
            "",
        ).strip()

        authorization = request.headers.get(
            "Authorization",
            "",
        ).strip()

        scheme, separator, provided = authorization.partition(" ")

        if not expected:
            return False

        if not separator or scheme.lower() != "bearer":
            return False

        provided = provided.strip()

        return bool(
            provided
            and compare_digest(provided, expected)
        )

"""Request correlation ID propagation.

X-Request-ID is the canonical BrainOn request identifier.
X-Trace-ID is kept as a compatibility alias for existing clients/logging.
"""

import uuid


def _request_id(value=None):
    if value:
        try:
            return str(uuid.UUID(str(value)))
        except (ValueError, TypeError, AttributeError):
            pass

    return str(uuid.uuid4())


class CorrelationIdMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        incoming = (
            request.headers.get("X-Request-ID")
            or request.headers.get("X-Trace-ID")
        )

        request_id = _request_id(incoming)

        # Canonical request correlation identifier.
        request.request_id = request_id

        # Backward-compatible alias.
        request.trace_id = request_id

        response = self.get_response(request)

        response["X-Request-ID"] = request_id
        response["X-Trace-ID"] = request_id

        return response

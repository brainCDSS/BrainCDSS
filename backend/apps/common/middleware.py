"""Request correlation ID propagation and structured request logging.

X-Request-ID is the canonical BrainOn request identifier.
X-Trace-ID is kept as a compatibility alias.

Request logs intentionally exclude raw URL/query/body/headers/IP to avoid
placing patient or other sensitive data into the observability pipeline.
"""

import json
import time
import uuid

from apps.common.tracking import build_tracking_code


def _request_id(value=None):
    if value:
        try:
            return str(uuid.UUID(str(value)))
        except (ValueError, TypeError, AttributeError):
            pass

    return str(uuid.uuid4())


def _route_name(request):
    resolver_match = getattr(
        request,
        "resolver_match",
        None,
    )

    if resolver_match is None:
        return "unresolved"

    return (
        getattr(
            resolver_match,
            "view_name",
            None,
        )
        or getattr(
            resolver_match,
            "url_name",
            None,
        )
        or "unresolved"
    )


def _severity(status_code):
    if status_code >= 500:
        return "ERROR"

    if status_code >= 400:
        return "WARNING"

    return "INFO"


def _write_request_log(
    request,
    *,
    request_id,
    status_code,
    duration_ms,
):
    event = {
        "severity": _severity(status_code),
        "message": "http_request_completed",
        "event": "HTTP_REQUEST",
        "source_service": "brainon-backend",
        "request_id": request_id,
        "trace_id": request_id,
        "method": request.method,
        "route": _route_name(request),
        "status": status_code,
        "duration_ms": duration_ms,
    }

    # Cloud Run automatically captures stdout in Cloud Logging.
    # One JSON object per line keeps the record structured/searchable.
    print(
        json.dumps(
            event,
            ensure_ascii=False,
            separators=(",", ":"),
        ),
        flush=True,
    )


class CorrelationIdMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        started = time.perf_counter()

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

        if response.status_code >= 400:
            response["X-Tracking-Code"] = (
                build_tracking_code(
                    request_id
                )
            )

        duration_ms = round(
            (
                time.perf_counter()
                - started
            )
            * 1000,
            2,
        )

        _write_request_log(
            request,
            request_id=request_id,
            status_code=response.status_code,
            duration_ms=duration_ms,
        )

        return response

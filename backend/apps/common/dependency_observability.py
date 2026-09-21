"""BrainOn dependency / partial-failure observability.

Goal
----
A request may return HTTP 2xx / SUCCESS while an internal dependency
inside the response reports FAILED, TIMEOUT, WARNING, DEGRADED, etc.

Those conditions must remain visible to SYSTEM_ADMIN without changing
the clinical/API response itself.

Signals
-------
1. Prometheus:
   brainon_dependency_results_total{
       dependency,
       operation,
       outcome
   }

2. AuditLog:
   action=DEPENDENCY_DEGRADED
   outcome=WARNING
   request_id=<same request correlation ID>

3. Structured application warning:
   BRAINON_DEPENDENCY_DEGRADED {...}

The structured log is available to Docker/Alloy/Loki pipelines.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from prometheus_client import Counter

from apps.audit.services.audit_event import (
    record_audit_event,
)


logger = logging.getLogger(
    "brainon.observability"
)


DEPENDENCY_RESULTS = Counter(
    "brainon_dependency_results",
    (
        "Results reported by BrainOn "
        "internal/downstream dependencies."
    ),
    [
        "dependency",
        "operation",
        "outcome",
    ],
)


# ============================================================
# Outcome vocabulary
# ============================================================

_SUCCESS = {
    "SUCCESS",
    "SUCCEEDED",
    "OK",
    "COMPLETED",
    "HEALTHY",
    "AVAILABLE",
    "UP",
    "CONNECTED",
}


_FAILURE_MAP = {
    "FAILED": "failed",
    "FAILURE": "failed",

    "ERROR": "error",

    "TIMEOUT": "timeout",
    "TIMED_OUT": "timeout",

    "WARNING": "warning",
    "WARN": "warning",

    "DEGRADED": "degraded",

    "PARTIAL_FAILURE":
        "partial_failure",

    "PARTIAL_SUCCESS":
        "partial_success",

    "UNAVAILABLE":
        "unavailable",

    "UNHEALTHY":
        "unhealthy",

    "DOWN":
        "unavailable",

    "NOT_CONFIGURED":
        "not_configured",

    "DISCONNECTED":
        "disconnected",

    "CIRCUIT_OPEN":
        "circuit_open",
}


_CONTAINER_KEYS = {
    "details",
    "detail",

    "dependencies",
    "dependency_results",

    "services",
    "service_results",

    "checks",
    "health_checks",

    "integrations",

    "downstream",
    "downstreams",

    "components",

    "providers",
    "subsystems",

    "external_services",
}


_STATUS_KEYS = {
    "status",
    "outcome",
    "state",
    "result",
}


_NAME_KEYS = (
    "dependency",
    "service",
    "provider",
    "component",
    "name",
)


_OPERATION_KEYS = (
    "operation",
    "action",
    "check",
    "method",
)


_REASON_KEYS = (
    "failure_code",
    "error_code",
    "code",
    "reason",
    "error",
    "message",
)


_GENERIC_NAMES = {
    "data",
    "payload",
    "response",
    "details",
    "detail",
    "services",
    "dependencies",
    "checks",
    "components",
    "integrations",
}


_UUID_RE = re.compile(
    r"^[0-9a-fA-F]{8}-"
    r"[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{12}$"
)


# ============================================================
# Normalization
# ============================================================

def _normalize_token(
    value: Any,
) -> str:
    if not isinstance(
        value,
        str,
    ):
        return ""

    return (
        value
        .strip()
        .upper()
        .replace("-", "_")
        .replace(" ", "_")
    )


def _canonical_outcome(
    value: Any,
):
    token = _normalize_token(
        value
    )

    if token in _SUCCESS:
        return "success"

    return _FAILURE_MAP.get(
        token
    )


def _requires_attention(
    outcome: str,
) -> bool:
    return (
        outcome != "success"
    )


def _safe_label(
    value: Any,
    *,
    fallback: str,
    limit: int = 64,
) -> str:
    text = str(
        value or ""
    ).strip()

    if not text:
        return fallback

    if (
        _UUID_RE.match(text)
        or text.isdigit()
    ):
        return fallback

    text = re.sub(
        r"[^a-zA-Z0-9_.:-]+",
        "_",
        text,
    )

    text = text.strip(
        "_.:-"
    ).lower()

    if not text:
        return fallback

    return text[:limit]


def _first_string(
    item: dict,
    keys,
):
    for key in keys:
        value = item.get(
            key
        )

        if isinstance(
            value,
            str,
        ):
            value = value.strip()

            if value:
                return value

    return None


# ============================================================
# Detector
# ============================================================

def _walk_operational_value(
    value,
    *,
    path,
    inherited_name=None,
    depth=0,
):
    if depth > 6:
        return []

    results = []

    if isinstance(
        value,
        list,
    ):
        for index, item in enumerate(
            value
        ):
            results.extend(
                _walk_operational_value(
                    item,
                    path=(
                        path
                        + [
                            str(index)
                        ]
                    ),
                    inherited_name=(
                        inherited_name
                    ),
                    depth=depth + 1,
                )
            )

        return results

    if not isinstance(
        value,
        dict,
    ):
        return results


    explicit_name = (
        _first_string(
            value,
            _NAME_KEYS,
        )
    )

    dependency = (
        explicit_name
        or inherited_name
    )

    if not dependency:
        for part in reversed(
            path
        ):
            if (
                part
                and part.lower()
                not in _GENERIC_NAMES
                and not part.isdigit()
            ):
                dependency = part
                break

    dependency = _safe_label(
        dependency,
        fallback="unknown",
    )


    operation = (
        _first_string(
            value,
            _OPERATION_KEYS,
        )
        or (
            path[-1]
            if path
            else "response_detail"
        )
    )

    operation = _safe_label(
        operation,
        fallback="response_detail",
        limit=80,
    )


    # --------------------------------------------------------
    # Normal status/outcome/state/result fields
    # --------------------------------------------------------

    for status_key in (
        "status",
        "outcome",
        "state",
        "result",
    ):
        if status_key not in value:
            continue

        outcome = _canonical_outcome(
            value.get(
                status_key
            )
        )

        if not outcome:
            continue

        reason = (
            _first_string(
                value,
                _REASON_KEYS,
            )
        )

        results.append({
            "dependency":
                dependency,

            "operation":
                operation,

            "outcome":
                outcome,

            "raw_status":
                str(
                    value.get(
                        status_key
                    )
                )[:80],

            "reason":
                (
                    reason[:500]
                    if reason
                    else None
                ),

            "path":
                ".".join(
                    path
                )[:240],
        })

        break


    # --------------------------------------------------------
    # orthanc_status=FAILED 같은 형태
    # --------------------------------------------------------

    for key, child in value.items():
        if (
            isinstance(
                child,
                str,
            )
            and key.lower().endswith(
                "_status"
            )
        ):
            outcome = (
                _canonical_outcome(
                    child
                )
            )

            if outcome:
                dep = (
                    key[
                        :-len(
                            "_status"
                        )
                    ]
                )

                results.append({
                    "dependency":
                        _safe_label(
                            dep,
                            fallback=(
                                dependency
                            ),
                        ),

                    "operation":
                        operation,

                    "outcome":
                        outcome,

                    "raw_status":
                        child[:80],

                    "reason":
                        None,

                    "path":
                        ".".join(
                            path
                            + [key]
                        )[:240],
                })


    # --------------------------------------------------------
    # Children
    # --------------------------------------------------------

    for key, child in value.items():
        if not isinstance(
            child,
            (
                dict,
                list,
            ),
        ):
            continue

        child_name = (
            dependency
        )

        if (
            key.lower()
            not in _GENERIC_NAMES
            and not key.isdigit()
        ):
            child_name = key

        results.extend(
            _walk_operational_value(
                child,
                path=(
                    path
                    + [key]
                ),
                inherited_name=(
                    child_name
                ),
                depth=depth + 1,
            )
        )

    return results


def extract_dependency_results(
    payload,
):
    """Extract operational dependency outcomes from one API response.

    Important:
    - We do NOT scan arbitrary arrays of normal business records.
    - Automatic scanning starts from known operational containers.
    - When the top-level response explicitly says SUCCESS/OK/etc,
      direct child service dictionaries are also inspected.
    """

    if not isinstance(
        payload,
        dict,
    ):
        return []


    top_outcome = None

    for key in _STATUS_KEYS:
        if key in payload:
            top_outcome = (
                _canonical_outcome(
                    payload.get(
                        key
                    )
                )
            )

            if top_outcome:
                break


    candidates = []


    # --------------------------------------------------------
    # Known operational containers anywhere in shallow dict
    # --------------------------------------------------------

    def find_containers(
        item,
        *,
        path,
        depth,
    ):
        if (
            depth > 3
            or not isinstance(
                item,
                dict,
            )
        ):
            return

        for key, child in item.items():
            if (
                key.lower()
                in _CONTAINER_KEYS
                and isinstance(
                    child,
                    (
                        dict,
                        list,
                    ),
                )
            ):
                candidates.append(
                    (
                        child,
                        path + [key],
                        None,
                    )
                )

            if (
                isinstance(
                    child,
                    dict,
                )
                and depth < 3
            ):
                find_containers(
                    child,
                    path=(
                        path
                        + [key]
                    ),
                    depth=depth + 1,
                )


    find_containers(
        payload,
        path=[],
        depth=0,
    )


    # --------------------------------------------------------
    # Outer SUCCESS but direct child service says FAILED
    #
    # {
    #   "status": "SUCCESS",
    #   "notification": {"status": "FAILED"}
    # }
    # --------------------------------------------------------

    if top_outcome == "success":
        for key, child in payload.items():
            if key.lower() in (
                _STATUS_KEYS
                | _CONTAINER_KEYS
            ):
                continue

            if isinstance(
                child,
                dict,
            ):
                child_status = None

                for status_key in (
                    "status",
                    "outcome",
                    "state",
                    "result",
                ):
                    if (
                        status_key
                        in child
                    ):
                        child_status = (
                            _canonical_outcome(
                                child.get(
                                    status_key
                                )
                            )
                        )
                        break

                if child_status:
                    candidates.append(
                        (
                            child,
                            [key],
                            key,
                        )
                    )


    # --------------------------------------------------------
    # top-level xxx_status
    # --------------------------------------------------------

    direct_status_results = []

    for key, value in payload.items():
        if (
            isinstance(
                value,
                str,
            )
            and key.lower().endswith(
                "_status"
            )
        ):
            outcome = (
                _canonical_outcome(
                    value
                )
            )

            if outcome:
                direct_status_results.append({
                    "dependency":
                        _safe_label(
                            key[
                                :-len(
                                    "_status"
                                )
                            ],
                            fallback=(
                                "unknown"
                            ),
                        ),

                    "operation":
                        "response_summary",

                    "outcome":
                        outcome,

                    "raw_status":
                        value[:80],

                    "reason":
                        None,

                    "path":
                        key[:240],
                })


    results = list(
        direct_status_results
    )

    for (
        candidate,
        path,
        name,
    ) in candidates:
        results.extend(
            _walk_operational_value(
                candidate,
                path=path,
                inherited_name=name,
            )
        )


    # --------------------------------------------------------
    # de-duplicate
    # --------------------------------------------------------

    unique = []

    seen = set()

    for result in results:
        key = (
            result[
                "dependency"
            ],
            result[
                "operation"
            ],
            result[
                "outcome"
            ],
            result[
                "path"
            ],
        )

        if key in seen:
            continue

        seen.add(
            key
        )

        unique.append(
            result
        )

    return unique


# ============================================================
# Metric / Audit / Log
# ============================================================

def _metric(
    result,
):
    DEPENDENCY_RESULTS.labels(
        dependency=(
            _safe_label(
                result.get(
                    "dependency"
                ),
                fallback="unknown",
            )
        ),

        operation=(
            _safe_label(
                result.get(
                    "operation"
                ),
                fallback="unknown",
                limit=80,
            )
        ),

        outcome=(
            _safe_label(
                result.get(
                    "outcome"
                ),
                fallback="unknown",
            )
        ),
    ).inc()


def _request_route(
    request,
):
    match = getattr(
        request,
        "resolver_match",
        None,
    )

    route = getattr(
        match,
        "route",
        None,
    )

    if route:
        return str(
            route
        )[:128]

    return "api_request"


def _record_incident(
    *,
    request,
    http_status,
    failures,
):
    request_id = getattr(
        request,
        "request_id",
        None,
    )

    route = (
        _request_route(
            request
        )
    )

    compact_failures = []

    for item in failures[:20]:
        compact_failures.append({
            "dependency":
                item.get(
                    "dependency"
                ),

            "operation":
                item.get(
                    "operation"
                ),

            "outcome":
                item.get(
                    "outcome"
                ),

            "raw_status":
                item.get(
                    "raw_status"
                ),

            "reason":
                item.get(
                    "reason"
                ),

            "path":
                item.get(
                    "path"
                ),
        })


    summary = ", ".join(
        (
            f"{item['dependency']}="
            f"{item['outcome']}"
        )
        for item
        in compact_failures[:6]
    )

    reason = (
        f"{len(failures)} internal "
        f"dependency result(s) require "
        f"attention"
    )

    if summary:
        reason += (
            ": "
            + summary
        )


    log_payload = {
        "event":
            "DEPENDENCY_DEGRADED",

        "http_status":
            http_status,

        "route":
            route,

        "request_id":
            request_id,

        "failures":
            compact_failures,
    }


    # Loki / container structured warning.
    logger.warning(
        "BRAINON_DEPENDENCY_DEGRADED %s",
        json.dumps(
            log_payload,
            ensure_ascii=False,
            default=str,
        ),
    )


    # Audit persistence must NEVER turn a successful
    # business response into an error.
    try:
        record_audit_event(
            source_service=(
                "backend-observability"
            ),

            action=(
                "DEPENDENCY_DEGRADED"
            ),

            resource_type=(
                "api_response"
            ),

            resource_id=route,

            outcome="WARNING",

            request=request,

            reason=reason[:2000],

            after_json={
                "http_status":
                    http_status,

                "route":
                    route,

                "failures":
                    compact_failures,
            },
        )

    except Exception:
        logger.exception(
            "DEPENDENCY_AUDIT_WRITE_FAILED "
            "request_id=%s",
            request_id,
        )


def record_dependency_result(
    *,
    dependency,
    operation,
    outcome,
    request=None,
    reason=None,
    metadata=None,
):
    """Explicit instrumentation helper for dependency clients.

    Orthanc / FCM / AI / DUR / other adapters can call this when they
    know the downstream result even if that result is not returned in
    the API response.
    """

    canonical = (
        _canonical_outcome(
            outcome
        )
    )

    if not canonical:
        canonical = (
            _safe_label(
                outcome,
                fallback="unknown",
            )
        )

    result = {
        "dependency":
            _safe_label(
                dependency,
                fallback="unknown",
            ),

        "operation":
            _safe_label(
                operation,
                fallback="unknown",
                limit=80,
            ),

        "outcome":
            canonical,

        "raw_status":
            str(
                outcome
            )[:80],

        "reason":
            (
                str(reason)[:500]
                if reason
                else None
            ),

        "path":
            "explicit",
    }

    _metric(
        result
    )

    if (
        request is not None
        and _requires_attention(
            canonical
        )
    ):
        _record_incident(
            request=request,
            http_status=None,
            failures=[
                {
                    **result,
                    "metadata":
                        metadata,
                }
            ],
        )


# ============================================================
# Middleware
# ============================================================

class DependencyOutcomeObservabilityMiddleware:
    """Observe hidden downstream failures inside successful responses."""

    def __init__(
        self,
        get_response,
    ):
        self.get_response = (
            get_response
        )

    def __call__(
        self,
        request,
    ):
        response = self.get_response(
            request
        )

        try:
            status_code = int(
                response.status_code
            )

            # HTTP failures are already covered by
            # HttpPrometheusMetricsMiddleware.
            #
            # Here we care specifically about:
            #
            # HTTP 2xx / outer SUCCESS
            #     +
            # nested service FAILED/TIMEOUT/etc.
            if not (
                200
                <= status_code
                < 300
            ):
                return response


            payload = getattr(
                response,
                "data",
                None,
            )


            # Django JsonResponse fallback
            if payload is None:
                content_type = (
                    response.get(
                        "Content-Type",
                        ""
                    )
                    or ""
                )

                if (
                    "application/json"
                    in content_type.lower()
                    and not getattr(
                        response,
                        "streaming",
                        False,
                    )
                ):
                    content = (
                        getattr(
                            response,
                            "content",
                            b"",
                        )
                    )

                    # Operational summaries should be small.
                    # Do not parse very large responses.
                    if (
                        content
                        and len(content)
                        <= 2_000_000
                    ):
                        try:
                            payload = (
                                json.loads(
                                    content.decode(
                                        "utf-8"
                                    )
                                )
                            )

                        except (
                            UnicodeError,
                            json.JSONDecodeError,
                        ):
                            payload = None


            results = (
                extract_dependency_results(
                    payload
                )
            )


            if not results:
                return response


            for result in results:
                _metric(
                    result
                )


            failures = [
                result
                for result
                in results
                if _requires_attention(
                    result[
                        "outcome"
                    ]
                )
            ]


            if failures:
                _record_incident(
                    request=request,
                    http_status=(
                        status_code
                    ),
                    failures=failures,
                )


        except Exception:
            # Observability must never alter the API response.
            logger.exception(
                "DEPENDENCY_RESPONSE_OBSERVABILITY_FAILED "
                "request_id=%s",
                getattr(
                    request,
                    "request_id",
                    None,
                ),
            )


        return response

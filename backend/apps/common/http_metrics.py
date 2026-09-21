"""HTTP-level Prometheus metrics for BrainOn.

This module deliberately supplements the existing BrainOn metrics
implementation instead of replacing it.
"""

from __future__ import annotations

import os
import time

from prometheus_client import (
    REGISTRY,
    CollectorRegistry,
    Counter,
    Histogram,
    generate_latest,
    multiprocess,
)


HTTP_REQUESTS = Counter(
    "brainon_http_requests",
    "Total BrainOn HTTP API requests.",
    [
        "method",
        "route",
        "status_class",
    ],
)


HTTP_DURATION = Histogram(
    "brainon_http_request_duration_seconds",
    "BrainOn HTTP API request duration in seconds.",
    [
        "method",
        "route",
    ],
    buckets=(
        0.005,
        0.01,
        0.025,
        0.05,
        0.1,
        0.25,
        0.5,
        1.0,
        2.5,
        5.0,
        10.0,
    ),
)


class HttpPrometheusMetricsMiddleware:
    """Measure normalized /api/ traffic.

    Resolver route templates are used instead of raw request paths,
    so patient UUIDs and other identifiers never become Prometheus
    labels.
    """

    EXCLUDED = {
        "/api/v1/health/",
    }

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
        measure = (
            request.path.startswith(
                "/api/"
            )
            and request.path
            not in self.EXCLUDED
        )

        if not measure:
            return self.get_response(
                request
            )

        started = (
            time.perf_counter()
        )

        response = self.get_response(
            request
        )

        elapsed = (
            time.perf_counter()
            - started
        )

        match = getattr(
            request,
            "resolver_match",
            None,
        )

        route = (
            getattr(
                match,
                "route",
                None,
            )
            or "unmatched"
        )

        code = int(
            response.status_code
        )

        status_class = (
            f"{code // 100}xx"
        )

        HTTP_REQUESTS.labels(
            method=request.method,
            route=route,
            status_class=status_class,
        ).inc()

        HTTP_DURATION.labels(
            method=request.method,
            route=route,
        ).observe(
            elapsed
        )

        return response


def render_http_prometheus() -> str:
    """Render HTTP metrics.

    Gunicorn uses Prometheus multiprocess mode.
    Single-process execution, including tests, falls back to REGISTRY.
    """

    multiproc_dir = (
        os.getenv(
            "PROMETHEUS_MULTIPROC_DIR",
            "",
        )
        .strip()
    )

    if multiproc_dir:
        registry = (
            CollectorRegistry()
        )

        multiprocess.MultiProcessCollector(
            registry
        )

    else:
        registry = REGISTRY

    return (
        generate_latest(
            registry
        )
        .decode(
            "utf-8",
            errors="replace",
        )
    )

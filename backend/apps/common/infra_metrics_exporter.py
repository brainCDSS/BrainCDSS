"""BrainOn infrastructure Prometheus exporter.

Read-only operational probes:
- Django Backend
- Frontend
- PostgreSQL
- RabbitMQ
- Orthanc / PACS
- AI Inference
- Prometheus
- Loki
- Grafana

No clinical DB writes are performed.
"""

from __future__ import annotations

import base64
import logging
import os
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor

import psycopg

from prometheus_client import (
    Counter,
    Gauge,
    start_http_server,
)


logging.basicConfig(
    level=os.getenv(
        "LOG_LEVEL",
        "INFO",
    ),
    format=(
        "%(asctime)s "
        "%(levelname)s "
        "%(name)s "
        "%(message)s"
    ),
)

logger = logging.getLogger(
    "brainon.infra.metrics"
)


# ============================================================
# Prometheus metrics
# ============================================================

SERVICE_UP = Gauge(
    "brainon_service_up",
    "BrainOn service availability.",
    ["service"],
)

SERVICE_LATENCY = Gauge(
    "brainon_service_probe_duration_seconds",
    "Latest BrainOn service probe duration.",
    ["service"],
)

SERVICE_LAST_SUCCESS = Gauge(
    "brainon_service_last_success_unixtime",
    "Unix time of latest successful service probe.",
    ["service"],
)

SERVICE_FAILURES = Counter(
    "brainon_service_probe_failures",
    "Total BrainOn service health probe failures.",
    ["service"],
)


POSTGRES_SIZE = Gauge(
    "brainon_postgres_database_size_bytes",
    "Current BrainOn PostgreSQL database size.",
)

POSTGRES_CONNECTIONS = Gauge(
    "brainon_postgres_connections",
    "Current PostgreSQL connections to BrainOn database.",
)

POSTGRES_CACHE_HIT_RATIO = Gauge(
    "brainon_postgres_cache_hit_ratio",
    "PostgreSQL block cache hit ratio.",
)

POSTGRES_XACT_COMMIT = Gauge(
    "brainon_postgres_xact_commit_total",
    "PostgreSQL committed transactions.",
)

POSTGRES_XACT_ROLLBACK = Gauge(
    "brainon_postgres_xact_rollback_total",
    "PostgreSQL rolled back transactions.",
)

POSTGRES_DEADLOCKS = Gauge(
    "brainon_postgres_deadlocks_total",
    "PostgreSQL deadlocks.",
)

POSTGRES_QUERY_LATENCY = Gauge(
    "brainon_postgres_probe_duration_seconds",
    "Duration of monitoring PostgreSQL probe.",
)


# ============================================================
# Helpers
# ============================================================

_token_lock = threading.Lock()

_cached_id_token = None
_cached_id_token_until = 0.0


def _set_result(
    service,
    *,
    ok,
    elapsed,
):
    SERVICE_UP.labels(
        service=service,
    ).set(
        1 if ok else 0
    )

    SERVICE_LATENCY.labels(
        service=service,
    ).set(
        elapsed
    )

    if ok:
        SERVICE_LAST_SUCCESS.labels(
            service=service,
        ).set(
            time.time()
        )
    else:
        SERVICE_FAILURES.labels(
            service=service,
        ).inc()


def _basic_auth(
    username,
    password,
):
    raw = (
        f"{username}:{password}"
        .encode("utf-8")
    )

    return (
        "Basic "
        + base64.b64encode(
            raw
        ).decode("ascii")
    )


def _cloud_run_token():
    global _cached_id_token
    global _cached_id_token_until

    now = time.monotonic()

    with _token_lock:

        if (
            _cached_id_token
            and now
            < _cached_id_token_until
        ):
            return _cached_id_token

        from google.auth.transport.requests import (
            Request,
        )

        from google.oauth2 import (
            id_token,
        )

        audience = (
            os.getenv(
                "INFERENCE_AUTH_AUDIENCE",
                "",
            ).strip()
            or os.getenv(
                "INFERENCE_API_URL",
                "",
            ).strip()
        )

        token = (
            id_token.fetch_id_token(
                Request(),
                audience,
            )
        )

        _cached_id_token = token

        # ID tokens are normally much longer-lived.
        # Refresh conservatively every 30 minutes.
        _cached_id_token_until = (
            now
            + 1800
        )

        return token


def _probe_http(
    service,
    url,
    *,
    headers=None,
    timeout=5,
):
    started = (
        time.perf_counter()
    )

    try:
        request = (
            urllib.request.Request(
                url,
                headers=(
                    headers
                    or {}
                ),
                method="GET",
            )
        )

        with urllib.request.urlopen(
            request,
            timeout=timeout,
        ) as response:

            status = int(
                response.status
            )

            # Read only a small amount.
            response.read(
                4096
            )

        ok = (
            200
            <= status
            < 400
        )

        elapsed = (
            time.perf_counter()
            - started
        )

        _set_result(
            service,
            ok=ok,
            elapsed=elapsed,
        )

        return


    except Exception as exc:

        elapsed = (
            time.perf_counter()
            - started
        )

        _set_result(
            service,
            ok=False,
            elapsed=elapsed,
        )

        logger.warning(
            "SERVICE_PROBE_FAILED "
            "service=%s "
            "error=%s",
            service,
            type(exc).__name__,
        )


# ============================================================
# PostgreSQL
# ============================================================

def _probe_postgres():
    service = "postgresql"

    started = (
        time.perf_counter()
    )

    try:
        connection = (
            psycopg.connect(
                dbname=os.environ[
                    "POSTGRES_DB"
                ],
                user=os.environ[
                    "POSTGRES_USER"
                ],
                password=os.environ[
                    "POSTGRES_PASSWORD"
                ],
                host=os.environ[
                    "POSTGRES_HOST"
                ],
                port=int(
                    os.getenv(
                        "POSTGRES_PORT",
                        "5432",
                    )
                ),
                connect_timeout=5,
            )
        )

        try:
            with connection.cursor() as cursor:

                cursor.execute(
                    """
                    SELECT
                        numbackends,
                        xact_commit,
                        xact_rollback,
                        blks_read,
                        blks_hit,
                        deadlocks
                    FROM pg_stat_database
                    WHERE datname = current_database()
                    """
                )

                row = cursor.fetchone()

                cursor.execute(
                    """
                    SELECT
                        pg_database_size(
                            current_database()
                        )
                    """
                )

                size_row = (
                    cursor.fetchone()
                )

            if row:

                (
                    numbackends,
                    xact_commit,
                    xact_rollback,
                    blks_read,
                    blks_hit,
                    deadlocks,
                ) = row

                POSTGRES_CONNECTIONS.set(
                    float(
                        numbackends
                        or 0
                    )
                )

                POSTGRES_XACT_COMMIT.set(
                    float(
                        xact_commit
                        or 0
                    )
                )

                POSTGRES_XACT_ROLLBACK.set(
                    float(
                        xact_rollback
                        or 0
                    )
                )

                POSTGRES_DEADLOCKS.set(
                    float(
                        deadlocks
                        or 0
                    )
                )

                reads = float(
                    blks_read
                    or 0
                )

                hits = float(
                    blks_hit
                    or 0
                )

                denominator = (
                    reads
                    + hits
                )

                ratio = (
                    hits / denominator
                    if denominator > 0
                    else 1.0
                )

                POSTGRES_CACHE_HIT_RATIO.set(
                    ratio
                )


            if size_row:

                POSTGRES_SIZE.set(
                    float(
                        size_row[0]
                        or 0
                    )
                )


        finally:
            connection.close()


        elapsed = (
            time.perf_counter()
            - started
        )

        POSTGRES_QUERY_LATENCY.set(
            elapsed
        )

        _set_result(
            service,
            ok=True,
            elapsed=elapsed,
        )


    except Exception as exc:

        elapsed = (
            time.perf_counter()
            - started
        )

        POSTGRES_QUERY_LATENCY.set(
            elapsed
        )

        _set_result(
            service,
            ok=False,
            elapsed=elapsed,
        )

        logger.warning(
            "POSTGRES_PROBE_FAILED "
            "error=%s",
            type(exc).__name__,
        )


# ============================================================
# Service probes
# ============================================================

def _probe_backend():
    _probe_http(
        "backend",
        (
            "http://backend:8080/"
            "api/v1/health/"
        ),
    )


def _probe_frontend():
    _probe_http(
        "frontend",
        "http://frontend:8080/",
    )


def _probe_prometheus():
    _probe_http(
        "prometheus",
        (
            "http://prometheus:9090/"
            "-/healthy"
        ),
    )


def _probe_loki():
    _probe_http(
        "loki",
        "http://loki:3100/ready",
    )


def _probe_grafana():
    _probe_http(
        "grafana",
        (
            "http://grafana:3000/"
            "api/health"
        ),
    )


def _probe_rabbitmq():
    username = (
        os.getenv(
            "RABBITMQ_DEFAULT_USER",
            "brainon",
        )
    )

    password = (
        os.getenv(
            "RABBITMQ_DEFAULT_PASS",
            "",
        )
    )

    headers = {
        "Authorization":
            _basic_auth(
                username,
                password,
            ),
    }

    _probe_http(
        "rabbitmq",
        (
            "http://rabbitmq:15672/"
            "api/health/checks/alarms"
        ),
        headers=headers,
    )


def _probe_orthanc():
    base = (
        os.getenv(
            "ORTHANC_URL",
            "http://orthanc:8042",
        )
        .rstrip("/")
    )

    username = (
        os.getenv(
            "ORTHANC_USERNAME",
            "",
        )
    )

    password = (
        os.getenv(
            "ORTHANC_PASSWORD",
            "",
        )
    )

    headers = {}

    if username:
        headers[
            "Authorization"
        ] = _basic_auth(
            username,
            password,
        )

    _probe_http(
        "orthanc",
        base + "/system",
        headers=headers,
    )


def _probe_inference():
    base = (
        os.getenv(
            "INFERENCE_API_URL",
            "",
        )
        .strip()
        .rstrip("/")
    )

    if not base:
        _set_result(
            "ai_inference",
            ok=False,
            elapsed=0,
        )
        return


    headers = {}


    use_id_token = (
        os.getenv(
            "INFERENCE_USE_ID_TOKEN",
            "true",
        )
        .strip()
        .lower()
        in {
            "1",
            "true",
            "yes",
            "on",
        }
    )


    try:
        if (
            use_id_token
            and base.startswith(
                "https://"
            )
        ):
            headers[
                "Authorization"
            ] = (
                "Bearer "
                + _cloud_run_token()
            )

    except Exception as exc:

        logger.warning(
            "INFERENCE_ID_TOKEN_FAILED "
            "error=%s",
            type(exc).__name__,
        )

        _set_result(
            "ai_inference",
            ok=False,
            elapsed=0,
        )

        return


    _probe_http(
        "ai_inference",
        base + "/health",
        headers=headers,
        timeout=10,
    )


# ============================================================
# Probe cycle
# ============================================================

PROBES = (
    _probe_backend,
    _probe_frontend,
    _probe_postgres,
    _probe_rabbitmq,
    _probe_orthanc,
    _probe_inference,
    _probe_prometheus,
    _probe_loki,
    _probe_grafana,
)


def probe_cycle():

    with ThreadPoolExecutor(
        max_workers=len(
            PROBES
        ),
    ) as executor:

        futures = [
            executor.submit(
                probe
            )
            for probe
            in PROBES
        ]

        for future in futures:

            try:
                future.result()

            except Exception:
                logger.exception(
                    "UNEXPECTED_PROBE_ERROR"
                )


def monitor_loop():

    while True:

        started = (
            time.monotonic()
        )

        probe_cycle()

        elapsed = (
            time.monotonic()
            - started
        )

        time.sleep(
            max(
                5,
                15 - elapsed,
            )
        )


def main():

    start_http_server(
        9810,
        addr="0.0.0.0",
    )

    logger.info(
        "BrainOn infra exporter "
        "listening on :9810"
    )

    probe_cycle()

    monitor_loop()


if __name__ == "__main__":
    main()

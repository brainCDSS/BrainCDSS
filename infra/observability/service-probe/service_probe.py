"""BrainOn operational service probe.

Read-only checks only.

Metrics
-------
brainon_service_health_state:
    1  = healthy
    0  = unhealthy
   -1  = endpoint reachable but local probe authentication unavailable

brainon_service_reachable:
    1 = endpoint/database reached
    0 = unreachable

brainon_service_probe_duration_seconds

brainon_service_http_status

brainon_service_auth_ready

brainon_postgres_connections

brainon_postgres_database_size_bytes
"""

from __future__ import annotations

import base64
import concurrent.futures
import os
import time
import urllib.error
import urllib.request

from http.server import (
    BaseHTTPRequestHandler,
    ThreadingHTTPServer,
)

import psycopg


PORT = int(
    os.getenv(
        "SERVICE_PROBE_PORT",
        "9810",
    )
)


def _env(
    name,
    default="",
):
    return (
        os.getenv(
            name,
            default,
        )
        or default
    ).strip()


def _bool_env(
    name,
    default=False,
):
    value = _env(
        name,
        "true"
        if default
        else "false",
    ).lower()

    return value in {
        "1",
        "true",
        "yes",
        "on",
    }


def _http_request(
    *,
    service,
    url,
    headers=None,
    timeout=5,
    healthy_codes=None,
):
    started = time.perf_counter()

    headers = (
        headers
        or {}
    )

    healthy_codes = (
        healthy_codes
        or range(
            200,
            300,
        )
    )

    status = 0
    reachable = 0
    health = 0

    try:
        request = urllib.request.Request(
            url,
            headers=headers,
            method="GET",
        )

        with urllib.request.urlopen(
            request,
            timeout=timeout,
        ) as response:

            status = int(
                response.status
            )

            reachable = 1

            health = (
                1
                if status
                in healthy_codes
                else 0
            )

    except urllib.error.HTTPError as exc:

        status = int(
            exc.code
        )

        # HTTP response 자체를 받았으므로
        # network endpoint는 reachable.
        reachable = 1

        health = (
            1
            if status
            in healthy_codes
            else 0
        )

    except Exception:
        status = 0
        reachable = 0
        health = 0


    return {
        "service":
            service,

        "health":
            health,

        "reachable":
            reachable,

        "duration":
            (
                time.perf_counter()
                - started
            ),

        "http_status":
            status,

        "auth_ready":
            1,
    }


def probe_backend():
    base = _env(
        "BACKEND_URL",
        "http://backend:8080",
    ).rstrip("/")

    return _http_request(
        service="backend",
        url=(
            base
            + "/api/v1/health/"
        ),
    )


def probe_frontend():
    base = _env(
        "FRONTEND_URL",
        "http://frontend:8080",
    ).rstrip("/")

    return _http_request(
        service="frontend",
        url=(
            base
            + "/"
        ),
    )


def probe_grafana():
    base = _env(
        "GRAFANA_URL",
        "http://grafana:3000",
    ).rstrip("/")

    return _http_request(
        service="grafana",
        url=(
            base
            + "/api/health"
        ),
    )


def probe_loki():
    base = _env(
        "LOKI_URL",
        "http://loki:3100",
    ).rstrip("/")

    return _http_request(
        service="loki",
        url=(
            base
            + "/ready"
        ),
    )


def probe_prometheus():
    base = _env(
        "PROMETHEUS_URL",
        "http://prometheus:9090",
    ).rstrip("/")

    return _http_request(
        service="prometheus",
        url=(
            base
            + "/-/ready"
        ),
    )


def probe_orthanc():
    base = _env(
        "ORTHANC_URL",
        "http://orthanc:8042",
    ).rstrip("/")

    username = _env(
        "ORTHANC_USERNAME"
    )

    password = _env(
        "ORTHANC_PASSWORD"
    )

    headers = {}

    if (
        username
        and password
    ):
        token = base64.b64encode(
            (
                username
                + ":"
                + password
            ).encode(
                "utf-8"
            )
        ).decode(
            "ascii"
        )

        headers[
            "Authorization"
        ] = (
            "Basic "
            + token
        )


    return _http_request(
        service="orthanc",
        url=(
            base
            + "/system"
        ),
        headers=headers,
    )


def _try_google_id_token(
    audience,
):
    try:
        from google.auth.transport.requests import (
            Request,
        )

        from google.oauth2 import (
            id_token,
        )

        token = (
            id_token.fetch_id_token(
                Request(),
                audience,
            )
        )

        if token:
            return token

    except Exception:
        pass

    return None


def probe_ai_inference():
    base = _env(
        "INFERENCE_API_URL"
    ).rstrip("/")

    if not base:
        return {
            "service":
                "ai_inference",

            "health":
                -1,

            "reachable":
                0,

            "duration":
                0.0,

            "http_status":
                0,

            "auth_ready":
                0,
        }


    use_id_token = _bool_env(
        "INFERENCE_USE_ID_TOKEN",
        True,
    )

    headers = {}

    auth_ready = 1


    if use_id_token:
        audience = _env(
            "INFERENCE_AUTH_AUDIENCE",
            base,
        )

        token = (
            _try_google_id_token(
                audience
            )
        )

        if token:
            headers[
                "Authorization"
            ] = (
                "Bearer "
                + token
            )

        else:
            auth_ready = 0


    result = _http_request(
        service="ai_inference",
        url=(
            base
            + "/health"
        ),
        headers=headers,
        timeout=8,
    )

    result[
        "auth_ready"
    ] = auth_ready


    # Local Docker 환경에서 Cloud Run ID token을
    # 발급할 ADC가 없는 경우가 있다.
    #
    # 401/403은 서비스 endpoint는 실제로
    # 살아 있으나 probe 인증을 완료하지 못한 상태.
    if (
        use_id_token
        and not auth_ready
        and result[
            "http_status"
        ] in {
            401,
            403,
        }
    ):
        result[
            "health"
        ] = -1


    return result


def probe_postgresql():
    started = time.perf_counter()

    result = {
        "service":
            "postgresql",

        "health":
            0,

        "reachable":
            0,

        "duration":
            0.0,

        "http_status":
            0,

        "auth_ready":
            1,

        "connections":
            0,

        "db_size":
            0,
    }


    try:
        with psycopg.connect(
            dbname=_env(
                "POSTGRES_DB"
            ),

            user=_env(
                "POSTGRES_USER"
            ),

            password=_env(
                "POSTGRES_PASSWORD"
            ),

            host=_env(
                "POSTGRES_HOST"
            ),

            port=int(
                _env(
                    "POSTGRES_PORT",
                    "5432",
                )
            ),

            connect_timeout=5,

        ) as connection:

            with connection.cursor() as cursor:

                cursor.execute(
                    "SELECT 1"
                )

                cursor.fetchone()


                cursor.execute(
                    """
                    SELECT COUNT(*)
                    FROM pg_stat_activity
                    WHERE datname = current_database()
                    """
                )

                row = cursor.fetchone()

                result[
                    "connections"
                ] = int(
                    row[0]
                    if row
                    else 0
                )


                cursor.execute(
                    """
                    SELECT pg_database_size(
                        current_database()
                    )
                    """
                )

                row = cursor.fetchone()

                result[
                    "db_size"
                ] = int(
                    row[0]
                    if row
                    else 0
                )


        result[
            "health"
        ] = 1

        result[
            "reachable"
        ] = 1

    except Exception:
        result[
            "health"
        ] = 0

        result[
            "reachable"
        ] = 0


    result[
        "duration"
    ] = (
        time.perf_counter()
        - started
    )

    return result


PROBES = [
    probe_backend,
    probe_frontend,
    probe_grafana,
    probe_loki,
    probe_prometheus,
    probe_orthanc,
    probe_ai_inference,
    probe_postgresql,
]


def collect():
    results = []

    with concurrent.futures.ThreadPoolExecutor(
        max_workers=len(
            PROBES
        )
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
                results.append(
                    future.result()
                )

            except Exception:
                pass


    results.sort(
        key=lambda item:
            item[
                "service"
            ]
    )

    return results


def render_metrics():
    results = collect()

    lines = [
        "# HELP brainon_service_health_state "
        "BrainOn service health: 1 healthy, "
        "0 unhealthy, -1 auth unavailable.",

        "# TYPE brainon_service_health_state gauge",

        "# HELP brainon_service_reachable "
        "Whether service endpoint is reachable.",

        "# TYPE brainon_service_reachable gauge",

        "# HELP brainon_service_probe_duration_seconds "
        "Service probe latency.",

        "# TYPE brainon_service_probe_duration_seconds gauge",

        "# HELP brainon_service_http_status "
        "Last HTTP status returned by service probe.",

        "# TYPE brainon_service_http_status gauge",

        "# HELP brainon_service_auth_ready "
        "Whether probe authentication is available.",

        "# TYPE brainon_service_auth_ready gauge",

        "# HELP brainon_postgres_connections "
        "Current connections to BrainOn PostgreSQL database.",

        "# TYPE brainon_postgres_connections gauge",

        "# HELP brainon_postgres_database_size_bytes "
        "BrainOn PostgreSQL database size.",

        "# TYPE brainon_postgres_database_size_bytes gauge",
    ]


    for item in results:

        service = item[
            "service"
        ]

        lines.append(
            'brainon_service_health_state'
            f'{{service="{service}"}} '
            f'{item["health"]}'
        )

        lines.append(
            'brainon_service_reachable'
            f'{{service="{service}"}} '
            f'{item["reachable"]}'
        )

        lines.append(
            'brainon_service_probe_duration_seconds'
            f'{{service="{service}"}} '
            f'{item["duration"]:.6f}'
        )

        lines.append(
            'brainon_service_http_status'
            f'{{service="{service}"}} '
            f'{item["http_status"]}'
        )

        lines.append(
            'brainon_service_auth_ready'
            f'{{service="{service}"}} '
            f'{item["auth_ready"]}'
        )


        if service == "postgresql":

            lines.append(
                "brainon_postgres_connections "
                + str(
                    item.get(
                        "connections",
                        0,
                    )
                )
            )

            lines.append(
                "brainon_postgres_database_size_bytes "
                + str(
                    item.get(
                        "db_size",
                        0,
                    )
                )
            )


    return (
        "\n".join(
            lines
        )
        + "\n"
    )


class Handler(
    BaseHTTPRequestHandler
):

    def do_GET(
        self,
    ):
        if self.path not in {
            "/metrics",
            "/metrics/",
        }:
            self.send_response(
                404
            )

            self.end_headers()

            return


        body = (
            render_metrics()
            .encode(
                "utf-8"
            )
        )

        self.send_response(
            200
        )

        self.send_header(
            "Content-Type",
            (
                "text/plain; "
                "version=0.0.4; "
                "charset=utf-8"
            ),
        )

        self.send_header(
            "Content-Length",
            str(
                len(body)
            ),
        )

        self.end_headers()

        self.wfile.write(
            body
        )


    def log_message(
        self,
        format,
        *args,
    ):
        # URL / credentials 등을 console log에 남기지 않는다.
        return


def main():
    server = ThreadingHTTPServer(
        (
            "0.0.0.0",
            PORT,
        ),
        Handler,
    )

    server.serve_forever()


if __name__ == "__main__":
    main()

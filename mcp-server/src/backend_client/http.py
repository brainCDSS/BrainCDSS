"""HTTP client for the BrainOn Django internal MCP API."""

from typing import Any

import httpx

from .base import BackendClient


class HttpBackendClient(BackendClient):

    def __init__(
        self,
        base_url: str,
        token: str,
        timeout_seconds: float = 10.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.token = token.strip()
        self.timeout_seconds = timeout_seconds

        if not self.base_url:
            raise ValueError("BACKEND_URL_REQUIRED")

        if not self.token:
            raise ValueError("MCP_BACKEND_TOKEN_REQUIRED")

    def get(
        self,
        path: str,
        trace_id: str,
        params: dict[str, Any] | None = None,
    ) -> dict:
        url = f"{self.base_url}/{path.lstrip('/')}"

        response = httpx.get(
            url,
            params=params,
            headers={
                "Authorization": f"Bearer {self.token}",
                "X-Request-ID": trace_id,
                "X-Trace-ID": trace_id,
            },
            timeout=self.timeout_seconds,
        )

        response.raise_for_status()

        payload = response.json()

        if not isinstance(payload, dict):
            raise ValueError("INVALID_BACKEND_RESPONSE")

        return payload

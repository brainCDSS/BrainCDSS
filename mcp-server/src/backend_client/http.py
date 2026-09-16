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
            raise ValueError(
                "BACKEND_URL_REQUIRED"
            )

        if not self.token:
            raise ValueError(
                "MCP_BACKEND_TOKEN_REQUIRED"
            )

    def get(
        self,
        path: str,
        trace_id: str,
        params: dict[str, Any] | None = None,
        *,
        actor_id: str,
        actor_role: str,
    ) -> dict:
        url = (
            f"{self.base_url}/"
            f"{path.lstrip('/')}"
        )

        response = httpx.get(
            url,
            params=params,
            headers={
                "Authorization":
                    f"Bearer {self.token}",

                # 동일 요청을 BrainOn 전체 구간에서
                # 추적하기 위한 correlation 값.
                "X-Request-ID":
                    trace_id,

                "X-Trace-ID":
                    trace_id,

                # MCP Tool을 호출한 실제 사용자 Context.
                #
                # Django Internal API는 서비스 토큰으로
                # 보호된 내부 경계이며, 이 값은
                # 추적/Audit Context로 전달한다.
                "X-BrainOn-Actor-ID":
                    actor_id,

                "X-BrainOn-Actor-Role":
                    actor_role,
            },
            timeout=
                self.timeout_seconds,
        )

        response.raise_for_status()

        payload = response.json()

        if not isinstance(
            payload,
            dict,
        ):
            raise ValueError(
                "INVALID_BACKEND_RESPONSE"
            )

        return payload
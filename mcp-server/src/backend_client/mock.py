"""No-PHI deterministic backend used when service credentials are absent."""

from typing import Any

from .base import BackendClient


class MockBackendClient(BackendClient):

    def get(
        self,
        path: str,
        trace_id: str,
        params: dict[str, Any] | None = None,
        *,
        actor_id: str,
        actor_role: str,
    ) -> dict:
        return {
            "is_mock": True,
            "status": "NOT_IMPLEMENTED",
            "path": path,
            "trace_id": trace_id,
            "actor_id": actor_id,
            "actor_role": actor_role,
            "params": params or {},
        }
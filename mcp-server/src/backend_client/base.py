"""Django internal API boundary; implementations must never query PostgreSQL."""

from abc import ABC, abstractmethod
from typing import Any


class BackendClient(ABC):

    @abstractmethod
    def get(
        self,
        path: str,
        trace_id: str,
        params: dict[str, Any] | None = None,
    ) -> dict:
        ...

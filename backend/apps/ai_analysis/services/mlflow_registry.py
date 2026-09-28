"""Read-only MLflow Registry access for the private Cloud Run service.

The Cloud Run runtime service account obtains an audience-bound ID token at
sync time.  No service-account key or long-lived MLflow token is persisted.
"""

from __future__ import annotations

import os
import threading
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterator

from google.auth.transport.requests import Request as GoogleAuthRequest
from google.oauth2 import id_token
from mlflow.tracking import MlflowClient


class MLflowRegistryError(RuntimeError):
    """A configuration or availability error from the MLflow Registry."""


@dataclass(frozen=True)
class RegistryModelVersion:
    registered_model_name: str
    model_version: str
    run_id: str
    artifact_uri: str
    experiment_id: str
    created_at: datetime
    updated_at: datetime
    metrics: dict[str, object]
    params: dict[str, object]
    tags: dict[str, object]


# MLflow reads MLFLOW_TRACKING_TOKEN when it creates HTTP host credentials.
# Process-local serialization prevents one request's short-lived Cloud Run ID
# token from being used by another request in the same gunicorn worker.
_MLFLOW_TOKEN_LOCK = threading.Lock()


def _configured_value(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise MLflowRegistryError(f"{name} is not configured")
    return value


def _to_datetime(timestamp_ms: object) -> datetime:
    try:
        return datetime.fromtimestamp(float(timestamp_ms) / 1000, tz=timezone.utc)
    except (TypeError, ValueError, OverflowError):
        return datetime.now(timezone.utc)


@contextmanager
def _authorized_mlflow_client() -> Iterator[MlflowClient]:
    """Yield an MLflow client with a freshly minted Cloud Run ID token."""

    tracking_uri = _configured_value("MLFLOW_TRACKING_URI").rstrip("/")
    audience = _configured_value("MLFLOW_CLOUD_RUN_AUDIENCE")
    try:
        token = id_token.fetch_id_token(GoogleAuthRequest(), audience)
    except Exception as exc:  # google-auth has several transport-specific errors
        raise MLflowRegistryError("could not obtain Cloud Run ID token") from exc

    with _MLFLOW_TOKEN_LOCK:
        previous_token = os.environ.get("MLFLOW_TRACKING_TOKEN")
        os.environ["MLFLOW_TRACKING_TOKEN"] = token
        try:
            yield MlflowClient(tracking_uri=tracking_uri)
        except MLflowRegistryError:
            raise
        except Exception as exc:
            raise MLflowRegistryError("MLflow Registry request failed") from exc
        finally:
            if previous_token is None:
                os.environ.pop("MLFLOW_TRACKING_TOKEN", None)
            else:
                os.environ["MLFLOW_TRACKING_TOKEN"] = previous_token


class MLflowRegistryClient:
    """Enumerate Registry metadata without mutating MLflow state."""

    @staticmethod
    def _all_pages(fetch_page) -> list[object]:
        records: list[object] = []
        page_token = None
        while True:
            page = fetch_page(page_token)
            records.extend(page)
            page_token = getattr(page, "token", None)
            if not page_token:
                return records

    def list_model_versions(self) -> list[RegistryModelVersion]:
        records: list[RegistryModelVersion] = []
        with _authorized_mlflow_client() as client:
            registered_models = self._all_pages(
                lambda page_token: client.search_registered_models(
                    max_results=1_000,
                    page_token=page_token,
                )
            )
            for registered_model in registered_models:
                name = str(registered_model.name)
                escaped_name = name.replace("'", "\\\\'")
                versions = self._all_pages(
                    lambda page_token: client.search_model_versions(
                        f"name = '{escaped_name}'",
                        max_results=1_000,
                        page_token=page_token,
                    )
                )
                for model_version in versions:
                    run_id = str(getattr(model_version, "run_id", "") or "")
                    run = client.get_run(run_id) if run_id else None
                    run_data = getattr(run, "data", None)
                    run_info = getattr(run, "info", None)
                    version_tags = dict(getattr(model_version, "tags", None) or {})
                    run_tags = dict(getattr(run_data, "tags", None) or {})
                    records.append(
                        RegistryModelVersion(
                            registered_model_name=name,
                            model_version=str(model_version.version),
                            run_id=run_id,
                            artifact_uri=str(
                                getattr(model_version, "source", "")
                                or getattr(run_info, "artifact_uri", "")
                            ),
                            experiment_id=str(
                                getattr(run_info, "experiment_id", "") or ""
                            ),
                            created_at=_to_datetime(
                                getattr(model_version, "creation_timestamp", None)
                            ),
                            updated_at=_to_datetime(
                                getattr(
                                    model_version,
                                    "last_updated_timestamp",
                                    getattr(model_version, "creation_timestamp", None),
                                )
                            ),
                            metrics=dict(getattr(run_data, "metrics", None) or {}),
                            params=dict(getattr(run_data, "params", None) or {}),
                            tags={
                                "model_version": version_tags,
                                "run": run_tags,
                            },
                        )
                    )
        return records

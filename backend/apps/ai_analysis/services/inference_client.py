"""HTTP client for the private Cloud Run inference service."""

from __future__ import annotations

import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings


class InferenceClientError(RuntimeError):
    def __init__(self, code, message, *, retryable=False):
        super().__init__(message)
        self.code = code
        self.retryable = retryable


def call_inference(payload: dict) -> dict:
    headers = {"Content-Type": "application/json"}

    trace_id = str(
        payload.get("trace_id")
        or ""
    ).strip()

    if trace_id:
        headers["X-Request-ID"] = trace_id
        headers["X-Trace-ID"] = trace_id

    if settings.INFERENCE_USE_ID_TOKEN:
        headers["Authorization"] = f"Bearer {_identity_token()}"
    request = Request(
        settings.INFERENCE_API_URL.rstrip("/") + "/v1/inferences",
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urlopen(request, timeout=settings.INFERENCE_TIMEOUT_SECONDS) as response:
            result = json.load(response)
    except HTTPError as exc:
        raise InferenceClientError(
            "INFERENCE_HTTP_ERROR", f"inference HTTP {exc.code}", retryable=exc.code in {429, 500, 502, 503, 504}
        ) from exc
    except (URLError, TimeoutError, OSError) as exc:
        raise InferenceClientError("INFERENCE_UNAVAILABLE", "inference service unavailable", retryable=True) from exc
    except (ValueError, TypeError) as exc:
        raise InferenceClientError("INVALID_INFERENCE_RESPONSE", "invalid inference JSON") from exc
    if not isinstance(result, dict) or result.get("analysis_id") != payload["analysis_id"]:
        raise InferenceClientError("INVALID_INFERENCE_RESPONSE", "inference response identity mismatch")
    return result


_cached_identity_credentials = None


def _identity_token():
    global _cached_identity_credentials
    try:
        from google.auth import default
        from google.auth.impersonated_credentials import Credentials, IDTokenCredentials
        from google.auth.transport.requests import Request as GoogleAuthRequest
        from google.oauth2 import id_token
    except ImportError as exc:
        raise InferenceClientError("INFERENCE_AUTH_UNAVAILABLE", "google-auth is not installed") from exc

    request = GoogleAuthRequest()
    target = os.getenv("INFERENCE_IMPERSONATE_SERVICE_ACCOUNT", "").strip()
    if target:
        if _cached_identity_credentials is None:
            source_credentials, _ = default(
                scopes=["https://www.googleapis.com/auth/cloud-platform"]
            )
            impersonated = Credentials(
                source_credentials=source_credentials,
                target_principal=target,
                target_scopes=["https://www.googleapis.com/auth/cloud-platform"],
                lifetime=3600,
            )
            _cached_identity_credentials = IDTokenCredentials(
                target_credentials=impersonated,
                target_audience=settings.INFERENCE_AUTH_AUDIENCE,
                include_email=True,
            )
        if not _cached_identity_credentials.valid:
            _cached_identity_credentials.refresh(request)
        return _cached_identity_credentials.token

    # Cloud Run and Worker Pool use the attached service account metadata.
    return id_token.fetch_id_token(request, settings.INFERENCE_AUTH_AUDIENCE)

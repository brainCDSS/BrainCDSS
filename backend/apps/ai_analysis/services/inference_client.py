"""HTTP client for the private Cloud Run inference service."""

from __future__ import annotations

import json
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


_cached_identity_token = None


def _identity_token():
    global _cached_identity_token
    if _cached_identity_token is None:
        try:
            from google.auth.transport.requests import Request as GoogleAuthRequest
            from google.oauth2 import id_token
        except ImportError as exc:
            raise InferenceClientError("INFERENCE_AUTH_UNAVAILABLE", "google-auth is not installed") from exc
        _cached_identity_token = id_token.fetch_id_token(
            GoogleAuthRequest(), settings.INFERENCE_AUTH_AUDIENCE
        )
    return _cached_identity_token

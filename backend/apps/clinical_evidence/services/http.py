"""Bounded HTTPS requests, with retries only for temporary upstream failures."""
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class ExternalServiceError(Exception):
    """Safe error code only; never log URLs with keys, response bodies or tokens."""


def request_bytes(url, *, data=None, headers=None, timeout=30, attempts=3, max_bytes=8_000_000):
    for attempt in range(attempts):
        try:
            request = Request(url, data=data, headers=headers or {})
            with urlopen(request, timeout=timeout) as response:
                body = response.read(max_bytes + 1)
                if len(body) > max_bytes:
                    raise ExternalServiceError("UPSTREAM_RESPONSE_TOO_LARGE")
                return body
        except HTTPError as exc:
            if exc.code not in {408, 429, 500, 502, 503, 504}:
                raise ExternalServiceError(f"UPSTREAM_HTTP_{exc.code}") from None
        except (URLError, TimeoutError, OSError):
            pass
        if attempt + 1 < attempts:
            time.sleep(2 ** attempt)
    raise ExternalServiceError("UPSTREAM_RETRY_EXHAUSTED")

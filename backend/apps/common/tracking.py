"""User-facing error tracking code helpers.

request_id remains the canonical internal correlation identifier.

tracking_code is a shorter reference intended for users/operators.
It is derived from the first 64 bits of the request UUID and is never
used as the primary identifier.
"""

import re
import uuid


TRACKING_CODE_PATTERN = re.compile(
    r"^ERR-([0-9A-F]{16})$",
    re.IGNORECASE,
)


def build_tracking_code(request_id) -> str:
    if not request_id:
        return ""

    try:
        normalized = uuid.UUID(
            str(request_id)
        ).hex.upper()
    except (
        ValueError,
        TypeError,
        AttributeError,
    ):
        return ""

    return (
        "ERR-"
        + normalized[:16]
    )


def tracking_code_prefix(
    tracking_code,
) -> str | None:
    if not tracking_code:
        return None

    match = TRACKING_CODE_PATTERN.fullmatch(
        str(tracking_code).strip()
    )

    if not match:
        return None

    return match.group(1).upper()

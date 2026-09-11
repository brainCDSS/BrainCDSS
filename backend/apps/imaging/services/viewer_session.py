from __future__ import annotations

import hashlib
import os
from datetime import timedelta
from urllib.parse import urlencode

import jwt

from django.conf import settings
from django.utils import timezone


VIEWER_SCOPE = "dicomweb.read"

VIEWER_ISSUER = "brainon-viewer"
VIEWER_AUDIENCE = "brainon-dicomweb"

# IMPORTANT:
# User SIMPLE_JWT lifetime/settings are NOT used or modified here.
VIEWER_TOKEN_TTL_SECONDS = 300


def _viewer_signing_key() -> str:
    configured = os.getenv(
        "VIEWER_JWT_SIGNING_KEY"
    )

    if configured:
        return configured

    # Local-development fallback.
    # User JWT signing key itself is NOT reused directly.
    return hashlib.sha256(
        (
            str(settings.SECRET_KEY)
            + ":brainon-viewer-token"
        ).encode("utf-8")
    ).hexdigest()


def issue_viewer_session(
    *,
    user,
    study,
    purpose,
    include_ai_overlay,
    ai_overlay_available,
):
    now = timezone.now()

    expires_at = now + timedelta(
        seconds=VIEWER_TOKEN_TTL_SECONDS
    )

    claims = {
        "token_type": "viewer",
        "sub": str(user.id),

        # Study binding
        "study_id": str(study.id),
        "study_instance_uid":
            study.study_instance_uid,

        # DICOMweb authorization
        "scope": VIEWER_SCOPE,

        "purpose": purpose,
        "include_ai_overlay":
            bool(include_ai_overlay),

        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
        "iss": VIEWER_ISSUER,
        "aud": VIEWER_AUDIENCE,
    }

    token = jwt.encode(
        claims,
        _viewer_signing_key(),
        algorithm="HS256",
    )

    viewer_base_url = os.getenv(
        "OHIF_VIEWER_BASE_URL",
        "/viewer",
    ).rstrip("/")

    dicomweb_base_url = os.getenv(
        "DICOMWEB_BASE_URL",
        "/dicom-web",
    ).rstrip("/")

    query = urlencode({
        "StudyInstanceUIDs":
            study.study_instance_uid,
    })

    launch_url = (
        f"{viewer_base_url}?{query}"
    )

    return {
        # Canonical Backend contract
        "launch_url": launch_url,
        "dicomweb_base_url":
            dicomweb_base_url,
        "viewer_token": token,
        "expires_at": expires_at,
        "ai_overlay_available":
            bool(ai_overlay_available),

        # Current Frontend compatibility.
        # Do not create DB fields for these.
        "viewer_url": launch_url,
        "token": token,
    }

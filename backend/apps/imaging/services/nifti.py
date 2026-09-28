from datetime import timedelta
from urllib.parse import unquote

import google.auth
from google.auth import credentials as google_credentials
from google.auth import impersonated_credentials
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.http import FileResponse, Http404

from apps.imaging.models import NiftiArtifact


ANALYSIS_INPUTS = {
    "HEMORRHAGIC_STROKE_CT": ("CT",),
    "ISCHEMIC_STROKE_DWI_ADC": ("DWI", "ADC"),
    "CEREBRAL_ANEURYSM_MRA": ("MRA",),
}


def study_input_bundles(study):
    artifacts = {
        artifact.role: artifact
        for artifact in NiftiArtifact.objects.filter(series__study=study).select_related("series")
    }
    bundles = []
    for analysis_type, roles in ANALYSIS_INPUTS.items():
        selected = [artifacts.get(role) for role in roles]
        ready = all(selected)
        bundles.append({
            "analysis_type": analysis_type,
            "ready": ready,
            "missing_roles": [role for role, item in zip(roles, selected) if item is None],
            "inputs": [artifact_payload(item) for item in selected if item],
        })
    return bundles


def artifact_payload(artifact):
    return {
        "artifact_id": str(artifact.id),
        "series_id": str(artifact.series_id),
        "role": artifact.role,
        "series_description": artifact.series.series_description,
        "size_bytes": artifact.size_bytes,
        "sha256": artifact.sha256,
        "content_url": f"/api/v1/nifti-artifacts/{artifact.id}/content",
    }


def create_signed_gcs_uri(uri):
    bucket, blob_name = parse_allowed_gcs_uri(uri)
    try:
        from google.cloud import storage
        credentials, _ = google.auth.default(
            scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )
        signing_service_account = (
            settings.GCS_SIGNING_SERVICE_ACCOUNT_EMAIL
            or getattr(credentials, "service_account_email", "")
        )
        if not signing_service_account:
            raise ImproperlyConfigured(
                "GCS_SIGNING_SERVICE_ACCOUNT_EMAIL is required to sign GCS URLs."
            )
        if signing_service_account != getattr(credentials, "signer_email", None):
            credentials = impersonated_credentials.Credentials(
                source_credentials=credentials,
                target_principal=signing_service_account,
                target_scopes=["https://www.googleapis.com/auth/cloud-platform"],
                lifetime=300,
            )
        if not isinstance(credentials, google_credentials.Signing):
            raise ImproperlyConfigured(
                "Configured Google credentials cannot sign GCS URLs."
            )
        blob = storage.Client(credentials=credentials).bucket(bucket).blob(blob_name)
        return blob.generate_signed_url(
            version="v4",
            expiration=timedelta(seconds=settings.GCS_SIGNED_URL_TTL_SECONDS),
            method="GET",
            credentials=credentials,
        )
    except Exception as exc:
        if isinstance(exc, ImproperlyConfigured):
            raise
        raise Http404("NIfTI object is unavailable") from exc


def create_signed_gcs_artifact_uri(artifact):
    return create_signed_gcs_uri(artifact.uri)


def open_gcs_uri(uri):
    """Stream result artifacts that have not yet moved to signed redirects."""
    bucket, blob_name = parse_allowed_gcs_uri(uri)
    try:
        from google.cloud import storage
        stream = storage.Client().bucket(bucket).blob(blob_name).open("rb")
    except Exception as exc:
        raise Http404("NIfTI object is unavailable") from exc
    response = FileResponse(stream, content_type="application/gzip")
    response["Content-Disposition"] = f'inline; filename="{blob_name.rsplit("/", 1)[-1]}"'
    response["Cache-Control"] = "private, max-age=300"
    return response


def parse_allowed_gcs_uri(uri):
    if not uri.startswith("gs://"):
        raise Http404("Invalid artifact URI")
    bucket, separator, name = unquote(uri[5:]).partition("/")
    allowed = set(getattr(settings, "GCS_NIFTI_ALLOWED_BUCKETS", []))
    if not separator or not name or bucket not in allowed:
        raise Http404("Artifact bucket is not allowed")
    return bucket, name

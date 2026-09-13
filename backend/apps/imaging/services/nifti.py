from urllib.parse import unquote

from django.conf import settings
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


def open_gcs_uri(uri):
    bucket, blob_name = parse_allowed_gcs_uri(uri)
    try:
        from google.cloud import storage
        blob = storage.Client().bucket(bucket).blob(blob_name)
        stream = blob.open("rb")
    except Exception as exc:
        raise Http404("NIfTI object is unavailable") from exc
    response = FileResponse(stream, content_type="application/gzip")
    response["Content-Disposition"] = f'inline; filename="{blob_name.rsplit("/", 1)[-1]}"'
    response["Cache-Control"] = "private, max-age=300"
    return response


def open_gcs_artifact(artifact):
    return open_gcs_uri(artifact.uri)


def parse_allowed_gcs_uri(uri):
    if not uri.startswith("gs://"):
        raise Http404("Invalid artifact URI")
    bucket, separator, name = unquote(uri[5:]).partition("/")
    allowed = set(getattr(settings, "GCS_NIFTI_ALLOWED_BUCKETS", []))
    if not separator or not name or bucket not in allowed:
        raise Http404("Artifact bucket is not allowed")
    return bucket, name

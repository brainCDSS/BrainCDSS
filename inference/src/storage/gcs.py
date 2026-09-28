"""Validated GCS downloads and uploads with size and SHA-256 checks."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from src.errors import InferenceServiceError


@dataclass(frozen=True)
class ObjectInfo:
    uri: str
    size_bytes: int
    sha256: str


def parse_gs_uri(uri: str) -> tuple[str, str]:
    parsed = urlparse(uri)
    if parsed.scheme != "gs" or not parsed.netloc or not parsed.path.strip("/"):
        raise InferenceServiceError("INVALID_REQUEST", "invalid GCS URI")
    if parsed.params or parsed.query or parsed.fragment:
        raise InferenceServiceError("INVALID_REQUEST", "GCS URI cannot contain parameters")
    return parsed.netloc, parsed.path.lstrip("/")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class GCSStorage:
    def __init__(self, allowed_buckets: set[str], client=None):
        if not allowed_buckets:
            raise ValueError("at least one allowed GCS bucket is required")
        self.allowed_buckets = allowed_buckets
        if client is None:
            from google.cloud import storage

            client = storage.Client()
        self.client = client

    def _blob(self, uri: str):
        bucket_name, object_name = parse_gs_uri(uri)
        if bucket_name not in self.allowed_buckets:
            raise InferenceServiceError(
                "INVALID_REQUEST",
                "GCS bucket is not allowed",
                detail={"bucket": bucket_name},
            )
        return self.client.bucket(bucket_name).blob(object_name)

    def download(self, uri: str, destination: Path, *, size_bytes=None, sha256=None) -> ObjectInfo:
        blob = self._blob(uri)
        if not blob.exists():
            raise InferenceServiceError("INPUT_NOT_FOUND", "GCS object does not exist")
        blob.reload()
        if size_bytes is not None and int(blob.size) != int(size_bytes):
            raise InferenceServiceError("INPUT_CHECKSUM_MISMATCH", "input size does not match")
        destination.parent.mkdir(parents=True, exist_ok=True)
        blob.download_to_filename(str(destination))
        actual_size = destination.stat().st_size
        actual_sha256 = sha256_file(destination)
        if size_bytes is not None and actual_size != int(size_bytes):
            raise InferenceServiceError("INPUT_CHECKSUM_MISMATCH", "downloaded size does not match")
        if sha256 is not None and actual_sha256 != sha256.lower():
            raise InferenceServiceError("INPUT_CHECKSUM_MISMATCH", "downloaded SHA-256 does not match")
        return ObjectInfo(uri=uri, size_bytes=actual_size, sha256=actual_sha256)

    def download_json(self, uri: str, destination: Path) -> dict:
        self.download(uri, destination)
        try:
            return json.loads(destination.read_text(encoding="utf-8-sig"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise InferenceServiceError("INVALID_REQUEST", "invalid JSON object") from exc

    def upload(self, source: Path, uri: str, *, content_type=None) -> ObjectInfo:
        blob = self._blob(uri)
        blob.upload_from_filename(str(source), content_type=content_type)
        blob.reload()
        size_bytes = source.stat().st_size
        if int(blob.size) != size_bytes:
            raise InferenceServiceError(
                "OUTPUT_UPLOAD_FAILED", "uploaded object size does not match", retryable=True
            )
        return ObjectInfo(uri=uri, size_bytes=size_bytes, sha256=sha256_file(source))

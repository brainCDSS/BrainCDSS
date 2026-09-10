"""Resolve and verify immutable nnU-Net bundles described by GCS manifests."""

from __future__ import annotations

import json
import threading
from pathlib import Path

from src.errors import InferenceServiceError, ModelNotReadyError
from src.schemas import AnalysisType, ModelSelector
from src.storage import GCSStorage
from src.storage.gcs import sha256_file


class ManifestModelLoader:
    def __init__(self, storage: GCSStorage, cache_root: Path, model_bucket: str):
        self.storage = storage
        self.cache_root = cache_root
        self.model_bucket = model_bucket
        self._locks: dict[str, threading.Lock] = {}
        self._locks_guard = threading.Lock()

    def resolve_manifest_uri(self, selector: ModelSelector) -> str:
        if selector.manifest_uri:
            return selector.manifest_uri
        if selector.alias:
            raise ModelNotReadyError(
                "MLflow alias resolution is not configured",
                detail={"model": selector.name, "alias": selector.alias},
            )
        return f"gs://{self.model_bucket}/{selector.name}/{selector.version}/manifest.json"

    def prepare(self, selector: ModelSelector, analysis_type: AnalysisType) -> tuple[dict, Path, str]:
        manifest_uri = self.resolve_manifest_uri(selector)
        cache_key = manifest_uri.replace("gs://", "").replace("/", "_")
        bundle_dir = self.cache_root / cache_key
        with self._locks_guard:
            lock = self._locks.setdefault(cache_key, threading.Lock())
        with lock:
            manifest_path = bundle_dir / "manifest.json"
            manifest = self.storage.download_json(manifest_uri, manifest_path)
            self._validate_manifest(manifest, selector, analysis_type)
            prefix = manifest["gcs_prefix"].rstrip("/")
            for entry in manifest["files"]:
                relative = entry["path"]
                destination = bundle_dir / Path(relative)
                if (
                    destination.is_file()
                    and destination.stat().st_size == entry["size_bytes"]
                    and sha256_file(destination) == entry["sha256"]
                ):
                    continue
                try:
                    self.storage.download(
                        f"{prefix}/{relative}",
                        destination,
                        size_bytes=entry["size_bytes"],
                        sha256=entry["sha256"],
                    )
                except InferenceServiceError as exc:
                    if exc.code == "INPUT_CHECKSUM_MISMATCH":
                        exc.code = "MODEL_CHECKSUM_MISMATCH"
                    raise
            (bundle_dir / ".verified").write_text(
                json.dumps({"manifest_uri": manifest_uri}), encoding="utf-8"
            )
        return manifest, bundle_dir, manifest_uri

    @staticmethod
    def _validate_manifest(manifest: dict, selector: ModelSelector, analysis_type: AnalysisType):
        required = {
            "bundle_id", "model_name", "analysis_type", "framework", "gcs_prefix",
            "checkpoint", "trainer", "nnunet", "inputs", "files", "readiness",
        }
        missing = sorted(required - manifest.keys())
        if missing:
            raise ModelNotReadyError("model manifest is incomplete", detail={"missing": missing})
        if manifest["analysis_type"] != analysis_type.value:
            raise InferenceServiceError("MODEL_NOT_FOUND", "model analysis type does not match")
        if manifest["model_name"] != selector.name:
            raise InferenceServiceError("MODEL_NOT_FOUND", "model name does not match")
        if selector.version and manifest["bundle_id"] != selector.version:
            raise InferenceServiceError("MODEL_NOT_FOUND", "model version does not match")
        if manifest["framework"] != "nnunetv2":
            raise ModelNotReadyError("unsupported model framework")
        expected = manifest.get("inputs", {}).get("roles")
        if not expected:
            raise ModelNotReadyError("manifest input roles are missing")

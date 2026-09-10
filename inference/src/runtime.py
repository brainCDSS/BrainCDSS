"""Shared construction of the inference runtime for API and MOSEC workers."""

import os
from functools import lru_cache
from pathlib import Path

from src.model_loader import ManifestModelLoader
from src.orchestrator import InferenceService
from src.storage import GCSStorage


@lru_cache(maxsize=1)
def get_service() -> InferenceService:
    model_bucket = _required_env("GCS_MODEL_BUCKET")
    result_bucket = _required_env("GCS_RESULT_BUCKET")
    allowed = {
        value.strip()
        for value in os.getenv(
            "GCS_ALLOWED_BUCKETS", f"{model_bucket},{result_bucket}"
        ).split(",")
        if value.strip()
    }
    storage = GCSStorage(allowed)
    loader = ManifestModelLoader(
        storage,
        Path(os.getenv("MODEL_CACHE_ROOT", "/tmp/braincdss/models")),
        model_bucket,
    )
    return InferenceService(
        storage,
        loader,
        Path(os.getenv("INFERENCE_WORK_ROOT", "/tmp/braincdss/requests")),
        result_bucket,
    )


def _required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"{name} is required")
    return value

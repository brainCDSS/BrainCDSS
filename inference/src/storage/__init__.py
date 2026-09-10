"""Object storage boundary for model, input, and result artifacts."""

from .gcs import GCSStorage, ObjectInfo, parse_gs_uri

__all__ = ["GCSStorage", "ObjectInfo", "parse_gs_uri"]

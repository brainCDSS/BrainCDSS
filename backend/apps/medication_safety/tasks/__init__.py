"""Medication Safety Celery task entry point."""

from .dur_sync import sync_mfds_dur_data


__all__ = [
    "sync_mfds_dur_data",
]

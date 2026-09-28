"""Medication Celery task registration."""

from .reminders import (
    send_medication_reminders,
)

__all__ = [
    "send_medication_reminders",
]
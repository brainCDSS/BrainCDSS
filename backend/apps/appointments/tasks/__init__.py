"""Appointment Celery task registration."""

from .reminders import (
    send_appointment_reminders,
)

__all__ = [
    "send_appointment_reminders",
]
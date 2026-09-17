"""Consultation persistence models."""

import uuid

from django.db import models

# === FINAL_DB_GENERATED_IMPORTS_START ===
from .models_generated import Consultation, ConsultationHistory
# === FINAL_DB_GENERATED_IMPORTS_END ===


class ConsultationMessage(models.Model):
    """A durable message exchanged by the two clinicians in a consultation."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    consultation = models.ForeignKey(
        Consultation,
        on_delete=models.CASCADE,
        related_name="messages",
    )
    sender = models.ForeignKey(
        "accounts.User",
        on_delete=models.PROTECT,
        related_name="sent_consultation_messages",
    )
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "consultation_messages"
        ordering = ("created_at", "id")
        indexes = [
            models.Index(
                fields=("consultation", "created_at"),
                name="consult_msg_cons_created_idx",
            ),
        ]

    def __str__(self):
        return str(self.pk)

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


class ConsultationChatPresence(models.Model):
    """Short-lived participant state for the consultation message panel."""

    consultation = models.ForeignKey(Consultation, on_delete=models.CASCADE, related_name="chat_presences")
    user = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="consultation_chat_presences")
    last_seen_at = models.DateTimeField()
    is_typing = models.BooleanField(default=False)
    typing_updated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "consultation_chat_presences"
        constraints = [models.UniqueConstraint(fields=("consultation", "user"), name="uq_consultation_chat_presence")]
        indexes = [models.Index(fields=("consultation", "last_seen_at"), name="consult_chat_presence_seen_idx")]

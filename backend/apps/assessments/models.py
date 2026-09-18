"""assessments persistence models; TODO after domain schema approval."""

import uuid

from django.db import models

# === FINAL_DB_GENERATED_IMPORTS_START ===
from .models_generated import InitialAssessment, AssessmentItem, EmergencyEvent
# === FINAL_DB_GENERATED_IMPORTS_END ===


class TriageReview(models.Model):
    """Append-only physician re-triage history for a completed assessment."""

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    assessment = models.ForeignKey(
        InitialAssessment,
        on_delete=models.PROTECT,
        db_column="assessment_id",
        related_name="triage_reviews",
    )
    reviewer = models.ForeignKey(
        "accounts.User",
        on_delete=models.PROTECT,
        db_column="reviewer_id",
        related_name="triage_reviews",
    )
    reviewer_role = models.CharField(
        max_length=40,
        db_column="reviewer_role",
    )
    priority = models.CharField(
        max_length=20,
        db_index=True,
        db_column="priority",
    )
    reason = models.TextField(
        db_column="reason",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        db_column="created_at",
    )

    class Meta:
        db_table = "triage_reviews"
        ordering = ("created_at", "id")
        indexes = [
            models.Index(
                fields=("assessment", "created_at"),
                name="idx_triage_review_assess_time",
            ),
        ]

    def __str__(self):
        return str(self.pk)

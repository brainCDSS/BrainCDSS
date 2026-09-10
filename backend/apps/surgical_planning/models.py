"""surgical_planning persistence models; TODO after domain schema approval."""

# [추가] 수술·시술 플래닝 저장 모델

import uuid

from django.conf import settings
from django.db import models


class SurgicalPlanStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    IN_PROGRESS = "IN_PROGRESS", "In progress"
    REVIEW_REQUESTED = "REVIEW_REQUESTED", "Review requested"
    CONFIRMED = "CONFIRMED", "Confirmed"
    CANCELLED = "CANCELLED", "Cancelled"


class SurgicalPlan(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(
        "patients.Patient", on_delete=models.PROTECT, related_name="surgical_plans"
    )
    encounter = models.ForeignKey(
        "clinical_records.Encounter",
        on_delete=models.PROTECT,
        related_name="surgical_plans",
        null=True,
        blank=True,
    )
    study = models.ForeignKey(
        "imaging.ImagingStudy", on_delete=models.PROTECT, related_name="surgical_plans"
    )
    ai_analysis = models.ForeignKey(
        "ai_analysis.AIAnalysis",
        on_delete=models.SET_NULL,
        related_name="surgical_plans",
        null=True,
        blank=True,
    )
    status = models.CharField(
        max_length=20,
        choices=SurgicalPlanStatus.choices,
        default=SurgicalPlanStatus.DRAFT,
        db_index=True,
    )
    version = models.PositiveIntegerField(default=1)
    treatment_type = models.CharField(max_length=100, blank=True)
    memo = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_surgical_plans",
    )
    finalized_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="finalized_surgical_plans",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    finalized_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "surgical_plans"
        ordering = ("-updated_at",)


class SurgicalPlanClip(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    planning = models.ForeignKey(
        SurgicalPlan, on_delete=models.CASCADE, related_name="clips"
    )
    clip_id = models.CharField(max_length=100)
    clip_type = models.CharField(max_length=50)
    size = models.DecimalField(max_digits=10, decimal_places=3)
    position_x = models.DecimalField(max_digits=12, decimal_places=4)
    position_y = models.DecimalField(max_digits=12, decimal_places=4)
    position_z = models.DecimalField(max_digits=12, decimal_places=4)
    rotation_x = models.DecimalField(max_digits=12, decimal_places=4, default=0)
    rotation_y = models.DecimalField(max_digits=12, decimal_places=4, default=0)
    rotation_z = models.DecimalField(max_digits=12, decimal_places=4, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "surgical_plan_clips"
        ordering = ("created_at",)


class SurgicalPlanMessage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    planning = models.ForeignKey(
        SurgicalPlan, on_delete=models.CASCADE, related_name="messages"
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="surgical_plan_messages",
    )
    message = models.TextField()
    viewer_state = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "surgical_plan_messages"
        ordering = ("created_at",)

# [추가 끝] 수술·시술 플래닝 저장 모델

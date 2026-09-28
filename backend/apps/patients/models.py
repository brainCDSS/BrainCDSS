"""Patients persistence models and clinician care assignments."""

import uuid

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone

# === FINAL_DB_GENERATED_IMPORTS_START ===
from .models_generated import Patient, FavoriteHospital, PatientMergeHistory
# === FINAL_DB_GENERATED_IMPORTS_END ===


class PatientCareAssignment(models.Model):
    """Explicit, auditable clinician access relationship for a patient."""

    class AssignmentRole(models.TextChoices):
        PRIMARY = "PRIMARY", "Primary care"
        CONSULTING = "CONSULTING", "Consulting clinician"
        COVERING = "COVERING", "Covering clinician"

    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        ENDED = "ENDED", "Ended"

    class Source(models.TextChoices):
        MANUAL = "MANUAL", "Manual assignment"
        AI_ANALYSIS = "AI_ANALYSIS", "AI analysis ownership"
        CONSULTATION = "CONSULTATION", "Consultation"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(Patient, on_delete=models.PROTECT, related_name="care_assignments")
    clinician = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="patient_care_assignments")
    role = models.CharField(max_length=20, choices=AssignmentRole.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE, db_index=True)
    source = models.CharField(max_length=20, choices=Source.choices, default=Source.MANUAL)
    started_at = models.DateTimeField(default=timezone.now)
    ended_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "patient_care_assignments"
        indexes = [
            models.Index(fields=["clinician", "status"], name="idx_ptcare_clin_status"),
            models.Index(fields=["patient", "status"], name="idx_ptcare_patient_status"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["patient", "clinician", "role"],
                condition=Q(status="ACTIVE"),
                name="uq_patient_care_active_role",
            ),
        ]

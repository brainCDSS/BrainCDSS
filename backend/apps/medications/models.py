"""medications persistence models; TODO after domain schema approval."""

import uuid

from django.db import models

# === FINAL_DB_GENERATED_IMPORTS_START ===
from .models_generated import MedicationSchedule, MedicationIntake, Medication
# === FINAL_DB_GENERATED_IMPORTS_END ===


class MedicationDiseaseGroup(models.Model):
    class DiseaseGroup(models.TextChoices):
        HEMORRHAGIC_STROKE = "HEMORRHAGIC_STROKE", "뇌출혈"
        ISCHEMIC_STROKE = "ISCHEMIC_STROKE", "뇌경색"
        CEREBRAL_ANEURYSM = "CEREBRAL_ANEURYSM", "뇌동맥류"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    medication = models.ForeignKey(
        Medication,
        on_delete=models.CASCADE,
        related_name="disease_groups",
    )
    disease_group = models.CharField(max_length=32, choices=DiseaseGroup.choices, db_index=True)
    evidence_source = models.CharField(max_length=500, blank=True)
    note = models.CharField(max_length=500, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "medication_disease_groups"
        constraints = [
            models.UniqueConstraint(
                fields=["medication", "disease_group"],
                name="uq_medication_disease_group",
            ),
        ]

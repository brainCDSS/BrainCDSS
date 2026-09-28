# -*- coding: utf-8 -*-
# ================================================================
# AUTO-GENERATED FROM FINAL BrainOn DB CONTRACT.
# Source mapping: 최종_CDSS_BrainOn_DB_API_DjangoApp.xlsx
# Do not hand-edit this file.
# ================================================================

import uuid

from django.db import models
from django.utils import timezone as django_timezone

class MedicationIngredient(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_column='id')
    medication = models.ForeignKey('medications.Medication', on_delete=models.PROTECT, db_column='medication_id', related_name='+')
    ingredient = models.ForeignKey('medication_safety.DrugIngredient', on_delete=models.PROTECT, db_column='ingredient_id', related_name='+')
    amount = models.DecimalField(max_digits=12, decimal_places=4, null=True, db_column='amount')
    unit = models.CharField(max_length=30, null=True, blank=True, db_column='unit')
    is_active = models.BooleanField(db_index=True, default=True, db_column='is_active')
    created_at = models.DateTimeField(default=django_timezone.now, db_column='created_at')

    class Meta:
        db_table = 'medication_ingredients'
        constraints = [
            models.UniqueConstraint(fields=['medication', 'ingredient'], name='uq_medication_ingredients_medication_ingredient'),
        ]

    def __str__(self):
        return str(self.pk)

class PatientAllergy(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_column='id')
    patient = models.ForeignKey('patients.Patient', on_delete=models.PROTECT, db_column='patient_id', related_name='+', db_index=True)
    ingredient = models.ForeignKey('medication_safety.DrugIngredient', on_delete=models.SET_NULL, db_column='ingredient_id', related_name='+', null=True, blank=True, db_index=True)
    substance = models.CharField(max_length=200, null=True, blank=True, db_index=True, db_column='substance')
    reaction = models.CharField(max_length=255, null=True, blank=True, db_column='reaction')
    severity = models.CharField(max_length=20, db_index=True, default='MODERATE', db_column='severity')
    status = models.CharField(max_length=20, db_index=True, default='ACTIVE', db_column='status')
    recorded_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, db_column='recorded_by_id', related_name='+', null=True, blank=True, db_index=True)
    created_at = models.DateTimeField(db_index=True, default=django_timezone.now, db_column='created_at')
    updated_at = models.DateTimeField(default=django_timezone.now, db_column='updated_at')

    class Meta:
        db_table = 'patient_allergies'

    def __str__(self):
        return str(self.pk)

class MedicationSafetyOverride(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_column='id')
    patient = models.ForeignKey('patients.Patient', on_delete=models.PROTECT, db_column='patient_id', related_name='+', db_index=True)
    prescription = models.ForeignKey('prescriptions.Prescription', on_delete=models.SET_NULL, db_column='prescription_id', related_name='+', null=True, blank=True, db_index=True)
    doctor = models.ForeignKey('accounts.User', on_delete=models.PROTECT, db_column='doctor_id', related_name='+', db_index=True)
    alert_type = models.CharField(max_length=30, db_index=True, db_column='alert_type')
    severity = models.CharField(max_length=20, db_index=True, db_column='severity')
    rule_type = models.CharField(max_length=50, null=True, blank=True, db_index=True, db_column='rule_type')
    rule = models.UUIDField(null=True, db_index=True, db_column='rule_id')
    reason = models.TextField(db_column='reason')
    created_at = models.DateTimeField(db_index=True, default=django_timezone.now, db_column='created_at')

    class Meta:
        db_table = 'medication_safety_overrides'

    def __str__(self):
        return str(self.pk)

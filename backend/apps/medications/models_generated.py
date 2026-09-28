# -*- coding: utf-8 -*-
# ================================================================
# AUTO-GENERATED FROM FINAL BrainOn DB CONTRACT.
# Source mapping: 최종_CDSS_BrainOn_DB_API_DjangoApp.xlsx
# Do not hand-edit this file.
# ================================================================

import uuid

from django.db import models
from django.utils import timezone as django_timezone

class MedicationSchedule(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_column='id')
    prescription_item = models.ForeignKey('prescriptions.PrescriptionItem', on_delete=models.CASCADE, db_column='prescription_item_id', related_name='+', db_index=True)
    scheduled_at = models.DateTimeField(db_index=True, db_column='scheduled_at')
    time_slot = models.CharField(max_length=20, null=True, blank=True, db_index=True, db_column='time_slot')
    dose = models.DecimalField(max_digits=10, decimal_places=2, db_column='dose')
    created_at = models.DateTimeField(db_column='created_at')

    class Meta:
        db_table = 'medication_schedules'

    def __str__(self):
        return str(self.pk)

class MedicationIntake(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_column='id')
    schedule = models.OneToOneField('medications.MedicationSchedule', on_delete=models.CASCADE, db_column='schedule_id', related_name='+')
    recorded_by = models.ForeignKey('accounts.User', on_delete=models.PROTECT, db_column='recorded_by_id', related_name='+', db_index=True)
    status = models.CharField(max_length=20, db_index=True, db_column='status')
    taken_at = models.DateTimeField(null=True, db_index=True, db_column='taken_at')
    note = models.TextField(null=True, blank=True, db_column='note')
    created_at = models.DateTimeField(db_column='created_at')
    updated_at = models.DateTimeField(db_column='updated_at')

    class Meta:
        db_table = 'medication_intakes'

    def __str__(self):
        return str(self.pk)

class Medication(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_column='id')
    medication_code = models.CharField(max_length=50, unique=True, db_column='medication_code')
    medication_name = models.CharField(max_length=200, db_index=True, db_column='medication_name')
    dosage_form = models.CharField(max_length=50, null=True, blank=True, db_column='dosage_form')
    strength = models.CharField(max_length=100, null=True, blank=True, db_column='strength')
    manufacturer = models.CharField(max_length=150, null=True, blank=True, db_column='manufacturer')
    is_active = models.BooleanField(db_column='is_active')
    created_at = models.DateTimeField(db_column='created_at')
    updated_at = models.DateTimeField(db_column='updated_at')

    class Meta:
        db_table = 'medications'

    def __str__(self):
        return str(self.pk)

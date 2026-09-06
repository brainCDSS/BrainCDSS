# -*- coding: utf-8 -*-
# ================================================================
# AUTO-GENERATED FROM FINAL BrainOn DB CONTRACT.
# Source mapping: 최종_CDSS_BrainOn_DB_API_DjangoApp.xlsx
# Do not hand-edit this file.
# ================================================================

import uuid

from django.db import models
from django.utils import timezone as django_timezone

class Prescription(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_column='id')
    encounter = models.ForeignKey('clinical_records.Encounter', on_delete=models.PROTECT, db_column='encounter_id', related_name='+', db_index=True)
    prescribed_by = models.ForeignKey('accounts.User', on_delete=models.PROTECT, db_column='prescribed_by_id', related_name='+', db_index=True)
    status = models.CharField(max_length=20, db_index=True, db_column='status')
    finalized_at = models.DateTimeField(null=True, db_column='finalized_at')
    created_at = models.DateTimeField(db_column='created_at')
    updated_at = models.DateTimeField(db_column='updated_at')

    class Meta:
        db_table = 'prescriptions'

    def __str__(self):
        return str(self.pk)

class PrescriptionItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_column='id')
    prescription = models.ForeignKey('prescriptions.Prescription', on_delete=models.CASCADE, db_column='prescription_id', related_name='+', db_index=True)
    medication = models.ForeignKey('medications.Medication', on_delete=models.PROTECT, db_column='medication_id', related_name='+', db_index=True)
    medication_code = models.CharField(max_length=50, null=True, blank=True, db_index=True, db_column='medication_code')
    medication_name = models.CharField(max_length=200, db_column='medication_name')
    dose = models.DecimalField(max_digits=10, decimal_places=2, db_column='dose')
    dose_unit = models.CharField(max_length=30, db_column='dose_unit')
    route = models.CharField(max_length=30, null=True, blank=True, db_column='route')
    frequency_per_day = models.IntegerField(db_column='frequency_per_day')
    timing = models.CharField(max_length=30, null=True, blank=True, db_column='timing')
    start_date = models.DateField(db_index=True, db_column='start_date')
    duration_days = models.IntegerField(db_column='duration_days')
    instructions = models.TextField(null=True, blank=True, db_column='instructions')
    created_at = models.DateTimeField(db_column='created_at')
    updated_at = models.DateTimeField(db_column='updated_at')

    class Meta:
        db_table = 'prescription_items'

    def __str__(self):
        return str(self.pk)

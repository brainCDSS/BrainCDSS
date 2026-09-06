# -*- coding: utf-8 -*-
# ================================================================
# AUTO-GENERATED FROM FINAL BrainOn DB CONTRACT.
# Source mapping: 최종_CDSS_BrainOn_DB_API_DjangoApp.xlsx
# Do not hand-edit this file.
# ================================================================

import uuid

from django.db import models
from django.utils import timezone as django_timezone

class ClinicalNote(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_column='id')
    encounter = models.ForeignKey('clinical_records.Encounter', on_delete=models.PROTECT, db_column='encounter_id', related_name='+', db_index=True)
    author = models.ForeignKey('accounts.User', on_delete=models.PROTECT, db_column='author_id', related_name='+', db_index=True)
    subjective = models.TextField(null=True, blank=True, db_column='subjective')
    objective = models.TextField(null=True, blank=True, db_column='objective')
    assessment = models.TextField(null=True, blank=True, db_column='assessment')
    plan = models.TextField(null=True, blank=True, db_column='plan')
    clinical_opinion = models.TextField(null=True, blank=True, db_column='clinical_opinion')
    status = models.CharField(max_length=20, db_index=True, db_column='status')
    finalized_at = models.DateTimeField(null=True, db_column='finalized_at')
    created_at = models.DateTimeField(db_column='created_at')
    updated_at = models.DateTimeField(db_column='updated_at')

    class Meta:
        db_table = 'clinical_notes'

    def __str__(self):
        return str(self.pk)

class Encounter(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_column='id')
    patient = models.ForeignKey('patients.Patient', on_delete=models.PROTECT, db_column='patient_id', related_name='+', db_index=True)
    appointment = models.ForeignKey('appointments.Appointment', on_delete=models.SET_NULL, db_column='appointment_id', related_name='+', null=True, blank=True, db_index=True)
    encounter_no = models.CharField(max_length=50, unique=True, db_column='encounter_no')
    encounter_type = models.CharField(max_length=20, db_index=True, db_column='encounter_type')
    status = models.CharField(max_length=20, db_index=True, db_column='status')
    arrived_at = models.DateTimeField(db_index=True, db_column='arrived_at')
    started_at = models.DateTimeField(null=True, db_column='started_at')
    ended_at = models.DateTimeField(null=True, db_column='ended_at')
    created_at = models.DateTimeField(db_column='created_at')
    updated_at = models.DateTimeField(db_column='updated_at')

    class Meta:
        db_table = 'encounters'

    def __str__(self):
        return str(self.pk)

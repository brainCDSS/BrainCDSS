# -*- coding: utf-8 -*-
# ================================================================
# AUTO-GENERATED FROM FINAL BrainOn DB CONTRACT.
# Source mapping: 최종_CDSS_BrainOn_DB_API_DjangoApp.xlsx
# Do not hand-edit this file.
# ================================================================

import uuid

from django.db import models
from django.utils import timezone as django_timezone

class InitialAssessment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_column='id')
    encounter = models.ForeignKey('clinical_records.Encounter', on_delete=models.PROTECT, db_column='encounter_id', related_name='+', db_index=True)
    assessor = models.ForeignKey('accounts.User', on_delete=models.PROTECT, db_column='assessor_id', related_name='+', db_index=True)
    assigned_neurologist = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, db_column='assigned_neurologist_id', related_name='+', null=True, blank=True, db_index=True)
    status = models.CharField(max_length=20, db_index=True, db_column='status')
    total_score = models.IntegerField(null=True, db_column='total_score')
    triage_priority = models.CharField(max_length=20, null=True, blank=True, db_index=True, db_column='triage_priority')
    onset_at = models.DateTimeField(null=True, db_column='onset_at')
    lkw_at = models.DateTimeField(null=True, db_column='lkw_at')
    symptom_note = models.TextField(null=True, blank=True, db_column='symptom_note')
    completed_at = models.DateTimeField(null=True, db_column='completed_at')
    created_at = models.DateTimeField(db_column='created_at')
    updated_at = models.DateTimeField(db_column='updated_at')

    class Meta:
        db_table = 'initial_assessments'

    def __str__(self):
        return str(self.pk)

class AssessmentItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_column='id')
    assessment = models.ForeignKey('assessments.InitialAssessment', on_delete=models.PROTECT, db_column='assessment_id', related_name='+', db_index=True)
    item_group = models.CharField(max_length=30, db_index=True, db_column='item_group')
    item_code = models.CharField(max_length=50, db_index=True, db_column='item_code')
    value_text = models.TextField(null=True, blank=True, db_column='value_text')
    value_numeric = models.DecimalField(max_digits=10, decimal_places=2, null=True, db_column='value_numeric')
    unit = models.CharField(max_length=20, null=True, blank=True, db_column='unit')
    score = models.IntegerField(null=True, db_column='score')
    is_red_flag = models.BooleanField(db_column='is_red_flag')
    note = models.TextField(null=True, blank=True, db_column='note')
    recorded_at = models.DateTimeField(db_column='recorded_at')

    class Meta:
        db_table = 'assessment_items'

    def __str__(self):
        return str(self.pk)

class EmergencyEvent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_column='id')
    assessment = models.ForeignKey('assessments.InitialAssessment', on_delete=models.PROTECT, db_column='assessment_id', related_name='+', db_index=True)
    encounter = models.ForeignKey('clinical_records.Encounter', on_delete=models.PROTECT, db_column='encounter_id', related_name='+', db_index=True)
    assigned_neurologist = models.ForeignKey('accounts.User', on_delete=models.PROTECT, db_column='assigned_neurologist_id', related_name='+', db_index=True)
    event_type = models.CharField(max_length=50, db_index=True, db_column='event_type')
    priority = models.CharField(max_length=20, db_index=True, db_column='priority')
    status = models.CharField(max_length=20, db_index=True, db_column='status')
    occurred_at = models.DateTimeField(db_column='occurred_at')
    notified_at = models.DateTimeField(null=True, db_column='notified_at')
    acknowledged_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, db_column='acknowledged_by_id', related_name='+', null=True, blank=True, db_index=True)
    acknowledged_at = models.DateTimeField(null=True, db_column='acknowledged_at')
    created_at = models.DateTimeField(db_column='created_at')

    class Meta:
        db_table = 'emergency_events'

    def __str__(self):
        return str(self.pk)

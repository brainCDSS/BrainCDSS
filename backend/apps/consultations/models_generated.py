# -*- coding: utf-8 -*-
# ================================================================
# AUTO-GENERATED FROM FINAL BrainOn DB CONTRACT.
# Source mapping: 최종_CDSS_BrainOn_DB_API_DjangoApp.xlsx
# Do not hand-edit this file.
# ================================================================

import uuid

from django.db import models
from django.utils import timezone as django_timezone

class Consultation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_column='id')
    encounter = models.ForeignKey('clinical_records.Encounter', on_delete=models.PROTECT, db_column='encounter_id', related_name='+', db_index=True)
    consultation_type = models.CharField(max_length=30, db_index=True, db_column='consultation_type')
    requested_by = models.ForeignKey('accounts.User', on_delete=models.PROTECT, db_column='requested_by_id', related_name='+', db_index=True)
    assigned_to = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, db_column='assigned_to_id', related_name='+', null=True, blank=True, db_index=True)
    priority = models.CharField(max_length=20, db_index=True, db_column='priority')
    reason = models.TextField(db_column='reason')
    status = models.CharField(max_length=20, db_index=True, db_column='status')
    final_opinion = models.TextField(null=True, blank=True, db_column='final_opinion')
    treatment_plan = models.TextField(null=True, blank=True, db_column='treatment_plan')
    requested_at = models.DateTimeField(db_column='requested_at')
    accepted_at = models.DateTimeField(null=True, db_column='accepted_at')
    started_at = models.DateTimeField(null=True, db_column='started_at')
    completed_at = models.DateTimeField(null=True, db_column='completed_at')
    response_viewed_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, db_column='response_viewed_by_id', related_name='+', null=True, blank=True, db_index=True)
    response_viewed_at = models.DateTimeField(null=True, db_index=True, db_column='response_viewed_at')
    cancelled_at = models.DateTimeField(null=True, db_column='cancelled_at')
    cancel_reason = models.TextField(null=True, blank=True, db_column='cancel_reason')
    created_at = models.DateTimeField(db_column='created_at')
    updated_at = models.DateTimeField(db_column='updated_at')

    class Meta:
        db_table = 'consultations'

    def __str__(self):
        return str(self.pk)

class ConsultationHistory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_column='id')
    consultation = models.ForeignKey('consultations.Consultation', on_delete=models.CASCADE, db_column='consultation_id', related_name='+', db_index=True)
    from_status = models.CharField(max_length=20, null=True, blank=True, db_column='from_status')
    to_status = models.CharField(max_length=20, db_index=True, db_column='to_status')
    changed_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, db_column='changed_by_id', related_name='+', null=True, blank=True, db_index=True)
    reason = models.TextField(null=True, blank=True, db_column='reason')
    changed_at = models.DateTimeField(db_index=True, db_column='changed_at')

    class Meta:
        db_table = 'consultation_histories'

    def __str__(self):
        return str(self.pk)

# -*- coding: utf-8 -*-
# ================================================================
# AUTO-GENERATED FROM FINAL BrainOn DB CONTRACT.
# Source mapping: 최종_CDSS_BrainOn_DB_API_DjangoApp.xlsx
# Do not hand-edit this file.
# ================================================================

import uuid

from django.db import models
from django.utils import timezone as django_timezone

class RadiologyReport(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_column='id')
    study = models.ForeignKey('imaging.ImagingStudy', on_delete=models.PROTECT, db_column='study_id', related_name='+', db_index=True)
    referenced_ai_analysis = models.ForeignKey('ai_analysis.AIAnalysis', on_delete=models.SET_NULL, db_column='referenced_ai_analysis_id', related_name='+', null=True, blank=True, db_index=True)
    status = models.CharField(max_length=20, db_index=True, db_column='status')
    version = models.IntegerField(db_column='version')
    is_current = models.BooleanField(db_index=True, db_column='is_current')
    findings = models.TextField(db_column='findings')
    impression = models.TextField(db_column='impression')
    recommendation = models.TextField(db_column='recommendation')
    structured_findings = models.JSONField(default=dict, db_column='structured_findings')
    author = models.ForeignKey('accounts.User', on_delete=models.PROTECT, db_column='author_id', related_name='+', db_index=True)
    preliminary_at = models.DateTimeField(null=True, db_index=True, db_column='preliminary_at')
    finalized_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, db_column='finalized_by_id', related_name='+', null=True, blank=True, db_index=True)
    finalized_at = models.DateTimeField(null=True, db_index=True, db_column='finalized_at')
    critical_finding = models.BooleanField(db_index=True, db_column='critical_finding')
    critical_level = models.CharField(max_length=16, db_index=True, db_column='critical_level')
    created_at = models.DateTimeField(db_column='created_at')
    updated_at = models.DateTimeField(db_column='updated_at')

    class Meta:
        db_table = 'radiology_radiologyreport'

    def __str__(self):
        return str(self.pk)

class RadiologyReportRevision(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_column='id')
    report = models.ForeignKey('radiology.RadiologyReport', on_delete=models.CASCADE, db_column='report_id', related_name='+', db_index=True)
    version = models.IntegerField(db_column='version')
    previous_snapshot = models.JSONField(db_column='previous_snapshot')
    new_snapshot = models.JSONField(db_column='new_snapshot')
    change_reason = models.TextField(db_column='change_reason')
    changed_by = models.ForeignKey('accounts.User', on_delete=models.PROTECT, db_column='changed_by_id', related_name='+', db_index=True)
    changed_at = models.DateTimeField(db_index=True, db_column='changed_at')

    class Meta:
        db_table = 'radiology_radiologyreportrevision'

    def __str__(self):
        return str(self.pk)

class RadiologyMeasurement(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_column='id')
    report = models.ForeignKey('radiology.RadiologyReport', on_delete=models.CASCADE, db_column='report_id', related_name='+', db_index=True)
    measurement_type = models.CharField(max_length=64, db_index=True, db_column='measurement_type')
    label = models.CharField(max_length=255, db_column='label')
    value_numeric = models.DecimalField(max_digits=14, decimal_places=4, db_column='value_numeric')
    unit = models.CharField(max_length=32, db_column='unit')
    created_by = models.ForeignKey('accounts.User', on_delete=models.PROTECT, db_column='created_by_id', related_name='+', db_index=True)
    created_at = models.DateTimeField(db_column='created_at')

    class Meta:
        db_table = 'radiology_radiologymeasurement'

    def __str__(self):
        return str(self.pk)

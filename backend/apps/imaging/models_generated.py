# -*- coding: utf-8 -*-
# ================================================================
# AUTO-GENERATED FROM FINAL BrainOn DB CONTRACT.
# Source mapping: 최종_CDSS_BrainOn_DB_API_DjangoApp.xlsx
# Do not hand-edit this file.
# ================================================================

import uuid

from django.db import models
from django.utils import timezone as django_timezone

class ImagingOrder(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_column='id')
    patient = models.ForeignKey('patients.Patient', on_delete=models.PROTECT, db_column='patient_id', related_name='+', db_index=True)
    accession_number = models.CharField(max_length=64, null=True, blank=True, db_index=True, db_column='accession_number')
    procedure_code = models.CharField(max_length=64, db_index=True, db_column='procedure_code')
    procedure_name = models.CharField(max_length=255, db_column='procedure_name')
    modality = models.CharField(max_length=16, db_index=True, db_column='modality')
    priority = models.CharField(max_length=16, db_index=True, db_column='priority')
    status = models.CharField(max_length=20, db_index=True, db_column='status')
    reason = models.TextField(db_column='reason')
    requested_by = models.ForeignKey('accounts.User', on_delete=models.PROTECT, db_column='requested_by_id', related_name='+', db_index=True)
    requested_at = models.DateTimeField(db_index=True, db_column='requested_at')
    scheduled_at = models.DateTimeField(null=True, db_index=True, db_column='scheduled_at')
    created_at = models.DateTimeField(db_column='created_at')
    updated_at = models.DateTimeField(db_column='updated_at')
    encounter = models.ForeignKey('clinical_records.Encounter', on_delete=models.PROTECT, db_column='encounter_id', related_name='+', db_index=True)

    class Meta:
        db_table = 'imaging_imagingorder'

    def __str__(self):
        return str(self.pk)

class ImagingStudy(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_column='id')
    patient = models.ForeignKey('patients.Patient', on_delete=models.SET_NULL, db_column='patient_id', related_name='+', null=True, blank=True, db_index=True)
    imaging_order = models.ForeignKey('imaging.ImagingOrder', on_delete=models.SET_NULL, db_column='imaging_order_id', related_name='+', null=True, blank=True, db_index=True)
    study_instance_uid = models.CharField(max_length=64, unique=True, db_column='study_instance_uid')
    accession_number = models.CharField(max_length=64, db_index=True, db_column='accession_number')
    orthanc_study = models.CharField(max_length=128, null=True, blank=True, unique=True, db_column='orthanc_study_id')
    study_datetime = models.DateTimeField(null=True, db_index=True, db_column='study_datetime')
    modalities = models.JSONField(db_column='modalities')
    study_description = models.CharField(max_length=255, db_column='study_description')
    series_count = models.IntegerField(db_column='series_count')
    instance_count = models.IntegerField(db_column='instance_count')
    status = models.CharField(max_length=20, db_index=True, db_column='status')
    last_synced_at = models.DateTimeField(null=True, db_index=True, db_column='last_synced_at')
    created_at = models.DateTimeField(db_column='created_at')
    updated_at = models.DateTimeField(db_column='updated_at')

    class Meta:
        db_table = 'imaging_imagingstudy'

    def __str__(self):
        return str(self.pk)

class SeriesReference(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_column='id')
    study = models.ForeignKey('imaging.ImagingStudy', on_delete=models.PROTECT, db_column='study_id', related_name='+', db_index=True)
    series_instance_uid = models.CharField(max_length=64, unique=True, db_column='series_instance_uid')
    orthanc_series = models.CharField(max_length=128, null=True, blank=True, unique=True, db_column='orthanc_series_id')
    series_number = models.IntegerField(null=True, db_column='series_number')
    modality = models.CharField(max_length=16, db_index=True, db_column='modality')
    series_description = models.CharField(max_length=255, db_column='series_description')
    protocol_name = models.CharField(max_length=255, db_column='protocol_name')
    instance_count = models.IntegerField(db_column='instance_count')
    frame_count = models.IntegerField(default=0, db_column='frame_count')
    rows = models.IntegerField(null=True, db_column='rows')
    columns = models.IntegerField(null=True, db_column='columns')
    slice_thickness = models.DecimalField(max_digits=8, decimal_places=3, null=True, db_column='slice_thickness')
    is_complete = models.BooleanField(db_index=True, default=False, db_column='is_complete')
    is_ai_eligible = models.BooleanField(db_index=True, db_column='is_ai_eligible')
    ai_exclusion_reason = models.CharField(max_length=255, db_column='ai_exclusion_reason')
    created_at = models.DateTimeField(db_column='created_at')
    updated_at = models.DateTimeField(db_column='updated_at')

    class Meta:
        db_table = 'imaging_seriesreference'

    def __str__(self):
        return str(self.pk)

class DicomObjectReference(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_column='id')
    study = models.ForeignKey('imaging.ImagingStudy', on_delete=models.PROTECT, db_column='study_id', related_name='+', db_index=True)
    series = models.ForeignKey('imaging.SeriesReference', on_delete=models.SET_NULL, db_column='series_id', related_name='+', null=True, blank=True, db_index=True)
    object_type = models.CharField(max_length=32, db_index=True, db_column='object_type')
    sop_instance_uid = models.CharField(max_length=64, unique=True, db_column='sop_instance_uid')
    orthanc_instance = models.CharField(max_length=128, null=True, blank=True, unique=True, db_column='orthanc_instance_id')
    storage_status = models.CharField(max_length=20, db_index=True, db_column='storage_status')
    created_at = models.DateTimeField(db_column='created_at')

    class Meta:
        db_table = 'imaging_dicomobjectreference'

    def __str__(self):
        return str(self.pk)

class ImagingOrderStatusHistory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_column='id')
    imaging_order = models.ForeignKey('imaging.ImagingOrder', on_delete=models.PROTECT, db_column='imaging_order_id', related_name='+', db_index=True)
    previous_status = models.CharField(max_length=20, null=True, blank=True, db_column='previous_status')
    status = models.CharField(max_length=20, db_index=True, db_column='status')
    occurred_at = models.DateTimeField(db_index=True, db_column='occurred_at')
    reason = models.TextField(db_column='reason')
    recorded_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, db_column='recorded_by_id', related_name='+', null=True, blank=True)

    class Meta:
        db_table = 'imaging_imagingorderstatushistory'

    def __str__(self):
        return str(self.pk)

class DicomTransferJob(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_column='id')
    study = models.ForeignKey('imaging.ImagingStudy', on_delete=models.PROTECT, db_column='study_id', related_name='+', db_index=True)
    analysis = models.ForeignKey('ai_analysis.AIAnalysis', on_delete=models.SET_NULL, db_column='analysis_id', related_name='+', null=True, blank=True, db_index=True)
    transfer_type = models.CharField(max_length=32, db_index=True, db_column='transfer_type')
    target_system = models.CharField(max_length=64, db_index=True, db_column='target_system')
    status = models.CharField(max_length=20, db_index=True, db_column='status')
    attempt_count = models.SmallIntegerField(db_column='attempt_count')
    last_error_code = models.CharField(max_length=64, null=True, blank=True, db_index=True, db_column='last_error_code')
    started_at = models.DateTimeField(null=True, db_column='started_at')
    completed_at = models.DateTimeField(null=True, db_index=True, db_column='completed_at')
    trace = models.CharField(max_length=64, db_index=True, db_column='trace_id')

    class Meta:
        db_table = 'imaging_dicomtransferjob'

    def __str__(self):
        return str(self.pk)

class ImagingReconciliationTask(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_column='id')
    study = models.ForeignKey('imaging.ImagingStudy', on_delete=models.PROTECT, db_column='study_id', related_name='+', db_index=True)
    imaging_order = models.ForeignKey('imaging.ImagingOrder', on_delete=models.SET_NULL, db_column='imaging_order_id', related_name='+', null=True, blank=True, db_index=True)
    issue_code = models.CharField(max_length=64, db_index=True, db_column='issue_code')
    status = models.CharField(max_length=20, db_index=True, db_column='status')
    resolved_patient = models.ForeignKey('patients.Patient', on_delete=models.SET_NULL, db_column='resolved_patient_id', related_name='+', null=True, blank=True, db_index=True)
    resolution_note = models.TextField(db_column='resolution_note')
    resolved_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, db_column='resolved_by_id', related_name='+', null=True, blank=True)
    detected_at = models.DateTimeField(db_index=True, db_column='detected_at')
    resolved_at = models.DateTimeField(null=True, db_index=True, db_column='resolved_at')

    class Meta:
        db_table = 'imaging_reconciliationtask'

    def __str__(self):
        return str(self.pk)

class KeyImageSelection(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_column='id')
    study = models.ForeignKey('imaging.ImagingStudy', on_delete=models.PROTECT, db_column='study_id', related_name='+', db_index=True)
    sop_instance_uid = models.CharField(max_length=64, db_index=True, db_column='sop_instance_uid')
    frame_number = models.IntegerField(null=True, db_column='frame_number')
    label = models.CharField(max_length=255, db_column='label')
    selected_by = models.ForeignKey('accounts.User', on_delete=models.PROTECT, db_column='selected_by_id', related_name='+', db_index=True)
    selected_at = models.DateTimeField(db_index=True, db_column='selected_at')

    class Meta:
        db_table = 'imaging_keyimageselection'

    def __str__(self):
        return str(self.pk)

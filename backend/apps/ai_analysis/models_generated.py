# -*- coding: utf-8 -*-
# ================================================================
# AUTO-GENERATED FROM FINAL BrainOn DB CONTRACT.
# Source mapping: 최종_CDSS_BrainOn_DB_API_DjangoApp.xlsx
# Do not hand-edit this file.
# ================================================================

import uuid

from django.db import models
from django.utils import timezone as django_timezone

class AIModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_column='id')
    code = models.CharField(max_length=100, unique=True, db_column='code')
    display_name = models.CharField(max_length=255, db_column='display_name')
    task_type = models.CharField(max_length=32, db_index=True, db_column='task_type')
    disease_scope = models.CharField(max_length=32, db_index=True, db_column='disease_scope')
    supported_modalities = models.JSONField(db_column='supported_modalities')
    description = models.TextField(db_column='description')
    is_enabled = models.BooleanField(db_index=True, db_column='is_enabled')
    created_at = models.DateTimeField(db_column='created_at')
    updated_at = models.DateTimeField(db_column='updated_at')

    class Meta:
        db_table = 'ai_aimodel'

    def __str__(self):
        return str(self.pk)

class ModelVersion(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_column='id')
    model = models.ForeignKey('ai_analysis.AIModel', on_delete=models.PROTECT, db_column='model_id', related_name='+', db_index=True)
    version = models.CharField(max_length=64, db_column='version')
    mlflow_registered_model_name = models.CharField(max_length=255, db_index=True, db_column='mlflow_registered_model_name')
    mlflow_model_version = models.CharField(max_length=64, db_column='mlflow_model_version')
    mlflow_run = models.CharField(max_length=128, db_index=True, db_column='mlflow_run_id')
    artifact_uri = models.CharField(max_length=1024, db_column='artifact_uri')
    container_image_digest = models.CharField(max_length=128, db_column='container_image_digest')
    code_commit_sha = models.CharField(max_length=64, db_index=True, db_column='code_commit_sha')
    input_contract = models.JSONField(default=dict, db_column='input_contract')
    output_contract = models.JSONField(default=dict, db_column='output_contract')
    preprocessing_config = models.JSONField(default=dict, db_column='preprocessing_config')
    validation_status = models.CharField(max_length=20, db_index=True, db_column='validation_status')
    is_active = models.BooleanField(db_index=True, db_column='is_active')
    performance_metrics = models.JSONField(db_column='performance_metrics')
    created_at = models.DateTimeField(db_column='created_at')
    updated_at = models.DateTimeField(db_column='updated_at')

    class Meta:
        db_table = 'ai_modelversion'

    def __str__(self):
        return str(self.pk)

class AIAnalysis(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_column='id')
    study = models.ForeignKey('imaging.ImagingStudy', on_delete=models.PROTECT, db_column='study_id', related_name='+', db_index=True)
    model_version = models.ForeignKey('ai_analysis.ModelVersion', on_delete=models.PROTECT, db_column='model_version_id', related_name='+', db_index=True)
    model_config_version = models.ForeignKey('ai_analysis.AIModelConfigVersion', on_delete=models.PROTECT, db_column='model_config_version_id', related_name='+', db_index=True)
    routing_config_version = models.ForeignKey('ai_analysis.AIRoutingConfigVersion', on_delete=models.SET_NULL, db_column='routing_config_version_id', related_name='+', null=True, blank=True, db_index=True)
    analysis_type = models.CharField(max_length=64, db_index=True, db_column='analysis_type')
    status = models.CharField(max_length=20, db_index=True, db_column='status')
    stage = models.CharField(max_length=32, db_index=True, db_column='stage')
    priority = models.CharField(max_length=20, db_index=True, db_column='priority')
    requested_by = models.ForeignKey('accounts.User', on_delete=models.PROTECT, db_column='requested_by_id', related_name='+', db_index=True)
    attempt_count = models.SmallIntegerField(db_column='attempt_count')
    trace = models.CharField(max_length=64, db_index=True, db_column='trace_id')
    requested_at = models.DateTimeField(db_index=True, db_column='requested_at')
    started_at = models.DateTimeField(null=True, db_column='started_at')
    completed_at = models.DateTimeField(null=True, db_column='completed_at')
    failure_code = models.CharField(max_length=64, null=True, blank=True, db_index=True, db_column='failure_code')
    created_at = models.DateTimeField(db_column='created_at')
    updated_at = models.DateTimeField(db_column='updated_at')

    class Meta:
        db_table = 'ai_aianalysis'

    def __str__(self):
        return str(self.pk)

class AIAnalysisInputSeries(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_column='id')
    analysis = models.ForeignKey('ai_analysis.AIAnalysis', on_delete=models.CASCADE, db_column='analysis_id', related_name='+', db_index=True)
    series = models.ForeignKey('imaging.SeriesReference', on_delete=models.PROTECT, db_column='series_id', related_name='+', db_index=True)
    role = models.CharField(max_length=32, db_index=True, db_column='role')

    class Meta:
        db_table = 'ai_aianalysisinputseries'

    def __str__(self):
        return str(self.pk)

class AIAnalysisAttempt(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_column='id')
    analysis = models.ForeignKey('ai_analysis.AIAnalysis', on_delete=models.CASCADE, db_column='analysis_id', related_name='+', db_index=True)
    attempt_number = models.SmallIntegerField(db_column='attempt_number')
    status = models.CharField(max_length=20, db_index=True, db_column='status')
    stage = models.CharField(max_length=32, db_column='stage')
    started_at = models.DateTimeField(null=True, db_column='started_at')
    finished_at = models.DateTimeField(null=True, db_column='finished_at')
    error_code = models.CharField(max_length=64, null=True, blank=True, db_index=True, db_column='error_code')
    trace = models.CharField(max_length=64, db_index=True, db_column='trace_id')

    class Meta:
        db_table = 'ai_aianalysisattempt'

    def __str__(self):
        return str(self.pk)

class AIAnalysisResult(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_column='id')
    analysis = models.OneToOneField('ai_analysis.AIAnalysis', on_delete=models.PROTECT, db_column='analysis_id', related_name='+')
    is_positive = models.BooleanField(null=True, db_index=True, db_column='is_positive')
    confidence = models.DecimalField(max_digits=6, decimal_places=5, null=True, db_column='confidence')
    lesion_count = models.IntegerField(null=True, db_column='lesion_count')
    total_volume_ml = models.DecimalField(max_digits=12, decimal_places=4, null=True, db_column='total_volume_ml')
    max_diameter_mm = models.DecimalField(max_digits=10, decimal_places=3, null=True, db_column='max_diameter_mm')
    severity = models.CharField(max_length=32, db_index=True, db_column='severity')
    structured_findings = models.JSONField(db_column='structured_findings')
    generated_at = models.DateTimeField(db_index=True, db_column='generated_at')

    class Meta:
        db_table = 'ai_aianalysisresult'

    def __str__(self):
        return str(self.pk)

class AIResultReview(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_column='id')
    result = models.ForeignKey('ai_analysis.AIAnalysisResult', on_delete=models.PROTECT, db_column='result_id', related_name='+', db_index=True)
    reviewer = models.ForeignKey('accounts.User', on_delete=models.PROTECT, db_column='reviewer_id', related_name='+', db_index=True)
    decision = models.CharField(max_length=16, db_index=True, db_column='decision')
    comment = models.TextField(db_column='comment')
    corrected_findings = models.JSONField(db_column='corrected_findings')
    reviewed_at = models.DateTimeField(db_index=True, db_column='reviewed_at')

    class Meta:
        db_table = 'ai_airesultreview'

    def __str__(self):
        return str(self.pk)

class AIModelConfigVersion(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_column='id')
    model_version = models.ForeignKey('ai_analysis.ModelVersion', on_delete=models.PROTECT, db_column='model_version_id', related_name='+', db_index=True)
    config_version = models.CharField(max_length=32, db_column='config_version')
    threshold_config = models.JSONField(db_column='threshold_config')
    is_active = models.BooleanField(db_index=True, db_column='is_active')
    created_at = models.DateTimeField(db_column='created_at')

    class Meta:
        db_table = 'ai_modelconfigversion'

    def __str__(self):
        return str(self.pk)

class AIRoutingConfigVersion(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_column='id')
    version = models.CharField(max_length=32, unique=True, db_column='version')
    modality = models.CharField(max_length=16, db_index=True, db_column='modality')
    analysis_type = models.CharField(max_length=64, db_index=True, db_column='analysis_type')
    target_model_version = models.ForeignKey('ai_analysis.ModelVersion', on_delete=models.SET_NULL, db_column='target_model_version_id', related_name='+', null=True, blank=True, db_index=True)
    is_active = models.BooleanField(db_index=True, db_column='is_active')
    created_at = models.DateTimeField(db_column='created_at')

    class Meta:
        db_table = 'ai_airoutingconfigversion'

    def __str__(self):
        return str(self.pk)

class AIAnalysisStatusHistory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_column='id')
    analysis = models.ForeignKey('ai_analysis.AIAnalysis', on_delete=models.CASCADE, db_column='analysis_id', related_name='+', db_index=True)
    previous_status = models.CharField(max_length=20, null=True, blank=True, db_column='previous_status')
    status = models.CharField(max_length=20, db_index=True, db_column='status')
    stage = models.CharField(max_length=32, db_index=True, db_column='stage')
    reason_code = models.CharField(max_length=64, null=True, blank=True, db_index=True, db_column='reason_code')
    occurred_at = models.DateTimeField(db_index=True, db_column='occurred_at')

    class Meta:
        db_table = 'ai_aianalysisstatushistory'

    def __str__(self):
        return str(self.pk)

class AIResultArtifact(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_column='id')
    result = models.ForeignKey('ai_analysis.AIAnalysisResult', on_delete=models.CASCADE, db_column='result_id', related_name='+', db_index=True)
    artifact_type = models.CharField(max_length=32, db_index=True, db_column='artifact_type')
    uri = models.CharField(max_length=1024, db_column='uri')
    dicom_object_reference = models.OneToOneField('imaging.DicomObjectReference', on_delete=models.SET_NULL, db_column='dicom_object_reference_id', related_name='+', null=True, blank=True)
    status = models.CharField(max_length=20, db_index=True, db_column='status')
    created_at = models.DateTimeField(db_column='created_at')

    class Meta:
        db_table = 'ai_airesultartifact'

    def __str__(self):
        return str(self.pk)

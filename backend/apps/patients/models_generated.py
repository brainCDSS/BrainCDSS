# -*- coding: utf-8 -*-
# ================================================================
# AUTO-GENERATED FROM FINAL BrainOn DB CONTRACT.
# Source mapping: 최종_CDSS_BrainOn_DB_API_DjangoApp.xlsx
# Do not hand-edit this file.
# ================================================================

import uuid

from django.db import models
from django.utils import timezone as django_timezone

class Patient(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_column='id')
    user = models.OneToOneField('accounts.User', on_delete=models.SET_NULL, db_column='user_id', related_name='+', null=True, blank=True)
    patient_no = models.CharField(max_length=30, unique=True, db_column='patient_no')
    name = models.CharField(max_length=100, db_index=True, db_column='name')
    birth_date = models.DateField(null=True, db_index=True, db_column='birth_date')
    estimated_age = models.SmallIntegerField(null=True, db_column='estimated_age')
    sex = models.CharField(max_length=10, null=True, blank=True, db_column='sex')
    phone = models.CharField(max_length=30, null=True, blank=True, db_column='phone')
    emergency_contact = models.CharField(max_length=30, null=True, blank=True, db_column='emergency_contact')
    status = models.CharField(max_length=20, db_index=True, default='ACTIVE', db_column='status')
    merged_into_patient = models.ForeignKey('self', on_delete=models.SET_NULL, db_column='merged_into_patient_id', related_name='+', null=True, blank=True, db_index=True)
    merged_at = models.DateTimeField(null=True, db_index=True, db_column='merged_at')
    merged_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, db_column='merged_by_id', related_name='+', null=True, blank=True, db_index=True)
    created_by = models.ForeignKey('accounts.User', on_delete=models.PROTECT, db_column='created_by_id', related_name='+', db_index=True)
    created_at = models.DateTimeField(default=django_timezone.now, db_column='created_at')
    updated_at = models.DateTimeField(default=django_timezone.now, db_column='updated_at')
    pregnancy_status = models.CharField(max_length=20, db_index=True, default='UNKNOWN', db_column='pregnancy_status')
    pregnancy_status_updated_at = models.DateTimeField(null=True, db_index=True, db_column='pregnancy_status_updated_at')
    allergy_info = models.TextField(null=True, blank=True, db_column='allergy_info')

    class Meta:
        db_table = 'patients'
        constraints = [
            models.CheckConstraint(condition=models.Q(estimated_age__gte=0, estimated_age__lte=150), name='ck_patients_estimated_age_range'),
        ]

    def __str__(self):
        return str(self.pk)

class FavoriteHospital(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_column='id')
    patient = models.ForeignKey('patients.Patient', on_delete=models.CASCADE, db_column='patient_id', related_name='+')
    hospital = models.ForeignKey('organizations.Hospital', on_delete=models.CASCADE, db_column='hospital_id', related_name='+')
    created_at = models.DateTimeField(default=django_timezone.now, db_column='created_at')

    class Meta:
        db_table = 'favorite_hospitals'
        constraints = [
            models.UniqueConstraint(fields=['patient', 'hospital'], name='uq_favorite_hospitals_patient_hospital'),
        ]

    def __str__(self):
        return str(self.pk)

class PatientMergeHistory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_column='id')
    source_patient = models.OneToOneField('patients.Patient', on_delete=models.PROTECT, db_column='source_patient_id', related_name='+')
    target_patient = models.ForeignKey('patients.Patient', on_delete=models.PROTECT, db_column='target_patient_id', related_name='+', db_index=True)
    merged_by = models.ForeignKey('accounts.User', on_delete=models.PROTECT, db_column='merged_by_id', related_name='+', db_index=True)
    reason = models.TextField(null=True, blank=True, db_column='reason')
    merged_at = models.DateTimeField(db_index=True, default=django_timezone.now, db_column='merged_at')

    class Meta:
        db_table = 'patient_merge_history'

    def __str__(self):
        return str(self.pk)

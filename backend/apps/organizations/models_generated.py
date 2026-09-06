# -*- coding: utf-8 -*-
# ================================================================
# AUTO-GENERATED FROM FINAL BrainOn DB CONTRACT.
# Source mapping: 최종_CDSS_BrainOn_DB_API_DjangoApp.xlsx
# Do not hand-edit this file.
# ================================================================

import uuid

from django.db import models
from django.utils import timezone as django_timezone

class Hospital(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_column='id')
    name = models.CharField(max_length=150, db_index=True, db_column='name')
    address = models.CharField(max_length=255, db_column='address')
    phone = models.CharField(max_length=30, null=True, blank=True, db_column='phone')
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, db_column='latitude')
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, db_column='longitude')
    place = models.CharField(max_length=120, null=True, blank=True, unique=True, db_column='place_id')
    is_active = models.BooleanField(db_index=True, default=True, db_column='is_active')

    class Meta:
        db_table = 'hospitals'

    def __str__(self):
        return str(self.pk)

class Department(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_column='id')
    hospital = models.ForeignKey('organizations.Hospital', on_delete=models.PROTECT, db_column='hospital_id', related_name='+', db_index=True)
    code = models.CharField(max_length=30, unique=True, db_column='code')
    name = models.CharField(max_length=100, db_index=True, db_column='name')
    is_active = models.BooleanField(db_index=True, default=True, db_column='is_active')

    class Meta:
        db_table = 'departments'
        constraints = [
            models.UniqueConstraint(fields=['hospital', 'code'], name='uq_departments_hospital_code'),
        ]

    def __str__(self):
        return str(self.pk)

class Clinician(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_column='id')
    user = models.OneToOneField('accounts.User', on_delete=models.PROTECT, db_column='user_id', related_name='+')
    department = models.ForeignKey('organizations.Department', on_delete=models.PROTECT, db_column='department_id', related_name='+', db_index=True)
    license_no = models.CharField(max_length=50, null=True, blank=True, unique=True, db_column='license_no')
    specialty = models.CharField(max_length=100, null=True, blank=True, db_column='specialty')
    is_active = models.BooleanField(db_index=True, default=True, db_column='is_active')

    class Meta:
        db_table = 'clinicians'

    def __str__(self):
        return str(self.pk)

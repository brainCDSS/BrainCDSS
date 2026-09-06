# -*- coding: utf-8 -*-
# ================================================================
# AUTO-GENERATED FROM FINAL BrainOn DB CONTRACT.
# Source mapping: 최종_CDSS_BrainOn_DB_API_DjangoApp.xlsx
# Do not hand-edit this file.
# ================================================================

import uuid

from django.db import models
from django.utils import timezone as django_timezone

class ClinicianSchedule(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_column='id')
    clinician = models.ForeignKey('organizations.Clinician', on_delete=models.PROTECT, db_column='clinician_id', related_name='+', db_index=True)
    weekday = models.SmallIntegerField(db_index=True, db_column='weekday')
    start_time = models.TimeField(db_column='start_time')
    end_time = models.TimeField(db_column='end_time')
    slot_minutes = models.SmallIntegerField(default=30, db_column='slot_minutes')
    effective_from = models.DateField(db_index=True, db_column='effective_from')
    effective_to = models.DateField(null=True, db_index=True, db_column='effective_to')
    is_active = models.BooleanField(db_index=True, default=True, db_column='is_active')

    class Meta:
        db_table = 'clinician_schedules'
        constraints = [
            models.CheckConstraint(condition=models.Q(weekday__gte=0, weekday__lte=6), name='ck_clinician_schedules_weekday_range'),
            models.CheckConstraint(condition=models.Q(slot_minutes__gt=0), name='ck_clinician_schedules_slot_minutes_gt'),
        ]

    def __str__(self):
        return str(self.pk)

class AppointmentSlot(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_column='id')
    clinician = models.ForeignKey('organizations.Clinician', on_delete=models.PROTECT, db_column='clinician_id', related_name='+', db_index=True)
    schedule = models.ForeignKey('appointments.ClinicianSchedule', on_delete=models.SET_NULL, db_column='schedule_id', related_name='+', null=True, blank=True, db_index=True)
    start_at = models.DateTimeField(db_column='start_at')
    end_at = models.DateTimeField(db_column='end_at')
    status = models.CharField(max_length=20, db_index=True, default='AVAILABLE', db_column='status')
    held_until = models.DateTimeField(null=True, db_index=True, db_column='held_until')
    version = models.IntegerField(default=0, db_column='version')
    created_at = models.DateTimeField(default=django_timezone.now, db_column='created_at')

    class Meta:
        db_table = 'appointment_slots'
        constraints = [
            models.UniqueConstraint(fields=['clinician', 'start_at'], name='uq_appointment_slots_clinician_start_at'),
        ]

    def __str__(self):
        return str(self.pk)

class Appointment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_column='id')
    patient = models.ForeignKey('patients.Patient', on_delete=models.PROTECT, db_column='patient_id', related_name='+', db_index=True)
    hospital = models.ForeignKey('organizations.Hospital', on_delete=models.PROTECT, db_column='hospital_id', related_name='+', db_index=True)
    department = models.ForeignKey('organizations.Department', on_delete=models.PROTECT, db_column='department_id', related_name='+', db_index=True)
    clinician = models.ForeignKey('organizations.Clinician', on_delete=models.PROTECT, db_column='clinician_id', related_name='+', db_index=True)
    slot = models.ForeignKey('appointments.AppointmentSlot', on_delete=models.PROTECT, db_column='slot_id', related_name='+', db_index=True)
    requested_slot = models.ForeignKey('appointments.AppointmentSlot', on_delete=models.SET_NULL, db_column='requested_slot_id', related_name='+', null=True, blank=True, db_index=True)
    status = models.CharField(max_length=20, db_index=True, default='REQUESTED', db_column='status')
    request_type = models.CharField(max_length=20, default='NEW', db_column='request_type')
    rejection_reason = models.CharField(max_length=255, null=True, blank=True, db_column='rejection_reason')
    cancel_reason = models.CharField(max_length=255, null=True, blank=True, db_column='cancel_reason')
    requested_at = models.DateTimeField(db_index=True, default=django_timezone.now, db_column='requested_at')
    reschedule_requested_at = models.DateTimeField(null=True, db_index=True, db_column='reschedule_requested_at')
    confirmed_at = models.DateTimeField(null=True, db_column='confirmed_at')
    handled_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, db_column='handled_by_id', related_name='+', null=True, blank=True, db_index=True)
    cancelled_at = models.DateTimeField(null=True, db_column='cancelled_at')
    completed_at = models.DateTimeField(null=True, db_column='completed_at')
    created_at = models.DateTimeField(default=django_timezone.now, db_column='created_at')
    updated_at = models.DateTimeField(default=django_timezone.now, db_column='updated_at')

    class Meta:
        db_table = 'appointments'

    def __str__(self):
        return str(self.pk)

class AppointmentStatusHistory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_column='id')
    appointment = models.ForeignKey('appointments.Appointment', on_delete=models.CASCADE, db_column='appointment_id', related_name='+', db_index=True)
    from_status = models.CharField(max_length=20, null=True, blank=True, db_column='from_status')
    to_status = models.CharField(max_length=20, db_index=True, db_column='to_status')
    changed_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, db_column='changed_by_id', related_name='+', null=True, blank=True, db_index=True)
    reason = models.CharField(max_length=255, null=True, blank=True, db_column='reason')
    created_at = models.DateTimeField(db_index=True, default=django_timezone.now, db_column='created_at')

    class Meta:
        db_table = 'appointment_status_history'

    def __str__(self):
        return str(self.pk)

# -*- coding: utf-8 -*-
# ================================================================
# AUTO-GENERATED FROM FINAL BrainOn DB CONTRACT.
# Source mapping: 최종_CDSS_BrainOn_DB_API_DjangoApp.xlsx
# Do not hand-edit this file.
# ================================================================

import uuid

from django.db import models
from django.utils import timezone as django_timezone

class NotificationSetting(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_column='id')
    user = models.OneToOneField('accounts.User', on_delete=models.PROTECT, db_column='user_id', related_name='+')
    dnd_enabled = models.BooleanField(default=False, db_column='dnd_enabled')
    dnd_start = models.TimeField(null=True, db_column='dnd_start')
    dnd_end = models.TimeField(null=True, db_column='dnd_end')
    timezone = models.CharField(max_length=40, default='Asia/Seoul', db_column='timezone')
    updated_at = models.DateTimeField(default=django_timezone.now, db_column='updated_at')

    class Meta:
        db_table = 'notification_settings'

    def __str__(self):
        return str(self.pk)

class NotificationCategoryPreference(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_column='id')
    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE, db_column='user_id', related_name='+')
    category = models.CharField(max_length=40, db_column='category')
    enabled = models.BooleanField(default=True, db_column='enabled')
    updated_at = models.DateTimeField(default=django_timezone.now, db_column='updated_at')

    class Meta:
        db_table = 'notification_category_preferences'
        constraints = [
            models.UniqueConstraint(fields=['user', 'category'], name='uq_notification_category_preferences_user_category'),
        ]

    def __str__(self):
        return str(self.pk)

class FCMDeviceToken(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_column='id')
    user = models.ForeignKey('accounts.User', on_delete=models.PROTECT, db_column='user_id', related_name='+', db_index=True)
    device = models.CharField(max_length=120, unique=True, db_column='device_id')
    platform = models.CharField(max_length=20, db_column='platform')
    token = models.TextField(unique=True, db_column='token')
    is_active = models.BooleanField(db_index=True, default=True, db_column='is_active')
    last_seen_at = models.DateTimeField(db_index=True, default=django_timezone.now, db_column='last_seen_at')
    created_at = models.DateTimeField(default=django_timezone.now, db_column='created_at')
    updated_at = models.DateTimeField(default=django_timezone.now, db_column='updated_at')

    class Meta:
        db_table = 'fcm_device_tokens'
        constraints = [
            models.UniqueConstraint(fields=['user', 'device', 'platform'], condition=models.Q(is_active=True), name='uq_fcm_device_tokens_user_device_platform_partial'),
        ]

    def __str__(self):
        return str(self.pk)

class Notification(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_column='id')
    recipient_user = models.ForeignKey('accounts.User', on_delete=models.PROTECT, db_column='recipient_user_id', related_name='+', db_index=True)
    category = models.CharField(max_length=40, db_index=True, db_column='category')
    severity = models.CharField(max_length=20, db_index=True, default='INFO', db_column='severity')
    title = models.CharField(max_length=150, db_column='title')
    body = models.TextField(db_column='body')
    data_json = models.JSONField(null=True, default=dict, db_column='data_json')
    is_read = models.BooleanField(db_index=True, default=False, db_column='is_read')
    read_at = models.DateTimeField(null=True, db_column='read_at')
    created_at = models.DateTimeField(db_index=True, default=django_timezone.now, db_column='created_at')

    class Meta:
        db_table = 'notifications'

    def __str__(self):
        return str(self.pk)

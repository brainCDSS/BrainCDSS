# -*- coding: utf-8 -*-
# ================================================================
# AUTO-GENERATED FROM FINAL BrainOn DB CONTRACT.
# Source mapping: 최종_CDSS_BrainOn_DB_API_DjangoApp.xlsx
# Do not hand-edit this file.
# ================================================================

import uuid

from django.db import models
from django.utils import timezone as django_timezone

class AuditLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_column='id')
    actor_user = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, db_column='actor_user_id', related_name='+', null=True, blank=True, db_index=True)
    actor_login = models.CharField(max_length=50, null=True, blank=True, db_index=True, db_column='actor_login_id')
    actor_role_code = models.CharField(max_length=40, null=True, blank=True, db_index=True, db_column='actor_role_code')
    source_service = models.CharField(max_length=64, db_index=True, db_column='source_service')
    action = models.CharField(max_length=80, db_index=True, db_column='action')
    resource_type = models.CharField(max_length=80, db_index=True, db_column='resource_type')
    resource = models.CharField(max_length=128, null=True, blank=True, db_index=True, db_column='resource_id')
    patient = models.UUIDField(null=True, db_index=True, db_column='patient_id')
    outcome = models.CharField(max_length=16, db_index=True, db_column='outcome')
    reason = models.TextField(null=True, blank=True, db_column='reason')
    before_json = models.JSONField(null=True, db_column='before_json')
    after_json = models.JSONField(null=True, db_column='after_json')
    request_ip = models.GenericIPAddressField(null=True, blank=True, db_index=True, db_column='request_ip')
    user_agent = models.TextField(null=True, blank=True, db_column='user_agent')
    request = models.UUIDField(null=True, db_index=True, db_column='request_id')
    occurred_at = models.DateTimeField(db_index=True, db_column='occurred_at')
    created_at = models.DateTimeField(db_index=True, default=django_timezone.now, db_column='created_at')

    class Meta:
        db_table = 'audit_auditlog'

    def __str__(self):
        return str(self.pk)

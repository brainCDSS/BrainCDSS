# -*- coding: utf-8 -*-
# ================================================================
# AUTO-GENERATED FROM FINAL BrainOn DB CONTRACT.
# Source mapping: 최종_CDSS_BrainOn_DB_API_DjangoApp.xlsx
# Do not hand-edit this file.
# ================================================================

import uuid

from django.db import models
from django.utils import timezone as django_timezone

class IntegrationTransaction(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_column='id')
    direction = models.CharField(max_length=16, db_index=True, db_column='direction')
    standard = models.CharField(max_length=32, db_index=True, db_column='standard')
    source_system = models.CharField(max_length=128, db_index=True, db_column='source_system')
    target_system = models.CharField(max_length=128, db_index=True, db_column='target_system')
    message_type = models.CharField(max_length=64, db_index=True, db_column='message_type')
    external_message = models.CharField(max_length=128, db_index=True, db_column='external_message_id')
    trace = models.CharField(max_length=64, db_index=True, db_column='trace_id')
    status = models.CharField(max_length=20, db_index=True, db_column='status')
    attempt_count = models.IntegerField(db_column='attempt_count')
    error_code = models.CharField(max_length=64, null=True, blank=True, db_index=True, db_column='error_code')
    started_at = models.DateTimeField(db_index=True, db_column='started_at')
    completed_at = models.DateTimeField(null=True, db_column='completed_at')

    class Meta:
        db_table = 'interoperability_integrationtransaction'

    def __str__(self):
        return str(self.pk)

class IntegrationCursor(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_column='id')
    integration_type = models.CharField(max_length=32, db_index=True, db_column='integration_type')
    source_system = models.CharField(max_length=128, db_index=True, db_column='source_system')
    cursor_value = models.CharField(max_length=255, db_column='cursor_value')
    last_processed_at = models.DateTimeField(null=True, db_column='last_processed_at')

    class Meta:
        db_table = 'interoperability_integrationcursor'

    def __str__(self):
        return str(self.pk)

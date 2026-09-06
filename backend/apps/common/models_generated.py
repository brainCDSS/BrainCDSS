# -*- coding: utf-8 -*-
# ================================================================
# AUTO-GENERATED FROM FINAL BrainOn DB CONTRACT.
# Source mapping: 최종_CDSS_BrainOn_DB_API_DjangoApp.xlsx
# Do not hand-edit this file.
# ================================================================

import uuid

from django.db import models
from django.utils import timezone as django_timezone

class OutboxEvent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_column='id')
    event_type = models.CharField(max_length=128, db_index=True, db_column='event_type')
    aggregate_type = models.CharField(max_length=64, db_index=True, db_column='aggregate_type')
    aggregate = models.CharField(max_length=128, db_index=True, db_column='aggregate_id')
    payload = models.JSONField(db_column='payload')
    status = models.CharField(max_length=20, db_index=True, db_column='status')
    retry_count = models.IntegerField(db_column='retry_count')
    published_at = models.DateTimeField(null=True, db_column='published_at')
    created_at = models.DateTimeField(db_index=True, db_column='created_at')

    class Meta:
        db_table = 'common_outboxevent'

    def __str__(self):
        return str(self.pk)

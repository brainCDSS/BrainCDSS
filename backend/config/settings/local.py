"""Local development settings.

The official BrainOn development database is PostgreSQL.
"""

from .base import *


DEBUG = True

# ==============================================
# 로컬 Django - Celery 큐 설정 추가
CELERY_CONTROL_QUEUE_DURABLE = False
CELERY_CONTROL_QUEUE_EXCLUSIVE = True

CELERY_EVENT_QUEUE_DURABLE = False
CELERY_EVENT_QUEUE_EXCLUSIVE = True
# ==============================================
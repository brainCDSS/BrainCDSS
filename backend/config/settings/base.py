"""Shared settings for the BrainOn Django backend."""

import os
from pathlib import Path
from datetime import timedelta
from celery.schedules import crontab
from dotenv import load_dotenv
from corsheaders.defaults import default_headers

from config.celery_queues import DEFAULT_QUEUE, TASK_QUEUES, TASK_ROUTES

BASE_DIR = Path(__file__).resolve().parents[2]
ROOT_DIR = BASE_DIR.parent

load_dotenv(ROOT_DIR / ".env")

# ---------------------------------------------------------------------
# Core
# ---------------------------------------------------------------------

SECRET_KEY = os.getenv(
    "DJANGO_SECRET_KEY",
    "unsafe-local-placeholder-only",
)

MCP_BACKEND_TOKEN = os.getenv("MCP_BACKEND_TOKEN", "")

# Independent literature feature; project/location reuse ADC configuration only.
CLINICAL_EVIDENCE_GEMINI_MODEL = os.getenv("CLINICAL_EVIDENCE_GEMINI_MODEL", "")
CLINICAL_EVIDENCE_GCP_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT", "")
CLINICAL_EVIDENCE_GCP_LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "global")
CLINICAL_EVIDENCE_SUMMARY_VERSION = os.getenv("CLINICAL_EVIDENCE_SUMMARY_VERSION", "abstract-v1")
CLINICAL_EVIDENCE_PUBMED_EMAIL = os.getenv("CLINICAL_EVIDENCE_PUBMED_EMAIL", "")
CLINICAL_EVIDENCE_PUBMED_API_KEY = os.getenv("CLINICAL_EVIDENCE_PUBMED_API_KEY", "")
CLINICAL_EVIDENCE_LOOKBACK_DAYS = int(os.getenv("CLINICAL_EVIDENCE_LOOKBACK_DAYS", "730"))
CLINICAL_EVIDENCE_SEARCH_LIMIT = int(os.getenv("CLINICAL_EVIDENCE_SEARCH_LIMIT", "60"))
CLINICAL_EVIDENCE_STORE_LIMIT = int(os.getenv("CLINICAL_EVIDENCE_STORE_LIMIT", "10"))
CLINICAL_EVIDENCE_HTTP_TIMEOUT = int(os.getenv("CLINICAL_EVIDENCE_HTTP_TIMEOUT", "30"))

DEBUG = False

ALLOWED_HOSTS = [
    host.strip()
    for host in os.getenv(
        "DJANGO_ALLOWED_HOSTS",
        "localhost,127.0.0.1",
    ).split(",")
    if host.strip()
]

# 예약설정시간으로 인해 추가함
APPOINTMENT_HOLD_TTL_MINUTES = int(
    os.getenv("APPOINTMENT_HOLD_TTL_MINUTES", "10")
)


# ---------------------------------------------------------------------
# Applications
# ---------------------------------------------------------------------

BRAINON_APPS = [
    "common",
    "accounts",
    "organizations",
    "patients",
    "appointments",
    "assessments",
    "clinical_records",
    "consultations",
    "prescriptions",
    "medications",
    "test_results",
    "imaging",
    "radiology",
    "ai_analysis",
    "cdss",
    "medication_safety",
    "notifications",
    "records_management",
    "surgical_planning",
    "assistant",
    "integrations",
    "clinical_evidence",
    "audit",
]


INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    "corsheaders",
    "rest_framework",
    "rest_framework_simplejwt.token_blacklist",
    "drf_spectacular",

    *[f"apps.{app}" for app in BRAINON_APPS],
]

AUTH_USER_MODEL = "accounts.User"

# ---------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------

MIDDLEWARE = [
    "apps.common.middleware.CorrelationIdMiddleware",
    "apps.common.http_metrics.HttpPrometheusMetricsMiddleware",
    "apps.common.dependency_observability.DependencyOutcomeObservabilityMiddleware",
    "django.middleware.security.SecurityMiddleware",

    # CORS headers must be added before CommonMiddleware.
    "corsheaders.middleware.CorsMiddleware",

    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
]


ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"


# ---------------------------------------------------------------------
# PostgreSQL
# ---------------------------------------------------------------------

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("POSTGRES_DB", "brainon"),
        "USER": os.getenv("POSTGRES_USER", "brainon"),
        "PASSWORD": os.getenv("POSTGRES_PASSWORD", ""),
        "HOST": os.getenv("POSTGRES_HOST", "localhost"),
        "PORT": os.getenv("POSTGRES_PORT", "5432"),
    }
}


# ---------------------------------------------------------------------
# Django REST Framework
# ---------------------------------------------------------------------

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_SCHEMA_CLASS": (
        "drf_spectacular.openapi.AutoSchema"
    ),
    "EXCEPTION_HANDLER": "apps.common.errors.api_exception_handler",
}


# ---------------------------------------------------------------------
# OpenAPI / Swagger
# ---------------------------------------------------------------------

SPECTACULAR_SETTINGS = {
    "TITLE": "BrainOn CDSS API",
    "DESCRIPTION": "BrainOn cerebrovascular CDSS backend API",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
}


# ---------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------

CORS_ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ALLOWED_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    ).split(",")
    if origin.strip()
]

CORS_ALLOW_HEADERS = (*default_headers, "idempotency-key")


# ---------------------------------------------------------------------
# Internationalization
# ---------------------------------------------------------------------

LANGUAGE_CODE = "ko-kr"
TIME_ZONE = "Asia/Seoul"

USE_I18N = True
USE_TZ = True


# ---------------------------------------------------------------------
# Static
# ---------------------------------------------------------------------

STATIC_URL = "static/"


# Django-generated implicit PK fallback only.
#
# BrainOn business tables will define explicit UUID primary keys.
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# ---------------------------------------------------------------------
# Celery
#
# RabbitMQ runtime validation will be performed later.
# ---------------------------------------------------------------------

CELERY_BROKER_URL = os.getenv(
    "CELERY_BROKER_URL",
    "amqp://guest:guest@localhost:5672//",
)

CELERY_RESULT_BACKEND = None
CELERY_TASK_IGNORE_RESULT = True
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_DEFAULT_QUEUE = DEFAULT_QUEUE
CELERY_TASK_QUEUES = TASK_QUEUES
CELERY_TASK_ROUTES = TASK_ROUTES
CELERY_TASK_CREATE_MISSING_QUEUES = False
CELERY_TASK_DEFAULT_DELIVERY_MODE = "persistent"
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
# RabbitMQ 4.3 rejects transient non-exclusive queues.
CELERY_CONTROL_QUEUE_EXCLUSIVE = True
CELERY_EVENT_QUEUE_EXCLUSIVE = True

# ---------------------------------------------------------------------
# Celery Beat
# ---------------------------------------------------------------------
# 1) Outbox: promptly retry PENDING/FAILED domain events.
# 2) MFDS DUR: refresh all seven reviewed reference-data types daily.
CELERY_BEAT_SCHEDULE = {
    "publish-pending-outbox-events": {
        "task": "apps.common.outbox_tasks.publish_pending_outbox_events",
        "schedule": crontab(minute="*"),
        "kwargs": {
            "limit": 100,
        },
    },
    "sync-mfds-dur-daily": {
        "task": "medication_safety.sync_mfds_dur_data",
        "schedule": crontab(
            hour=3,
            minute=30,
        ),
        "kwargs": {
            "kind": "ALL",
            "dry_run": False,
            "page_size": 100,
        },
    },
}

# Local-only bridge for synthetic inference verification. Disabled by default.
AI_INFERENCE_DEVELOPMENT_ENABLED = (
    os.getenv("AI_INFERENCE_DEVELOPMENT_ENABLED", "false").lower()
    == "true"
)
INFERENCE_API_URL = os.getenv(
    "INFERENCE_API_URL",
    "http://inference-api:8100",
)
INFERENCE_TIMEOUT_SECONDS = int(
    os.getenv("INFERENCE_TIMEOUT_SECONDS", "10")
)
INFERENCE_USE_ID_TOKEN = (
    os.getenv("INFERENCE_USE_ID_TOKEN", "false").lower() == "true"
)
INFERENCE_AUTH_AUDIENCE = os.getenv(
    "INFERENCE_AUTH_AUDIENCE",
    INFERENCE_API_URL,
)

GCS_NIFTI_ALLOWED_BUCKETS = [
    value.strip()
    for value in os.getenv(
        "GCS_NIFTI_ALLOWED_BUCKETS", "brainon-cdss-datasets,brainon-cdss-inference-results"
    ).split(",")
    if value.strip()
]
GCS_SIGNED_URL_TTL_SECONDS = int(
    os.getenv("GCS_SIGNED_URL_TTL_SECONDS", "300")
)
GCS_SIGNING_SERVICE_ACCOUNT_EMAIL = os.getenv(
    "GCS_SIGNING_SERVICE_ACCOUNT_EMAIL", ""
).strip()

# Orthanc is accessed only by backend/worker code. Browser clients use backend
# APIs and never receive these credentials.
ORTHANC_URL = os.getenv("ORTHANC_URL", "http://orthanc:8042").rstrip("/")
ORTHANC_USERNAME = os.getenv("ORTHANC_USERNAME", "brainon")
ORTHANC_PASSWORD = os.getenv("ORTHANC_PASSWORD", "")
ORTHANC_TIMEOUT_SECONDS = int(os.getenv("ORTHANC_TIMEOUT_SECONDS", "60"))




# =====================================================================
# 기본 JWT 설정 : 개발 종료 후 이거 사용하세요.
# =====================================================================
# # BEGIN BRAINON USER JWT SETTINGS
# # User JWT signing key.
# # Production: inject JWT_SIGNING_KEY through Cloud Run Secret Manager.

# _user_jwt_signing_key = os.getenv("JWT_SIGNING_KEY")

# SIMPLE_JWT = {
#     **globals().get("SIMPLE_JWT", {}),

#     # Access Token 유효시간
#     "ACCESS_TOKEN_LIFETIME": timedelta(minutes=5),

#     # Refresh Token 유효시간
#     "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
# }

# # JWT 전용 서명키가 환경변수에 있으면 사용
# if _user_jwt_signing_key:
#     SIMPLE_JWT["SIGNING_KEY"] = _user_jwt_signing_key

# # END BRAINON USER JWT SETTINGS



# =====================================================================
# 개발용 임시 JWT 설정
# =====================================================================
# JWT 설정
# 토큰 유효시간은 환경변수에서 관리
# 환경변수가 없으면 Simple JWT 기본값과 동일하게
# Access 5분 / Refresh 1일 사용
# =====================================================================

_user_jwt_signing_key = os.getenv("JWT_SIGNING_KEY")

# SIMPLE_JWT = {
#     **globals().get("SIMPLE_JWT", {}),

#     "ACCESS_TOKEN_LIFETIME": timedelta(
#         minutes=int(os.getenv("JWT_ACCESS_TOKEN_MINUTES", "5"))
#     ),

#     "REFRESH_TOKEN_LIFETIME": timedelta(
#         days=int(os.getenv("JWT_REFRESH_TOKEN_DAYS", "1"))
#     ),
# }

SIMPLE_JWT = {
    **globals().get("SIMPLE_JWT", {}),
    "ACCESS_TOKEN_LIFETIME": timedelta(
        minutes=int(os.getenv("JWT_ACCESS_TOKEN_MINUTES", "60"))
    ),
    "REFRESH_TOKEN_LIFETIME": timedelta(
        days=int(os.getenv("JWT_REFRESH_TOKEN_DAYS", "7"))
    ),
}

if _user_jwt_signing_key:
    SIMPLE_JWT["SIGNING_KEY"] = _user_jwt_signing_key

# =====================================================================

# BrainOn operational monitoring.
CELERY_WORKER_SEND_TASK_EVENTS = True
CELERY_TASK_SEND_SENT_EVENT = True
CELERY_TASK_TRACK_STARTED = True

# Explicit operational Celery task imports.
# Keep autodiscovery for application tasks; this guarantees that
# the observability probe is registered at worker startup.
CELERY_IMPORTS = tuple(
    dict.fromkeys(
        (
            *globals().get(
                "CELERY_IMPORTS",
                (),
            ),
            "apps.common.tasks",
        )
    )
)

"""Shared settings for the BrainOn Django backend."""

import os
from pathlib import Path
from datetime import timedelta
from dotenv import load_dotenv

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

DEBUG = False

ALLOWED_HOSTS = [
    host.strip()
    for host in os.getenv(
        "DJANGO_ALLOWED_HOSTS",
        "localhost,127.0.0.1",
    ).split(",")
    if host.strip()
]


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
    "ACCESS_TOKEN_LIFETIME": timedelta(days=3650),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=3650),
}

if _user_jwt_signing_key:
    SIMPLE_JWT["SIGNING_KEY"] = _user_jwt_signing_key

# =====================================================================
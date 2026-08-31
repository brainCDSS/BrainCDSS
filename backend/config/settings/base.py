"""Shared settings for the BrainOn Django backend."""

import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]


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
        "http://localhost:5173",
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
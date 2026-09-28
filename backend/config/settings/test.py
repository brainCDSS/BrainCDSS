"""
BrainOn isolated test settings.

Goals
-----
1. Never use the shared PostgreSQL / Cloud SQL database.
2. Never require RabbitMQ while running ordinary Django tests.
3. Keep tests deterministic and disposable.
4. Make accidental external-service access less likely.
"""

from .base import *


# ---------------------------------------------------------------------
# Core
# ---------------------------------------------------------------------

DEBUG = False

SECRET_KEY = (
    "brainon-test-only-secret-key-"
    "never-use-this-in-production"
)


# ---------------------------------------------------------------------
# Database
#
# IMPORTANT:
# Test execution must NEVER point to the shared BrainOn PostgreSQL DB.
# SQLite in-memory DB is created per test process and disappears when
# the process exits.
# ---------------------------------------------------------------------

DATABASES = {
    "default": {
        "ENGINE":
            "django.db.backends.sqlite3",

        "NAME":
            ":memory:",

        "CONN_MAX_AGE":
            0,

        "TEST": {
            "NAME":
                ":memory:",
        },
    },
}


# ---------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]


# ---------------------------------------------------------------------
# Celery
#
# Tests must not connect to the shared RabbitMQ runtime.
# ---------------------------------------------------------------------

CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
CELERY_TASK_STORE_EAGER_RESULT = False

CELERY_BROKER_URL = "memory://"

CELERY_RESULT_BACKEND = None
CELERY_TASK_IGNORE_RESULT = True


# ---------------------------------------------------------------------
# Cache / email
# ---------------------------------------------------------------------

CACHES = {
    "default": {
        "BACKEND":
            "django.core.cache.backends.locmem.LocMemCache",

        "LOCATION":
            "brainon-test-cache",
    },
}

EMAIL_BACKEND = (
    "django.core.mail.backends.locmem.EmailBackend"
)


# ---------------------------------------------------------------------
# External runtime integrations
#
# These values prevent ordinary tests from accidentally resolving
# production/internal runtime service names.
# Individual integration tests should mock the corresponding client.
# ---------------------------------------------------------------------

AI_INFERENCE_DEVELOPMENT_ENABLED = False

INFERENCE_API_URL = (
    "http://127.0.0.1:9/test-inference-disabled"
)

INFERENCE_USE_ID_TOKEN = False

ORTHANC_URL = (
    "http://127.0.0.1:9/test-orthanc-disabled"
)


# ---------------------------------------------------------------------
# Safety guard
#
# If this assertion ever fails, stop immediately rather than allowing
# tests to reach PostgreSQL / Cloud SQL.
# ---------------------------------------------------------------------

assert (
    DATABASES["default"]["ENGINE"]
    == "django.db.backends.sqlite3"
), "BrainOn tests must not use PostgreSQL."

assert (
    DATABASES["default"]["NAME"]
    == ":memory:"
), "BrainOn tests must use the isolated in-memory database."

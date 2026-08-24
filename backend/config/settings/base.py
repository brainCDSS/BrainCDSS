"""Shared settings for PostgreSQL, DRF/JWT and RabbitMQ-backed Celery."""
import os
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parents[2]
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "unsafe-local-placeholder-only")
DEBUG = False
ALLOWED_HOSTS = [x for x in os.getenv("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if x]
INSTALLED_APPS = ["django.contrib.auth","django.contrib.contenttypes","django.contrib.sessions","django.contrib.messages","django.contrib.staticfiles","rest_framework",*['apps.'+x for x in ["common","accounts","organizations","patients","appointments","assessments","clinical_records","consultations","prescriptions","medications","test_results","imaging","ai_analysis","cdss","medication_safety","notifications","records_management","surgical_planning","assistant","integrations","audit"]]]
MIDDLEWARE = ["apps.common.middleware.CorrelationIdMiddleware","django.middleware.security.SecurityMiddleware","django.contrib.sessions.middleware.SessionMiddleware","django.middleware.common.CommonMiddleware","django.middleware.csrf.CsrfViewMiddleware","django.contrib.auth.middleware.AuthenticationMiddleware","django.contrib.messages.middleware.MessageMiddleware"]
ROOT_URLCONF="config.urls"; TEMPLATES=[]; WSGI_APPLICATION="config.wsgi.application"; ASGI_APPLICATION="config.asgi.application"
DATABASES={"default":{"ENGINE":"django.db.backends.postgresql","NAME":os.getenv("POSTGRES_DB","brainon"),"USER":os.getenv("POSTGRES_USER","brainon"),"PASSWORD":os.getenv("POSTGRES_PASSWORD",""),"HOST":os.getenv("POSTGRES_HOST","localhost"),"PORT":os.getenv("POSTGRES_PORT","5432")}}
REST_FRAMEWORK={"DEFAULT_AUTHENTICATION_CLASSES":["rest_framework_simplejwt.authentication.JWTAuthentication"],"EXCEPTION_HANDLER":"apps.common.errors.api_exception_handler"}
LANGUAGE_CODE="ko-kr"; TIME_ZONE="Asia/Seoul"; USE_I18N=True; USE_TZ=True; STATIC_URL="static/"; DEFAULT_AUTO_FIELD="django.db.models.BigAutoField"
CELERY_BROKER_URL=os.getenv("CELERY_BROKER_URL","amqp://guest:guest@localhost:5672//"); CELERY_RESULT_BACKEND=None; CELERY_TASK_IGNORE_RESULT=True; CELERY_TIMEZONE=TIME_ZONE

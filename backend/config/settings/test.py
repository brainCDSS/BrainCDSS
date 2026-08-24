"""Hermetic test settings with no external services or API keys."""
from .base import *
SECRET_KEY="test-only-not-a-secret"; DATABASES={"default":{"ENGINE":"django.db.backends.sqlite3","NAME":":memory:"}}; PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"]


"""Local settings; in-memory SQLite makes first-run checks independent of Docker."""
from .base import *
DEBUG=True
DATABASES={"default":{"ENGINE":"django.db.backends.sqlite3","NAME":BASE_DIR / "local.sqlite3"}}


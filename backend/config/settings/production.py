"""Production baseline; deployment must inject every secret and trusted host."""
from .base import *
DEBUG=False
SECURE_PROXY_SSL_HEADER=("HTTP_X_FORWARDED_PROTO","https")


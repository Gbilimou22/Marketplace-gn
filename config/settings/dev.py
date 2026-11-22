"""
Development settings for Marketplace Guinée.
"""

from .base import *  # noqa: F403
from .base import BASE_DIR, env

DEBUG = env.bool("DEBUG", default=True)

SECRET_KEY = env("SECRET_KEY", default="django-insecure-dev-key-not-for-production-only-local-use")

ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["localhost", "127.0.0.1", "[::1]", "testserver"])

# Database: PostgreSQL via Docker Compose by default, fallback to SQLite if PostgreSQL is not up yet
DATABASES = {
    "default": env.db(
        "DATABASE_URL",
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
    )
}

# Console email backend for development
EMAIL_BACKEND = env("EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend")

# Password validation relaxed in dev for easier testing
AUTH_PASSWORD_VALIDATORS = []

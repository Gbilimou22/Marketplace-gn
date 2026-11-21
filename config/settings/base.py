"""
Django base settings for Marketplace Guinée project.

This file contains common configuration shared between dev and prod environments.
All business constraints and security requirements from AGENTS.md are configured here.
"""

from pathlib import Path

import environ

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Initialize environment variables handler
env = environ.Env()

# Take environment variables from .env file if it exists
env_file = BASE_DIR / ".env"
if env_file.exists():
    environ.Env.read_env(str(env_file))

# Application definition
DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",
]

THIRD_PARTY_APPS = [
    # django-allauth
    "allauth",
    "allauth.account",
]

LOCAL_APPS = [
    "apps.core.apps.CoreConfig",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    # allauth account middleware
    "allauth.account.middleware.AccountMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# Internationalization and Localization
# Context Guinea: timezone Africa/Conakry, Language French, Currency GNF
LANGUAGE_CODE = env("LANGUAGE_CODE", default="fr-fr")
TIME_ZONE = env("TIME_ZONE", default="Africa/Conakry")
USE_I18N = True
USE_TZ = True

# Custom application constants
CURRENCY_CODE = env("CURRENCY_CODE", default="GNF")
BAYESIAN_MIN_REVIEWS_THRESHOLD = env.int("BAYESIAN_MIN_REVIEWS_THRESHOLD", default=10)
DEFAULT_PAGE_SIZE = env.int("DEFAULT_PAGE_SIZE", default=20)

# Static files (CSS, JavaScript, Images)
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]

# Media files (User uploads: products, logos, etc.)
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"
# Max upload size: 5MB per file
DATA_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024

# Default primary key field type: BigAutoField (UUIDs are used on public models as explicit fields)
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Site framework (required by allauth)
SITE_ID = 1

# Authentication backends
AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]

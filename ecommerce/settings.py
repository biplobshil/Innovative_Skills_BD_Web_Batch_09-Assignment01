"""
Django settings for the ecommerce project.
"""
import os
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()  # reads .env from the project root

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = "django-insecure-change-this-in-production"

DEBUG = True

ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # 3rd party
    "rest_framework",
    "django_filters",
    "corsheaders",
    # local
    "store",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "ecommerce.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "store.context_processors.cart",
            ],
        },
    },
]

WSGI_APPLICATION = "ecommerce.wsgi.application"
ASGI_APPLICATION = "ecommerce.asgi.application"

# Default: SQLite for zero-config local dev.
# Swap to PostgreSQL in production for full-text search (see store/views.py).
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ---- Auth ----
LOGIN_URL = "/accounts/login/"
LOGIN_REDIRECT_URL = "/products/"
LOGOUT_REDIRECT_URL = "/products/"

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---- DRF ----
REST_FRAMEWORK = {
    "DEFAULT_FILTER_BACKENDS": ["django_filters.rest_framework.DjangoFilterBackend"],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 12,
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.AllowAny"],
}

# ---- CORS (open for local frontend dev) ----
CORS_ALLOW_ALL_ORIGINS = True

# ---- bKash Tokenized Checkout ----
# Get sandbox App Key/Secret/Username/Password by registering at
# https://developer.bka.sh — never commit real credentials to source control.
# Set these as environment variables (e.g. in a .env file loaded before
# manage.py runs, or in your shell/hosting provider's env config).
BKASH_BASE_URL = os.environ.get(
    "BKASH_BASE_URL", "https://tokenized.sandbox.bka.sh/v1.2.0-beta"
)


BKASH_APP_KEY = os.environ.get("BKASH_APP_KEY", "")
BKASH_APP_SECRET = os.environ.get("BKASH_APP_SECRET", "")
BKASH_USERNAME = os.environ.get("BKASH_USERNAME", "")
BKASH_PASSWORD = os.environ.get("BKASH_PASSWORD", "")


# ---- Email (order confirmation receipts) ----
# Dev default: prints emails to the runserver console instead of sending them.
# For real sending, set EMAIL_BACKEND to
# "django.core.mail.backends.smtp.EmailBackend" and fill in the SMTP_* vars
# below via environment variables / .env (e.g. Gmail SMTP, SendGrid, etc.)
EMAIL_BACKEND = os.environ.get(
    "EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend"
)
EMAIL_HOST = os.environ.get("EMAIL_HOST", "")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = os.environ.get("EMAIL_USE_TLS", "True") == "True"
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "no-reply@shopfast.example.com")


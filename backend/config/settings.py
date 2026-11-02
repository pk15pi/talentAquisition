import os
import warnings
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

from config.security import csv_setting, resolve_secret_key
from config.storage import build_storages

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR.parent / ".env")

DEBUG = os.getenv("DJANGO_DEBUG", "0") == "1"
SECRET_KEY = resolve_secret_key(os.getenv("DJANGO_SECRET_KEY"), debug=DEBUG)
if DEBUG and not os.getenv("DJANGO_SECRET_KEY", "").strip():
    warnings.warn(
        "DJANGO_SECRET_KEY is unset. Using a development-only key because DJANGO_DEBUG=1.",
        stacklevel=1,
    )

ALLOWED_HOSTS = csv_setting("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "rest_framework",
    "rest_framework_simplejwt",
    "apps.accounts",
    "apps.organizations",
    "apps.clients",
    "apps.sales",
    "apps.jobs",
    "apps.candidates",
    "apps.applications",
    "apps.recruitment",
    "apps.interviews",
    "apps.placements",
    "apps.billing",
    "apps.matching",
    "apps.reports",
    "apps.audit",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "apps.accounts.throttles.AdminLoginRateLimitMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
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
            ]
        },
    }
]
WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("POSTGRES_DB", "synfotalent"),
        "USER": os.getenv("POSTGRES_USER", "synfotalent"),
        "PASSWORD": os.getenv("POSTGRES_PASSWORD", "synfotalent_dev_password"),
        "HOST": os.getenv("POSTGRES_HOST", "localhost"),
        "PORT": os.getenv("POSTGRES_PORT", "5432"),
        "CONN_MAX_AGE": int(os.getenv("POSTGRES_CONN_MAX_AGE", "0")),
    }
}

AUTH_USER_MODEL = "accounts.User"
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Kolkata"
USE_I18N = True
USE_TZ = True
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
# Media is not mounted on Nginx. These modes keep resume files unreadable by other users on a shared volume.
FILE_UPLOAD_PERMISSIONS = 0o640
FILE_UPLOAD_DIRECTORY_PERMISSIONS = 0o750
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Debug defaults to the Vite origin so local login works. Production has no default origin.
_cors_default = "http://localhost:5173" if DEBUG else ""
CORS_ALLOWED_ORIGINS = csv_setting("CORS_ALLOWED_ORIGINS", _cors_default)
CORS_ALLOW_CREDENTIALS = False
CSRF_TRUSTED_ORIGINS = csv_setting("CSRF_TRUSTED_ORIGINS", "")

# Nginx terminates TLS. Gunicorn is reached over HTTP, including health checks,
# so Django must not redirect those requests. Secure cookies and HSTS still apply
# when debug is off. W008 (SSL redirect) and W021 (HSTS preload) stay silenced;
# preload is opt-in because it cannot be undone casually.
if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    USE_X_FORWARDED_HOST = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    CSRF_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    CSRF_COOKIE_SAMESITE = "Lax"
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_REFERRER_POLICY = "same-origin"
    X_FRAME_OPTIONS = "DENY"
    SECURE_HSTS_SECONDS = int(os.getenv("DJANGO_HSTS_SECONDS", "31536000"))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = os.getenv("DJANGO_HSTS_INCLUDE_SUBDOMAINS", "1") == "1"
    SECURE_HSTS_PRELOAD = os.getenv("DJANGO_HSTS_PRELOAD", "0") == "1"
    SECURE_SSL_REDIRECT = False
    SILENCED_SYSTEM_CHECKS = ["security.W008", "security.W021"]

_querystring_expire = os.getenv("AWS_QUERYSTRING_EXPIRE", "300").strip() or "300"
try:
    QUERYSTRING_EXPIRE = int(_querystring_expire)
except ValueError as exc:
    from django.core.exceptions import ImproperlyConfigured

    raise ImproperlyConfigured("AWS_QUERYSTRING_EXPIRE must be an integer number of seconds.") from exc

STORAGES, RESUME_OBJECT_STORAGE = build_storages(
    bucket=os.getenv("AWS_STORAGE_BUCKET_NAME", ""),
    access_key=os.getenv("AWS_ACCESS_KEY_ID", ""),
    secret_key=os.getenv("AWS_SECRET_ACCESS_KEY", ""),
    endpoint_url=os.getenv("AWS_S3_ENDPOINT_URL", ""),
    region_name=os.getenv("AWS_S3_REGION_NAME", ""),
    addressing_style=os.getenv("AWS_S3_ADDRESSING_STYLE", ""),
    querystring_expire=QUERYSTRING_EXPIRE,
)

CACHE_URL = os.getenv("CACHE_URL", "").strip()
if CACHE_URL:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": CACHE_URL,
            "OPTIONS": {"socket_connect_timeout": 2},
        }
    }
else:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "synfotalent",
        }
    }

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ("rest_framework_simplejwt.authentication.JWTAuthentication",),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_THROTTLE_CLASSES": (
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ),
    "DEFAULT_THROTTLE_RATES": {
        "anon": os.getenv("THROTTLE_ANON", "120/min"),
        "user": os.getenv("THROTTLE_USER", "600/min"),
        "login": os.getenv("THROTTLE_LOGIN", "30/min"),
    },
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 25,
    "DEFAULT_VERSIONING_CLASS": "rest_framework.versioning.URLPathVersioning",
    "DEFAULT_VERSION": "v1",
    "ALLOWED_VERSIONS": ("v1",),
    "EXCEPTION_HANDLER": "apps.errors.api_exception_handler",
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=30),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=1),
    "ROTATE_REFRESH_TOKENS": False,
    "BLACKLIST_AFTER_ROTATION": False,
    "UPDATE_LAST_LOGIN": True,
}

# Host-side default is localhost. Compose sets redis://redis:6379 for containers.
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "INFO"},
}

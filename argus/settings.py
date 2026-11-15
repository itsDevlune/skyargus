import os
from pathlib import Path

import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent
DEBUG = os.getenv("ARGUS_DEBUG", "1") == "1"
SECRET_KEY = os.getenv("SECRET_KEY", "local-only-argus-change-in-production")
if not DEBUG and SECRET_KEY == "local-only-argus-change-in-production":
    raise RuntimeError("Set SECRET_KEY for production")
ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1,testserver").split(",")
CSRF_TRUSTED_ORIGINS = [s for s in os.getenv("CSRF_TRUSTED_ORIGINS", "").split(",") if s]
INSTALLED_APPS = ["django.contrib.contenttypes", "django.contrib.sessions", "django.contrib.staticfiles", "apps.core"]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
ROOT_URLCONF = "argus.urls"
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.template.context_processors.csrf",
            ]
        },
    }
]
DATABASES = {"default": dj_database_url.config(default=f"sqlite:///{BASE_DIR / 'local.sqlite3'}", conn_max_age=60)}
STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
DATA_ROOT = Path(os.getenv("DATA_ROOT", BASE_DIR / "data"))
DATA_ROOT.mkdir(exist_ok=True, parents=True)
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
USE_TZ = True
TIME_ZONE = "UTC"
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
X_FRAME_OPTIONS = "DENY"
SECURE_CONTENT_TYPE_NOSNIFF = True
if not DEBUG:
    SESSION_COOKIE_SECURE = CSRF_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = True
    SECURE_REDIRECT_EXEMPT = [r"^health/$"]
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
CELERY_BROKER_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
CELERY_TASK_ACKS_LATE = True
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_TASK_TIME_LIMIT = 300
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
DATA_UPLOAD_MAX_MEMORY_SIZE = 65536
# Zero disables local job quotas. Optional deployment controls, not archive limits.
ARGUS_SESSION_ACTIVE_JOBS = max(0, int(os.getenv("ARGUS_SESSION_ACTIVE_JOBS", "0")))
ARGUS_SESSION_JOBS_PER_HOUR = max(0, int(os.getenv("ARGUS_SESSION_JOBS_PER_HOUR", "0")))
ARGUS_QUEUE_LIMIT = max(0, int(os.getenv("ARGUS_QUEUE_LIMIT", "0")))

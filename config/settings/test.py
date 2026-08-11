"""
MaintenanceHub — Test Settings
Used by CI (GitHub Actions) and local `manage.py test` runs.
"""
from .base import *  # noqa

DEBUG = False
SECRET_KEY = env("SECRET_KEY", default="test-secret-key-not-for-production")
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "testserver"]

# ── Database ──────────────────────────────────────────────────────────────────
# CI sets DATABASE_URL; fall back to SQLite for ultra-fast local unit tests
if not env("DATABASE_URL", default=None):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": ":memory:",
        }
    }

# ── Email ─────────────────────────────────────────────────────────────────────
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# ── Celery ────────────────────────────────────────────────────────────────────
# Run all Celery tasks synchronously so we don't need a running broker in tests
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# ── Cache ─────────────────────────────────────────────────────────────────────
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}

# ── Channels ──────────────────────────────────────────────────────────────────
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer",
    }
}

# ── Password hashing ──────────────────────────────────────────────────────────
# Use the fastest (weakest) hasher in tests to speed up User creation
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

# ── Media files ───────────────────────────────────────────────────────────────
# Write test uploads to a temp-like path; never committed or served
MEDIA_ROOT = "/tmp/maintenancehub_test_media/"

# ── Static files ──────────────────────────────────────────────────────────────
STATICFILES_STORAGE = "django.contrib.staticfiles.storage.StaticFilesStorage"

# ── Logging ───────────────────────────────────────────────────────────────────
# Suppress most logging noise during tests
LOGGING = {
    "version": 1,
    "disable_existing_loggers": True,
    "handlers": {"null": {"class": "logging.NullHandler"}},
    "root": {"handlers": ["null"]},
}

# ── Rate limiting ─────────────────────────────────────────────────────────────
# Disable rate limiting in tests to avoid 429s on login/register fixtures
RATELIMIT_ENABLE = False

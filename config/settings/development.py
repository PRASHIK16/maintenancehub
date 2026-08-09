"""
MaintenanceHub — Development Settings
"""
from .base import *  # noqa

DEBUG = True
SECRET_KEY = env("SECRET_KEY", default="dev-secret-key-not-for-production-use-only")
ALLOWED_HOSTS = ["*"]

# Use SQLite for development if no DATABASE_URL set
# Postgres is recommended even in dev — set DATABASE_URL in .env

# Email in console
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Django Debug Toolbar (optional)
try:
    import debug_toolbar  # noqa
    INSTALLED_APPS += ["debug_toolbar"]  # noqa
    MIDDLEWARE = ["debug_toolbar.middleware.DebugToolbarMiddleware"] + MIDDLEWARE  # noqa
    INTERNAL_IPS = ["127.0.0.1"]
except ImportError:
    pass

# Relaxed CSP for development
CORS_ALLOW_ALL_ORIGINS = True

# Show emails in console
CELERY_TASK_ALWAYS_EAGER = False  # Set True to run Celery tasks synchronously in tests

# Static files served by Django in dev
STATICFILES_STORAGE = "django.contrib.staticfiles.storage.StaticFilesStorage"

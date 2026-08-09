"""MaintenanceHub config package — Celery auto-discovery."""
from .celery import app as celery_app

__all__ = ("celery_app",)

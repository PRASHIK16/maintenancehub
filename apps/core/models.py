"""Core models — shared abstract base models."""
from django.db import models
from django.utils import timezone


class TimeStampedModel(models.Model):
    """Abstract base model with created_at and updated_at timestamps."""
    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class ActiveManager(models.Manager):
    """Default manager that excludes soft-deleted records."""

    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)


class AllObjectsManager(models.Manager):
    """Manager that returns ALL records, including soft-deleted ones."""

    def get_queryset(self):
        return super().get_queryset()


class SoftDeleteModel(models.Model):
    """
    Abstract base model with soft deletion support.

    Subclasses automatically get two managers:
      - objects     → excludes soft-deleted records (default)
      - all_objects → includes soft-deleted records
    """
    is_deleted = models.BooleanField(default=False, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    objects = ActiveManager()
    all_objects = AllObjectsManager()

    class Meta:
        abstract = True

    def soft_delete(self, user=None):
        """Mark this record as deleted without removing it from the database."""
        self.is_deleted = True
        self.deleted_at = timezone.now()
        if user is not None:
            self.deleted_by = user
        self.save(update_fields=["is_deleted", "deleted_at", "deleted_by"])

    def restore(self):
        """Undo a soft deletion."""
        self.is_deleted = False
        self.deleted_at = None
        self.deleted_by = None
        self.save(update_fields=["is_deleted", "deleted_at", "deleted_by"])

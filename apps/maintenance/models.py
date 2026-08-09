"""
MaintenanceHub — Preventive Maintenance Models
Tracks scheduled maintenance schedules and work order records.
"""
from django.db import models
from apps.core.models import TimeStampedModel


class MaintenanceFrequency(models.TextChoices):
    DAILY = "daily", "Daily"
    WEEKLY = "weekly", "Weekly"
    MONTHLY = "monthly", "Monthly"
    QUARTERLY = "quarterly", "Quarterly"
    BIANNUAL = "biannual", "Bi-Annual"
    ANNUAL = "annual", "Annual"
    CUSTOM = "custom", "Custom (days)"


class MaintenanceStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    PAUSED = "paused", "Paused"
    COMPLETED = "completed", "Completed"
    OVERDUE = "overdue", "Overdue"


class PreventiveMaintenance(TimeStampedModel):
    """
    A scheduled preventive maintenance plan for an asset or location.
    """
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="preventive_maintenance_schedules",
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    asset = models.ForeignKey(
        "assets.Asset",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="maintenance_schedules",
    )
    location = models.ForeignKey(
        "organizations.Location",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="maintenance_schedules",
    )
    assigned_team = models.ForeignKey(
        "organizations.Team",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="maintenance_schedules",
    )
    frequency = models.CharField(
        max_length=20, choices=MaintenanceFrequency.choices,
        default=MaintenanceFrequency.MONTHLY,
    )
    interval_days = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="Used when frequency=custom",
    )
    last_done_at = models.DateTimeField(null=True, blank=True)
    next_due_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=20, choices=MaintenanceStatus.choices,
        default=MaintenanceStatus.ACTIVE,
    )
    estimated_duration_hours = models.DecimalField(
        max_digits=5, decimal_places=1, null=True, blank=True,
    )
    checklist = models.TextField(
        blank=True,
        help_text="Line-separated checklist items",
    )
    created_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_schedules",
    )

    class Meta:
        db_table = "maintenance_schedule"
        ordering = ["next_due_at"]

    def __str__(self):
        return f"{self.title} ({self.get_frequency_display()})"

    @property
    def checklist_items(self):
        """Return checklist as a list of strings."""
        if not self.checklist:
            return []
        return [item.strip() for item in self.checklist.splitlines() if item.strip()]

"""
MaintenanceHub — Asset Management Models
"""
from django.db import models
from apps.core.models import TimeStampedModel


class AssetStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    UNDER_MAINTENANCE = "under_maintenance", "Under Maintenance"
    RETIRED = "retired", "Retired"
    DISPOSED = "disposed", "Disposed"


class Asset(TimeStampedModel):
    """
    Physical asset that can be associated with a maintenance ticket.
    e.g. AC unit, Generator, Fire extinguisher, Elevator.
    """
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="assets",
    )
    asset_code = models.CharField(max_length=50, db_index=True)
    name = models.CharField(max_length=200)
    asset_type = models.CharField(max_length=100)
    brand = models.CharField(max_length=100, blank=True)
    model_number = models.CharField(max_length=100, blank=True)
    serial_number = models.CharField(max_length=100, blank=True)
    location = models.ForeignKey(
        "organizations.Location",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assets",
    )
    status = models.CharField(max_length=20, choices=AssetStatus.choices, default=AssetStatus.ACTIVE)
    purchase_date = models.DateField(null=True, blank=True)
    warranty_expiry = models.DateField(null=True, blank=True)
    last_maintenance_date = models.DateField(null=True, blank=True)
    next_maintenance_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "assets_asset"
        unique_together = [["organization", "asset_code"]]
        ordering = ["name"]

    def __str__(self):
        return f"{self.asset_code} — {self.name}"


class MaintenanceSchedule(TimeStampedModel):
    """Preventive maintenance schedule for an asset or category."""
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="maintenance_schedules",
    )
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE, null=True, blank=True, related_name="schedules")
    category = models.ForeignKey(
        "tickets.Category", on_delete=models.SET_NULL, null=True, blank=True, related_name="schedules"
    )
    assigned_team = models.ForeignKey(
        "organizations.Team", on_delete=models.SET_NULL, null=True, blank=True
    )
    frequency_days = models.PositiveIntegerField(help_text="Repeat every N days")
    last_run = models.DateTimeField(null=True, blank=True)
    next_run = models.DateTimeField(null=True, blank=True, db_index=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "assets_maintenance_schedule"

    def __str__(self):
        return self.name

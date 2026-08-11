"""Admin registrations for the assets app."""
from django.contrib import admin
from .models import Asset, MaintenanceSchedule


@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    list_display = ["asset_code", "name", "asset_type", "status", "organization", "location", "next_maintenance_date"]
    list_filter = ["status", "asset_type", "organization"]
    search_fields = ["asset_code", "name", "serial_number", "brand"]
    autocomplete_fields = ["organization", "location"]
    readonly_fields = ["created_at", "updated_at"]
    fieldsets = (
        ("Identity", {
            "fields": ("organization", "asset_code", "name", "asset_type", "brand", "model_number", "serial_number"),
        }),
        ("Location & Status", {
            "fields": ("location", "status"),
        }),
        ("Maintenance Dates", {
            "fields": ("purchase_date", "warranty_expiry", "last_maintenance_date", "next_maintenance_date"),
        }),
        ("Notes", {
            "fields": ("notes",),
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )


@admin.register(MaintenanceSchedule)
class MaintenanceScheduleAdmin(admin.ModelAdmin):
    list_display = ["name", "organization", "frequency_days", "next_run", "is_active"]
    list_filter = ["is_active", "organization"]
    search_fields = ["name", "description"]
    readonly_fields = ["created_at", "updated_at"]

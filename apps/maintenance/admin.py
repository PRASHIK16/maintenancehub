"""Admin registrations for the maintenance app."""
from django.contrib import admin
from .models import PreventiveMaintenance


@admin.register(PreventiveMaintenance)
class PreventiveMaintenanceAdmin(admin.ModelAdmin):
    list_display = ["title", "organization", "frequency", "status", "next_due_at", "assigned_team"]
    list_filter = ["status", "frequency", "organization"]
    search_fields = ["title", "description"]
    autocomplete_fields = ["organization", "asset", "location", "assigned_team", "created_by"]
    readonly_fields = ["created_at", "updated_at"]
    fieldsets = (
        ("Basic Info", {
            "fields": ("organization", "title", "description", "created_by"),
        }),
        ("Schedule", {
            "fields": ("frequency", "interval_days", "last_done_at", "next_due_at", "status"),
        }),
        ("Assignment", {
            "fields": ("asset", "location", "assigned_team"),
        }),
        ("Details", {
            "fields": ("estimated_duration_hours", "checklist"),
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )

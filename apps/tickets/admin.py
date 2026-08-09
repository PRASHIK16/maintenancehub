"""Admin registrations for the tickets app."""
from django.contrib import admin
from .models import (
    Category, SLARule, Ticket, TicketStatusHistory,
    TicketComment, TicketAttachment, TicketActivity,
)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "organization", "parent", "is_active", "created_at"]
    list_filter = ["organization", "is_active"]
    search_fields = ["name"]
    ordering = ["organization", "name"]


@admin.register(SLARule)
class SLARuleAdmin(admin.ModelAdmin):
    list_display = ["organization", "priority", "response_time_hours", "resolution_time_hours"]
    list_filter = ["organization", "priority"]


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = [
        "ticket_number", "title", "organization", "priority", "status",
        "assigned_to", "created_at", "sla_resolution_due",
    ]
    list_filter = ["organization", "priority", "status", "created_at"]
    search_fields = ["ticket_number", "title", "description", "created_by__full_name"]
    raw_id_fields = ["created_by", "assigned_to", "category", "location", "assigned_team"]
    readonly_fields = ["ticket_number", "created_at", "updated_at", "sla_response_due", "sla_resolution_due"]
    date_hierarchy = "created_at"
    ordering = ["-created_at"]

    fieldsets = [
        ("Ticket Info", {"fields": [
            "ticket_number", "organization", "created_by", "title", "description",
            "category", "location", "priority", "status",
        ]}),
        ("Assignment", {"fields": ["assigned_to", "assigned_team"]}),
        ("SLA", {"fields": ["sla_response_due", "sla_resolution_due", "sla_response_met", "sla_resolution_met"]}),
        ("Timeline", {"fields": [
            "first_response_at", "assigned_at", "work_started_at",
            "resolved_at", "closed_at", "verified_at",
        ], "classes": ["collapse"]}),
        ("Feedback", {"fields": ["rating", "rating_comment", "resolution_notes"]}),
        ("Contact", {"fields": ["contact_phone", "preferred_visit_time"]}),
        ("Timestamps", {"fields": ["created_at", "updated_at"], "classes": ["collapse"]}),
    ]


@admin.register(TicketComment)
class TicketCommentAdmin(admin.ModelAdmin):
    list_display = ["ticket", "author", "is_internal", "created_at"]
    list_filter = ["is_internal"]
    raw_id_fields = ["ticket", "author"]


@admin.register(TicketAttachment)
class TicketAttachmentAdmin(admin.ModelAdmin):
    list_display = ["original_filename", "ticket", "uploaded_by", "file_size", "created_at"]
    raw_id_fields = ["ticket", "uploaded_by"]


@admin.register(TicketActivity)
class TicketActivityAdmin(admin.ModelAdmin):
    list_display = ["ticket", "actor", "activity_type", "timestamp"]
    list_filter = ["activity_type"]
    raw_id_fields = ["ticket", "actor"]
    readonly_fields = ["timestamp"]


@admin.register(TicketStatusHistory)
class TicketStatusHistoryAdmin(admin.ModelAdmin):
    list_display = ["ticket", "from_status", "to_status", "changed_by", "timestamp"]
    raw_id_fields = ["ticket", "changed_by"]
    readonly_fields = ["timestamp"]

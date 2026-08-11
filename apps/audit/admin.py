"""Admin registrations for the audit log app."""
from django.contrib import admin
from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ["timestamp", "user", "action", "object_repr", "organization", "ip_address"]
    list_filter = ["action", "organization"]
    search_fields = ["user__email", "object_repr", "message", "ip_address"]
    readonly_fields = [
        "organization", "user", "action", "content_type", "object_id",
        "object_repr", "old_value", "new_value", "message",
        "ip_address", "user_agent", "timestamp",
    ]
    date_hierarchy = "timestamp"
    ordering = ["-timestamp"]

    def has_add_permission(self, request):
        return False  # Audit logs are immutable

    def has_change_permission(self, request, obj=None):
        return False  # Audit logs are immutable

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser  # Only superusers can purge

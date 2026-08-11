"""
MaintenanceHub — Audit Log Models
Immutable audit trail for all important actions.
"""
from django.db import models
from apps.core.models import TimeStampedModel


class AuditAction(models.TextChoices):
    CREATE = "create", "Created"
    UPDATE = "update", "Updated"
    DELETE = "delete", "Deleted"
    STATUS_CHANGE = "status_change", "Status Changed"
    ASSIGN = "assign", "Assigned"
    UNASSIGN = "unassign", "Unassigned"
    LOGIN = "login", "Logged In"
    LOGOUT = "logout", "Logged Out"
    PERMISSION_CHANGE = "permission_change", "Permission Changed"
    PRIORITY_CHANGE = "priority_change", "Priority Changed"
    COMMENT_ADD = "comment_add", "Comment Added"
    ATTACHMENT_ADD = "attachment_add", "Attachment Added"
    ATTACHMENT_DELETE = "attachment_delete", "Attachment Deleted"
    REOPEN = "reopen", "Reopened"
    CLOSE = "close", "Closed"
    VERIFY = "verify", "Verified"
    BULK_ACTION = "bulk_action", "Bulk Action"


class AuditLog(models.Model):
    """
    Immutable audit log entry. Never updated, never deleted.
    Records who did what to which object, when, and from where.
    """
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
        db_index=True,
    )
    user = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
    )
    action = models.CharField(max_length=30, choices=AuditAction.choices, db_index=True)

    # Generic FK to any model
    content_type = models.ForeignKey(
        "contenttypes.ContentType",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    object_id = models.PositiveBigIntegerField(null=True, blank=True, db_index=True)
    object_repr = models.CharField(max_length=500, blank=True)

    # Change details
    old_value = models.JSONField(null=True, blank=True)
    new_value = models.JSONField(null=True, blank=True)
    message = models.TextField(blank=True)

    # Request metadata
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=500, blank=True)

    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "audit_log"
        verbose_name = "Audit Log"
        verbose_name_plural = "Audit Logs"
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["organization", "timestamp"]),
            models.Index(fields=["user", "timestamp"]),
            models.Index(fields=["content_type", "object_id"]),
        ]

    def __str__(self):
        return f"{self.user} {self.action} {self.object_repr} at {self.timestamp}"

    @classmethod
    def log(cls, request, action, obj=None, message="", old_value=None, new_value=None):
        """Convenience method to create an audit log entry."""
        from django.contrib.contenttypes.models import ContentType

        user = request.user if request and hasattr(request, "user") and request.user.is_authenticated else None
        org = getattr(request, "org", None) if request else None
        ip = getattr(request, "audit_ip", None) if request else None
        ua = getattr(request, "audit_user_agent", "") if request else ""

        ct = None
        obj_id = None
        obj_repr = ""
        if obj is not None:
            ct = ContentType.objects.get_for_model(obj)
            obj_id = obj.pk
            obj_repr = str(obj)[:500]

        return cls.objects.create(
            organization=org,
            user=user,
            action=action,
            content_type=ct,
            object_id=obj_id,
            object_repr=obj_repr,
            old_value=old_value,
            new_value=new_value,
            message=message,
            ip_address=ip,
            user_agent=ua,
        )

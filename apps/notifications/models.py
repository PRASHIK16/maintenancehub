"""
MaintenanceHub — Notification Models
"""
from django.db import models
from apps.core.models import TimeStampedModel


class NotificationType(models.TextChoices):
    TICKET_CREATED = "ticket_created", "Ticket Created"
    TICKET_ASSIGNED = "ticket_assigned", "Ticket Assigned"
    TICKET_REASSIGNED = "ticket_reassigned", "Ticket Reassigned"
    TICKET_STATUS_CHANGED = "ticket_status_changed", "Status Changed"
    TICKET_PRIORITY_CHANGED = "ticket_priority_changed", "Priority Changed"
    COMMENT_ADDED = "comment_added", "Comment Added"
    SLA_APPROACHING = "sla_approaching", "SLA Approaching"
    SLA_BREACHED = "sla_breached", "SLA Breached"
    RESOLUTION_SUBMITTED = "resolution_submitted", "Resolution Submitted"
    TICKET_REOPENED = "ticket_reopened", "Ticket Reopened"
    TICKET_CLOSED = "ticket_closed", "Ticket Closed"
    MAINTENANCE_SCHEDULED = "maintenance_scheduled", "Maintenance Scheduled"
    TICKET_RATED = "ticket_rated", "Ticket Rated"


class Notification(TimeStampedModel):
    """
    A notification for a specific user.
    """
    recipient = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="notifications",
        db_index=True,
    )
    notification_type = models.CharField(max_length=40, choices=NotificationType.choices, db_index=True)
    title = models.CharField(max_length=200)
    message = models.TextField()
    link = models.CharField(max_length=500, blank=True)
    is_read = models.BooleanField(default=False, db_index=True)
    read_at = models.DateTimeField(null=True, blank=True)

    # Related object (usually a ticket)
    ticket = models.ForeignKey(
        "tickets.Ticket",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notifications",
    )

    class Meta:
        db_table = "notifications_notification"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["recipient", "is_read"]),
            models.Index(fields=["recipient", "created_at"]),
        ]

    def __str__(self):
        return f"[{self.notification_type}] {self.title} → {self.recipient.display_name}"

    def mark_read(self):
        from django.utils import timezone
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=["is_read", "read_at"])

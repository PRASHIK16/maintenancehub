"""
MaintenanceHub — Ticket Domain Models
Core ticket system with full lifecycle management.
"""
import os
import uuid
from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from apps.core.models import TimeStampedModel


# ── Priority ──────────────────────────────────────────────────────────────────

class Priority(models.TextChoices):
    LOW = "low", "Low"
    MEDIUM = "medium", "Medium"
    HIGH = "high", "High"
    CRITICAL = "critical", "Critical"


# ── Status State Machine ───────────────────────────────────────────────────────

class TicketStatus(models.TextChoices):
    SUBMITTED = "submitted", "Submitted"
    TRIAGED = "triaged", "Triaged"
    ASSIGNED = "assigned", "Assigned"
    IN_PROGRESS = "in_progress", "In Progress"
    ON_HOLD = "on_hold", "On Hold"
    RESOLVED = "resolved", "Resolved"
    VERIFICATION_PENDING = "verification_pending", "Verification Pending"
    CLOSED = "closed", "Closed"
    REOPENED = "reopened", "Reopened"
    CANCELLED = "cancelled", "Cancelled"


# Valid transitions: from_status → set of allowed to_statuses
VALID_TRANSITIONS = {
    TicketStatus.SUBMITTED: {
        TicketStatus.TRIAGED,
        TicketStatus.ASSIGNED,
        TicketStatus.CANCELLED,
    },
    TicketStatus.TRIAGED: {
        TicketStatus.ASSIGNED,
        TicketStatus.CANCELLED,
        TicketStatus.ON_HOLD,
    },
    TicketStatus.ASSIGNED: {
        TicketStatus.IN_PROGRESS,
        TicketStatus.ON_HOLD,
        TicketStatus.CANCELLED,
        TicketStatus.TRIAGED,
    },
    TicketStatus.IN_PROGRESS: {
        TicketStatus.RESOLVED,
        TicketStatus.VERIFICATION_PENDING,
        TicketStatus.ON_HOLD,
        TicketStatus.ASSIGNED,
    },
    TicketStatus.ON_HOLD: {
        TicketStatus.ASSIGNED,
        TicketStatus.IN_PROGRESS,
        TicketStatus.CANCELLED,
    },
    TicketStatus.RESOLVED: {
        TicketStatus.VERIFICATION_PENDING,
        TicketStatus.CLOSED,
        TicketStatus.REOPENED,
    },
    TicketStatus.VERIFICATION_PENDING: {
        TicketStatus.CLOSED,
        TicketStatus.REOPENED,
    },
    TicketStatus.CLOSED: {
        TicketStatus.REOPENED,
    },
    TicketStatus.REOPENED: {
        TicketStatus.TRIAGED,
        TicketStatus.ASSIGNED,
        TicketStatus.IN_PROGRESS,
        TicketStatus.CANCELLED,
    },
    TicketStatus.CANCELLED: set(),  # Terminal state
}


# ── Category ──────────────────────────────────────────────────────────────────

class Category(TimeStampedModel):
    """
    Ticket category (e.g. Electrical, Plumbing, HVAC, IT).
    Scoped to an organization. Can have subcategories.
    """
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="categories",
    )
    parent = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="subcategories",
    )
    name = models.CharField(max_length=100)
    icon = models.CharField(max_length=50, blank=True, help_text="Heroicon name e.g. bolt, wrench")
    color = models.CharField(max_length=7, default="#6366f1")
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    # Auto-assign team
    default_team = models.ForeignKey(
        "organizations.Team",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="default_categories",
    )

    class Meta:
        db_table = "tickets_category"
        ordering = ["sort_order", "name"]
        unique_together = [["organization", "parent", "name"]]
        verbose_name = "Category"
        verbose_name_plural = "Categories"

    def __str__(self):
        return f"{self.parent.name} / {self.name}" if self.parent else self.name


# ── SLA Rule ──────────────────────────────────────────────────────────────────

class SLARule(TimeStampedModel):
    """
    SLA configuration per organization per priority.
    """
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="sla_rules",
    )
    priority = models.CharField(max_length=10, choices=Priority.choices)
    response_time_hours = models.PositiveIntegerField(default=2)  # First response
    resolution_time_hours = models.PositiveIntegerField(default=24)  # Full resolution
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "tickets_sla_rule"
        unique_together = [["organization", "priority"]]
        verbose_name = "SLA Rule"

    def __str__(self):
        return f"{self.organization.name} — {self.priority}: {self.resolution_time_hours}h"


# ── Ticket ────────────────────────────────────────────────────────────────────

class Ticket(TimeStampedModel):
    """
    Core ticket model — the central entity of MaintenanceHub.
    """
    # Human-readable ID
    ticket_number = models.CharField(max_length=20, unique=True, db_index=True)

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="tickets",
        db_index=True,
    )

    # Requester
    created_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_tickets",
    )

    # Content
    title = models.CharField(max_length=300, db_index=True)
    description = models.TextField()
    preferred_visit_time = models.CharField(max_length=200, blank=True)
    contact_phone = models.CharField(max_length=20, blank=True)

    # Classification
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tickets",
    )
    subcategory = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sub_tickets",
    )
    location = models.ForeignKey(
        "organizations.Location",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tickets",
    )
    asset = models.ForeignKey(
        "assets.Asset",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tickets",
    )

    # Priority & Status
    priority = models.CharField(
        max_length=10,
        choices=Priority.choices,
        default=Priority.MEDIUM,
        db_index=True,
    )
    status = models.CharField(
        max_length=25,
        choices=TicketStatus.choices,
        default=TicketStatus.SUBMITTED,
        db_index=True,
    )

    # Assignment
    assigned_to = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_tickets",
    )
    assigned_team = models.ForeignKey(
        "organizations.Team",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="team_tickets",
    )

    # SLA tracking
    sla_response_due = models.DateTimeField(null=True, blank=True)
    sla_resolution_due = models.DateTimeField(null=True, blank=True)
    sla_response_met = models.BooleanField(null=True, blank=True)
    sla_resolution_met = models.BooleanField(null=True, blank=True)

    # Timeline milestones
    first_response_at = models.DateTimeField(null=True, blank=True)
    assigned_at = models.DateTimeField(null=True, blank=True)
    work_started_at = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)

    # Resolution
    resolution_notes = models.TextField(blank=True)
    rating = models.PositiveSmallIntegerField(null=True, blank=True)  # 1–5
    rating_comment = models.TextField(blank=True)

    # Recurrence tracking
    recurrence_count = models.PositiveIntegerField(default=0)
    is_recurring_flagged = models.BooleanField(default=False)

    # AI classification
    ai_suggested_category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ai_suggested_tickets",
    )
    ai_suggested_priority = models.CharField(max_length=10, choices=Priority.choices, blank=True)
    ai_confidence = models.FloatField(null=True, blank=True)

    class Meta:
        db_table = "tickets_ticket"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["organization", "status"]),
            models.Index(fields=["organization", "priority"]),
            models.Index(fields=["organization", "created_at"]),
            models.Index(fields=["assigned_to", "status"]),
            models.Index(fields=["status", "sla_resolution_due"]),
        ]
        verbose_name = "Ticket"
        verbose_name_plural = "Tickets"

    def __str__(self):
        return f"{self.ticket_number}: {self.title}"

    def save(self, *args, **kwargs):
        if not self.ticket_number:
            self.ticket_number = self._generate_ticket_number()
        super().save(*args, **kwargs)

    def _generate_ticket_number(self):
        """Generate a unique ticket number like MH-10482."""
        import random
        while True:
            number = f"MH-{random.randint(10000, 99999)}"
            if not Ticket.objects.filter(ticket_number=number).exists():
                return number

    def transition_to(self, new_status, user=None, note=""):
        """
        Controlled status transition with validation.
        Raises ValidationError if the transition is not allowed.
        """
        current = self.status
        allowed = VALID_TRANSITIONS.get(current, set())
        if new_status not in allowed:
            raise ValidationError(
                f"Cannot transition from '{current}' to '{new_status}'. "
                f"Allowed: {', '.join(allowed) or 'none'}"
            )

        old_status = self.status
        self.status = new_status
        now = timezone.now()

        # Update milestone timestamps
        if new_status == TicketStatus.ASSIGNED and not self.assigned_at:
            self.assigned_at = now
        elif new_status == TicketStatus.IN_PROGRESS and not self.work_started_at:
            self.work_started_at = now
        elif new_status in (TicketStatus.RESOLVED, TicketStatus.VERIFICATION_PENDING):
            self.resolved_at = now
        elif new_status == TicketStatus.CLOSED:
            self.closed_at = now
        elif new_status == TicketStatus.VERIFICATION_PENDING:
            pass  # handled by resolved_at above

        self.save()

        # Record in history
        TicketStatusHistory.objects.create(
            ticket=self,
            from_status=old_status,
            to_status=new_status,
            changed_by=user,
            note=note,
        )

        return self

    @property
    def sla_status(self):
        """Return SLA status string: on_track, at_risk, breached."""
        if not self.sla_resolution_due:
            return "none"
        now = timezone.now()
        if self.status in (TicketStatus.CLOSED, TicketStatus.CANCELLED):
            return "closed"
        if now > self.sla_resolution_due:
            return "breached"
        remaining = (self.sla_resolution_due - now).total_seconds()
        warning_threshold = 4 * 3600  # 4 hours warning
        if remaining < warning_threshold:
            return "at_risk"
        return "on_track"

    @property
    def age_hours(self):
        """How many hours since the ticket was created."""
        return (timezone.now() - self.created_at).total_seconds() / 3600

    @property
    def is_overdue(self):
        return self.sla_status == "breached"

    @property
    def priority_badge_class(self):
        classes = {
            Priority.LOW: "badge-priority-low",
            Priority.MEDIUM: "badge-priority-medium",
            Priority.HIGH: "badge-priority-high",
            Priority.CRITICAL: "badge-priority-critical",
        }
        return classes.get(self.priority, "")

    @property
    def status_badge_class(self):
        classes = {
            TicketStatus.SUBMITTED: "badge-status-submitted",
            TicketStatus.TRIAGED: "badge-status-triaged",
            TicketStatus.ASSIGNED: "badge-status-assigned",
            TicketStatus.IN_PROGRESS: "badge-status-in-progress",
            TicketStatus.ON_HOLD: "badge-status-on-hold",
            TicketStatus.RESOLVED: "badge-status-resolved",
            TicketStatus.VERIFICATION_PENDING: "badge-status-verification",
            TicketStatus.CLOSED: "badge-status-closed",
            TicketStatus.REOPENED: "badge-status-reopened",
            TicketStatus.CANCELLED: "badge-status-cancelled",
        }
        return classes.get(self.status, "")


# ── Status History ─────────────────────────────────────────────────────────────

class TicketStatusHistory(models.Model):
    """Immutable record of every status transition."""
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="status_history")
    from_status = models.CharField(max_length=25, choices=TicketStatus.choices)
    to_status = models.CharField(max_length=25, choices=TicketStatus.choices)
    changed_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    note = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "tickets_status_history"
        ordering = ["timestamp"]

    def __str__(self):
        return f"{self.ticket.ticket_number}: {self.from_status} → {self.to_status}"


# ── Comment ───────────────────────────────────────────────────────────────────

class TicketComment(TimeStampedModel):
    """
    Comment on a ticket.
    Can be public (visible to user) or internal (staff/managers only).
    """
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, related_name="ticket_comments")
    body = models.TextField()
    is_internal = models.BooleanField(default=False, db_index=True)
    is_edited = models.BooleanField(default=False)
    edited_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "tickets_comment"
        ordering = ["created_at"]

    def __str__(self):
        kind = "Internal" if self.is_internal else "Public"
        return f"[{kind}] {self.author} on {self.ticket.ticket_number}"


# ── Attachment ────────────────────────────────────────────────────────────────

def attachment_upload_path(instance, filename):
    """Generate secure upload path with UUID."""
    ext = filename.rsplit(".", 1)[-1].lower()
    safe_name = f"{uuid.uuid4().hex}.{ext}"
    return f"attachments/{instance.ticket.organization_id}/{instance.ticket.ticket_number}/{safe_name}"


class TicketAttachment(TimeStampedModel):
    """
    File attachment on a ticket.
    Access is controlled — files are not directly accessible via URL without auth.
    """
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="attachments")
    uploaded_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        related_name="uploaded_attachments",
    )
    file = models.FileField(upload_to=attachment_upload_path)
    original_filename = models.CharField(max_length=255)
    file_size = models.PositiveBigIntegerField()
    content_type = models.CharField(max_length=100)
    is_evidence = models.BooleanField(default=False, help_text="Evidence uploaded by maintenance staff")

    class Meta:
        db_table = "tickets_attachment"
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.original_filename} on {self.ticket.ticket_number}"

    @property
    def file_size_display(self):
        if self.file_size < 1024:
            return f"{self.file_size} B"
        elif self.file_size < 1024 * 1024:
            return f"{self.file_size / 1024:.1f} KB"
        return f"{self.file_size / (1024 * 1024):.1f} MB"

    @property
    def is_image(self):
        return self.content_type.startswith("image/")

    @property
    def extension(self):
        return self.original_filename.rsplit(".", 1)[-1].lower() if "." in self.original_filename else ""


# ── Activity Log (Timeline) ───────────────────────────────────────────────────

class ActivityType(models.TextChoices):
    TICKET_CREATED = "ticket_created", "Ticket Created"
    STATUS_CHANGED = "status_changed", "Status Changed"
    ASSIGNED = "assigned", "Assigned"
    REASSIGNED = "reassigned", "Reassigned"
    PRIORITY_CHANGED = "priority_changed", "Priority Changed"
    COMMENT_ADDED = "comment_added", "Comment Added"
    INTERNAL_NOTE = "internal_note", "Internal Note Added"
    ATTACHMENT_ADDED = "attachment_added", "Attachment Added"
    SLA_BREACHED = "sla_breached", "SLA Breached"
    REOPENED = "reopened", "Reopened"
    RESOLVED = "resolved", "Marked Resolved"
    VERIFIED = "verified", "Resolution Verified"
    CLOSED = "closed", "Closed"
    RATED = "rated", "Service Rated"


class TicketActivity(models.Model):
    """
    Immutable activity timeline entry for a ticket.
    Every meaningful action creates one of these.
    """
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="activities", db_index=True)
    actor = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ticket_activities",
    )
    activity_type = models.CharField(max_length=30, choices=ActivityType.choices)
    description = models.TextField()
    metadata = models.JSONField(default=dict, blank=True)
    is_internal = models.BooleanField(default=False)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "tickets_activity"
        ordering = ["timestamp"]

    def __str__(self):
        return f"{self.activity_type} on {self.ticket.ticket_number} at {self.timestamp}"

    @classmethod
    def create(cls, ticket, actor, activity_type, description, metadata=None, is_internal=False):
        return cls.objects.create(
            ticket=ticket,
            actor=actor,
            activity_type=activity_type,
            description=description,
            metadata=metadata or {},
            is_internal=is_internal,
        )

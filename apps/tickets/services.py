"""
MaintenanceHub — Ticket Domain Services
Business logic layer. Keeps views thin.
"""
from django.utils import timezone
from django.conf import settings

from .models import Ticket, TicketActivity, ActivityType, TicketAttachment, SLARule


class TicketService:
    """Service class for ticket business logic."""

    @staticmethod
    def create_ticket(form, user, organization, files=None):
        """
        Create a ticket from a validated form.
        Sets up SLA deadlines, creates the initial activity log entry,
        and handles file attachments.
        """
        ticket = form.save(commit=False)
        ticket.organization = organization
        ticket.created_by = user
        ticket.save()

        # Set SLA deadlines
        TicketService.apply_sla(ticket, organization)

        # Initial activity
        TicketActivity.create(
            ticket=ticket,
            actor=user,
            activity_type=ActivityType.TICKET_CREATED,
            description=f"Ticket {ticket.ticket_number} created by {user.display_name}",
        )

        # Auto-assign based on category default team
        if ticket.category and ticket.category.default_team:
            team = ticket.category.default_team
            ticket.assigned_team = team
            ticket.save(update_fields=["assigned_team"])

        # Handle attachments
        if files:
            for f in files:
                if f.size <= settings.MAX_UPLOAD_SIZE:
                    TicketAttachment.objects.create(
                        ticket=ticket,
                        uploaded_by=user,
                        file=f,
                        original_filename=f.name,
                        file_size=f.size,
                        content_type=f.content_type,
                    )

        # Notify admins/managers
        from apps.notifications.tasks import notify_ticket_created
        notify_ticket_created.delay(ticket.pk)

        return ticket

    @staticmethod
    def apply_sla(ticket, organization):
        """Calculate and set SLA deadlines based on priority."""
        try:
            sla_rule = SLARule.objects.get(
                organization=organization,
                priority=ticket.priority,
                is_active=True,
            )
            response_hours = sla_rule.response_time_hours
            resolution_hours = sla_rule.resolution_time_hours
        except SLARule.DoesNotExist:
            # Fallback to global defaults
            defaults = settings.SLA_DEFAULTS
            response_hours = 2
            resolution_hours = defaults.get(ticket.priority.upper(), 24)

        now = ticket.created_at or timezone.now()
        ticket.sla_response_due = now + timezone.timedelta(hours=response_hours)
        ticket.sla_resolution_due = now + timezone.timedelta(hours=resolution_hours)
        ticket.save(update_fields=["sla_response_due", "sla_resolution_due"])

    @staticmethod
    def get_recurring_issues(organization, ticket):
        """
        Check if this ticket is part of a recurring pattern.
        Returns count of similar recent tickets.
        """
        if not ticket.location or not ticket.category:
            return 0

        from django.utils import timezone
        thirty_days_ago = timezone.now() - timezone.timedelta(days=30)

        count = Ticket.objects.filter(
            organization=organization,
            location=ticket.location,
            category=ticket.category,
            created_at__gte=thirty_days_ago,
        ).exclude(pk=ticket.pk).count()

        return count

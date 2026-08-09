"""
MaintenanceHub — Celery Notification Tasks
All notification processing is asynchronous.
"""
from celery import shared_task
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def notify_ticket_created(self, ticket_id):
    """Notify org admins and managers when a new ticket is created."""
    try:
        from apps.tickets.models import Ticket
        from apps.accounts.models import User, UserRole
        from .models import Notification, NotificationType

        ticket = Ticket.objects.select_related("organization", "created_by", "category").get(pk=ticket_id)
        org = ticket.organization

        # Notify managers and org admins
        recipients = User.objects.filter(
            organization=org,
            role__in=[UserRole.ORG_ADMIN, UserRole.MANAGER],
            is_active=True,
            email_notifications=True,
        )

        for user in recipients:
            Notification.objects.create(
                recipient=user,
                notification_type=NotificationType.TICKET_CREATED,
                title=f"New ticket: {ticket.ticket_number}",
                message=f"{ticket.created_by.display_name} reported: {ticket.title}",
                link=f"/dashboard/tickets/{ticket.pk}/",
                ticket=ticket,
            )

        logger.info(f"Ticket created notifications sent for {ticket.ticket_number}")

    except Exception as exc:
        logger.error(f"notify_ticket_created failed: {exc}")
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def notify_ticket_assigned(self, ticket_id, assignee_id, assigner_id):
    """Notify the assignee when a ticket is assigned to them."""
    try:
        from apps.tickets.models import Ticket
        from apps.accounts.models import User
        from .models import Notification, NotificationType

        ticket = Ticket.objects.get(pk=ticket_id)
        assignee = User.objects.get(pk=assignee_id)
        assigner = User.objects.get(pk=assigner_id)

        Notification.objects.create(
            recipient=assignee,
            notification_type=NotificationType.TICKET_ASSIGNED,
            title=f"Ticket assigned: {ticket.ticket_number}",
            message=f"{assigner.display_name} assigned you ticket '{ticket.title}'",
            link=f"/dashboard/tickets/{ticket.pk}/",
            ticket=ticket,
        )

        # Also notify the requester
        if ticket.created_by and ticket.created_by != assignee:
            Notification.objects.create(
                recipient=ticket.created_by,
                notification_type=NotificationType.TICKET_ASSIGNED,
                title=f"Your ticket {ticket.ticket_number} has been assigned",
                message=f"Assigned to {assignee.display_name}",
                link=f"/dashboard/tickets/{ticket.pk}/",
                ticket=ticket,
            )

    except Exception as exc:
        logger.error(f"notify_ticket_assigned failed: {exc}")
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def notify_ticket_status_change(self, ticket_id, new_status, actor_id):
    """Notify relevant parties when ticket status changes."""
    try:
        from apps.tickets.models import Ticket, TicketStatus
        from apps.accounts.models import User
        from .models import Notification, NotificationType

        ticket = Ticket.objects.get(pk=ticket_id)
        actor = User.objects.get(pk=actor_id)
        status_labels = dict(TicketStatus.choices)

        recipients = set()
        if ticket.created_by and ticket.created_by != actor:
            recipients.add(ticket.created_by)
        if ticket.assigned_to and ticket.assigned_to != actor:
            recipients.add(ticket.assigned_to)

        for recipient in recipients:
            Notification.objects.create(
                recipient=recipient,
                notification_type=NotificationType.TICKET_STATUS_CHANGED,
                title=f"Ticket {ticket.ticket_number} status updated",
                message=f"Status changed to {status_labels.get(new_status, new_status)} by {actor.display_name}",
                link=f"/dashboard/tickets/{ticket.pk}/",
                ticket=ticket,
            )

    except Exception as exc:
        logger.error(f"notify_ticket_status_change failed: {exc}")
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def notify_comment_added(self, ticket_id, comment_id, author_id):
    """Notify ticket stakeholders when a comment is added."""
    try:
        from apps.tickets.models import Ticket, TicketComment
        from apps.accounts.models import User
        from .models import Notification, NotificationType

        ticket = Ticket.objects.get(pk=ticket_id)
        comment = TicketComment.objects.get(pk=comment_id)
        author = User.objects.get(pk=author_id)

        if comment.is_internal:
            return  # Internal notes don't notify requester

        recipients = set()
        if ticket.created_by and ticket.created_by != author:
            recipients.add(ticket.created_by)
        if ticket.assigned_to and ticket.assigned_to != author:
            recipients.add(ticket.assigned_to)

        for recipient in recipients:
            Notification.objects.create(
                recipient=recipient,
                notification_type=NotificationType.COMMENT_ADDED,
                title=f"New comment on {ticket.ticket_number}",
                message=f"{author.display_name}: {comment.body[:100]}",
                link=f"/dashboard/tickets/{ticket.pk}/",
                ticket=ticket,
            )

    except Exception as exc:
        logger.error(f"notify_comment_added failed: {exc}")
        raise self.retry(exc=exc)


@shared_task
def check_sla_breaches():
    """Periodic task: detect SLA breaches and send alerts."""
    from django.utils import timezone
    from apps.tickets.models import Ticket, TicketStatus
    from .models import Notification, NotificationType
    from apps.accounts.models import User, UserRole

    now = timezone.now()
    overdue = Ticket.objects.filter(
        sla_resolution_due__lt=now,
        sla_resolution_met__isnull=True,
        status__in=[
            TicketStatus.SUBMITTED, TicketStatus.TRIAGED,
            TicketStatus.ASSIGNED, TicketStatus.IN_PROGRESS
        ],
    ).select_related("organization", "assigned_to")

    for ticket in overdue:
        ticket.sla_resolution_met = False
        ticket.save(update_fields=["sla_resolution_met"])

        # Alert managers
        managers = User.objects.filter(
            organization=ticket.organization,
            role__in=[UserRole.ORG_ADMIN, UserRole.MANAGER],
        )
        for manager in managers:
            if not Notification.objects.filter(
                ticket=ticket,
                notification_type=NotificationType.SLA_BREACHED,
                created_at__gte=now - timezone.timedelta(hours=4),
            ).exists():
                Notification.objects.create(
                    recipient=manager,
                    notification_type=NotificationType.SLA_BREACHED,
                    title=f"SLA Breached: {ticket.ticket_number}",
                    message=f"Ticket '{ticket.title}' has exceeded its resolution deadline.",
                    link=f"/dashboard/tickets/{ticket.pk}/",
                    ticket=ticket,
                )

    logger.info(f"SLA check complete. {overdue.count()} tickets breached.")

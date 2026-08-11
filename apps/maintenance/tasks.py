"""
MaintenanceHub — Maintenance Celery Tasks
Periodic tasks for preventive maintenance automation.
"""
from celery import shared_task
import logging

logger = logging.getLogger(__name__)


@shared_task
def create_overdue_maintenance_tickets():
    """
    Periodic task: find all due/overdue PreventiveMaintenance schedules
    and auto-create maintenance tickets for them.
    Runs daily via CELERY_BEAT_SCHEDULE.
    """
    from django.utils import timezone
    from .models import PreventiveMaintenance, MaintenanceStatus
    from apps.tickets.models import Ticket, TicketPriority, TicketStatus

    now = timezone.now()
    due_schedules = PreventiveMaintenance.objects.filter(
        status=MaintenanceStatus.ACTIVE,
        next_due_at__lte=now,
    ).select_related("organization", "asset", "location", "assigned_team", "created_by")

    created_count = 0
    for schedule in due_schedules:
        # Don't create duplicate tickets (check if an open ticket already exists for this schedule)
        existing = Ticket.objects.filter(
            organization=schedule.organization,
            title__startswith=f"[PM] {schedule.title}",
            status__in=[
                TicketStatus.SUBMITTED, TicketStatus.TRIAGED,
                TicketStatus.ASSIGNED, TicketStatus.IN_PROGRESS,
            ],
        ).exists()

        if existing:
            continue

        # Find a system user (org admin) to be the creator
        from apps.accounts.models import User, UserRole
        system_user = User.objects.filter(
            organization=schedule.organization,
            role__in=[UserRole.ORG_ADMIN, UserRole.SUPER_ADMIN],
            is_active=True,
        ).first()

        if not system_user:
            logger.warning(f"No admin user found for org {schedule.organization}; skipping PM ticket creation.")
            continue

        description = f"Preventive maintenance required:\n{schedule.description}\n\n"
        if schedule.checklist_items:
            description += "Checklist:\n"
            for item in schedule.checklist_items:
                description += f"• {item}\n"

        try:
            # Find a suitable category for preventive maintenance
            from apps.tickets.models import Category
            pm_category = Category.objects.filter(
                organization=schedule.organization,
                name__icontains="maintenance",
            ).first()

            ticket = Ticket.objects.create(
                organization=schedule.organization,
                ticket_number=Ticket.generate_ticket_number(schedule.organization),
                title=f"[PM] {schedule.title}",
                description=description.strip(),
                priority=TicketPriority.MEDIUM,
                status=TicketStatus.SUBMITTED,
                created_by=system_user,
                location=schedule.location,
                category=pm_category,
                assigned_team=schedule.assigned_team,
            )

            # Update schedule
            schedule.last_done_at = now
            _set_next_due(schedule)
            schedule.save(update_fields=["last_done_at", "next_due_at"])

            created_count += 1
            logger.info(f"Auto-created PM ticket {ticket.ticket_number} for schedule '{schedule.title}'")

        except Exception as exc:
            logger.error(f"Failed to create PM ticket for schedule {schedule.pk}: {exc}")

    logger.info(f"Maintenance ticket creation complete: {created_count} tickets created.")
    return created_count


def _set_next_due(schedule):
    """Calculate and set the next_due_at based on frequency."""
    from django.utils import timezone
    from datetime import timedelta
    from .models import MaintenanceFrequency

    freq = schedule.frequency
    now = timezone.now()

    freq_map = {
        MaintenanceFrequency.DAILY: 1,
        MaintenanceFrequency.WEEKLY: 7,
        MaintenanceFrequency.MONTHLY: 30,
        MaintenanceFrequency.QUARTERLY: 90,
        MaintenanceFrequency.BIANNUAL: 180,
        MaintenanceFrequency.ANNUAL: 365,
    }

    if freq == MaintenanceFrequency.CUSTOM and schedule.interval_days:
        days = schedule.interval_days
    else:
        days = freq_map.get(freq, 30)

    schedule.next_due_at = now + timedelta(days=days)

"""
MaintenanceHub — Ticket Model Tests
Tests for the state machine, SLA logic, and service layer.
"""
from django.test import TestCase
from django.utils import timezone
from django.core.exceptions import ValidationError

from apps.accounts.models import User, UserRole
from apps.organizations.models import Organization
from apps.tickets.models import (
    Ticket, TicketStatus, TicketPriority, SLARule, Category, VALID_TRANSITIONS
)
from apps.tickets.services import TicketService


def make_org(name="Test Org"):
    """Helper: create a test organization."""
    return Organization.objects.create(name=name, slug=name.lower().replace(" ", "-"))


def make_user(org, email="test@example.com", role=UserRole.STAFF):
    """Helper: create a test user."""
    return User.objects.create_user(
        email=email,
        password="testpass123",
        organization=org,
        role=role,
        first_name="Test",
        last_name="User",
    )


def make_ticket(org, user, status=TicketStatus.SUBMITTED, priority=TicketPriority.MEDIUM, title="Test Ticket"):
    """Helper: create a test ticket."""
    return Ticket.objects.create(
        organization=org,
        title=title,
        description="Test description",
        priority=priority,
        status=status,
        created_by=user,
    )


class TicketNumberGenerationTest(TestCase):
    """Test that ticket numbers are auto-generated correctly."""

    def setUp(self):
        self.org = make_org()
        self.user = make_user(self.org)

    def test_ticket_number_is_generated_on_save(self):
        ticket = make_ticket(self.org, self.user)
        self.assertTrue(ticket.ticket_number.startswith("MH-"))
        self.assertEqual(len(ticket.ticket_number), 8)  # MH-XXXXX

    def test_ticket_numbers_are_unique(self):
        t1 = make_ticket(self.org, self.user, title="Ticket 1")
        t2 = make_ticket(self.org, self.user, title="Ticket 2")
        self.assertNotEqual(t1.ticket_number, t2.ticket_number)


class TicketStateMachineTest(TestCase):
    """Test the VALID_TRANSITIONS state machine via transition_to()."""

    def setUp(self):
        self.org = make_org()
        self.user = make_user(self.org)

    def test_submitted_can_transition_to_triaged(self):
        ticket = make_ticket(self.org, self.user, status=TicketStatus.SUBMITTED)
        ticket.transition_to(TicketStatus.TRIAGED, user=self.user)
        ticket.refresh_from_db()
        self.assertEqual(ticket.status, TicketStatus.TRIAGED)

    def test_submitted_can_transition_to_assigned(self):
        ticket = make_ticket(self.org, self.user, status=TicketStatus.SUBMITTED)
        ticket.transition_to(TicketStatus.ASSIGNED, user=self.user)
        ticket.refresh_from_db()
        self.assertEqual(ticket.status, TicketStatus.ASSIGNED)

    def test_in_progress_can_transition_to_resolved(self):
        ticket = make_ticket(self.org, self.user, status=TicketStatus.IN_PROGRESS)
        ticket.transition_to(TicketStatus.RESOLVED, user=self.user)
        ticket.refresh_from_db()
        self.assertEqual(ticket.status, TicketStatus.RESOLVED)

    def test_invalid_transition_raises_validation_error(self):
        ticket = make_ticket(self.org, self.user, status=TicketStatus.SUBMITTED)
        with self.assertRaises(ValidationError):
            ticket.transition_to(TicketStatus.RESOLVED, user=self.user)

    def test_closed_to_open_raises_validation_error(self):
        ticket = make_ticket(self.org, self.user, status=TicketStatus.CLOSED)
        with self.assertRaises(ValidationError):
            ticket.transition_to(TicketStatus.SUBMITTED, user=self.user)

    def test_reopened_transition_from_resolved(self):
        ticket = make_ticket(self.org, self.user, status=TicketStatus.RESOLVED)
        ticket.transition_to(TicketStatus.REOPENED, user=self.user)
        ticket.refresh_from_db()
        self.assertEqual(ticket.status, TicketStatus.REOPENED)

    def test_valid_transitions_coverage(self):
        """Ensure VALID_TRANSITIONS covers all non-terminal statuses."""
        non_terminal = [
            TicketStatus.SUBMITTED, TicketStatus.TRIAGED, TicketStatus.ASSIGNED,
            TicketStatus.IN_PROGRESS, TicketStatus.ON_HOLD, TicketStatus.RESOLVED,
            TicketStatus.VERIFICATION_PENDING,
        ]
        for status in non_terminal:
            self.assertIn(status, VALID_TRANSITIONS, f"{status} missing from VALID_TRANSITIONS")
            self.assertTrue(len(VALID_TRANSITIONS[status]) > 0, f"{status} has no allowed transitions")


class SLATest(TestCase):
    """Test SLA deadline calculation."""

    def setUp(self):
        self.org = make_org()
        self.user = make_user(self.org)

    def test_sla_deadlines_are_set_from_sla_rule(self):
        SLARule.objects.create(
            organization=self.org,
            priority=TicketPriority.HIGH,
            response_time_hours=1,
            resolution_time_hours=8,
        )
        ticket = make_ticket(self.org, self.user, priority=TicketPriority.HIGH)
        TicketService.apply_sla(ticket, self.org)
        ticket.refresh_from_db()
        self.assertIsNotNone(ticket.sla_response_due)
        self.assertIsNotNone(ticket.sla_resolution_due)
        # Resolution should be ~8 hours after creation
        delta = ticket.sla_resolution_due - ticket.sla_response_due
        self.assertAlmostEqual(delta.total_seconds() / 3600, 7, delta=0.1)

    def test_sla_falls_back_to_settings_defaults(self):
        """Without an SLARule the service uses SLA_DEFAULTS from settings."""
        ticket = make_ticket(self.org, self.user, priority=TicketPriority.MEDIUM)
        TicketService.apply_sla(ticket, self.org)
        ticket.refresh_from_db()
        self.assertIsNotNone(ticket.sla_resolution_due)

    def test_is_sla_breached_returns_false_before_deadline(self):
        ticket = make_ticket(self.org, self.user)
        ticket.sla_resolution_due = timezone.now() + timezone.timedelta(hours=5)
        ticket.save(update_fields=["sla_resolution_due"])
        self.assertFalse(ticket.is_sla_breached)

    def test_is_sla_breached_returns_true_after_deadline(self):
        ticket = make_ticket(self.org, self.user)
        ticket.sla_resolution_due = timezone.now() - timezone.timedelta(hours=1)
        ticket.save(update_fields=["sla_resolution_due"])
        self.assertTrue(ticket.is_sla_breached)


class TicketStrTest(TestCase):
    """Test ticket __str__ representation."""

    def setUp(self):
        self.org = make_org()
        self.user = make_user(self.org)

    def test_str_contains_ticket_number_and_title(self):
        ticket = make_ticket(self.org, self.user, title="Broken pipe in B2")
        self.assertIn("MH-", str(ticket))
        self.assertIn("Broken pipe in B2", str(ticket))

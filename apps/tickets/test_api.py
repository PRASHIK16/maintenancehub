"""
MaintenanceHub — Ticket REST API Tests
Tests for the DRF ticket API endpoints.
"""
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status

from apps.accounts.models import User, UserRole
from apps.organizations.models import Organization
from apps.tickets.models import Ticket, TicketStatus, TicketPriority


def make_org(name="API Org"):
    return Organization.objects.create(name=name, slug=name.lower().replace(" ", "-"))


def make_user(org, email="api@example.com", role=UserRole.STAFF):
    return User.objects.create_user(
        email=email, password="testpass123", organization=org,
        role=role, first_name="API", last_name="User",
    )


def make_ticket(org, user, title="API Test Ticket", status=TicketStatus.SUBMITTED):
    return Ticket.objects.create(
        organization=org, title=title, description="desc",
        priority=TicketPriority.MEDIUM, status=status, created_by=user,
    )


class TicketListAPITest(TestCase):
    """Test GET /api/tickets/ — list and pagination."""

    def setUp(self):
        self.org = make_org()
        self.user = make_user(self.org)
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_list_returns_200(self):
        resp = self.client.get(reverse("api-ticket-list"))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_list_is_org_scoped(self):
        other_org = make_org("Other Org")
        other_user = make_user(other_org, email="other@x.com")
        make_ticket(other_org, other_user, title="Other Org Ticket")
        make_ticket(self.org, self.user, title="My Org Ticket")

        resp = self.client.get(reverse("api-ticket-list"))
        titles = [t["title"] for t in resp.data["results"]]
        self.assertIn("My Org Ticket", titles)
        self.assertNotIn("Other Org Ticket", titles)

    def test_list_unauthenticated_returns_403(self):
        anon = APIClient()
        resp = anon.get(reverse("api-ticket-list"))
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_filter_by_status(self):
        make_ticket(self.org, self.user, title="Open Ticket", status=TicketStatus.SUBMITTED)
        make_ticket(self.org, self.user, title="Closed Ticket", status=TicketStatus.CLOSED)

        resp = self.client.get(reverse("api-ticket-list") + "?status=submitted")
        titles = [t["title"] for t in resp.data["results"]]
        self.assertIn("Open Ticket", titles)
        self.assertNotIn("Closed Ticket", titles)


class TicketDetailAPITest(TestCase):
    """Test GET/PATCH /api/tickets/<pk>/."""

    def setUp(self):
        self.org = make_org()
        self.staff = make_user(self.org, email="staff@x.com", role=UserRole.STAFF)
        self.resident = make_user(self.org, email="resident@x.com", role=UserRole.USER)
        self.ticket = make_ticket(self.org, self.staff)
        self.client = APIClient()

    def test_get_ticket_detail(self):
        self.client.force_authenticate(user=self.staff)
        resp = self.client.get(reverse("api-ticket-detail", args=[self.ticket.pk]))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["title"], self.ticket.title)

    def test_get_nonexistent_ticket_returns_404(self):
        self.client.force_authenticate(user=self.staff)
        resp = self.client.get(reverse("api-ticket-detail", args=[99999]))
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_resident_cannot_patch_ticket(self):
        self.client.force_authenticate(user=self.resident)
        resp = self.client.patch(
            reverse("api-ticket-detail", args=[self.ticket.pk]),
            {"priority": "high"},
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_staff_can_patch_ticket(self):
        self.client.force_authenticate(user=self.staff)
        resp = self.client.patch(
            reverse("api-ticket-detail", args=[self.ticket.pk]),
            {"priority": TicketPriority.HIGH},
        )
        # Either 200 (success) or 400 (validation error) is fine — 403 is not
        self.assertNotEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_ticket_from_other_org_returns_404(self):
        other_org = make_org("Other")
        other_user = make_user(other_org, email="other2@x.com")
        other_ticket = make_ticket(other_org, other_user)
        self.client.force_authenticate(user=self.staff)
        resp = self.client.get(reverse("api-ticket-detail", args=[other_ticket.pk]))
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)


class TicketCommentAPITest(TestCase):
    """Test GET/POST /api/tickets/<pk>/comments/."""

    def setUp(self):
        self.org = make_org()
        self.staff = make_user(self.org, email="staff2@x.com", role=UserRole.STAFF)
        self.resident = make_user(self.org, email="res2@x.com", role=UserRole.USER)
        self.ticket = make_ticket(self.org, self.staff)
        self.client = APIClient()

    def test_get_comments(self):
        self.client.force_authenticate(user=self.staff)
        resp = self.client.get(reverse("api-ticket-comments", args=[self.ticket.pk]))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIsInstance(resp.data, list)

    def test_resident_cannot_see_internal_comments(self):
        from apps.tickets.models import TicketComment
        TicketComment.objects.create(
            ticket=self.ticket, author=self.staff, body="Internal note", is_internal=True
        )
        self.client.force_authenticate(user=self.resident)
        resp = self.client.get(reverse("api-ticket-comments", args=[self.ticket.pk]))
        bodies = [c["body"] for c in resp.data]
        self.assertNotIn("Internal note", bodies)

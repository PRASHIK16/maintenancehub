"""
MaintenanceHub — Account View Tests
Tests for login, RBAC mixins, and user API.
"""
from django.test import TestCase, Client
from django.urls import reverse

from apps.accounts.models import User, UserRole
from apps.organizations.models import Organization


def make_org(name="Test Org"):
    return Organization.objects.create(name=name, slug=name.lower().replace(" ", "-"))


def make_user(org, email="staff@example.com", role=UserRole.STAFF, password="testpass123"):
    return User.objects.create_user(
        email=email, password=password, organization=org, role=role,
        first_name="Test", last_name="User",
    )


class LoginViewTest(TestCase):
    """Tests for the LoginView."""

    def setUp(self):
        self.org = make_org()
        self.user = make_user(self.org)
        self.client = Client()

    def test_get_login_page(self):
        resp = self.client.get(reverse("accounts:login"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Sign in")

    def test_valid_login_redirects_to_dashboard(self):
        resp = self.client.post(reverse("accounts:login"), {
            "email": "staff@example.com",
            "password": "testpass123",
        }, follow=True)
        self.assertEqual(resp.status_code, 200)
        self.assertRedirects(resp, reverse("dashboard:home"), fetch_redirect_response=False)

    def test_invalid_password_shows_error(self):
        resp = self.client.post(reverse("accounts:login"), {
            "email": "staff@example.com",
            "password": "wrongpassword",
        })
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Invalid email address or password")

    def test_inactive_user_cannot_login(self):
        self.user.is_active = False
        self.user.save()
        resp = self.client.post(reverse("accounts:login"), {
            "email": "staff@example.com",
            "password": "testpass123",
        })
        self.assertNotEqual(resp.get("Location", ""), reverse("dashboard:home"))

    def test_authenticated_user_redirected_from_login(self):
        self.client.login(username="staff@example.com", password="testpass123")
        resp = self.client.get(reverse("accounts:login"))
        self.assertRedirects(resp, reverse("dashboard:home"), fetch_redirect_response=False)


class RBACMixinTest(TestCase):
    """Tests that RBAC mixins enforce role requirements."""

    def setUp(self):
        self.org = make_org()
        self.resident = make_user(self.org, email="resident@example.com", role=UserRole.USER)
        self.manager = make_user(self.org, email="manager@example.com", role=UserRole.MANAGER)
        self.client = Client()

    def test_resident_cannot_access_manager_pages(self):
        """Residents should be redirected from manager-only pages."""
        self.client.force_login(self.resident)
        resp = self.client.get(reverse("assets:create"))
        # Should redirect to login or 403
        self.assertIn(resp.status_code, [302, 403])

    def test_manager_can_access_asset_create(self):
        self.client.force_login(self.manager)
        resp = self.client.get(reverse("assets:create"))
        self.assertEqual(resp.status_code, 200)


class UserModelTest(TestCase):
    """Tests for the User model helper properties."""

    def setUp(self):
        self.org = make_org()

    def test_is_org_admin_true_for_org_admin(self):
        user = make_user(self.org, role=UserRole.ORG_ADMIN, email="a@x.com")
        self.assertTrue(user.is_org_admin)

    def test_is_org_admin_false_for_staff(self):
        user = make_user(self.org, role=UserRole.STAFF, email="b@x.com")
        self.assertFalse(user.is_org_admin)

    def test_is_manager_true(self):
        user = make_user(self.org, role=UserRole.MANAGER, email="c@x.com")
        self.assertTrue(user.is_manager)

    def test_display_name_returns_full_name(self):
        user = make_user(self.org, email="d@x.com")
        self.assertEqual(user.display_name, "Test User")

    def test_can_manage_returns_true_for_manager(self):
        user = make_user(self.org, role=UserRole.MANAGER, email="e@x.com")
        self.assertTrue(user.can_manage)

    def test_can_manage_returns_false_for_resident(self):
        user = make_user(self.org, role=UserRole.USER, email="f@x.com")
        self.assertFalse(user.can_manage)

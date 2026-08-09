"""
MaintenanceHub — Accounts Models
Custom User model with role-based access control.
"""
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils.translation import gettext_lazy as _
from apps.core.models import TimeStampedModel


class UserRole(models.TextChoices):
    SUPER_ADMIN = "super_admin", _("Super Admin")
    ORG_ADMIN = "org_admin", _("Organization Admin")
    MANAGER = "manager", _("Manager")
    STAFF = "staff", _("Maintenance Staff")
    USER = "user", _("User / Resident")


class UserManager(BaseUserManager):
    """Custom manager for User model."""

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email address is required")
        email = self.normalize_email(email)
        extra_fields.setdefault("role", UserRole.USER)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", UserRole.SUPER_ADMIN)
        extra_fields.setdefault("is_email_verified", True)

        if not extra_fields.get("is_staff"):
            raise ValueError("Superuser must have is_staff=True.")
        if not extra_fields.get("is_superuser"):
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(email, password, **extra_fields)


class User(AbstractUser, TimeStampedModel):
    """
    Custom User model.
    Email-based authentication with organization membership and roles.
    """
    username = None
    email = models.EmailField(_("email address"), unique=True)

    # Profile
    full_name = models.CharField(max_length=200)
    phone = models.CharField(max_length=20, blank=True)
    avatar = models.ImageField(upload_to="avatars/", null=True, blank=True)
    bio = models.TextField(blank=True)

    # Organization & Role
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="members",
    )
    role = models.CharField(
        max_length=20,
        choices=UserRole.choices,
        default=UserRole.USER,
        db_index=True,
    )

    # Department / Team (for staff)
    department = models.CharField(max_length=100, blank=True)
    employee_id = models.CharField(max_length=50, blank=True)

    # Location context (for residents/students)
    unit_number = models.CharField(max_length=50, blank=True, help_text="Room/Unit/Flat number")

    # Verification & Status
    is_email_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    # Preferences
    email_notifications = models.BooleanField(default=True)
    push_notifications = models.BooleanField(default=True)
    theme_preference = models.CharField(
        max_length=10,
        choices=[("light", "Light"), ("dark", "Dark"), ("system", "System")],
        default="system",
    )

    # Timestamps from AbstractUser (first_name, last_name not used — full_name used instead)
    first_name = None
    last_name = None

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["full_name"]

    objects = UserManager()

    class Meta:
        db_table = "accounts_user"
        verbose_name = "User"
        verbose_name_plural = "Users"
        indexes = [
            models.Index(fields=["organization", "role"]),
            models.Index(fields=["email"]),
        ]

    def __str__(self):
        return f"{self.full_name} <{self.email}>"

    @property
    def display_name(self):
        return self.full_name or self.email.split("@")[0]

    @property
    def initials(self):
        parts = self.full_name.split()
        if len(parts) >= 2:
            return f"{parts[0][0]}{parts[-1][0]}".upper()
        return self.full_name[:2].upper() if self.full_name else "??"

    # ── Role checks ──────────────────────────────────────────────────────────

    @property
    def is_super_admin(self):
        return self.role == UserRole.SUPER_ADMIN

    @property
    def is_org_admin(self):
        return self.role == UserRole.ORG_ADMIN

    @property
    def is_manager(self):
        return self.role == UserRole.MANAGER

    @property
    def is_staff_member(self):
        return self.role == UserRole.STAFF

    @property
    def is_regular_user(self):
        return self.role == UserRole.USER

    @property
    def can_manage(self):
        """Can this user manage tickets (assign, triage, etc.)?"""
        return self.role in (UserRole.SUPER_ADMIN, UserRole.ORG_ADMIN, UserRole.MANAGER)

    @property
    def can_administer(self):
        """Can this user administer the organization?"""
        return self.role in (UserRole.SUPER_ADMIN, UserRole.ORG_ADMIN)

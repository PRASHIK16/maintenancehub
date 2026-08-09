"""
MaintenanceHub — Organizations Models
Multi-tenant organization structure.
"""
from django.db import models
from apps.core.models import TimeStampedModel


class OrganizationType(models.TextChoices):
    COLLEGE = "college", "College / University"
    HOSTEL = "hostel", "Hostel / PG"
    APARTMENT = "apartment", "Apartment / Residential Society"
    OFFICE = "office", "Office / Corporate"
    COWORKING = "coworking", "Coworking Space"
    FACILITY = "facility", "Facility Management"
    OTHER = "other", "Other"


class Organization(TimeStampedModel):
    """
    Top-level tenant. All data is scoped to an Organization.
    Users, tickets, assets, locations — everything belongs to one org.
    """
    name = models.CharField(max_length=200, db_index=True)
    slug = models.SlugField(unique=True, max_length=100)
    org_type = models.CharField(max_length=20, choices=OrganizationType.choices, default=OrganizationType.OTHER)
    description = models.TextField(blank=True)
    logo = models.ImageField(upload_to="org_logos/", null=True, blank=True)
    website = models.URLField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, default="India")
    is_active = models.BooleanField(default=True)

    # Feature flags
    enable_asset_management = models.BooleanField(default=True)
    enable_preventive_maintenance = models.BooleanField(default=True)
    enable_ai_classification = models.BooleanField(default=False)
    enable_sla = models.BooleanField(default=True)

    class Meta:
        db_table = "organizations_organization"
        verbose_name = "Organization"
        verbose_name_plural = "Organizations"

    def __str__(self):
        return self.name


class Location(TimeStampedModel):
    """
    Hierarchical location within an organization.
    e.g. Building A → Floor 3 → Room 304
    """
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="locations")
    parent = models.ForeignKey("self", on_delete=models.SET_NULL, null=True, blank=True, related_name="children")
    name = models.CharField(max_length=200)
    location_type = models.CharField(
        max_length=30,
        choices=[
            ("building", "Building"),
            ("block", "Block / Wing"),
            ("floor", "Floor"),
            ("room", "Room / Unit"),
            ("area", "Area / Zone"),
            ("outdoor", "Outdoor / Grounds"),
            # Hostel-specific
            ("hostel_block", "Hostel Block"),
            ("hostel_floor", "Hostel Floor"),
            ("hostel_room", "Hostel Room"),
            ("common_area", "Common Area"),
            ("washroom", "Washroom / Bathroom"),
            # Lab-specific
            ("lab", "Laboratory"),
            ("workshop", "Workshop"),
        ],
        default="room",
    )
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "organizations_location"
        verbose_name = "Location"
        verbose_name_plural = "Locations"
        ordering = ["name"]
        unique_together = [["organization", "parent", "name"]]

    def __str__(self):
        if self.parent:
            return f"{self.parent} → {self.name}"
        return self.name

    @property
    def full_path(self):
        """Return full hierarchical path as string."""
        parts = [self.name]
        current = self.parent
        while current:
            parts.insert(0, current.name)
            current = current.parent
        return " → ".join(parts)


class Team(TimeStampedModel):
    """
    A maintenance team within an organization.
    e.g. Electrical, Plumbing, HVAC, IT Support
    """
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="teams")
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    color = models.CharField(max_length=7, default="#6366f1")  # hex color for UI
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "organizations_team"
        verbose_name = "Team"
        verbose_name_plural = "Teams"
        unique_together = [["organization", "name"]]

    def __str__(self):
        return f"{self.name} ({self.organization.name})"


class TeamMembership(TimeStampedModel):
    """Many-to-many between User and Team, with lead flag."""
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="memberships")
    user = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="team_memberships")
    is_lead = models.BooleanField(default=False)

    class Meta:
        db_table = "organizations_team_membership"
        unique_together = [["team", "user"]]

    def __str__(self):
        return f"{self.user.display_name} in {self.team.name}"


class ResidentProfile(TimeStampedModel):
    """
    Hostel resident profile. Links a User to a specific room and
    captures hostel-specific data like room number, bed, and dates.
    """
    GENDER_CHOICES = [("M", "Male"), ("F", "Female"), ("O", "Other")]

    user = models.OneToOneField(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="resident_profile",
    )
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="residents",
    )
    room = models.ForeignKey(
        Location,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="residents",
        limit_choices_to={"location_type__in": ["hostel_room", "room"]},
    )
    room_number = models.CharField(max_length=20, blank=True, help_text="Display room number/label")
    bed_number = models.CharField(max_length=10, blank=True, help_text="Bed letter/number within room")
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, blank=True)
    check_in_date = models.DateField(null=True, blank=True)
    check_out_date = models.DateField(null=True, blank=True)
    emergency_contact_name = models.CharField(max_length=150, blank=True)
    emergency_contact_phone = models.CharField(max_length=20, blank=True)
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "organizations_resident_profile"
        verbose_name = "Resident Profile"
        verbose_name_plural = "Resident Profiles"

    def __str__(self):
        room_label = self.room_number or (self.room.name if self.room else "no room")
        return f"{self.user.display_name} — {room_label}"

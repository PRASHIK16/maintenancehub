"""Admin registrations for the organizations app."""
from django.contrib import admin
from .models import Organization, Location, Team, TeamMembership, ResidentProfile


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "org_type", "is_active", "created_at"]
    list_filter = ["org_type", "is_active"]
    search_fields = ["name", "slug"]
    prepopulated_fields = {"slug": ["name"]}
    readonly_fields = ["created_at", "updated_at"]


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ["name", "organization", "location_type", "parent", "is_active"]
    list_filter = ["organization", "location_type", "is_active"]
    search_fields = ["name"]
    raw_id_fields = ["parent"]


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ["name", "organization", "color", "is_active"]
    list_filter = ["organization", "is_active"]
    search_fields = ["name"]


@admin.register(TeamMembership)
class TeamMembershipAdmin(admin.ModelAdmin):
    list_display = ["team", "user", "is_lead"]
    raw_id_fields = ["team", "user"]


@admin.register(ResidentProfile)
class ResidentProfileAdmin(admin.ModelAdmin):
    list_display = ["user", "organization", "room_number", "bed_number", "gender", "check_in_date"]
    list_filter = ["organization", "gender"]
    search_fields = ["user__email", "user__first_name", "user__last_name", "room_number"]
    raw_id_fields = ["user", "organization", "room"]

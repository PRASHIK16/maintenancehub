"""Organization settings and hostel views."""
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.views.generic import View, TemplateView, ListView
from django.http import HttpResponse
from django.db.models import Count, Q
from apps.accounts.mixins import AdminRequiredMixin, ManagerRequiredMixin
from .models import Organization, Location, Team, ResidentProfile
from .forms import OrganizationProfileForm, OrganizationFeaturesForm, LocationForm, TeamForm, ResidentProfileForm


class OrgSettingsMixin(AdminRequiredMixin):
    """Shared context for all org settings pages."""

    def get_org(self):
        return self.request.user.organization

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs) if hasattr(super(), "get_context_data") else {}
        ctx["org"] = self.get_org()
        return ctx


# ── Profile ───────────────────────────────────────────────────────────────────

class OrganizationSettingsView(OrgSettingsMixin, View):
    template_name = "organizations/profile.html"

    def get(self, request):
        org = self.get_org()
        form = OrganizationProfileForm(instance=org)
        feat_form = OrganizationFeaturesForm(instance=org)
        return render(request, self.template_name, {
            "org": org,
            "form": form,
            "feat_form": feat_form,
            "section": "profile",
        })

    def post(self, request):
        org = self.get_org()
        action = request.POST.get("action", "profile")

        if action == "features":
            feat_form = OrganizationFeaturesForm(request.POST, instance=org)
            form = OrganizationProfileForm(instance=org)
            if feat_form.is_valid():
                feat_form.save()
                messages.success(request, "Feature settings saved.")
                return redirect("organizations:settings")
        else:
            form = OrganizationProfileForm(request.POST, request.FILES, instance=org)
            feat_form = OrganizationFeaturesForm(instance=org)
            if form.is_valid():
                form.save()
                messages.success(request, "Organization profile updated.")
                return redirect("organizations:settings")

        return render(request, self.template_name, {
            "org": org,
            "form": form,
            "feat_form": feat_form,
            "section": "profile",
        })


# ── Locations ─────────────────────────────────────────────────────────────────

class LocationListView(OrgSettingsMixin, TemplateView):
    template_name = "organizations/locations.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        org = self.get_org()
        ctx["locations"] = Location.objects.filter(
            organization=org, parent=None
        ).prefetch_related("children__children")
        ctx["total_count"] = Location.objects.filter(organization=org).count()
        ctx["section"] = "locations"
        return ctx


class LocationCreateView(OrgSettingsMixin, View):
    template_name = "organizations/location_form.html"

    def get(self, request):
        org = self.get_org()
        form = LocationForm(org)
        return render(request, self.template_name, {
            "form": form, "org": org, "section": "locations", "action": "Add",
        })

    def post(self, request):
        org = self.get_org()
        form = LocationForm(org, request.POST)
        if form.is_valid():
            loc = form.save(commit=False)
            loc.organization = org
            loc.save()
            messages.success(request, f"Location '{loc.name}' created.")
            return redirect("organizations:locations")
        return render(request, self.template_name, {
            "form": form, "org": org, "section": "locations", "action": "Add",
        })


class LocationEditView(OrgSettingsMixin, View):
    template_name = "organizations/location_form.html"

    def get(self, request, pk):
        org = self.get_org()
        loc = get_object_or_404(Location, pk=pk, organization=org)
        form = LocationForm(org, instance=loc)
        return render(request, self.template_name, {
            "form": form, "org": org, "location": loc,
            "section": "locations", "action": "Edit",
        })

    def post(self, request, pk):
        org = self.get_org()
        loc = get_object_or_404(Location, pk=pk, organization=org)
        form = LocationForm(org, request.POST, instance=loc)
        if form.is_valid():
            form.save()
            messages.success(request, f"Location '{loc.name}' updated.")
            return redirect("organizations:locations")
        return render(request, self.template_name, {
            "form": form, "org": org, "location": loc,
            "section": "locations", "action": "Edit",
        })


class LocationDeleteView(OrgSettingsMixin, View):
    def post(self, request, pk):
        org = self.get_org()
        loc = get_object_or_404(Location, pk=pk, organization=org)
        name = loc.name
        child_count = loc.children.count()
        if child_count:
            messages.error(request, f"Cannot delete '{name}' — it has {child_count} sub-location(s). Remove those first.")
        else:
            loc.delete()
            messages.success(request, f"Location '{name}' deleted.")
        return redirect("organizations:locations")


# ── Teams ─────────────────────────────────────────────────────────────────────

class TeamListView(OrgSettingsMixin, TemplateView):
    template_name = "organizations/teams.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        org = self.get_org()
        ctx["teams"] = Team.objects.filter(organization=org).prefetch_related("memberships__user")
        ctx["section"] = "teams"
        return ctx


class TeamCreateView(OrgSettingsMixin, View):
    template_name = "organizations/team_form.html"

    def get(self, request):
        form = TeamForm()
        return render(request, self.template_name, {
            "form": form, "section": "teams", "action": "Add",
        })

    def post(self, request):
        org = self.get_org()
        form = TeamForm(request.POST)
        if form.is_valid():
            team = form.save(commit=False)
            team.organization = org
            team.save()
            messages.success(request, f"Team '{team.name}' created.")
            return redirect("organizations:teams")
        return render(request, self.template_name, {
            "form": form, "section": "teams", "action": "Add",
        })


class TeamEditView(OrgSettingsMixin, View):
    template_name = "organizations/team_form.html"

    def get(self, request, pk):
        org = self.get_org()
        team = get_object_or_404(Team, pk=pk, organization=org)
        form = TeamForm(instance=team)
        return render(request, self.template_name, {
            "form": form, "team": team, "section": "teams", "action": "Edit",
        })

    def post(self, request, pk):
        org = self.get_org()
        team = get_object_or_404(Team, pk=pk, organization=org)
        form = TeamForm(request.POST, instance=team)
        if form.is_valid():
            form.save()
            messages.success(request, f"Team '{team.name}' updated.")
            return redirect("organizations:teams")
        return render(request, self.template_name, {
            "form": form, "team": team, "section": "teams", "action": "Edit",
        })


class TeamDeleteView(OrgSettingsMixin, View):
    def post(self, request, pk):
        org = self.get_org()
        team = get_object_or_404(Team, pk=pk, organization=org)
        name = team.name
        team.delete()
        messages.success(request, f"Team '{name}' deleted.")
        return redirect("organizations:teams")


# ── Hostel ────────────────────────────────────────────────────────────────────

class HostelDashboardView(ManagerRequiredMixin, View):
    """Hostel warden dashboard — room-by-room issue tracker."""
    template_name = "organizations/hostel_dashboard.html"

    def get(self, request):
        from apps.tickets.models import Ticket
        org = request.user.organization

        # Hostel blocks / buildings
        hostel_blocks = Location.objects.filter(
            organization=org,
            location_type__in=["hostel_block", "block"],
            parent=None,
        ).prefetch_related("children__children")

        # Active residents
        residents = ResidentProfile.objects.filter(
            organization=org, is_active=True
        ).select_related("user", "room").order_by("room__name")

        # Open hostel tickets (in hostel locations)
        hostel_location_ids = Location.objects.filter(
            organization=org,
        ).filter(
            Q(location_type__in=["hostel_block", "hostel_floor", "hostel_room",
                                  "hostel_floor", "common_area", "washroom"])
            | Q(name__icontains="hostel")
            | Q(name__icontains="hostel")
        ).values_list("id", flat=True)

        # Broaden to include any location under a hostel block
        hostel_top = Location.objects.filter(
            organization=org,
            parent=None,
        ).filter(
            Q(name__icontains="hostel") | Q(location_type="hostel_block")
        )
        all_hostel_loc_ids = set()
        for top in hostel_top:
            all_hostel_loc_ids.add(top.id)
            for child in top.children.all():
                all_hostel_loc_ids.add(child.id)
                for grandchild in child.children.all():
                    all_hostel_loc_ids.add(grandchild.id)

        open_tickets = Ticket.objects.filter(
            organization=org,
            location_id__in=all_hostel_loc_ids,
        ).exclude(status__in=["closed", "cancelled"]).select_related(
            "created_by", "assigned_to", "location", "category"
        ).order_by("-created_at")

        stats = {
            "total_residents": residents.count(),
            "open_tickets": open_tickets.count(),
            "critical_tickets": open_tickets.filter(priority="critical").count(),
            "unassigned_tickets": open_tickets.filter(assigned_to=None).count(),
        }

        return render(request, self.template_name, {
            "org": org,
            "hostel_blocks": hostel_blocks,
            "residents": residents,
            "open_tickets": open_tickets[:20],
            "stats": stats,
        })


class ResidentListView(ManagerRequiredMixin, View):
    template_name = "organizations/resident_list.html"

    def get(self, request):
        org = request.user.organization
        residents = ResidentProfile.objects.filter(
            organization=org
        ).select_related("user", "room").order_by("room__name", "user__full_name")
        return render(request, self.template_name, {
            "residents": residents,
            "org": org,
        })


class ResidentCreateView(ManagerRequiredMixin, View):
    template_name = "organizations/resident_form.html"

    def get(self, request):
        org = request.user.organization
        form = ResidentProfileForm(org)
        return render(request, self.template_name, {"form": form, "action": "Add"})

    def post(self, request):
        org = request.user.organization
        form = ResidentProfileForm(org, request.POST)
        if form.is_valid():
            profile = form.save(commit=False)
            profile.organization = org
            profile.save()
            messages.success(request, f"Resident profile created for {profile.user.display_name}.")
            return redirect("organizations:hostel-residents")
        return render(request, self.template_name, {"form": form, "action": "Add"})


class ResidentEditView(ManagerRequiredMixin, View):
    template_name = "organizations/resident_form.html"

    def get(self, request, pk):
        org = request.user.organization
        profile = get_object_or_404(ResidentProfile, pk=pk, organization=org)
        form = ResidentProfileForm(org, instance=profile)
        return render(request, self.template_name, {
            "form": form, "profile": profile, "action": "Edit",
        })

    def post(self, request, pk):
        org = request.user.organization
        profile = get_object_or_404(ResidentProfile, pk=pk, organization=org)
        form = ResidentProfileForm(org, request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Resident profile updated.")
            return redirect("organizations:hostel-residents")
        return render(request, self.template_name, {
            "form": form, "profile": profile, "action": "Edit",
        })

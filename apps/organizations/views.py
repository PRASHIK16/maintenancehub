"""Organization settings views."""
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.views.generic import View, TemplateView, ListView
from django.http import HttpResponse
from apps.accounts.mixins import AdminRequiredMixin
from .models import Organization, Location, Team
from .forms import OrganizationProfileForm, OrganizationFeaturesForm, LocationForm, TeamForm


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

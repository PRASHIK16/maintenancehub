"""Preventive maintenance views."""
from django.views import View
from django.views.generic import ListView
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from apps.accounts.mixins import OrgRequiredMixin, ManagerRequiredMixin
from .models import PreventiveMaintenance, MaintenanceStatus, MaintenanceFrequency


class MaintenanceListView(OrgRequiredMixin, ListView):
    """List all maintenance schedules for the organization."""
    template_name = "maintenance/list.html"
    context_object_name = "schedules"
    paginate_by = 20

    def get_queryset(self):
        qs = PreventiveMaintenance.objects.filter(
            organization=self.request.user.organization
        ).select_related("asset", "location", "assigned_team")

        status = self.request.GET.get("status", "")
        if status:
            qs = qs.filter(status=status)

        return qs.order_by("next_due_at")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        org = self.request.user.organization
        ctx["status_choices"] = MaintenanceStatus.choices
        ctx["active_count"] = PreventiveMaintenance.objects.filter(
            organization=org, status=MaintenanceStatus.ACTIVE
        ).count()
        ctx["overdue_count"] = PreventiveMaintenance.objects.filter(
            organization=org, status=MaintenanceStatus.OVERDUE
        ).count()
        return ctx


class MaintenanceCreateView(ManagerRequiredMixin, View):
    """Create a new preventive maintenance schedule."""
    template_name = "maintenance/form.html"

    def get(self, request):
        from apps.assets.models import Asset
        from apps.organizations.models import Location, Team
        return render(request, self.template_name, {
            "action": "Create",
            "frequency_choices": MaintenanceFrequency.choices,
            "assets": Asset.objects.filter(
                organization=request.user.organization, status="active"
            ),
            "locations": Location.objects.filter(
                organization=request.user.organization, is_active=True
            ),
            "teams": Team.objects.filter(
                organization=request.user.organization, is_active=True
            ),
        })

    def post(self, request):
        try:
            pm = PreventiveMaintenance.objects.create(
                organization=request.user.organization,
                title=request.POST["title"],
                description=request.POST.get("description", ""),
                asset_id=request.POST.get("asset") or None,
                location_id=request.POST.get("location") or None,
                assigned_team_id=request.POST.get("assigned_team") or None,
                frequency=request.POST.get("frequency", MaintenanceFrequency.MONTHLY),
                interval_days=request.POST.get("interval_days") or None,
                next_due_at=request.POST.get("next_due_at") or None,
                estimated_duration_hours=request.POST.get("estimated_duration_hours") or None,
                checklist=request.POST.get("checklist", ""),
                created_by=request.user,
            )
            messages.success(request, f"Maintenance schedule '{pm.title}' created.")
            return redirect("maintenance:list")
        except Exception as e:
            messages.error(request, f"Error creating schedule: {e}")
            return redirect("maintenance:create")


class MaintenanceDetailView(OrgRequiredMixin, View):
    """View a maintenance schedule detail."""
    template_name = "maintenance/detail.html"

    def get(self, request, pk):
        schedule = get_object_or_404(
            PreventiveMaintenance, pk=pk, organization=request.user.organization
        )
        return render(request, self.template_name, {"schedule": schedule})

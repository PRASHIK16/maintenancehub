"""Preventive maintenance views."""
from django.views import View
from django.views.generic import ListView
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from apps.accounts.mixins import OrgRequiredMixin, ManagerRequiredMixin
from .models import PreventiveMaintenance, MaintenanceStatus, MaintenanceFrequency
from .forms import PreventiveMaintenanceForm


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
    """Create a new preventive maintenance schedule using PreventiveMaintenanceForm."""
    template_name = "maintenance/form.html"

    def get(self, request):
        form = PreventiveMaintenanceForm(
            organization=request.user.organization, user=request.user
        )
        return render(request, self.template_name, {"form": form, "action": "Create"})

    def post(self, request):
        form = PreventiveMaintenanceForm(
            request.POST,
            organization=request.user.organization,
            user=request.user,
        )
        if form.is_valid():
            pm = form.save()
            messages.success(request, f"Maintenance schedule '{pm.title}' created.")
            return redirect("maintenance:list")
        return render(request, self.template_name, {"form": form, "action": "Create"})


class MaintenanceDetailView(OrgRequiredMixin, View):
    """View a maintenance schedule detail."""
    template_name = "maintenance/detail.html"

    def get(self, request, pk):
        schedule = get_object_or_404(
            PreventiveMaintenance, pk=pk, organization=request.user.organization
        )
        return render(request, self.template_name, {"schedule": schedule})

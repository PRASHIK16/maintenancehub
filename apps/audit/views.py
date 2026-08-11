"""
MaintenanceHub — Audit Log Views
Read-only audit log browser for org admins and managers.
"""
from django.views.generic import ListView
from django.utils import timezone

from apps.accounts.mixins import AdminRequiredMixin
from .models import AuditLog, AuditAction


class AuditLogListView(AdminRequiredMixin, ListView):
    """Paginated, filterable audit log for the current organization."""
    model = AuditLog
    template_name = "audit/list.html"
    context_object_name = "logs"
    paginate_by = 50

    def get_queryset(self):
        qs = AuditLog.objects.filter(
            organization=self.request.org
        ).select_related("user").order_by("-timestamp")

        # Filters
        action = self.request.GET.get("action")
        if action:
            qs = qs.filter(action=action)

        user_q = self.request.GET.get("user")
        if user_q:
            qs = qs.filter(user__email__icontains=user_q)

        date_from = self.request.GET.get("from")
        if date_from:
            try:
                from datetime import datetime
                dt = datetime.strptime(date_from, "%Y-%m-%d")
                qs = qs.filter(timestamp__date__gte=dt.date())
            except ValueError:
                pass

        date_to = self.request.GET.get("to")
        if date_to:
            try:
                from datetime import datetime
                dt = datetime.strptime(date_to, "%Y-%m-%d")
                qs = qs.filter(timestamp__date__lte=dt.date())
            except ValueError:
                pass

        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["action_choices"] = AuditAction.choices
        ctx["filter_action"] = self.request.GET.get("action", "")
        ctx["filter_user"] = self.request.GET.get("user", "")
        ctx["filter_from"] = self.request.GET.get("from", "")
        ctx["filter_to"] = self.request.GET.get("to", "")
        return ctx

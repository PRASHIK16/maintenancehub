"""Organization settings views."""
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView
from apps.accounts.mixins import AdminRequiredMixin


class OrganizationSettingsView(AdminRequiredMixin, TemplateView):
    """Organization settings — placeholder for Phase 12."""
    template_name = "organizations/settings.html"

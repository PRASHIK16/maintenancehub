"""
MaintenanceHub — RBAC Mixins
Role-based access control enforcement for class-based views.
"""
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.contrib import messages

from .models import UserRole


class OrgRequiredMixin(LoginRequiredMixin):
    """Ensures the user belongs to an organization."""

    def dispatch(self, request, *args, **kwargs):
        result = super().dispatch(request, *args, **kwargs)
        if hasattr(result, "status_code") and result.status_code == 302:
            return result
        if not request.user.organization:
            messages.error(request, "You are not associated with any organization.")
            return redirect("accounts:profile")
        return result


class ManagerRequiredMixin(OrgRequiredMixin):
    """Requires at least Manager role."""

    def dispatch(self, request, *args, **kwargs):
        result = super().dispatch(request, *args, **kwargs)
        if hasattr(result, "status_code") and result.status_code == 302:
            return result
        if not request.user.can_manage:
            raise PermissionDenied
        return result


class AdminRequiredMixin(OrgRequiredMixin):
    """Requires Org Admin or Super Admin role."""

    def dispatch(self, request, *args, **kwargs):
        result = super().dispatch(request, *args, **kwargs)
        if hasattr(result, "status_code") and result.status_code == 302:
            return result
        if not request.user.can_administer:
            raise PermissionDenied
        return result


class SuperAdminRequiredMixin(LoginRequiredMixin):
    """Requires Super Admin role."""

    def dispatch(self, request, *args, **kwargs):
        result = super().dispatch(request, *args, **kwargs)
        if hasattr(result, "status_code") and result.status_code == 302:
            return result
        if not request.user.is_super_admin:
            raise PermissionDenied
        return result


class StaffRequiredMixin(OrgRequiredMixin):
    """Requires at least Staff role (staff or above)."""

    def dispatch(self, request, *args, **kwargs):
        result = super().dispatch(request, *args, **kwargs)
        if hasattr(result, "status_code") and result.status_code == 302:
            return result
        allowed_roles = {UserRole.STAFF, UserRole.MANAGER, UserRole.ORG_ADMIN, UserRole.SUPER_ADMIN}
        if request.user.role not in allowed_roles:
            raise PermissionDenied
        return result


class SameTenantMixin:
    """
    Ensures the requested object belongs to the same organization as the request user.
    Assumes the view has get_object() and the object has .organization field.
    """

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        if hasattr(obj, "organization") and obj.organization != self.request.user.organization:
            raise PermissionDenied
        return obj

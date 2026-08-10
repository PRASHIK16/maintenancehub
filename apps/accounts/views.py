"""
MaintenanceHub — Authentication Views
Login, logout, registration, password reset, profile.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views import View
from django.views.decorators.http import require_POST
from django.utils.decorators import method_decorator
from django.contrib.auth.forms import PasswordChangeForm

from .models import User, UserRole
from .forms import LoginForm, RegistrationForm, UserProfileForm


class LoginView(View):
    """Email/password login with role-based redirect."""
    template_name = "auth/login.html"

    FEATURES = [
        "SLA-driven ticket management with auto-alerts",
        "Role-based access for staff and residents",
        "Kanban, analytics, and real-time dashboards",
        "Asset tracking and preventive maintenance",
    ]

    def get(self, request):
        if request.user.is_authenticated:
            return redirect("dashboard:home")
        form = LoginForm()
        return render(request, self.template_name, {"form": form, "features": self.FEATURES})

    def post(self, request):
        form = LoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"]
            password = form.cleaned_data["password"]
            user = authenticate(request, email=email, password=password)
            if user is not None and user.is_active:
                login(request, user)
                next_url = request.GET.get("next", "")
                if next_url and next_url.startswith("/"):
                    return redirect(next_url)
                return redirect("dashboard:home")
            form.add_error(None, "Invalid email address or password.")
        return render(request, self.template_name, {"form": form, "features": self.FEATURES})


class LogoutView(View):
    def get(self, request):
        logout(request)
        return redirect("core:landing")

    def post(self, request):
        logout(request)
        return redirect("core:landing")


class RegisterView(View):
    """User self-registration (creates USER role by default)."""
    template_name = "auth/register.html"

    def get(self, request):
        if request.user.is_authenticated:
            return redirect("dashboard:home")
        form = RegistrationForm()
        return render(request, self.template_name, {"form": form})

    def post(self, request):
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.role = UserRole.USER
            user.save()
            login(request, user)
            messages.success(request, f"Welcome to MaintenanceHub, {user.display_name}!")
            return redirect("dashboard:home")
        return render(request, self.template_name, {"form": form})


@method_decorator(login_required, name="dispatch")
class ProfileView(View):
    """User profile settings."""
    template_name = "auth/profile.html"

    def get(self, request):
        form = UserProfileForm(instance=request.user)
        password_form = PasswordChangeForm(request.user)
        return render(request, self.template_name, {
            "form": form,
            "password_form": password_form,
        })

    def post(self, request):
        if "change_password" in request.POST:
            password_form = PasswordChangeForm(request.user, request.POST)
            if password_form.is_valid():
                user = password_form.save()
                update_session_auth_hash(request, user)
                messages.success(request, "Password updated successfully.")
                return redirect("accounts:profile")
            form = UserProfileForm(instance=request.user)
        else:
            form = UserProfileForm(request.POST, request.FILES, instance=request.user)
            password_form = PasswordChangeForm(request.user)
            if form.is_valid():
                form.save()
                messages.success(request, "Profile updated successfully.")
                return redirect("accounts:profile")

        return render(request, self.template_name, {
            "form": form,
            "password_form": password_form,
        })


@require_POST
@login_required
def set_theme(request):
    """Persist theme preference server-side."""
    import json
    try:
        data = json.loads(request.body)
        theme = data.get("theme", "system")
        if theme in ("light", "dark", "system"):
            request.user.theme_preference = theme
            request.user.save(update_fields=["theme_preference"])
    except Exception:
        pass
    return JsonResponse({"ok": True})

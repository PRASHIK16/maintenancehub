"""
Core views — landing page, health checks, version endpoint.
"""
from django.shortcuts import render
from django.views import View
from django.http import JsonResponse
from django.db import connection
from django.core.cache import cache
from django.conf import settings
import time
import django


class HealthCheckView(View):
    """Basic liveness probe — returns 200 if Django is running."""

    def get(self, request):
        return JsonResponse({
            "status": "ok",
            "timestamp": int(time.time()),
            "service": "maintenancehub",
        })


class HealthReadyView(View):
    """Readiness probe — checks database and cache connectivity."""

    def get(self, request):
        checks = {}
        status_code = 200

        # Database check
        try:
            connection.ensure_connection()
            checks["database"] = "ok"
        except Exception as e:
            checks["database"] = f"error: {str(e)}"
            status_code = 503

        # Cache/Redis check
        try:
            cache.set("health_check", "ok", timeout=5)
            result = cache.get("health_check")
            checks["cache"] = "ok" if result == "ok" else "error: value mismatch"
        except Exception as e:
            checks["cache"] = f"error: {str(e)}"
            status_code = 503

        return JsonResponse({
            "status": "ready" if status_code == 200 else "degraded",
            "checks": checks,
            "timestamp": int(time.time()),
        }, status=status_code)


class VersionView(View):
    """
    Version endpoint for deployment tracking.
    Returns app version, Django version, Python version, and environment.
    """

    def get(self, request):
        import sys
        import platform
        return JsonResponse({
            "app": "MaintenanceHub",
            "version": getattr(settings, "APP_VERSION", "0.0.0"),
            "environment": getattr(settings, "ENVIRONMENT", "unknown"),
            "django_version": django.get_version(),
            "python_version": sys.version.split(" ")[0],
            "platform": platform.system(),
            "timestamp": int(time.time()),
        })


def landing_page(request):
    """Public landing page."""
    if request.user.is_authenticated:
        from django.shortcuts import redirect
        return redirect("dashboard:home")
    return render(request, "landing/index.html")


def handler404(request, exception):
    return render(request, "errors/404.html", status=404)


def handler403(request, exception):
    return render(request, "errors/403.html", status=403)


def handler500(request):
    return render(request, "errors/500.html", status=500)

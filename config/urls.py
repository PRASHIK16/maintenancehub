"""
MaintenanceHub — Root URL Configuration
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from apps.core.views import HealthCheckView, HealthReadyView

urlpatterns = [
    # Health checks
    path("health/", HealthCheckView.as_view(), name="health"),
    path("health/ready/", HealthReadyView.as_view(), name="health-ready"),

    # Django admin
    path("admin/", admin.site.urls),

    # Public landing
    path("", include("apps.core.urls")),

    # Authentication
    path("auth/", include("apps.accounts.urls")),

    # Main application
    path("dashboard/", include("apps.tickets.urls")),
    path("organizations/", include("apps.organizations.urls")),
    path("notifications/", include("apps.notifications.urls")),
    path("analytics/", include("apps.analytics.urls")),
    path("assets/", include("apps.assets.urls")),
    path("maintenance/", include("apps.maintenance.urls")),
    path("audit/", include("apps.audit.urls")),

    # REST API
    path("api/", include("apps.tickets.api_urls")),
    path("api/accounts/", include("apps.accounts.api_urls")),

    # JWT Auth endpoints
    path("api/auth/token/", include("apps.accounts.jwt_urls")),
]

# Custom error handlers
handler403 = "apps.core.views.handler403"
handler404 = "apps.core.views.handler404"
handler500 = "apps.core.views.handler500"

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    try:
        import debug_toolbar
        urlpatterns = [path("__debug__/", include(debug_toolbar.urls))] + urlpatterns
    except ImportError:
        pass

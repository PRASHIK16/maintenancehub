"""URL patterns for organizations app."""
from django.urls import path
from . import views

app_name = "organizations"

urlpatterns = [
    path("settings/", views.OrganizationSettingsView.as_view(), name="settings"),
]

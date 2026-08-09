"""URL patterns for organizations app."""
from django.urls import path
from . import views

app_name = "organizations"

urlpatterns = [
    # Profile & features
    path("settings/", views.OrganizationSettingsView.as_view(), name="settings"),

    # Locations
    path("settings/locations/", views.LocationListView.as_view(), name="locations"),
    path("settings/locations/add/", views.LocationCreateView.as_view(), name="location-create"),
    path("settings/locations/<int:pk>/edit/", views.LocationEditView.as_view(), name="location-edit"),
    path("settings/locations/<int:pk>/delete/", views.LocationDeleteView.as_view(), name="location-delete"),

    # Teams
    path("settings/teams/", views.TeamListView.as_view(), name="teams"),
    path("settings/teams/add/", views.TeamCreateView.as_view(), name="team-create"),
    path("settings/teams/<int:pk>/edit/", views.TeamEditView.as_view(), name="team-edit"),
    path("settings/teams/<int:pk>/delete/", views.TeamDeleteView.as_view(), name="team-delete"),
]

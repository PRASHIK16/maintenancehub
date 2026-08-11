"""URL patterns for analytics app."""
from django.urls import path
from . import views

app_name = "analytics"

urlpatterns = [
    path("", views.AnalyticsOverviewView.as_view(), name="overview"),
    path("stats/", views.StatsPartialView.as_view(), name="stats"),
    path("export/", views.AnalyticsExportView.as_view(), name="export"),
]

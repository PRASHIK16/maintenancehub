"""URL patterns for analytics app."""
from django.urls import path
from . import views

app_name = "analytics"

urlpatterns = [
    path("", views.AnalyticsOverviewView.as_view(), name="overview"),
    path("stats/", views.StatsPartialView.as_view(), name="stats"),
    path("export/", views.AnalyticsExportView.as_view(), name="export"),
    path("recurring/", views.RecurringIssuesView.as_view(), name="recurring"),
    path("sla-report/", views.SLAReportView.as_view(), name="sla-report"),
]

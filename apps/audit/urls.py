"""URL configuration for the audit app."""
from django.urls import path
from . import views

app_name = "audit"

urlpatterns = [
    path("", views.AuditLogListView.as_view(), name="list"),
]

"""Notification URL patterns."""
from django.urls import path
from . import views

app_name = "notifications"

urlpatterns = [
    path("", views.NotificationListView.as_view(), name="list"),
    path("panel/", views.NotificationPanelView.as_view(), name="panel"),
    path("<int:pk>/read/", views.mark_notification_read, name="mark-read"),
    path("mark-all-read/", views.mark_all_read, name="mark-all-read"),
]

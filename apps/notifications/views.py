"""Notification views — center, panel, mark-read."""
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.http import HttpResponse
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils import timezone

from .models import Notification


class NotificationPanelView(LoginRequiredMixin, View):
    """HTMX notification panel dropdown."""

    def get(self, request):
        notifications = request.user.notifications.select_related("ticket").order_by("-created_at")[:15]
        return render(request, "notifications/panel.html", {"notifications": notifications})


class NotificationListView(LoginRequiredMixin, View):
    """Full notification center page."""

    def get(self, request):
        tab = request.GET.get("tab", "unread")
        qs = request.user.notifications.select_related("ticket").order_by("-created_at")

        if tab == "unread":
            notifications = qs.filter(is_read=False)
        elif tab == "read":
            notifications = qs.filter(is_read=True)[:50]
        else:
            notifications = qs[:50]

        return render(request, "notifications/list.html", {
            "notifications": notifications,
            "tab": tab,
            "unread_count": qs.filter(is_read=False).count(),
        })


@require_POST
@login_required
def mark_notification_read(request, pk):
    notification = get_object_or_404(Notification, pk=pk, recipient=request.user)
    notification.mark_read()
    if request.headers.get("HX-Request"):
        return HttpResponse("")  # Remove from UI
    return HttpResponse(status=204)


@require_POST
@login_required
def mark_all_read(request):
    request.user.notifications.filter(is_read=False).update(
        is_read=True, read_at=timezone.now()
    )
    if request.headers.get("HX-Request"):
        return render(request, "notifications/panel.html", {"notifications": []})
    from django.shortcuts import redirect
    return redirect("notifications:list")

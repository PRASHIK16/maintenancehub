"""Inject notification count into all templates."""


def notifications_context(request):
    if not request.user.is_authenticated:
        return {"unread_notifications_count": 0}
    count = request.user.notifications.filter(is_read=False).count()
    return {"unread_notifications_count": count}

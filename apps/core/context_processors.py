"""
Global template context processors.
"""
from django.conf import settings


def global_context(request):
    """Inject global app context into all templates."""
    context = {
        "APP_NAME": settings.APP_NAME,
        "SITE_URL": settings.SITE_URL,
        "DEBUG": settings.DEBUG,
    }

    if request.user.is_authenticated:
        context["user_role"] = getattr(request.user, "role", None)
        context["user_org"] = getattr(request.user, "organization", None)

    return context

"""Custom template tags and filters for MaintenanceHub."""
from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter(name="split")
def split_filter(value, delimiter=","):
    """Split a string by a delimiter and return a list.

    Usage: {{ "a|b|c"|split:"|" }}
    """
    return value.split(delimiter)


@register.filter(name="multiply")
def multiply(value, factor):
    """Multiply a value by a factor."""
    try:
        return float(value) * float(factor)
    except (TypeError, ValueError):
        return value


@register.filter(name="percentage")
def percentage(value, total):
    """Return percentage of value/total as an integer."""
    try:
        total = float(total)
        if total == 0:
            return 0
        return int(float(value) / total * 100)
    except (TypeError, ValueError, ZeroDivisionError):
        return 0


@register.filter(name="subtract")
def subtract(value, arg):
    """Subtract arg from value."""
    try:
        return int(value) - int(arg)
    except (TypeError, ValueError):
        return value


@register.filter(name="get_item")
def get_item(dictionary, key):
    """Get an item from a dictionary by key."""
    if isinstance(dictionary, dict):
        return dictionary.get(key)
    return None


@register.simple_tag
def priority_color(priority):
    """Return Tailwind CSS color class for a priority level."""
    colors = {
        "critical": "red",
        "high": "orange",
        "medium": "yellow",
        "low": "green",
    }
    return colors.get(priority.lower() if priority else "", "gray")


@register.inclusion_tag("components/avatar.html", takes_context=True)
def user_avatar(context, user, size="md"):
    """Render a user avatar with initials fallback."""
    return {"user": user, "size": size}

"""Admin registrations for the accounts app."""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = [
        "email", "full_name", "role", "organization",
        "is_active", "is_email_verified", "date_joined",
    ]
    list_filter = ["role", "organization", "is_active", "is_email_verified"]
    search_fields = ["email", "full_name", "phone"]
    ordering = ["-date_joined"]
    readonly_fields = ["date_joined", "last_login", "created_at", "updated_at"]

    fieldsets = [
        ("Authentication", {"fields": ["email", "password"]}),
        ("Personal Info", {"fields": ["full_name", "phone", "avatar", "bio", "unit_number"]}),
        ("Organization", {"fields": ["organization", "role", "department", "employee_id"]}),
        ("Permissions", {"fields": [
            "is_active", "is_staff", "is_superuser", "is_email_verified",
            "groups", "user_permissions",
        ]}),
        ("Preferences", {"fields": ["theme_preference", "email_notifications", "push_notifications"]}),
        ("Timestamps", {"fields": ["date_joined", "last_login", "created_at", "updated_at"], "classes": ["collapse"]}),
    ]

    add_fieldsets = [
        (None, {
            "classes": ["wide"],
            "fields": ["email", "full_name", "organization", "role", "password1", "password2"],
        }),
    ]

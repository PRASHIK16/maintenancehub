"""DRF Serializers for the accounts app."""
from rest_framework import serializers
from .models import User


class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer for reading/updating the authenticated user's profile."""
    organization_name = serializers.CharField(source="organization.name", read_only=True)

    class Meta:
        model = User
        fields = [
            "id", "email", "full_name", "phone", "role",
            "organization", "organization_name",
            "department", "employee_id", "unit_number",
            "bio", "is_email_verified",
            "email_notifications", "push_notifications", "theme_preference",
            "date_joined", "last_login",
        ]
        read_only_fields = [
            "id", "email", "role", "organization", "organization_name",
            "is_email_verified", "date_joined", "last_login",
        ]


class UserListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for user lists (org-scoped)."""
    class Meta:
        model = User
        fields = ["id", "full_name", "email", "role", "department", "is_active"]
        read_only_fields = fields

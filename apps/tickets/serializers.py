"""DRF Serializers for the tickets app."""
from rest_framework import serializers
from .models import Ticket, TicketComment, Category, SLARule


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "parent", "is_active"]


class TicketListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list endpoints."""
    created_by_name = serializers.CharField(source="created_by.full_name", read_only=True)
    assigned_to_name = serializers.CharField(source="assigned_to.full_name", read_only=True, default=None)
    category_name = serializers.CharField(source="category.name", read_only=True, default=None)

    class Meta:
        model = Ticket
        fields = [
            "id", "ticket_number", "title", "priority", "status",
            "created_by_name", "assigned_to_name", "category_name",
            "sla_response_due", "sla_resolution_due",
            "created_at", "updated_at",
        ]
        read_only_fields = fields


class TicketDetailSerializer(serializers.ModelSerializer):
    """Full serializer for ticket detail and create/update."""
    created_by_name = serializers.CharField(source="created_by.full_name", read_only=True)
    assigned_to_name = serializers.CharField(source="assigned_to.full_name", read_only=True, default=None)
    category_name = serializers.CharField(source="category.name", read_only=True, default=None)
    location_path = serializers.CharField(source="location.full_path", read_only=True, default=None)

    class Meta:
        model = Ticket
        fields = [
            "id", "ticket_number", "title", "description",
            "priority", "status", "category", "category_name",
            "location", "location_path",
            "created_by", "created_by_name",
            "assigned_to", "assigned_to_name",
            "sla_response_due", "sla_resolution_due",
            "sla_response_met", "sla_resolution_met",
            "first_response_at", "resolved_at", "closed_at",
            "contact_phone", "preferred_visit_time",
            "rating", "rating_comment", "resolution_notes",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "ticket_number", "created_by", "created_by_name",
            "sla_response_due", "sla_resolution_due",
            "sla_response_met", "sla_resolution_met",
            "first_response_at", "resolved_at", "closed_at",
            "created_at", "updated_at",
        ]

    def create(self, validated_data):
        request = self.context["request"]
        validated_data["organization"] = request.user.organization
        validated_data["created_by"] = request.user
        return super().create(validated_data)


class TicketCommentSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source="author.full_name", read_only=True)

    class Meta:
        model = TicketComment
        fields = ["id", "ticket", "author", "author_name", "body", "is_internal", "created_at"]
        read_only_fields = ["id", "author", "author_name", "created_at"]

    def create(self, validated_data):
        validated_data["author"] = self.context["request"].user
        return super().create(validated_data)

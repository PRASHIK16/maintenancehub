"""REST API URLs for accounts — v1."""
from django.urls import path
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from .models import User
from .serializers import UserProfileSerializer, UserListSerializer


@api_view(["GET", "PATCH"])
@permission_classes([IsAuthenticated])
def me(request):
    """
    GET   /api/accounts/me/  → current user profile
    PATCH /api/accounts/me/  → update own profile
    """
    if request.method == "GET":
        serializer = UserProfileSerializer(request.user)
        return Response(serializer.data)

    serializer = UserProfileSerializer(
        request.user, data=request.data, partial=True
    )
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def user_list(request):
    """
    GET /api/accounts/users/  → list users in the same organization
    Managers and above only.
    """
    if request.user.role not in ("manager", "org_admin", "super_admin"):
        return Response({"detail": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)

    users = User.objects.filter(
        organization=request.user.organization,
        is_active=True,
    ).order_by("full_name")

    role = request.GET.get("role")
    if role:
        users = users.filter(role=role)

    serializer = UserListSerializer(users, many=True)
    return Response({"count": users.count(), "results": serializer.data})


urlpatterns = [
    path("me/", me, name="api-me"),
    path("users/", user_list, name="api-user-list"),
]

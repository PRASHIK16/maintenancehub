"""REST API URLs for tickets — v1."""
from django.urls import path
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from .models import Ticket, TicketComment
from .serializers import TicketListSerializer, TicketDetailSerializer, TicketCommentSerializer


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def ticket_list_create(request):
    """
    GET  /api/tickets/       → paginated ticket list (org-scoped)
    POST /api/tickets/       → create a new ticket
    """
    if request.method == "GET":
        qs = Ticket.objects.filter(
            organization=request.user.organization
        ).select_related("created_by", "assigned_to", "category").order_by("-created_at")

        # Filter by status or priority
        if s := request.GET.get("status"):
            qs = qs.filter(status=s)
        if p := request.GET.get("priority"):
            qs = qs.filter(priority=p)

        # Simple pagination
        page = int(request.GET.get("page", 1))
        page_size = int(request.GET.get("page_size", 25))
        start = (page - 1) * page_size
        total = qs.count()
        tickets = qs[start:start + page_size]

        serializer = TicketListSerializer(tickets, many=True)
        return Response({
            "count": total,
            "page": page,
            "page_size": page_size,
            "results": serializer.data,
        })

    # POST — create
    serializer = TicketDetailSerializer(data=request.data, context={"request": request})
    if serializer.is_valid():
        ticket = serializer.save()
        return Response(
            TicketDetailSerializer(ticket, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET", "PATCH"])
@permission_classes([IsAuthenticated])
def ticket_detail(request, pk):
    """
    GET   /api/tickets/<pk>/  → ticket detail
    PATCH /api/tickets/<pk>/  → partial update (staff/manager)
    """
    try:
        ticket = Ticket.objects.get(pk=pk, organization=request.user.organization)
    except Ticket.DoesNotExist:
        return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

    if request.method == "GET":
        serializer = TicketDetailSerializer(ticket, context={"request": request})
        return Response(serializer.data)

    # PATCH — only staff/manager/admin
    if request.user.role not in ("staff", "manager", "admin"):
        return Response({"detail": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)

    serializer = TicketDetailSerializer(
        ticket, data=request.data, partial=True, context={"request": request}
    )
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def ticket_comments(request, pk):
    """
    GET  /api/tickets/<pk>/comments/  → list comments
    POST /api/tickets/<pk>/comments/  → add a comment
    """
    try:
        ticket = Ticket.objects.get(pk=pk, organization=request.user.organization)
    except Ticket.DoesNotExist:
        return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

    if request.method == "GET":
        comments = TicketComment.objects.filter(ticket=ticket)
        # Residents only see public comments
        if request.user.role == "user":
            comments = comments.filter(is_internal=False)
        serializer = TicketCommentSerializer(comments, many=True)
        return Response(serializer.data)

    # POST
    data = request.data.copy()
    data["ticket"] = ticket.pk
    # Only staff/manager/admin can post internal notes
    if request.user.role == "user":
        data["is_internal"] = False
    serializer = TicketCommentSerializer(data=data, context={"request": request})
    if serializer.is_valid():
        comment = serializer.save()
        return Response(TicketCommentSerializer(comment).data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


urlpatterns = [
    path("tickets/", ticket_list_create, name="api-ticket-list"),
    path("tickets/<int:pk>/", ticket_detail, name="api-ticket-detail"),
    path("tickets/<int:pk>/comments/", ticket_comments, name="api-ticket-comments"),
]

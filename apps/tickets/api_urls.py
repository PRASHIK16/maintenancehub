"""REST API URLs for tickets — v1."""
from django.urls import path
from django.db.models import Q
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from .models import Ticket, TicketComment
from .serializers import TicketListSerializer, TicketDetailSerializer, TicketCommentSerializer

# Valid sort fields exposed via the API
TICKET_SORT_FIELDS = {
    "created_at": "created_at",
    "-created_at": "-created_at",
    "priority": "priority",
    "-priority": "-priority",
    "sla_resolution_due": "sla_resolution_due",
    "-sla_resolution_due": "-sla_resolution_due",
    "status": "status",
}

PAGE_SIZE_MAX = 100


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def ticket_list_create(request):
    """
    GET  /api/tickets/       → paginated ticket list (org-scoped)
    POST /api/tickets/       → create a new ticket

    Query params (GET):
      status      Filter by ticket status (exact)
      priority    Filter by priority (exact)
      category    Filter by category ID
      assigned_to Filter by assignee user ID
      q           Full-text search in ticket_number, title, description
      ordering    Sort field (see TICKET_SORT_FIELDS); default: -created_at
      page        Page number (1-based, default 1)
      page_size   Results per page (default 25, max 100)
    """
    if request.method == "GET":
        qs = Ticket.objects.filter(
            organization=request.user.organization
        ).select_related("created_by", "assigned_to", "category").order_by("-created_at")

        # --- Filters ---
        if s := request.GET.get("status"):
            qs = qs.filter(status=s)
        if p := request.GET.get("priority"):
            qs = qs.filter(priority=p)
        if cat := request.GET.get("category"):
            qs = qs.filter(category_id=cat)
        if assignee := request.GET.get("assigned_to"):
            qs = qs.filter(assigned_to_id=assignee)

        # --- Full-text search ---
        if q := request.GET.get("q", "").strip():
            qs = qs.filter(
                Q(ticket_number__icontains=q) |
                Q(title__icontains=q) |
                Q(description__icontains=q)
            )

        # --- Ordering ---
        ordering_param = request.GET.get("ordering", "-created_at")
        ordering = TICKET_SORT_FIELDS.get(ordering_param, "-created_at")
        qs = qs.order_by(ordering)

        # --- Pagination ---
        try:
            page = max(1, int(request.GET.get("page", 1)))
            page_size = min(PAGE_SIZE_MAX, max(1, int(request.GET.get("page_size", 25))))
        except (ValueError, TypeError):
            page, page_size = 1, 25

        start = (page - 1) * page_size
        total = qs.count()
        tickets = qs[start:start + page_size]

        serializer = TicketListSerializer(tickets, many=True)
        return Response({
            "count": total,
            "page": page,
            "page_size": page_size,
            "total_pages": max(1, (total + page_size - 1) // page_size),
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

    # PATCH — only staff/manager/org_admin (matches UserRole values)
    if request.user.role not in ("staff", "manager", "org_admin", "super_admin"):
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

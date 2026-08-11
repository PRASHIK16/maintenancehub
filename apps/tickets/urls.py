"""Ticket and dashboard URL patterns."""
from django.urls import path
from . import views

app_name = "dashboard"

urlpatterns = [
    # Dashboards
    path("", views.DashboardView.as_view(), name="home"),
    path("my-tickets/", views.MyTicketsView.as_view(), name="my-tickets"),
    path("tickets/", views.AllTicketsView.as_view(), name="all-tickets"),
    path("tickets/kanban/", views.KanbanView.as_view(), name="kanban"),
    path("search/", views.SearchView.as_view(), name="search"),

    # Ticket CRUD
    path("tickets/new/", views.CreateTicketView.as_view(), name="create-ticket"),
    path("tickets/<int:pk>/", views.TicketDetailView.as_view(), name="ticket-detail"),
    path("tickets/<int:pk>/update/", views.TicketUpdateView.as_view(), name="ticket-update"),

    # Workflow actions
    path("tickets/<int:pk>/transition/", views.TicketTransitionView.as_view(), name="ticket-transition"),
    path("tickets/<int:pk>/assign/", views.AssignTicketView.as_view(), name="ticket-assign"),
    path("tickets/<int:pk>/comment/", views.AddCommentView.as_view(), name="ticket-comment"),
    path("tickets/<int:pk>/attachment/", views.UploadAttachmentView.as_view(), name="ticket-attachment"),
    path("tickets/<int:pk>/rate/", views.RateTicketView.as_view(), name="ticket-rate"),
    path("tickets/<int:pk>/kanban-move/", views.KanbanMoveView.as_view(), name="kanban-move"),

    # Bulk actions
    path("tickets/bulk-action/", views.BulkTicketActionView.as_view(), name="bulk-action"),
]

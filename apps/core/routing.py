"""WebSocket URL routing for MaintenanceHub."""
from django.urls import re_path
from apps.core import consumers

websocket_urlpatterns = [
    re_path(r"ws/dashboard/$", consumers.DashboardConsumer.as_asgi()),
    re_path(r"ws/tickets/(?P<ticket_id>\d+)/$", consumers.TicketConsumer.as_asgi()),
]

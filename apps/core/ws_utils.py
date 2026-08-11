"""
WebSocket broadcast utilities.
Call these from views/tasks to push real-time updates to connected clients.
"""
import logging
from asgiref.sync import async_to_sync

logger = logging.getLogger(__name__)


def broadcast_ticket_update(ticket, event_type="update", extra=None):
    """
    Broadcast a ticket event to:
      - The ticket-specific group (ticket_<id>) so the detail page updates live
      - The org dashboard group (dashboard_<org_id>) so counters/kanban stay fresh
    """
    try:
        from channels.layers import get_channel_layer
        channel_layer = get_channel_layer()
        if channel_layer is None:
            return  # Channels not configured (e.g. during tests without redis)

        payload = {
            "type": "ticket_update",
            "data": {
                "event": event_type,
                "ticket_id": ticket.pk,
                "ticket_number": ticket.ticket_number,
                "status": ticket.status,
                "priority": ticket.priority,
                **(extra or {}),
            },
        }

        # Dashboard group — org-wide
        async_to_sync(channel_layer.group_send)(
            f"dashboard_{ticket.organization_id}", payload
        )

        # Ticket-specific group
        ticket_payload = {
            "type": "ticket_message",
            "data": payload["data"],
        }
        async_to_sync(channel_layer.group_send)(
            f"ticket_{ticket.pk}", ticket_payload
        )
    except Exception as exc:
        logger.warning(f"WS broadcast failed (non-fatal): {exc}")


def broadcast_comment_added(ticket, comment):
    """Broadcast a new comment to the ticket's WebSocket group."""
    try:
        from channels.layers import get_channel_layer
        channel_layer = get_channel_layer()
        if channel_layer is None:
            return

        async_to_sync(channel_layer.group_send)(
            f"ticket_{ticket.pk}",
            {
                "type": "ticket_message",
                "data": {
                    "event": "comment_added",
                    "ticket_id": ticket.pk,
                    "comment_id": comment.pk,
                    "author": comment.author.display_name,
                    "is_internal": comment.is_internal,
                    "body_preview": comment.body[:120],
                },
            },
        )
    except Exception as exc:
        logger.warning(f"WS comment broadcast failed (non-fatal): {exc}")

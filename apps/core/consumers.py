"""
WebSocket consumers for real-time updates.
"""
import json
from channels.generic.websocket import AsyncWebsocketConsumer


class DashboardConsumer(AsyncWebsocketConsumer):
    """Sends live dashboard updates to admin/manager users."""

    async def connect(self):
        if not self.scope["user"].is_authenticated:
            await self.close()
            return
        user = self.scope["user"]
        self.group_name = f"dashboard_{user.organization_id}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def ticket_update(self, event):
        """Receive ticket update and send to WebSocket."""
        await self.send(text_data=json.dumps(event["data"]))


class TicketConsumer(AsyncWebsocketConsumer):
    """Sends live updates for a specific ticket."""

    async def connect(self):
        if not self.scope["user"].is_authenticated:
            await self.close()
            return
        self.ticket_id = self.scope["url_route"]["kwargs"]["ticket_id"]
        self.group_name = f"ticket_{self.ticket_id}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def ticket_message(self, event):
        await self.send(text_data=json.dumps(event["data"]))

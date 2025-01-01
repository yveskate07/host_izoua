"""import django
from asgiref.sync import async_to_sync
from channels.generic.websocket import AsyncWebsocketConsumer, AsyncConsumer
from channels.layers import get_channel_layer
from django.template import Context, Template
import json
import asyncio

from izouapp.models import orders


class BackgroundScriptConsumer(AsyncConsumer):
    async def start_script(self, event):
        while True:
            orders_ = orders.objects.filter(status='pending', create_at=django.utils.timezone.now)
            for order in orders_:
                if not order.notified and order.is_deadline_close:
                    channel_layer = get_channel_layer()
                    message = order.str_for_alert()
                    async_to_sync(channel_layer.group_send)(
                        "notifications",
                        {
                            "type": "send_notification",
                            "message": message
                        }
                    )
                    order.notified = True
            # Placez votre logique ici
            await asyncio.sleep(120)  # Pause de 2 min

class NotificationConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        await self.accept()
        await self.channel_layer.group_add("notifications", self.channel_name)

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard("notifications", self.channel_name)

    async def send_notification(self, event):
        message = event["message"]

        template = Template('<div class="notification"><p>{{message}}</p></div>')
        context = Context({"message": message})
        rendered_notification = template.render(context)

        await self.send(
            text_data=json.dumps(
                {
                    "type": "notification",
                    "message": rendered_notification
                }
            )
        )"""

import asyncio
import json

import django
from asgiref.sync import sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer, AsyncConsumer
from channels.layers import get_channel_layer
from django.template import Context, Template
from django.utils.timezone import now
from izouapp.models import orders


class BackgroundScriptConsumer(AsyncConsumer):
    async def start_script(self, event):
        while True:
            # Charger les commandes en attente via une fonction synchrone
            orders_ = await sync_to_async(self.get_pending_orders)()
            for order in orders_:
                if not order.notified and order.is_deadline_close:
                    # Envoyer une notification via la couche de canaux
                    message = order.str_for_alert()
                    await self.channel_layer.group_send(
                        "notifications",
                        {
                            "type": "send_notification",
                            "message": message
                        }
                    )
                    # Mettre à jour l'état de l'objet
                    await sync_to_async(self.mark_as_notified)(order)
            # Pause de 2 minutes
            await asyncio.sleep(120)

    @staticmethod
    def get_pending_orders():
        # Évaluer les résultats en tant que liste
        return list(orders.objects.filter(status='pending', create_at=django.utils.timezone.now()))

    @staticmethod
    def mark_as_notified(order):
        """Marque une commande comme notifiée."""
        order.notified = True
        order.save()


class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # Accepter la connexion WebSocket
        await self.accept()
        await self.channel_layer.group_add("notifications", self.channel_name)

    async def disconnect(self, close_code):
        # Retirer le client du groupe
        await self.channel_layer.group_discard("notifications", self.channel_name)

    async def send_notification(self, event):
        # Récupérer le message de l'événement
        message = event["message"]

        # Rendre le message via un template Django
        template = Template('<div class="notification"><p>{{message}}</p></div>')
        context = Context({"message": message})
        rendered_notification = template.render(context)

        # Envoyer les données via WebSocket
        await self.send(
            text_data=json.dumps(
                {
                    "type": "notification",
                    "message": rendered_notification
                }
            )
        )


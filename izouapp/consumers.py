import traceback
from datetime import datetime

import django
from asgiref.sync import sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
import asyncio
import json

from accounts.models import Manager_or_Admin
from izouapp.mail_sender import send_period_digest
from izouapp.models import orders


class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_group_name = 'notifications'

        # Ajouter le client au groupe
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

        # Lancer une tâche en arrière-plan pour envoyer des messages en continu
        self.task = asyncio.create_task(self.send_messages())

    async def disconnect(self, close_code):
        # Supprimer le client du groupe
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
        # Annuler la tâche si elle existe
        if hasattr(self, 'task'):
            self.task.cancel()

    async def receive(self, text_data):
        print('Receiving message from the client...')
        text_data_json = json.loads(text_data)
        message = text_data_json['message']

        # Envoyer un message au groupe
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': message
            }
        )

    async def chat_message(self, event):
        print("Sending message to the client...")
        message = event['message']

        # Envoyer le message au client WebSocket
        await self.send(text_data=json.dumps({
            'type': 'chat',
            'message': message
        }))

    async def send_messages(self):
        """Tâche en arrière-plan pour envoyer des messages en continu au backend et des emails quelques fois."""
        count = 0
        while True:
            try:
                today = datetime.now()
                if today.weekday() == 0:  # Lundi
                    await self.send_digest_emails(period="week", subject="Votre digest hebdomadaire.")
                elif today.day == 1:  # Premier jour du mois
                    await self.send_digest_emails(period="month", subject="Votre digest mensuel.")

                # Vérification des commandes en attente
                await self.check_pending_orders()

            except Exception as e:
                # Loggez l'erreur pour le débogage
                print(f"*************************** Erreur dans send_messages : {e} *************************** ")
                traceback.print_exc()  # affichage des infos complète de 'exception
            finally:
                # Pause entre les exécutions
                await asyncio.sleep(5)

    async def send_digest_emails(self, period, subject):
        """Envoie des emails digest aux superusers."""
        superusers = await sync_to_async(list)(Manager_or_Admin.objects.filter(is_superuser=True))
        for user in superusers:
            if user.email:
                try:
                    print("ici on essaie d'envoyer un mail")
                    send_period_digest(period=period, to_email=user.email, subject=subject)
                except Exception as e:
                    print(f"Erreur lors de l'envoi de l'email à {user.email} : {e}")

    async def check_pending_orders(self):
        pending_orders = await sync_to_async(list)(orders.objects.filter(status='pending', create_at=django.utils.timezone.now().date(), notified=False))

        for order in pending_orders:
            if order.is_deadline_close:
                try:
                    alert_message = await order.str_for_alert
                    await self.channel_layer.group_send(
                        self.room_group_name,
                        {
                            'type': 'chat_message',
                            'message': alert_message,
                        }
                    )
                except Exception as e:
                    traceback.print_exc() # affichage des infos complète de 'exception
                    #print(f"Erreur lors de l'envoi de la notification pour la commande {order.order_id} : {e}")
                else:
                    order.notified = True
                    await sync_to_async(order.save)()


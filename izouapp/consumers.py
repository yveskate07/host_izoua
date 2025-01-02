from channels.generic.websocket import AsyncWebsocketConsumer
import asyncio
import json


class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        print("Client trying to connect...")
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
        """Tâche en arrière-plan pour envoyer des messages en continu."""
        count = 0
        while True:
            count += 1
            message = f"Message automatique {count}"
            print(f"Envoi : {message}")

            # Envoyer un message à tous les clients du groupe
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message': message
                }
            )

            # Pause entre chaque message
            await asyncio.sleep(5)

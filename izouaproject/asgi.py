"""import asyncio
import os
from channels.layers import get_channel_layer
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application
from izouapp.consumers import BackgroundScriptConsumer

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'izouaproject.settings')

django_application = get_asgi_application()

from . import urls # noqa isort:skip

async def start_background_task():
    channel_layer = get_channel_layer()
    consumer = BackgroundScriptConsumer()
    await consumer.start_script(None)

asyncio.create_task(start_background_task())
application = ProtocolTypeRouter(
    {
        "http": get_asgi_application(),
        "websocket": URLRouter(urls.websocket_urlpatterns),
        "channel": BackgroundScriptConsumer,
    }
)
"""

import os
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application

# Définir l'environnement Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'izouaproject.settings')

# Charger l'application Django
django_application = get_asgi_application()

# Importer les URLs après la configuration de l'environnement Django
from . import urls  # noqa isort:skip
from izouapp.consumers import BackgroundScriptConsumer

# Fonction pour démarrer la tâche d'arrière-plan
async def start_background_task():
    consumer = BackgroundScriptConsumer()
    await consumer.start_script(None)

# Fonction de wrapper ASGI
class CustomProtocolTypeRouter(ProtocolTypeRouter):
    async def __call__(self, scope, receive, send):
        # Démarrer les tâches d'arrière-plan avant de router
        if not hasattr(self, "_background_task_started"):
            self._background_task_started = True
            import asyncio
            asyncio.create_task(start_background_task())
        await super().__call__(scope, receive, send)

# Configuration finale de l'application
application = CustomProtocolTypeRouter(
    {
        "http": django_application,
        "websocket": URLRouter(urls.websocket_urlpatterns),
    }
)
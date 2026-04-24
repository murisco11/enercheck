from src.app.core.config import Settings
from src.messaging.base import MessagingBackend
from src.messaging.in_memory import InMemoryMessageBus


def build_messaging_backend(settings: Settings) -> MessagingBackend:
    if settings.messaging_backend == "inmemory":
        bus = InMemoryMessageBus()
        return MessagingBackend(publisher=bus, consumer=bus)

    raise ValueError(f"Backend de mensageria nao suportado: {settings.messaging_backend}")

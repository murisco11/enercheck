from dataclasses import dataclass
from typing import Protocol

from src.messaging.events import MessageEnvelope


class MessagePublisher(Protocol):
    async def publish(self, envelope: MessageEnvelope) -> None:
        """Publica um evento."""


class MessageConsumer(Protocol):
    async def consume(self) -> MessageEnvelope | None:
        """Consome um evento se disponivel."""


@dataclass(slots=True)
class MessagingBackend:
    publisher: MessagePublisher
    consumer: MessageConsumer

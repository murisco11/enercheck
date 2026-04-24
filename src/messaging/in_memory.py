from asyncio import Queue, QueueEmpty

from src.messaging.events import MessageEnvelope


class InMemoryMessageBus:
    def __init__(self) -> None:
        self._queue: Queue[MessageEnvelope] = Queue()

    async def publish(self, envelope: MessageEnvelope) -> None:
        await self._queue.put(envelope)

    async def consume(self) -> MessageEnvelope | None:
        try:
            return self._queue.get_nowait()
        except QueueEmpty:
            return None

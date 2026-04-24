import pytest

from src.messaging.events import MessageEnvelope
from src.messaging.in_memory import InMemoryMessageBus


@pytest.mark.asyncio
async def test_in_memory_bus_publish_and_consume() -> None:
    bus = InMemoryMessageBus()
    envelope = MessageEnvelope(event_name="sample.created", payload={"id": "1"})

    await bus.publish(envelope)
    consumed = await bus.consume()

    assert consumed == envelope

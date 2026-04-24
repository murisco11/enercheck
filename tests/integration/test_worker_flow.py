import pytest

from src.integrations.ai.mock import MockAIProvider
from src.messaging.events import MessageEnvelope
from src.messaging.in_memory import InMemoryMessageBus
from src.modules.ai_demo.application.use_cases import AIDemoService
from src.worker.main import process_event


@pytest.mark.asyncio
async def test_worker_processes_ai_demo_event_without_error() -> None:
    bus = InMemoryMessageBus()
    envelope = MessageEnvelope(
        event_name="ai_demo.requested",
        payload={"job_id": "job-1", "message": "rodar fluxo"},
    )
    await bus.publish(envelope)
    consumed = await bus.consume()

    service = AIDemoService(ai_provider=MockAIProvider(prefix="[worker]"))
    await process_event(service, consumed.event_name, consumed.payload)

    assert consumed.payload["job_id"] == "job-1"

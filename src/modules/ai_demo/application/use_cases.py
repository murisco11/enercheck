from uuid import uuid4

from src.integrations.ai.base import AIProvider
from src.messaging.base import MessagePublisher
from src.messaging.events import MessageEnvelope
from src.modules.ai_demo.domain.models import (
    AIDemoJobCreatedResponse,
    AIDemoResponse,
)


class AIDemoService:
    def __init__(self, ai_provider: AIProvider) -> None:
        self._ai_provider = ai_provider

    async def respond(self, message: str) -> AIDemoResponse:
        result = await self._ai_provider.generate_text(message)
        return AIDemoResponse(provider=result.provider, output=result.output)


class EnqueueAIDemoJobUseCase:
    event_name = "ai_demo.requested"

    def __init__(self, publisher: MessagePublisher) -> None:
        self._publisher = publisher

    async def execute(self, message: str) -> AIDemoJobCreatedResponse:
        job_id = str(uuid4())
        envelope = MessageEnvelope(
            event_name=self.event_name,
            payload={"job_id": job_id, "message": message},
        )
        await self._publisher.publish(envelope)
        return AIDemoJobCreatedResponse(
            event_name=envelope.event_name,
            job_id=job_id,
            status="queued",
        )

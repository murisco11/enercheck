from dataclasses import dataclass

from src.app.core.config import Settings
from src.integrations.ai.base import AIProvider
from src.messaging.base import MessageConsumer, MessagePublisher
from src.modules.ai_demo.application.use_cases import AIDemoService


@dataclass(slots=True)
class AppContainer:
    settings: Settings
    ai_provider: AIProvider
    message_publisher: MessagePublisher
    message_consumer: MessageConsumer
    ai_demo_service: AIDemoService

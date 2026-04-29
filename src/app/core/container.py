from dataclasses import dataclass

from src.app.core.config import Settings
from src.db.session import DatabaseSessionManager
from src.integrations.ai.base import AIProvider
from src.messaging.base import MessageConsumer, MessagePublisher
from src.modules.ai_demo.application.use_cases import AIDemoService
from src.modules.users.application.use_cases import UserService


@dataclass(slots=True)
class AppContainer:
    settings: Settings
    db_session_manager: DatabaseSessionManager
    ai_provider: AIProvider
    message_publisher: MessagePublisher
    message_consumer: MessageConsumer
    ai_demo_service: AIDemoService
    user_service: UserService

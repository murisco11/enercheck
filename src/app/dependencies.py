from functools import lru_cache

from src.app.core.config import get_settings
from src.app.core.container import AppContainer
from src.db.session import DatabaseSessionManager
from src.integrations.ai.factory import build_ai_provider
from src.messaging.factory import build_messaging_backend
from src.modules.ai_demo.application.use_cases import (
    AIDemoService,
    EnqueueAIDemoJobUseCase,
)
from src.modules.users.application.use_cases import UserService
from src.modules.users.infrastructure.repository import SQLAlchemyUserRepository


@lru_cache
def get_container() -> AppContainer:
    settings = get_settings()
    db_session_manager = DatabaseSessionManager(settings.resolved_database_url)
    message_backend = build_messaging_backend(settings)
    ai_provider = build_ai_provider(settings)
    ai_demo_service = AIDemoService(ai_provider=ai_provider)
    user_repository = SQLAlchemyUserRepository(db_session_manager.session_factory)
    user_service = UserService(repository=user_repository)

    return AppContainer(
        settings=settings,
        db_session_manager=db_session_manager,
        ai_provider=ai_provider,
        message_publisher=message_backend.publisher,
        message_consumer=message_backend.consumer,
        ai_demo_service=ai_demo_service,
        user_service=user_service,
    )


def get_ai_demo_service() -> AIDemoService:
    return get_container().ai_demo_service


def get_enqueue_ai_demo_job_use_case() -> EnqueueAIDemoJobUseCase:
    container = get_container()
    return EnqueueAIDemoJobUseCase(publisher=container.message_publisher)


def get_user_service() -> UserService:
    return get_container().user_service

from functools import lru_cache

from src.app.core.config import get_settings
from src.app.core.container import AppContainer
from src.integrations.ai.factory import build_ai_provider
from src.messaging.factory import build_messaging_backend
from src.modules.ai_demo.application.use_cases import (
    AIDemoService,
    EnqueueAIDemoJobUseCase,
)


@lru_cache
def get_container() -> AppContainer:
    settings = get_settings()
    message_backend = build_messaging_backend(settings)
    ai_provider = build_ai_provider(settings)
    ai_demo_service = AIDemoService(ai_provider=ai_provider)

    return AppContainer(
        settings=settings,
        ai_provider=ai_provider,
        message_publisher=message_backend.publisher,
        message_consumer=message_backend.consumer,
        ai_demo_service=ai_demo_service,
    )


def get_ai_demo_service() -> AIDemoService:
    return get_container().ai_demo_service


def get_enqueue_ai_demo_job_use_case() -> EnqueueAIDemoJobUseCase:
    container = get_container()
    return EnqueueAIDemoJobUseCase(publisher=container.message_publisher)

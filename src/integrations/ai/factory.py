from src.app.core.config import Settings
from src.integrations.ai.base import AIProvider
from src.integrations.ai.mock import MockAIProvider


def build_ai_provider(settings: Settings) -> AIProvider:
    if settings.ai_provider == "mock":
        return MockAIProvider(prefix=settings.ai_mock_response_prefix)

    raise ValueError(f"AI provider nao suportado: {settings.ai_provider}")

from functools import lru_cache

from src.app.core.ai.base import AIProvider
from src.app.core.ai.mock import MockAIProvider
from src.app.core.ai.openai_provider import OpenAIProvider
from src.app.core.config import get_settings
from src.app.core.exceptions import IntegrationError


@lru_cache
def get_ai_provider() -> AIProvider:
    settings = get_settings()
    provider = settings.ai_provider.lower()
    if provider == "mock":
        return MockAIProvider(prefixo=settings.ai_mock_response_prefix)
    if provider == "openai":
        return OpenAIProvider(
            api_key=settings.openai_api_key or "",
            modelo_extracao=settings.openai_model_extracao,
            modelo_embedding=settings.openai_model_embedding,
        )
    raise IntegrationError(f"AI_PROVIDER desconhecido: {settings.ai_provider!r}")

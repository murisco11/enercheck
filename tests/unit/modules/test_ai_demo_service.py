import pytest

from src.integrations.ai.mock import MockAIProvider
from src.modules.ai_demo.application.use_cases import AIDemoService


@pytest.mark.asyncio
async def test_ai_demo_service_returns_provider_response() -> None:
    service = AIDemoService(ai_provider=MockAIProvider(prefix="[test]"))

    result = await service.respond("ola")

    assert result.provider == "mock"
    assert result.output.startswith("[test]")

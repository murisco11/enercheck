from src.app.core.config import Settings


def test_settings_load_from_environment() -> None:
    settings = Settings(
        APP_NAME="demo-app",
        AI_PROVIDER="mock",
        MESSAGING_BACKEND="inmemory",
    )

    assert settings.app_name == "demo-app"
    assert settings.ai_provider == "mock"
    assert settings.messaging_backend == "inmemory"

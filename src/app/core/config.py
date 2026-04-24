from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = Field(default="enercheck", alias="APP_NAME")
    app_env: str = Field(default="local", alias="APP_ENV")
    app_host: str = Field(default="0.0.0.0", alias="APP_HOST")
    app_port: int = Field(default=8000, alias="APP_PORT")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    ai_provider: str = Field(default="mock", alias="AI_PROVIDER")
    ai_mock_response_prefix: str = Field(default="[mock-ai]", alias="AI_MOCK_RESPONSE_PREFIX")
    messaging_backend: str = Field(default="inmemory", alias="MESSAGING_BACKEND")
    worker_poll_interval_seconds: float = Field(
        default=0.1,
        alias="WORKER_POLL_INTERVAL_SECONDS",
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()

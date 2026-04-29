from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL


class Settings(BaseSettings):
    app_name: str = Field(default="enercheck", alias="APP_NAME")
    app_env: str = Field(default="local", alias="APP_ENV")
    app_host: str = Field(default="0.0.0.0", alias="APP_HOST")
    app_port: int = Field(default=8000, alias="APP_PORT")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    auth_secret_key: str = Field(default="change-me-in-production", alias="AUTH_SECRET_KEY")
    auth_token_expire_minutes: int = Field(default=60, alias="AUTH_TOKEN_EXPIRE_MINUTES")
    database_url: str | None = Field(default=None, alias="DATABASE_URL")
    db_user: str = Field(default="enercheck", alias="DB_USER")
    db_password: str = Field(default="enercheck123", alias="DB_PASSWORD")
    db_host: str = Field(default="localhost", alias="DB_HOST")
    db_port: int = Field(default=5432, alias="DB_PORT")
    db_name: str = Field(default="enercheck_db", alias="DB_NAME")
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

    @property
    def resolved_database_url(self) -> str:
        if self.database_url:
            return self.database_url

        return URL.create(
            drivername="postgresql+psycopg",
            username=self.db_user,
            password=self.db_password,
            host=self.db_host,
            port=self.db_port,
            database=self.db_name,
        ).render_as_string(hide_password=False)


@lru_cache
def get_settings() -> Settings:
    return Settings()

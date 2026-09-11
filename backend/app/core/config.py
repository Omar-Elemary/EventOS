from functools import lru_cache
import os

from pydantic_settings import BaseSettings, SettingsConfigDict


def _default_database_url() -> str:
    if os.getenv("VERCEL"):
        return "sqlite+aiosqlite:///./eventos.sqlite"
    return "postgresql+asyncpg://eventos:eventos@localhost:5432/eventos"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        extra="ignore",
    )

    app_name: str = "EventOS"
    debug: bool = False

    database_url: str = _default_database_url()
    redis_url: str = "redis://localhost:6379/0"

    llm_provider: str = "mock"
    llm_model: str = "gpt-4o-mini"
    llm_api_key: str = ""
    llm_base_url: str = "https://api.openai.com/v1"
    llm_timeout: float = 25.0

    search_api_key: str = ""
    search_api_url: str = "https://api.search.brave.com/res/v1/web/search"

    use_mock_tools: bool = True
    max_iterations: int = 5
    contingency_rate: float = 0.10
    demo_user_email: str = "demo@eventos.local"
    cors_origins: str = "*"
    auth_secret: str = "eventos-dev-auth-secret"

    def cors_origin_list(self) -> list[str]:
        raw = (self.cors_origins or "*").strip()
        if raw == "*":
            return ["*"]
        return [part.strip() for part in raw.split(",") if part.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()

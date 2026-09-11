from functools import lru_cache

import structlog

from app.core.config import get_settings
from app.llm.base import LLMProvider
from app.llm.gemini import GeminiProvider
from app.llm.mock import MockLLMProvider
from app.llm.openai_compatible import OpenAICompatibleProvider

log = structlog.get_logger()


@lru_cache
def get_llm_provider() -> LLMProvider:
    settings = get_settings()
    provider = settings.llm_provider.lower().strip()
    if provider in {"mock", "none"}:
        return MockLLMProvider()
    if not (settings.llm_api_key or "").strip():
        log.warning("llm_api_key_missing_using_mock", configured_provider=provider)
        return MockLLMProvider()
    if provider in {"gemini", "google"}:
        return GeminiProvider(
            api_key=settings.llm_api_key,
            model=settings.llm_model,
            base_url=settings.llm_base_url,
            timeout=settings.llm_timeout,
        )
    return OpenAICompatibleProvider(
        api_key=settings.llm_api_key,
        model=settings.llm_model,
        base_url=settings.llm_base_url.rstrip("/"),
        timeout=settings.llm_timeout,
    )

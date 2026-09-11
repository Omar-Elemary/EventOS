from functools import lru_cache
import os

import structlog

from app.core.config import get_settings
from app.llm.base import LLMProvider
from app.llm.gemini import GeminiProvider
from app.llm.mock import MockLLMProvider
from app.llm.openai_compatible import OpenAICompatibleProvider

log = structlog.get_logger()


GROQ_BASE_URL = "https://api.groq.com/openai/v1"
GROQ_MODEL = "openai/gpt-oss-20b"


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
    if provider in {"groq"}:
        model = settings.llm_model.strip()
        if not model or "gemini" in model or "gpt-4o" in model or (os.getenv("VERCEL") and "120b" in model):
            model = GROQ_MODEL
        base = (settings.llm_base_url or "").rstrip("/")
        if not base or "openai.com" in base or "googleapis" in base:
            base = GROQ_BASE_URL
        return OpenAICompatibleProvider(
            api_key=settings.llm_api_key,
            model=model,
            base_url=base,
            timeout=min(settings.llm_timeout, 8.0) if os.getenv("VERCEL") else settings.llm_timeout,
        )
    return OpenAICompatibleProvider(
        api_key=settings.llm_api_key,
        model=settings.llm_model,
        base_url=settings.llm_base_url.rstrip("/"),
        timeout=settings.llm_timeout,
    )

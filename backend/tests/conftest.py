import os

os.environ.setdefault("LLM_PROVIDER", "mock")
os.environ.setdefault("USE_MOCK_TOOLS", "true")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

from app.core.config import get_settings
from app.llm.factory import get_llm_provider

get_settings.cache_clear()
get_llm_provider.cache_clear()

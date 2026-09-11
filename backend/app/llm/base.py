from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel


class LLMMessage(BaseModel):
    role: str
    content: str


class LLMProvider(ABC):
    name: str

    @abstractmethod
    async def complete_structured(
        self,
        schema: type[BaseModel],
        messages: list[LLMMessage],
        *,
        tools: list[dict[str, Any]] | None = None,
    ) -> BaseModel:
        """Return an instance of schema. Must not raise on parse retry; raise LLMError after failure."""


class LLMError(Exception):
    pass

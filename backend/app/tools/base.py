from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from pydantic import BaseModel, ValidationError

InT = TypeVar("InT", bound=BaseModel)
OutT = TypeVar("OutT")


class ToolError(Exception):
    def __init__(self, tool: str, message: str, *, retryable: bool = False) -> None:
        super().__init__(message)
        self.tool = tool
        self.message = message
        self.retryable = retryable


class Tool(ABC, Generic[InT, OutT]):
    name: str
    description: str
    input_model: type[InT]

    @abstractmethod
    async def _run(self, payload: InT) -> OutT:
        ...

    async def execute(self, raw: InT | dict) -> OutT:
        try:
            payload = raw if isinstance(raw, self.input_model) else self.input_model.model_validate(raw)
        except ValidationError as exc:
            raise ToolError(self.name, f"Invalid input: {exc}") from exc
        try:
            return await self._run(payload)
        except ToolError:
            raise
        except Exception as exc:
            raise ToolError(self.name, str(exc), retryable=True) from exc

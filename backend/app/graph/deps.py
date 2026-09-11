from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Protocol

from app.core.config import get_settings
from app.llm.base import LLMProvider
from app.llm.factory import get_llm_provider
from app.services.research import InMemoryResearchMemory, ResearchMemory
from app.tools import ToolRegistry, default_registry


class TraceSink(Protocol):
    async def persist_run(self, record: dict[str, Any]) -> None: ...
    async def emit(self, event_id: str, payload: dict[str, Any]) -> None: ...


class NullSink:
    def __init__(self) -> None:
        self.records: list[dict[str, Any]] = []
        self.events: list[dict[str, Any]] = []

    async def persist_run(self, record: dict[str, Any]) -> None:
        self.records.append(record)

    async def emit(self, event_id: str, payload: dict[str, Any]) -> None:
        self.events.append({"event_id": event_id, **payload})


@dataclass
class GraphDeps:
    tools: ToolRegistry
    llm: LLMProvider
    sink: TraceSink
    research: ResearchMemory = field(default_factory=InMemoryResearchMemory)
    max_iterations: int = 5
    persist_plan: Callable[[dict[str, Any]], Awaitable[None]] | None = None


def build_deps(
    sink: TraceSink | None = None,
    research: ResearchMemory | None = None,
    *,
    use_mock: bool | None = None,
) -> GraphDeps:
    settings = get_settings()
    tools = ToolRegistry(use_mock=use_mock) if use_mock is not None else default_registry()
    return GraphDeps(
        tools=tools,
        llm=get_llm_provider(),
        sink=sink or NullSink(),
        research=research or InMemoryResearchMemory(),
        max_iterations=settings.max_iterations,
    )

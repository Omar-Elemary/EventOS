from __future__ import annotations

import time
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
from typing import Any

import structlog

from app.domain.enums import AgentStatus
from app.domain.models import AgentMessage
from app.domain.state import EventState
from app.graph.deps import GraphDeps
from app.tools.base import ToolError

log = structlog.get_logger()

AgentFn = Callable[[EventState, GraphDeps], Awaitable[dict[str, Any]]]


async def run_agent_node(
    agent: str,
    task: str,
    state: EventState,
    deps: GraphDeps,
    fn: AgentFn,
    *,
    input_summary: str,
) -> dict[str, Any]:
    event_id = state["event_id"]
    run_id = state["run_id"]
    correlation_id = state.get("correlation_id") or run_id
    iteration = int(state.get("iteration") or 0)
    start = time.perf_counter()
    await deps.sink.emit(
        event_id,
        {"type": "agent_started", "agent": agent, "run_id": run_id, "iteration": iteration},
    )
    errors: list[str] = []
    status = AgentStatus.running
    output_summary = ""
    updates: dict[str, Any] = {}
    last_exc: Exception | None = None
    for attempt in range(2):
        try:
            updates = await fn(state, deps)
            output_summary = str(updates.pop("_output_summary", "completed"))
            extra_errors = updates.pop("_errors", [])
            errors.extend(extra_errors)
            status = AgentStatus.failed if errors and updates.get("status") == "needs_human_review" else AgentStatus.completed
            last_exc = None
            break
        except ToolError as exc:
            last_exc = exc
            errors.append(f"{exc.tool}: {exc.message}")
            if not exc.retryable or attempt == 1:
                break
        except Exception as exc:
            last_exc = exc
            errors.append(str(exc))
            break

    duration_ms = int((time.perf_counter() - start) * 1000)
    if last_exc is not None and status != AgentStatus.completed:
        status = AgentStatus.failed
        updates = {
            "status": "needs_human_review",
            "errors": [str(last_exc)],
        }
        output_summary = f"Failed: {last_exc}"

    record = {
        "event_id": event_id,
        "run_id": run_id,
        "correlation_id": correlation_id,
        "agent": agent,
        "status": status.value,
        "task": task,
        "input_summary": input_summary,
        "output_summary": output_summary,
        "iteration": iteration,
        "duration_ms": duration_ms,
        "errors": errors,
    }
    log.info("agent_run", **record)
    await deps.sink.persist_run(record)
    evt_type = "agent_failed" if status == AgentStatus.failed else "agent_completed"
    await deps.sink.emit(
        event_id,
        {"type": evt_type, "agent": agent, "run_id": run_id, "duration_ms": duration_ms, "errors": errors, "reason": errors[0] if errors else None},
    )
    msg = AgentMessage(
        agent=agent,
        status=status,
        task=task,
        input_summary=input_summary,
        output_summary=output_summary,
        timestamp=datetime.now(timezone.utc),
        duration_ms=duration_ms,
        iteration=iteration,
        errors=errors,
    )
    updates.setdefault("agent_messages", [msg])
    if errors:
        updates.setdefault("errors", errors)
    return updates

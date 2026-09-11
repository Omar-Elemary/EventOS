from __future__ import annotations

import uuid
from typing import Any

import structlog

from app.core.db import json_safe, session_maker
from app.domain.models import EventRequirements
from app.graph.builder import compile_graph
from app.graph.deps import GraphDeps, NullSink, build_deps
from app.models import ChatMessage, Event, PlanJob
from app.services.copilot import load_state, persist_state, policy_after_graph
from app.services.copilot_speak import speak
from app.services.persistence import persist_agent_run, persist_plan
from app.services.serialize import snapshot_state
from app.services.sse import EventBus, memory_bus

log = structlog.get_logger()


class DbSink:
    def __init__(self, bus: EventBus) -> None:
        self.bus = bus

    async def persist_run(self, record: dict[str, Any]) -> None:
        async with session_maker()() as session:
            await persist_agent_run(session, record)

    async def emit(self, event_id: str, payload: dict[str, Any]) -> None:
        await self.bus.publish(event_id, payload)


class PlannerWorker:
    """Enqueue interface compatible with a later Celery/RQ worker."""

    def __init__(self, bus: EventBus | None = None) -> None:
        self.bus = bus or memory_bus

    async def enqueue(self, event_id: str, *, force_over_budget: bool = False, extra: dict | None = None) -> str:
        run_id = str(uuid.uuid4())
        async with session_maker()() as session:
            session.add(
                PlanJob(
                    id=run_id,
                    event_id=event_id,
                    status="queued",
                    force_over_budget=force_over_budget,
                    extra=json_safe(extra or {}),
                )
            )
            event = await session.get(Event, event_id)
            if event:
                event.status = "planning"
            await session.commit()
        return run_id

    async def run_job(self, run_id: str) -> dict[str, Any]:
        async with session_maker()() as session:
            job = await session.get(PlanJob, run_id)
            if not job:
                raise KeyError(run_id)
            job.status = "running"
            event = await session.get(Event, job.event_id)
            extra = dict(job.extra or {})
            user_request = extra.get("user_request") or ((event.user_request if event else "") or "")
            event_id = job.event_id
            force = job.force_over_budget
            data_mode = extra.get("data_mode") or (getattr(event, "data_mode", None) if event else None) or "mock"
            await session.commit()

        sink = DbSink(self.bus)
        from app.services.research_db import DbResearchMemory
        from app.services.research import prefetch_evidence

        use_mock = data_mode != "live"
        deps = build_deps(sink=sink, research=DbResearchMemory(), use_mock=use_mock)

        async def _persist(snapshot: dict[str, Any]) -> None:
            async with session_maker()() as session:
                await persist_plan(session, event_id, snapshot)

        deps.persist_plan = _persist
        graph = compile_graph(deps)
        initial = {
            "run_id": run_id,
            "event_id": event_id,
            "correlation_id": run_id,
            "user_request": extra.get("user_request") or user_request,
            "requirements": extra.get("requirements"),
            "venues": extra.get("venues") or [],
            "vendors": extra.get("vendors") or [],
            "budget": extra.get("budget"),
            "schedule": extra.get("schedule"),
            "logistics": extra.get("logistics"),
            "risks": extra.get("risks") or [],
            "critic_result": None,
            "agent_messages": [],
            "iteration": 0,
            "status": "planning",
            "errors": [],
            "route_to": None,
            "missing_fields": [],
            "replan_mode": extra.get("replan_mode"),
            "force_over_budget": force,
        }
        if extra.get("requirements") and isinstance(extra["requirements"], dict):
            initial["requirements"] = EventRequirements.model_validate(extra["requirements"])
        req_obj = initial.get("requirements")
        if isinstance(req_obj, EventRequirements) and req_obj.location and req_obj.attendees:
            await prefetch_evidence(deps, req_obj, event_id=event_id)
        log.info("plan_start", run_id=run_id, event_id=event_id)
        result = await graph.ainvoke(initial)
        snapshot = snapshot_state(result)
        snapshot["status"] = result.get("status") or snapshot.get("status")
        async with session_maker()() as session:
            job = await session.get(PlanJob, run_id)
            if job:
                job.status = result.get("status") or "completed"
            event = await session.get(Event, event_id)
            if event:
                if result.get("status"):
                    event.status = result["status"]
                state = load_state(event)
                decision = policy_after_graph(state, snapshot)
                persist_state(event, decision.state)
                message = await speak(decision)
                session.add(
                    ChatMessage(
                        event_id=event_id,
                        role="assistant",
                        content=message,
                        extra={
                            "actions": [a.model_dump() for a in decision.actions],
                            "phase": decision.phase,
                            "policy": decision.policy,
                        },
                    )
                )
            await session.commit()
        await self.bus.publish(
            event_id,
            {
                "type": "plan_completed",
                "status": result.get("status"),
                "run_id": run_id,
                "copilot": True,
            },
        )
        return result

    async def mark_failed(self, run_id: str) -> None:
        event_id = None
        async with session_maker()() as session:
            job = await session.get(PlanJob, run_id)
            if job:
                event_id = job.event_id
                job.status = "failed"
                event = await session.get(Event, job.event_id)
                if event and event.status == "planning":
                    event.status = "needs_human_review"
            await session.commit()
        if event_id:
            await self.bus.publish(
                event_id,
                {"type": "plan_completed", "status": "failed", "run_id": run_id, "copilot": True},
            )

    async def safe_run(self, run_id: str) -> None:
        try:
            await self.run_job(run_id)
        except Exception:
            log.exception("plan_job_failed", run_id=run_id)
            try:
                await self.mark_failed(run_id)
            except Exception:
                log.exception("plan_job_mark_failed", run_id=run_id)

    async def resume_unfinished(self) -> int:
        from sqlalchemy import select

        async with session_maker()() as session:
            rows = (
                await session.scalars(select(PlanJob).where(PlanJob.status.in_(("queued", "running"))))
            ).all()
            ids = [row.id for row in rows]
        import asyncio

        for run_id in ids:
            asyncio.create_task(self.safe_run(run_id))
        if ids:
            log.info("plan_jobs_resumed", count=len(ids))
        return len(ids)


async def run_graph_memory(
    user_request: str,
    *,
    force_over_budget: bool = False,
    deps: GraphDeps | None = None,
    extra: dict | None = None,
) -> dict:
    deps = deps or build_deps(sink=NullSink())
    graph = compile_graph(deps)
    extra = extra or {}
    initial = {
        "run_id": str(uuid.uuid4()),
        "event_id": extra.get("event_id") or "test-event",
        "correlation_id": extra.get("correlation_id") or "test",
        "user_request": extra.get("user_request") or user_request,
        "requirements": extra.get("requirements"),
        "venues": extra.get("venues") or [],
        "vendors": extra.get("vendors") or [],
        "budget": extra.get("budget"),
        "schedule": extra.get("schedule"),
        "logistics": extra.get("logistics"),
        "risks": extra.get("risks") or [],
        "critic_result": None,
        "agent_messages": [],
        "iteration": 0,
        "status": "planning",
        "errors": [],
        "route_to": None,
        "missing_fields": [],
        "replan_mode": extra.get("replan_mode"),
        "force_over_budget": force_over_budget,
    }
    if extra.get("requirements") and isinstance(extra["requirements"], dict):
        initial["requirements"] = EventRequirements.model_validate(extra["requirements"])
    return await graph.ainvoke(initial)

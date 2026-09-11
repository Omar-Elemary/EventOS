import asyncio
import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete as sql_delete, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sse_starlette.sse import EventSourceResponse

from app.core.db import get_session
from app.models import (
    ActivityLog,
    AgentRun,
    Budget,
    BudgetItem,
    ChatMessage,
    Decision,
    Document,
    Event,
    EventRequirement,
    EventVenue,
    EventVendor,
    PlanJob,
    PlanSnapshot,
    ResearchRecord,
    Risk,
    ScheduleItem,
    Simulation,
    Task,
    Vendor,
    Venue,
)
from app.schemas.api import (
    CandidateAction,
    ChatActionOut,
    ChatIn,
    ChatOut,
    DecisionApply,
    EventCreate,
    EventOut,
    EventPatch,
    PlanAccepted,
    PlanRequest,
    SimulateIn,
    VendorCreate,
)
from app.seed import DEMO_USER_ID
from app.services.activity import add_activity
from app.services.copilot import is_prompt_chip, load_state, persist_state, policy, requirements_for_graph, seed_from_title, user_request_from_state, welcome_decision, _confirm_actions
from app.services.copilot_speak import speak, template_message  # welcome uses template_message; chips are EGP MCQ
from app.services.event_state import budget_out, decision_out, risk_out, schedule_out, task_out, venue_out, vendor_out
from app.services.persistence import bump_version, get_event_loaded
from app.services.serialize import snapshot_state
from app.services.simulate import impact_diff
from app.services.sse import memory_bus
from app.services.understand import understand_message
from app.workers.planner import PlannerWorker, run_graph_memory

router = APIRouter(prefix="/api")
worker = PlannerWorker()


def _event_out(e: Event) -> EventOut:
    out = EventOut.model_validate(e)
    out.copilot_state = load_state(e).model_dump()
    out.objectives = e.objectives or []
    out.tags = e.tags or []
    out.data_mode = e.data_mode or "mock"
    out.event_state_version = int(e.event_state_version or 0)
    return out


@router.post("/events", response_model=EventOut)
async def create_event(body: EventCreate, session: AsyncSession = Depends(get_session)):
    ev = Event(
        owner_id=DEMO_USER_ID,
        name=body.name,
        location=body.location,
        attendees=body.attendees,
        duration_days=body.duration_days,
        budget=body.budget,
        currency=body.currency,
        user_request=body.user_request,
        start_date=body.start_date,
        description=body.description,
        objectives=body.objectives or [],
        tags=body.tags or [],
        deadline=body.deadline,
        data_mode=body.data_mode or "mock",
        status="draft",
        event_state_version=0,
    )
    session.add(ev)
    await session.flush()
    state = seed_from_title(body.name, body.user_request)
    persist_state(ev, state)
    add_activity(session, ev.id, actor="user", action="create", summary=f"Created event {ev.name}")
    welcome = template_message(welcome_decision(state))
    session.add(
        ChatMessage(
            event_id=ev.id,
            role="assistant",
            content=welcome,
            extra={
                "actions": [a.model_dump() for a in state.available_actions],
                "phase": state.phase,
                "policy": "ASK" if state.missing_fields else "CONFIRM",
            },
        )
    )
    await session.commit()
    await session.refresh(ev)
    return _event_out(ev)


@router.get("/events", response_model=list[EventOut])
async def list_events(session: AsyncSession = Depends(get_session)):
    rows = (await session.scalars(select(Event).order_by(Event.created_at.desc()))).all()
    return [_event_out(r) for r in rows if not r.archived_at]


@router.get("/events/{event_id}", response_model=EventOut)
async def get_event(event_id: str, session: AsyncSession = Depends(get_session)):
    ev = await session.get(Event, event_id)
    if not ev:
        raise HTTPException(404, "event not found")
    return _event_out(ev)


@router.patch("/events/{event_id}", response_model=EventOut)
async def patch_event(event_id: str, body: EventPatch, session: AsyncSession = Depends(get_session)):
    ev = await session.get(Event, event_id)
    if not ev:
        raise HTTPException(404, "event not found")
    data = body.model_dump(exclude_unset=True)
    req_patch = data.pop("requirements", None)
    for k, v in data.items():
        setattr(ev, k, v)
    if req_patch:
        existing = await session.scalar(select(EventRequirement).where(EventRequirement.event_id == event_id))
        payload = dict(existing.payload) if existing else {}
        payload.update(req_patch)
        if existing:
            existing.payload = payload
        else:
            session.add(EventRequirement(event_id=event_id, payload=payload))
        if payload.get("location"):
            ev.location = payload["location"]
        if payload.get("attendees"):
            ev.attendees = int(payload["attendees"])
        if payload.get("budget") is not None:
            ev.budget = float(payload["budget"])
        if payload.get("duration_days"):
            ev.duration_days = int(payload["duration_days"])
    await bump_version(session, ev, actor="user", action="update", summary="Updated event settings")
    await session.commit()
    await session.refresh(ev)
    return _event_out(ev)


@router.post("/events/{event_id}/duplicate", response_model=EventOut)
async def duplicate_event(event_id: str, session: AsyncSession = Depends(get_session)):
    ev = await session.get(Event, event_id)
    if not ev:
        raise HTTPException(404, "event not found")
    copy = Event(
        owner_id=ev.owner_id,
        name=f"{ev.name} (copy)",
        location=ev.location,
        start_date=ev.start_date,
        attendees=ev.attendees,
        duration_days=ev.duration_days,
        budget=ev.budget,
        currency=ev.currency,
        status="draft",
        user_request=ev.user_request,
        description=ev.description,
        objectives=list(ev.objectives or []),
        tags=list(ev.tags or []),
        deadline=ev.deadline,
        data_mode=ev.data_mode or "mock",
        event_state_version=0,
    )
    session.add(copy)
    await session.flush()
    add_activity(session, copy.id, actor="user", action="duplicate", summary=f"Duplicated from {ev.name}")
    await session.commit()
    await session.refresh(copy)
    return _event_out(copy)


@router.post("/events/{event_id}/archive", response_model=EventOut)
async def archive_event(event_id: str, session: AsyncSession = Depends(get_session)):
    ev = await session.get(Event, event_id)
    if not ev:
        raise HTTPException(404, "event not found")
    if ev.archived_at:
        return _event_out(ev)
    ev.archived_at = datetime.now(timezone.utc)
    ev.status = "archived"
    await bump_version(session, ev, actor="user", action="archive", summary="Archived event")
    await session.commit()
    await session.refresh(ev)
    return _event_out(ev)


@router.post("/events/{event_id}/restore", response_model=EventOut)
async def restore_event(event_id: str, session: AsyncSession = Depends(get_session)):
    ev = await session.get(Event, event_id)
    if not ev:
        raise HTTPException(404, "event not found")
    ev.archived_at = None
    if ev.status == "archived":
        ev.status = "draft"
    await bump_version(session, ev, actor="user", action="restore", summary="Restored event")
    await session.commit()
    await session.refresh(ev)
    return _event_out(ev)


@router.delete("/events/{event_id}")
async def delete_event(event_id: str, session: AsyncSession = Depends(get_session)):
    ev = await session.get(Event, event_id)
    if not ev:
        raise HTTPException(404, "event not found")
    budget_ids = list((await session.scalars(select(Budget.id).where(Budget.event_id == event_id))).all())
    if budget_ids:
        await session.execute(sql_delete(BudgetItem).where(BudgetItem.budget_id.in_(budget_ids)))
    for model in (
        EventRequirement,
        EventVenue,
        EventVendor,
        Budget,
        ScheduleItem,
        Task,
        Risk,
        AgentRun,
        Document,
        Simulation,
        ChatMessage,
        PlanJob,
        ActivityLog,
        Decision,
        PlanSnapshot,
        ResearchRecord,
    ):
        await session.execute(sql_delete(model).where(model.event_id == event_id))
    await session.delete(ev)
    await session.commit()
    return {"ok": True}


@router.post("/events/{event_id}/plan", response_model=PlanAccepted)
async def start_plan(event_id: str, body: PlanRequest | None = None, session: AsyncSession = Depends(get_session)):
    ev = await session.get(Event, event_id)
    if not ev:
        raise HTTPException(404, "event not found")
    body = body or PlanRequest()
    extra = {}
    if body.user_request:
        extra["user_request"] = body.user_request
        ev.user_request = body.user_request
        await session.commit()
    extra["data_mode"] = ev.data_mode or "mock"
    run_id = await worker.enqueue(event_id, force_over_budget=body.force_over_budget, extra=extra)
    asyncio.create_task(worker.safe_run(run_id))
    return PlanAccepted(run_id=run_id, status="queued")


@router.get("/events/{event_id}/agents")
async def list_agents(event_id: str, session: AsyncSession = Depends(get_session)):
    rows = (
        await session.scalars(select(AgentRun).where(AgentRun.event_id == event_id).order_by(AgentRun.created_at))
    ).all()
    return [
        {
            "id": r.id,
            "agent": r.agent,
            "status": r.status,
            "task": r.task,
            "input_summary": r.input_summary,
            "output_summary": r.output_summary,
            "timestamp": r.created_at,
            "duration_ms": r.duration_ms,
            "iteration": r.iteration,
            "errors": r.errors,
            "run_id": r.run_id,
        }
        for r in rows
    ]


@router.get("/events/{event_id}/agents/stream")
async def stream_agents(event_id: str, run_id: str | None = None):
    async def gen():
        async for payload in memory_bus.subscribe(event_id):
            if run_id and payload.get("run_id") and payload.get("run_id") != run_id:
                continue
            yield {"event": payload.get("type", "message"), "data": json.dumps(payload)}

    return EventSourceResponse(gen())


@router.get("/events/{event_id}/budget")
async def get_budget(event_id: str, session: AsyncSession = Depends(get_session)):
    ev = await get_event_loaded(session, event_id)
    if not ev:
        raise HTTPException(404)
    brow = ev.budgets[0] if ev.budgets else None
    if brow:
        return budget_out(ev, brow)
    snap = ev.plan_snapshot or {}
    return snap.get("budget") or {}


@router.get("/events/{event_id}/schedule")
async def get_schedule(event_id: str, session: AsyncSession = Depends(get_session)):
    ev = await get_event_loaded(session, event_id)
    if not ev:
        raise HTTPException(404)
    if ev.schedule_items:
        return schedule_out(list(ev.schedule_items))
    snap = ev.plan_snapshot or {}
    return snap.get("schedule") or {"items": [], "conflicts": []}


@router.get("/events/{event_id}/tasks")
async def get_tasks(event_id: str, session: AsyncSession = Depends(get_session)):
    ev = await get_event_loaded(session, event_id)
    if not ev:
        raise HTTPException(404)
    return [task_out(t) for t in ev.tasks]


@router.get("/events/{event_id}/risks")
async def get_risks(event_id: str, session: AsyncSession = Depends(get_session)):
    ev = await get_event_loaded(session, event_id)
    if not ev:
        raise HTTPException(404)
    if ev.risks:
        return [risk_out(r) for r in ev.risks]
    snap = ev.plan_snapshot or {}
    return [risk_out(r) for r in (snap.get("risks") or [])]


@router.get("/events/{event_id}/venues")
async def get_event_venues(event_id: str, session: AsyncSession = Depends(get_session)):
    ev = await get_event_loaded(session, event_id)
    if not ev:
        raise HTTPException(404)
    if ev.event_venues:
        return [venue_out(v) for v in ev.event_venues]
    snap = ev.plan_snapshot or {}
    return snap.get("venues") or []


@router.post("/events/{event_id}/venues/{venue_row_id}")
async def update_event_venue(
    event_id: str,
    venue_row_id: str,
    body: CandidateAction,
    session: AsyncSession = Depends(get_session),
):
    row = await session.get(EventVenue, venue_row_id)
    if not row or row.event_id != event_id:
        raise HTTPException(404)
    ev = await session.get(Event, event_id)
    if body.status:
        if body.status == "selected":
            others = (await session.scalars(select(EventVenue).where(EventVenue.event_id == event_id))).all()
            for other in others:
                if other.id != row.id and other.status == "selected":
                    other.status = "shortlist"
        row.status = body.status
    if body.notes is not None:
        row.notes = body.notes
    await bump_version(session, ev, actor="user", action="venue_status", summary=f"{row.name} → {row.status}")
    await session.commit()
    return venue_out(row)


@router.get("/events/{event_id}/vendors")
async def get_event_vendors(event_id: str, session: AsyncSession = Depends(get_session)):
    ev = await get_event_loaded(session, event_id)
    if not ev:
        raise HTTPException(404)
    if ev.event_vendors:
        return [vendor_out(v) for v in ev.event_vendors]
    snap = ev.plan_snapshot or {}
    return snap.get("vendors") or []


@router.post("/events/{event_id}/vendors")
async def add_event_vendor(event_id: str, body: VendorCreate, session: AsyncSession = Depends(get_session)):
    ev = await session.get(Event, event_id)
    if not ev:
        raise HTTPException(404)
    row = EventVendor(
        event_id=event_id,
        name=body.name,
        category=body.category,
        location=body.location,
        estimated_cost=body.estimated_cost,
        notes=body.notes,
        status="shortlist",
        source_tier="mock",
        provider="mock",
        requires_quote=True,
        price_type="estimated",
    )
    session.add(row)
    await bump_version(session, ev, actor="user", action="add_vendor", summary=f"Added custom vendor {body.name}")
    await session.commit()
    await session.refresh(row)
    return vendor_out(row)


@router.post("/events/{event_id}/vendors/{vendor_row_id}")
async def update_event_vendor(
    event_id: str,
    vendor_row_id: str,
    body: CandidateAction,
    session: AsyncSession = Depends(get_session),
):
    row = await session.get(EventVendor, vendor_row_id)
    if not row or row.event_id != event_id:
        raise HTTPException(404)
    ev = await session.get(Event, event_id)
    if body.status:
        row.status = body.status
    if body.notes is not None:
        row.notes = body.notes
    await bump_version(session, ev, actor="user", action="vendor_status", summary=f"{row.name} → {row.status}")
    await session.commit()
    return vendor_out(row)


@router.get("/events/{event_id}/decisions")
async def list_decisions(event_id: str, session: AsyncSession = Depends(get_session)):
    ev = await session.get(Event, event_id)
    if not ev:
        raise HTTPException(404)
    rows = (await session.scalars(select(Decision).where(Decision.event_id == event_id).order_by(Decision.created_at))).all()
    return [decision_out(r) for r in rows]


@router.post("/events/{event_id}/decisions/{decision_id}")
async def apply_decision(
    event_id: str,
    decision_id: str,
    body: DecisionApply,
    session: AsyncSession = Depends(get_session),
):
    row = await session.get(Decision, decision_id)
    if not row or row.event_id != event_id:
        raise HTTPException(404)
    ev = await session.get(Event, event_id)
    row.status = "chosen"
    row.chosen_option = body.option_id
    await bump_version(session, ev, actor="user", action="decide", summary=f"{row.problem} → {body.option_id}")
    await session.commit()
    return decision_out(row)


@router.get("/events/{event_id}/activity")
async def list_activity(event_id: str, session: AsyncSession = Depends(get_session)):
    ev = await get_event_loaded(session, event_id)
    if not ev:
        raise HTTPException(404)
    rows = sorted(ev.activity_logs or [], key=lambda r: r.at or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
    return [
        {
            "id": r.id,
            "at": r.at,
            "actor": r.actor,
            "action": r.action,
            "summary": r.summary,
            "payload": r.payload,
            "state_version": r.state_version,
        }
        for r in rows[:200]
    ]


@router.get("/venues")
async def list_venues(session: AsyncSession = Depends(get_session)):
    rows = (await session.scalars(select(Venue))).all()
    return [
        {
            "id": v.id,
            "name": v.name,
            "location": v.location,
            "capacity": v.capacity,
            "estimated_cost": v.estimated_cost,
            "facilities": v.facilities,
            "source_type": v.source_type,
            "source_tier": v.source_tier,
            "provider": v.provider,
            "price_type": v.price_type,
            "requires_quote": v.requires_quote,
            "last_checked_at": v.last_checked_at,
            "extra": v.extra,
        }
        for v in rows
    ]


@router.get("/vendors")
async def list_vendors(category: str | None = None, session: AsyncSession = Depends(get_session)):
    stmt = select(Vendor)
    if category:
        stmt = stmt.where(Vendor.category == category)
    rows = (await session.scalars(stmt)).all()
    return [
        {
            "id": v.id,
            "name": v.name,
            "category": v.category,
            "location": v.location,
            "estimated_cost": v.estimated_cost,
            "rating": v.rating,
            "source_type": v.source_type,
            "source_tier": v.source_tier,
            "provider": v.provider,
            "price_type": v.price_type,
            "requires_quote": v.requires_quote,
        }
        for v in rows
    ]


@router.post("/events/{event_id}/simulate")
async def simulate(event_id: str, body: SimulateIn, session: AsyncSession = Depends(get_session)):
    ev = await session.get(Event, event_id)
    if not ev:
        raise HTTPException(404)
    original = ev.plan_snapshot or {}
    state = load_state(ev)
    req = dict(original.get("requirements") or state.requirements or {})
    if not req.get("location"):
        req["location"] = ev.location
    if not req.get("attendees"):
        req["attendees"] = ev.attendees
    if not req.get("duration_days"):
        req["duration_days"] = ev.duration_days
    if not req.get("budget"):
        req["budget"] = ev.budget
    req.setdefault("currency", ev.currency)
    req.setdefault("event_type", state.requirements.get("event_type") or "event")
    change: dict = {}
    if body.attendees is not None:
        change["attendees"] = body.attendees
        req["attendees"] = body.attendees
    if body.budget is not None:
        change["budget"] = body.budget
        req["budget"] = body.budget
    if body.duration_days is not None:
        change["duration_days"] = body.duration_days
        req["duration_days"] = body.duration_days
    if body.format:
        change["format"] = body.format
        req["format"] = body.format
    if body.vip_count is not None:
        change["vip_count"] = body.vip_count
        req["vip_count"] = body.vip_count
    request = (
        f"Plan a {req.get('duration_days')}-day {req.get('event_type')} in {req.get('location')} "
        f"for {req.get('attendees')} attendees with a {req.get('budget')} {req.get('currency') or 'EGP'} budget."
    )
    from app.graph.deps import build_deps

    use_mock = (ev.data_mode or "mock") != "live"
    result = await run_graph_memory(
        request,
        extra={"requirements": req, "user_request": request, "event_id": event_id},
        deps=build_deps(use_mock=use_mock),
    )
    new_snap = snapshot_state(result)
    orig_total = (original.get("budget") or {}).get("subtotal")
    new_total = (new_snap.get("budget") or {}).get("subtotal")
    cost_delta = None
    if orig_total is not None and new_total is not None:
        cost_delta = round(new_total - orig_total, 2)
    impacted = list(change.keys())
    if body.venue_unavailable:
        impacted.append("venues")
    impact = impact_diff(original, new_snap, change)
    sim = {
        "original": original,
        "change": change or {"venue_unavailable": body.venue_unavailable},
        "impacted": impacted or ["venues", "budget", "schedule", "risks"],
        "new_plan": new_snap,
        "cost_difference": cost_delta,
        "new_risks": new_snap.get("risks"),
        "impact": impact,
        "base_version": int(ev.event_state_version or 0),
        "status": "pending",
    }
    row = Simulation(
        event_id=event_id,
        change=sim["change"],
        original_snapshot=original,
        result_snapshot=new_snap,
        base_version=sim["base_version"],
        status="pending",
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)
    sim["id"] = row.id
    return sim


@router.post("/events/{event_id}/simulate/{sim_id}/apply")
async def apply_simulation(event_id: str, sim_id: str, session: AsyncSession = Depends(get_session)):
    ev = await session.get(Event, event_id)
    row = await session.get(Simulation, sim_id)
    if not ev or not row or row.event_id != event_id:
        raise HTTPException(404)
    live = int(ev.event_state_version or 0)
    if live != int(row.base_version or 0):
        row.status = "stale"
        await session.commit()
        raise HTTPException(
            409,
            "This simulation was created from an older plan. Recalculate before applying.",
        )
    row.status = "applied"
    change = row.change or {}
    if change.get("attendees"):
        ev.attendees = int(change["attendees"])
    if change.get("budget") is not None:
        ev.budget = float(change["budget"])
    if change.get("duration_days"):
        ev.duration_days = int(change["duration_days"])
    state = load_state(ev)
    if change.get("attendees"):
        state.requirements["attendees"] = ev.attendees
    if change.get("budget") is not None:
        state.requirements["budget"] = ev.budget
    if change.get("duration_days"):
        state.requirements["duration_days"] = ev.duration_days
    persist_state(ev, state)
    await bump_version(session, ev, actor="user", action="apply_sim", summary="Applied what-if to live event state")
    extra = {
        "user_request": user_request_from_state(state),
        "requirements": requirements_for_graph(state),
        "data_mode": ev.data_mode or "mock",
    }
    await session.commit()
    run_id = await worker.enqueue(event_id, extra=extra)
    asyncio.create_task(worker.safe_run(run_id))
    return {"ok": True, "run_id": run_id, "event_state_version": ev.event_state_version}


@router.post("/events/{event_id}/simulate/{sim_id}/discard")
async def discard_simulation(event_id: str, sim_id: str, session: AsyncSession = Depends(get_session)):
    row = await session.get(Simulation, sim_id)
    if not row or row.event_id != event_id:
        raise HTTPException(404)
    row.status = "discarded"
    await session.commit()
    return {"ok": True}


@router.get("/events/{event_id}/chat")
async def list_chat(event_id: str, session: AsyncSession = Depends(get_session)):
    rows = (
        await session.scalars(
            select(ChatMessage).where(ChatMessage.event_id == event_id).order_by(ChatMessage.created_at)
        )
    ).all()
    return [
        {
            "role": r.role,
            "content": r.content,
            "created_at": r.created_at,
            "extra": r.extra,
            "actions": (r.extra or {}).get("actions") if r.extra else None,
            "phase": (r.extra or {}).get("phase") if r.extra else None,
            "policy": (r.extra or {}).get("policy") if r.extra else None,
        }
        for r in rows
    ]


@router.post("/chat", response_model=ChatOut)
async def chat(body: ChatIn, session: AsyncSession = Depends(get_session)):
    text = (body.message or "").strip()
    action_id = body.action_id
    event_id = body.event_id
    ev = await session.get(Event, event_id) if event_id else None
    understood = await understand_message(text, action_id=action_id)

    if ev is None and understood.intent in {"plan", "edit", "confirm", "what_if", "decide"}:
        ev = Event(
            owner_id=DEMO_USER_ID,
            name=(text or "New event")[:80],
            user_request=text or None,
            status="draft",
            event_state_version=0,
        )
        session.add(ev)
        await session.commit()
        await session.refresh(ev)
        event_id = ev.id

    if event_id and not is_prompt_chip(action_id, text):
        session.add(
            ChatMessage(
                event_id=event_id,
                role="user",
                content=text or (action_id or ""),
                extra={"action_id": action_id} if action_id else None,
            )
        )
        await session.commit()

    state = load_state(ev)
    decision = policy(state, understood, event=ev)
    run_id = None
    simulation = None

    if decision.policy == "RUN" and ev:
        persist_state(ev, decision.state)
        ev.status = "planning"
        add_activity(session, ev.id, actor="copilot", action="confirm", summary="Brief confirmed")
        await session.commit()
        extra = {
            "user_request": user_request_from_state(decision.state),
            "requirements": requirements_for_graph(decision.state),
            "data_mode": ev.data_mode or "mock",
        }
        pending = decision.state.pending_apply or {}
        if pending.get("replan_mode"):
            extra["replan_mode"] = pending["replan_mode"]
        try:
            run_id = await worker.enqueue(event_id, extra=extra)
            asyncio.create_task(worker.safe_run(run_id))
        except Exception:
            import structlog

            structlog.get_logger().exception("plan_enqueue_failed", event_id=event_id)
            decision.state.phase = "confirm"
            decision.state.graph_status = "idle"
            decision.state.available_actions = _confirm_actions()
            decision.policy = "CONFIRM"
            decision.phase = "confirm"
            decision.actions = decision.state.available_actions
            persist_state(ev, decision.state)
            ev.status = "draft"
            await session.commit()
    elif decision.policy == "SIMULATE" and ev:
        patch = decision.simulate_patch or {}
        sim_body = SimulateIn(
            attendees=patch.get("attendees"),
            budget=patch.get("budget"),
            duration_days=patch.get("duration_days"),
            venue_unavailable=bool(patch.get("venue_unavailable")),
            format=patch.get("format"),
            vip_count=patch.get("vip_count"),
            description=text,
        )
        simulation = await simulate(event_id, sim_body, session)
        decision.state.last_simulation = {
            "id": simulation.get("id"),
            "change": simulation.get("change"),
            "cost_difference": simulation.get("cost_difference"),
            "impacted": simulation.get("impacted"),
            "impact": simulation.get("impact"),
            "base_version": simulation.get("base_version"),
        }
        decision.answer_facts = {
            "change": simulation.get("change"),
            "cost_difference": simulation.get("cost_difference"),
            "impact": simulation.get("impact"),
            "new_risks": [
                r.get("title")
                for r in (simulation.get("new_risks") or [])[:3]
                if isinstance(r, dict)
            ],
        }
        persist_state(ev, decision.state)
        await session.commit()
    elif ev:
        persist_state(ev, decision.state)
        await session.commit()

    message = await speak(decision)
    actions = [a.model_dump() for a in decision.actions]
    await _save_assistant(
        session,
        event_id,
        message,
        extra={"actions": actions, "phase": decision.phase, "policy": decision.policy},
    )
    return ChatOut(
        reply=message,
        intent=understood.intent,
        run_id=run_id,
        simulation=simulation,
        phase=decision.phase,
        policy=decision.policy,
        missing_fields=decision.missing_fields,
        actions=[ChatActionOut.model_validate(a) for a in actions],
    )


async def _save_assistant(
    session: AsyncSession,
    event_id: str | None,
    reply: str,
    extra: dict | None = None,
) -> None:
    if not event_id:
        return
    session.add(ChatMessage(event_id=event_id, role="assistant", content=reply, extra=extra))
    await session.commit()


@router.get("/health")
async def health():
    return {"ok": True, "time": datetime.now(timezone.utc).isoformat()}


@router.get("/health/ready")
async def ready(session: AsyncSession = Depends(get_session)):
    await session.execute(text("SELECT 1"))
    return {"ok": True, "db": True}

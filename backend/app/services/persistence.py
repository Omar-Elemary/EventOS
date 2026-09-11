from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.enums import product_status, risk_score
from app.models import (
    AgentRun,
    Budget,
    BudgetItem,
    Decision,
    Event,
    EventRequirement,
    EventVenue,
    EventVendor,
    PlanSnapshot,
    Risk,
    ScheduleItem,
    Task,
)
from app.services.activity import add_activity, utcnow


def _parse_dt(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    return utcnow()


def _str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    if hasattr(value, "value"):
        return str(value.value)
    return str(value)


def _task_phase(title: str) -> str:
    blob = title.lower()
    if any(x in blob for x in ("load-in", "load in", "install", "setup", "registration setup")):
        return "setup" if "load" not in blob else "load_in"
    if any(x in blob for x in ("teardown", "strike", "load-out", "load out")):
        return "teardown"
    if any(x in blob for x in ("setup", "booking", "confirm")):
        return "setup"
    return "event"


async def persist_plan(session: AsyncSession, event_id: str, snapshot: dict[str, Any]) -> None:
    event = await session.get(Event, event_id)
    if not event:
        return

    graph_status = snapshot.get("status") or event.status
    event.status = product_status(graph_status)
    event.updated_at = utcnow()
    event.plan_snapshot = {**snapshot, "event_state_version": event.event_state_version + 1}

    req = snapshot.get("requirements")
    if req:
        existing = await session.scalar(select(EventRequirement).where(EventRequirement.event_id == event_id))
        if existing:
            existing.payload = req
        else:
            session.add(EventRequirement(event_id=event_id, payload=req))
        event.attendees = req.get("attendees") or event.attendees
        event.duration_days = req.get("duration_days") or event.duration_days
        event.budget = req.get("budget") if req.get("budget") is not None else event.budget
        event.location = req.get("location") or event.location
        if req.get("description"):
            event.description = req.get("description")
        if req.get("objectives"):
            event.objectives = req.get("objectives")
        if req.get("tags"):
            event.tags = req.get("tags")

    await _merge_venues(session, event, snapshot.get("venues") or [])
    await _merge_vendors(session, event, snapshot.get("vendors") or [])
    await _merge_budget(session, event, snapshot.get("budget"))
    await _merge_schedule(session, event, snapshot.get("schedule") or {})
    await _merge_risks(session, event, snapshot.get("risks") or [])
    await _merge_decisions(session, event, snapshot.get("critic_result") or {})

    event.event_state_version = int(event.event_state_version or 0) + 1
    session.add(
        PlanSnapshot(
            event_id=event_id,
            version=event.event_state_version,
            snapshot=event.plan_snapshot,
        )
    )
    add_activity(
        session,
        event_id,
        actor="planner",
        action="persist_state",
        summary=f"Event state v{event.event_state_version} ({event.status})",
        payload={"status": event.status, "graph_status": graph_status},
        state_version=event.event_state_version,
    )
    await session.commit()


async def _merge_venues(session: AsyncSession, event: Event, venues: list[dict[str, Any]]) -> None:
    rows = (await session.scalars(select(EventVenue).where(EventVenue.event_id == event.id))).all()
    by_name = {r.name.lower(): r for r in rows}
    now = utcnow()
    selected_name = None
    for raw in venues:
        name = str(raw.get("name") or "")
        if not name:
            continue
        if raw.get("selected"):
            selected_name = name
        row = by_name.get(name.lower())
        locked = row.status in {"rejected"} if row else False
        payload = dict(
            name=name,
            location=raw.get("location") or "",
            capacity=int(raw.get("capacity") or 0),
            estimated_cost=float(raw.get("estimated_cost") or 0),
            facilities=raw.get("facilities") or [],
            suitability_score=float(raw.get("suitability_score") or 50),
            pros=raw.get("pros") or [],
            cons=raw.get("cons") or [],
            source_url=raw.get("source_url") or "",
            source_tier=_str(raw.get("source_tier"), "mock"),
            confidence=float(raw.get("confidence") or 0.7),
            last_checked_at=now,
            price_type=_str(raw.get("price_type"), "estimated"),
            requires_quote=bool(raw.get("requires_quote")),
            provider=_str(raw.get("provider"), "mock"),
            distance_km=raw.get("distance_km"),
            extra={"source": raw.get("source"), "source_type": _str(raw.get("source_type"), "mock")},
        )
        if row:
            if not locked:
                for key, val in payload.items():
                    setattr(row, key, val)
        else:
            row = EventVenue(event_id=event.id, status="considered", **payload)
            session.add(row)
            by_name[name.lower()] = row
    if selected_name:
        for row in by_name.values():
            if row.status == "rejected":
                continue
            row.status = "selected" if row.name == selected_name else (
                row.status if row.status == "shortlist" else "considered"
            )
    add_activity(
        session,
        event.id,
        actor="venue_agent",
        action="upsert_venues",
        summary=f"Added {len(venues)} venue candidates",
        payload={"count": len(venues), "selected": selected_name},
        state_version=event.event_state_version,
    )


async def _merge_vendors(session: AsyncSession, event: Event, vendors: list[dict[str, Any]]) -> None:
    rows = (await session.scalars(select(EventVendor).where(EventVendor.event_id == event.id))).all()
    by_key = {(r.name.lower(), r.category): r for r in rows}
    now = utcnow()
    for raw in vendors:
        name = str(raw.get("name") or "")
        category = _str(raw.get("category"))
        if not name:
            continue
        key = (name.lower(), category)
        row = by_key.get(key)
        services = raw.get("services") or []
        payload = dict(
            name=name,
            category=category,
            location=raw.get("location") or "",
            estimated_cost=float(raw.get("estimated_cost") or 0),
            rating=float(raw.get("rating") or 4),
            services=services,
            source_url=raw.get("source_url") or "",
            source_tier=_str(raw.get("source_tier"), "mock"),
            confidence=float(raw.get("confidence") or 0.7),
            last_checked_at=now,
            price_type=_str(raw.get("price_type"), "estimated"),
            requires_quote=bool(raw.get("requires_quote")),
            provider=_str(raw.get("provider"), "mock"),
        )
        selected = bool(raw.get("selected", True))
        if row:
            if row.status != "rejected":
                for k, val in payload.items():
                    setattr(row, k, val)
                if selected and row.status != "shortlist":
                    row.status = "selected"
        else:
            row = EventVendor(
                event_id=event.id,
                status="selected" if selected else "considered",
                **payload,
            )
            session.add(row)
            by_key[key] = row
    add_activity(
        session,
        event.id,
        actor="vendor_agent",
        action="upsert_vendors",
        summary=f"Added {len(vendors)} vendor candidates",
        payload={"count": len(vendors)},
        state_version=event.event_state_version,
    )


async def _merge_budget(session: AsyncSession, event: Event, budget: dict[str, Any] | None) -> None:
    if not budget:
        return
    brow = await session.scalar(select(Budget).where(Budget.event_id == event.id).options(selectinload(Budget.items)))
    existing_items = {(i.category, i.description): i for i in (brow.items if brow else [])}
    if not brow:
        brow = Budget(event_id=event.id, total_budget=budget.get("total_budget") or event.budget)
        session.add(brow)
        await session.flush()
    brow.total_budget = budget.get("total_budget") or event.budget
    brow.currency = budget.get("currency") or event.currency
    brow.subtotal = budget.get("subtotal") or 0
    brow.contingency = budget.get("contingency") or 0
    brow.remaining = budget.get("remaining") or 0
    brow.committed = budget.get("committed") or 0
    brow.estimated = budget.get("estimated") or 0
    seen: set[tuple[str, str]] = set()
    for it in budget.get("items") or []:
        key = (it.get("category") or "", it.get("description") or "")
        seen.add(key)
        row = existing_items.get(key)
        if row:
            row.estimated_cost = it.get("estimated_cost") or 0
            if row.status == "estimated":
                row.actual_cost = it.get("actual_cost") or row.actual_cost
            if it.get("vendor_name"):
                row.vendor_name = it.get("vendor_name")
        else:
            session.add(
                BudgetItem(
                    budget_id=brow.id,
                    category=it.get("category") or "",
                    description=it.get("description") or "",
                    estimated_cost=it.get("estimated_cost") or 0,
                    actual_cost=it.get("actual_cost") or 0,
                    status=it.get("status") or "estimated",
                    vendor_name=it.get("vendor_name"),
                    due_date=it.get("due_date"),
                    deposit=it.get("deposit") or 0,
                )
            )
    for key, row in existing_items.items():
        if key not in seen and row.status in {"committed", "paid"}:
            continue
        if key not in seen and row.status == "estimated":
            await session.delete(row)
    add_activity(
        session,
        event.id,
        actor="budget_agent",
        action="calculate_budget",
        summary=(
            f"Calculated projected cost: {brow.currency} {brow.subtotal + brow.contingency:,.0f}"
        ),
        payload={"subtotal": brow.subtotal, "remaining": brow.remaining},
        state_version=event.event_state_version,
    )


async def _merge_schedule(session: AsyncSession, event: Event, schedule: dict[str, Any]) -> None:
    existing = (await session.scalars(select(ScheduleItem).where(ScheduleItem.event_id == event.id))).all()
    for row in existing:
        await session.delete(row)
    items = schedule.get("items") or []
    for it in items:
        session.add(
            ScheduleItem(
                event_id=event.id,
                title=it.get("title") or "",
                start_time=_parse_dt(it.get("start_time")),
                end_time=_parse_dt(it.get("end_time")),
                location=it.get("location"),
                responsible_vendor=it.get("responsible_vendor"),
                depends_on=it.get("depends_on") or [],
                conflicts=it.get("conflicts") or [],
            )
        )
    tasks = (await session.scalars(select(Task).where(Task.event_id == event.id))).all()
    by_title = {t.title.lower(): t for t in tasks}
    for it in items:
        title = it.get("title") or ""
        row = by_title.get(title.lower())
        start = _parse_dt(it.get("start_time"))
        end = _parse_dt(it.get("end_time"))
        if row:
            row.start_time = start
            row.end_time = end
            row.depends_on = it.get("depends_on") or row.depends_on
            if not row.owner:
                row.owner = it.get("responsible_vendor")
        else:
            session.add(
                Task(
                    event_id=event.id,
                    title=title,
                    status="open",
                    start_time=start,
                    end_time=end,
                    depends_on=it.get("depends_on") or [],
                    owner=it.get("responsible_vendor"),
                    phase=_task_phase(title),
                )
            )


async def _merge_risks(session: AsyncSession, event: Event, risks: list[dict[str, Any]]) -> None:
    rows = (await session.scalars(select(Risk).where(Risk.event_id == event.id))).all()
    by_title = {r.title.lower(): r for r in rows}
    seen: set[str] = set()
    for raw in risks:
        title = str(raw.get("title") or "")
        if not title:
            continue
        seen.add(title.lower())
        sev = _str(raw.get("severity"), "medium")
        prob = float(raw.get("probability") or 0)
        score = float(raw.get("score") or 0) or risk_score(prob, sev)
        payload = dict(
            title=title,
            severity=sev,
            probability=prob,
            impact=raw.get("impact") or "",
            description=raw.get("description") or "",
            mitigation=raw.get("mitigation") or "",
            score=score,
            trigger=raw.get("trigger") or raw.get("description"),
            ai_recommendation=raw.get("ai_recommendation") or raw.get("mitigation"),
            explanation=raw.get("explanation") or raw.get("description") or "",
            solutions=raw.get("solutions") or [],
        )
        row = by_title.get(title.lower())
        if row:
            for k, val in payload.items():
                setattr(row, k, val)
            if not row.owner and raw.get("owner"):
                row.owner = raw.get("owner")
        else:
            session.add(
                Risk(
                    event_id=event.id,
                    owner=raw.get("owner") or "Operations",
                    status=raw.get("status") or "open",
                    **payload,
                )
            )
    for title, row in by_title.items():
        if title not in seen and row.status == "open":
            await session.delete(row)


async def _merge_decisions(session: AsyncSession, event: Event, critic: dict[str, Any]) -> None:
    if critic.get("approved"):
        add_activity(
            session,
            event.id,
            actor="critic",
            action="approved",
            summary="Approved plan",
            payload={"score": critic.get("score")},
            state_version=event.event_state_version,
        )
        return
    issues = critic.get("issues") or []
    if not issues:
        return
    add_activity(
        session,
        event.id,
        actor="critic",
        action="rejected",
        summary="Rejected plan: " + "; ".join(i.get("title") or i.get("message") or "" for i in issues[:2]),
        payload={"issues": issues},
        state_version=event.event_state_version,
    )
    open_rows = (
        await session.scalars(select(Decision).where(Decision.event_id == event.id, Decision.status == "open"))
    ).all()
    open_problems = {r.problem for r in open_rows}
    for issue in issues:
        problem = issue.get("title") or issue.get("message") or "Plan issue"
        if problem in open_problems:
            continue
        itype = issue.get("issue_type") or "other"
        options, consequences, rec = _decision_template(itype, issue)
        session.add(
            Decision(
                event_id=event.id,
                problem=problem,
                options=options,
                consequences=consequences,
                recommendation=rec,
                status="open",
            )
        )


def _decision_template(itype: str, issue: dict[str, Any]) -> tuple[list, list, str]:
    message = issue.get("message") or ""
    if itype == "budget":
        return (
            [
                {"id": "cheaper_venue", "label": "Choose cheaper venue"},
                {"id": "raise_budget", "label": "Increase budget"},
            ],
            [
                "Cheaper venue lowers spend, may reduce prestige or capacity headroom.",
                "Raising budget unblocks contracting but spends contingency.",
            ],
            "Start with a cheaper suitable venue; raise budget only if capacity would suffer.",
        )
    if itype == "venue_capacity":
        return (
            [
                {"id": "cheaper_venue", "label": "Choose larger / cheaper venue"},
                {"id": "keep_draft", "label": "Keep current venue"},
            ],
            ["A larger hall seats everyone.", "Keeping the current hall risks crowding."],
            "Move to a hall that fits attendees with 10% headroom.",
        )
    if itype == "schedule":
        return (
            [
                {"id": "registration_foyer", "label": "Move registration"},
                {"id": "proceed", "label": "Keep current layout"},
            ],
            ["Foyer registration removes the AV clash.", "Keeping the layout leaves the conflict."],
            "Put registration in the foyer so AV can occupy the hall.",
        )
    if itype == "vendors":
        return (
            [
                {"id": "search_broader", "label": "Search again"},
                {"id": "add_vendor_manual", "label": "Add vendor manually"},
                {"id": "continue_without", "label": "Continue without this category"},
            ],
            ["Broader search may find coverage.", "Manual add is fastest if you have a contact."],
            message or "Shortlist an alternative vendor or search again.",
        )
    return (
        [
            {"id": "proceed", "label": "Retry planning"},
            {"id": "keep_draft", "label": "Keep this draft"},
        ],
        [message or "Replanning may resolve the issue."],
        message or "Review the critic issue and choose a path.",
    )


async def persist_agent_run(session: AsyncSession, record: dict[str, Any]) -> None:
    session.add(
        AgentRun(
            event_id=record["event_id"],
            run_id=record["run_id"],
            correlation_id=record["correlation_id"],
            agent=record["agent"],
            status=record["status"],
            task=record.get("task", ""),
            input_summary=record.get("input_summary", ""),
            output_summary=record.get("output_summary", ""),
            iteration=record.get("iteration", 0),
            duration_ms=record.get("duration_ms", 0),
            errors=record.get("errors") or [],
        )
    )
    actor = record["agent"] if record["agent"] in {"critic", "copilot"} else f"{record['agent']}_agent"
    add_activity(
        session,
        record["event_id"],
        actor=actor,
        action=record["status"],
        summary=record.get("output_summary") or record.get("task") or record["agent"],
        payload={"errors": record.get("errors") or [], "duration_ms": record.get("duration_ms", 0)},
        state_version=0,
    )
    await session.commit()


async def bump_version(session: AsyncSession, event: Event, *, actor: str, action: str, summary: str) -> int:
    event.event_state_version = int(event.event_state_version or 0) + 1
    event.updated_at = utcnow()
    add_activity(
        session,
        event.id,
        actor=actor,
        action=action,
        summary=summary,
        state_version=event.event_state_version,
    )
    return event.event_state_version


async def get_event_loaded(session: AsyncSession, event_id: str) -> Event | None:
    return await session.scalar(
        select(Event)
        .options(
            selectinload(Event.requirements),
            selectinload(Event.budgets).selectinload(Budget.items),
            selectinload(Event.schedule_items),
            selectinload(Event.tasks),
            selectinload(Event.risks),
            selectinload(Event.event_venues),
            selectinload(Event.event_vendors),
            selectinload(Event.decisions),
            selectinload(Event.activity_logs),
            selectinload(Event.agent_runs),
            selectinload(Event.chat_messages),
        )
        .where(Event.id == event_id)
    )

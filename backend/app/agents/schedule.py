from datetime import datetime, timedelta, timezone

from app.domain.models import EventRequirements, Schedule, ScheduleItem, VenueCandidate
from app.domain.state import EventState
from app.graph.deps import GraphDeps
from app.graph.wrapper import run_agent_node


def _req(state: EventState) -> EventRequirements:
    raw = state["requirements"]
    return raw if isinstance(raw, EventRequirements) else EventRequirements.model_validate(raw)


def _selected_venue(state: EventState) -> VenueCandidate | None:
    for v in state.get("venues") or []:
        vv = v if isinstance(v, VenueCandidate) else VenueCandidate.model_validate(v)
        if vv.selected:
            return vv
    return None


async def _logic(state: EventState, deps: GraphDeps) -> dict:
    req = _req(state)
    venue = _selected_venue(state)
    loc = venue.name if venue else req.location
    start = req.preferred_date or datetime(2026, 11, 15, 8, 0, tzinfo=timezone.utc)
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    items: list[ScheduleItem] = []
    idx = 0

    def add(title: str, day: int, h0: int, m0: int, h1: int, m1: int, deps_ids: list[str], room: str | None = None) -> str:
        nonlocal idx
        idx += 1
        sid = f"s{idx}"
        d0 = start + timedelta(days=day)
        items.append(
            ScheduleItem(
                id=sid,
                title=title,
                start_time=d0.replace(hour=h0, minute=m0),
                end_time=d0.replace(hour=h1, minute=m1),
                location=room or loc,
                depends_on=deps_ids,
            )
        )
        return sid

    hall = loc
    foyer = f"{loc} foyer" if loc else "Foyer"
    dining = f"{loc} dining" if loc else "Dining"
    av = add("AV Setup", 0, 7, 0, 8, 30, [], hall)
    reh = add("Speaker Rehearsal", 0, 8, 30, 9, 30, [av], hall)
    add("Registration", 0, 8, 0, 9, 30, [], foyer)
    key = add("Keynote", 0, 9, 30, 11, 0, [reh, av], hall)
    add("Coffee Break", 0, 11, 0, 11, 30, [key], foyer)
    add("Session Block A", 0, 11, 30, 13, 0, [key], hall)
    add("Catering Lunch", 0, 13, 0, 14, 0, [], dining)
    add("Session Block B", 0, 14, 0, 16, 30, [], hall)
    add("Networking Reception", 0, 16, 30, 18, 0, [], foyer)

    for day in range(1, req.duration_days):
        add(f"Day {day + 1} Registration", day, 8, 30, 9, 30, [], foyer)
        add(f"Day {day + 1} Morning Sessions", day, 9, 30, 12, 30, [], hall)
        add(f"Day {day + 1} Lunch", day, 12, 30, 13, 30, [], dining)
        add(f"Day {day + 1} Afternoon Sessions", day, 13, 30, 16, 30, [], hall)

    last_day = req.duration_days - 1
    tear = add("Teardown", last_day, 17, 0, 19, 0, [], hall)

    # On first build with replan_mode schedule, avoid conflicts; if iteration 0 we keep valid schedule
    if state.get("replan_mode") != "schedule" and state.get("force_schedule_conflict"):
        # overlap keynote and rehearsal in same room
        items[1] = items[1].model_copy(update={"end_time": items[3].end_time})

    draft = Schedule(items=items)
    checked = await deps.tools.schedule_conflict_checker.execute(draft)
    schedule = Schedule(items=checked.items, conflicts=checked.conflicts)

    if schedule.conflicts:
        # Replan: push overlapping items into distinct rooms
        for it in schedule.items:
            if "Registration" in it.title or "Coffee" in it.title or "Networking" in it.title:
                it.location = foyer
            elif "Lunch" in it.title or "Catering" in it.title:
                it.location = dining
            it.conflicts = []
        checked = await deps.tools.schedule_conflict_checker.execute(Schedule(items=schedule.items))
        schedule = Schedule(items=checked.items, conflicts=checked.conflicts)

    return {
        "schedule": schedule,
        "_output_summary": f"{len(schedule.items)} sessions; {len(schedule.conflicts)} conflicts; teardown={tear}",
    }


async def schedule_node(state: EventState, deps: GraphDeps) -> dict:
    req = _req(state)
    return await run_agent_node(
        "schedule",
        "Build timeline with dependencies",
        state,
        deps,
        _logic,
        input_summary=f"{req.duration_days}-day program",
    )

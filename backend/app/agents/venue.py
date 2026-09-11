from app.domain.models import EventRequirements
from app.domain.state import EventState
from app.graph.deps import GraphDeps
from app.graph.wrapper import run_agent_node
from app.services.research import research_venues


def _req(state: EventState) -> EventRequirements:
    raw = state["requirements"]
    return raw if isinstance(raw, EventRequirements) else EventRequirements.model_validate(raw)


async def _logic(state: EventState, deps: GraphDeps) -> dict:
    req = _req(state)
    force = state.get("replan_mode") == "venue"
    venues, cached = await research_venues(deps, req, event_id=state.get("event_id"), force=force)
    if not venues:
        return {"venues": [], "_output_summary": "No venues found for this brief"}
    prev = state.get("venues") or []
    prev_selected = next((v for v in prev if getattr(v, "selected", False)), None)
    for v in venues:
        v.selected = False
    fitting = [v for v in venues if v.capacity >= req.attendees]
    pool = fitting or venues
    cap = max(req.budget * (0.30 if req.prefer_cheaper else 0.45), 1)
    affordable = [v for v in pool if v.estimated_cost <= cap]
    if (state.get("replan_mode") == "venue" or req.prefer_cheaper) and prev_selected:
        pool = [v for v in pool if v.name != prev_selected.name] or pool
        affordable = [v for v in pool if v.estimated_cost <= cap]
    pick = min(affordable or pool, key=lambda v: (v.estimated_cost, -v.suitability_score))
    pick.selected = True
    selected = next((v for v in venues if v.selected), None)
    name = selected.name if selected else "none"
    cap = selected.capacity if selected else 0
    origin = "cached research" if cached else ("live search" if not deps.tools.use_mock else "mock catalog")
    return {
        "venues": venues,
        "_output_summary": f"Selected {name} (capacity {cap}) from {len(venues)} venues ({origin})",
    }


async def venue_node(state: EventState, deps: GraphDeps) -> dict:
    req = _req(state)
    return await run_agent_node(
        "venue",
        "Search and score venues",
        state,
        deps,
        _logic,
        input_summary=f"{req.attendees} attendees in {req.location}",
    )

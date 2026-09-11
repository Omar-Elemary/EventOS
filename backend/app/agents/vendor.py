from app.domain.enums import VendorCategory
from app.domain.models import EventRequirements
from app.domain.state import EventState
from app.graph.deps import GraphDeps
from app.graph.wrapper import run_agent_node
from app.services.research import research_vendors

CORE_CATEGORIES = [
    VendorCategory.catering,
    VendorCategory.av,
    VendorCategory.photography,
    VendorCategory.security,
    VendorCategory.transportation,
    VendorCategory.staffing,
]

EXTRA_CATEGORIES = [
    VendorCategory.videography,
    VendorCategory.decoration,
    VendorCategory.lighting,
    VendorCategory.entertainment,
]


def _req(state: EventState) -> EventRequirements:
    raw = state["requirements"]
    return raw if isinstance(raw, EventRequirements) else EventRequirements.model_validate(raw)


async def _logic(state: EventState, deps: GraphDeps) -> dict:
    req = _req(state)
    cats = list(CORE_CATEGORIES)
    if int(state.get("iteration") or 0) == 0 and state.get("replan_mode") is None:
        cats = CORE_CATEGORIES + EXTRA_CATEGORIES
    selected = []
    cached_any = False
    force = state.get("replan_mode") == "vendor"
    for cat in cats:
        found, cached = await research_vendors(
            deps, req, cat, event_id=state.get("event_id"), force=force
        )
        cached_any = cached_any or cached
        if found:
            pick = found[0]
            pick.selected = True
            selected.append(pick)
    origin = "cached research" if cached_any else ("live search" if not deps.tools.use_mock else "mock catalog")
    return {
        "vendors": selected,
        "_output_summary": f"Selected {len(selected)} vendors across {len(cats)} categories ({origin})",
    }


async def vendor_node(state: EventState, deps: GraphDeps) -> dict:
    req = _req(state)
    return await run_agent_node(
        "vendor",
        "Source vendors by category",
        state,
        deps,
        _logic,
        input_summary=f"Location {req.location}, budget {req.budget}",
    )

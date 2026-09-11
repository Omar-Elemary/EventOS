from app.domain.models import (
    BudgetCalculationInput,
    BudgetItem,
    EventRequirements,
    VenueCandidate,
)
from app.domain.state import EventState
from app.graph.deps import GraphDeps
from app.graph.wrapper import run_agent_node
from app.services.research import research_fx


def _req(state: EventState) -> EventRequirements:
    raw = state["requirements"]
    return raw if isinstance(raw, EventRequirements) else EventRequirements.model_validate(raw)


def _venues(state: EventState) -> list[VenueCandidate]:
    raw = state.get("venues") or []
    out = []
    for v in raw:
        out.append(v if isinstance(v, VenueCandidate) else VenueCandidate.model_validate(v))
    return out


async def _logic(state: EventState, deps: GraphDeps) -> dict:
    req = _req(state)
    venues = _venues(state)
    selected = next((v for v in venues if v.selected), venues[0] if venues else None)
    items: list[BudgetItem] = []
    if selected:
        items.append(
            BudgetItem(
                category="venue",
                description=selected.name,
                estimated_cost=selected.estimated_cost,
            )
        )
    vendors = state.get("vendors") or []
    for vd in vendors:
        cat = vd.category.value if hasattr(vd.category, "value") else str(vd.category)
        if state.get("replan_mode") == "budget" and cat in {"entertainment", "lighting", "videography"}:
            continue
        items.append(
            BudgetItem(category=cat, description=vd.name, estimated_cost=float(vd.estimated_cost))
        )

    if state.get("force_over_budget") and state.get("replan_mode") != "budget":
        items.append(BudgetItem(category="production", description="Forced premium overlay (test)", estimated_cost=50000))

    currency = req.currency
    if currency != "USD":
        converted_items = []
        for it in items:
            conv = await research_fx(
                deps,
                it.estimated_cost,
                "USD",
                currency,
                event_id=state.get("event_id"),
            )
            converted_items.append(it.model_copy(update={"estimated_cost": conv.converted}))
        items = converted_items

    result = await deps.tools.budget_calculator.execute(
        BudgetCalculationInput(total_budget=req.budget, currency=currency, items=items)
    )
    if result.over_budget:
        cheaper = sorted(
            [v for v in venues if v.capacity >= req.attendees] or venues,
            key=lambda v: v.estimated_cost,
        )
        if cheaper and (not selected or selected.estimated_cost > req.budget * 0.4 or state.get("replan_mode") == "budget"):
            selected = cheaper[0]
            items = [i for i in items if i.category != "venue"]
            venue_cost = selected.estimated_cost
            if currency != "USD":
                conv = await research_fx(deps, venue_cost, "USD", currency, event_id=state.get("event_id"))
                venue_cost = conv.converted
            items.insert(
                0,
                BudgetItem(category="venue", description=selected.name, estimated_cost=venue_cost),
            )
            for v in venues:
                v.selected = v.name == selected.name
        result = await deps.tools.budget_calculator.execute(
            BudgetCalculationInput(total_budget=req.budget, currency=currency, items=items)
        )
        if result.over_budget:
            target = req.budget / 1.10
            current = sum(i.estimated_cost for i in items) or 1
            factor = min(1.0, target / current)
            items = [i.model_copy(update={"estimated_cost": round(i.estimated_cost * factor, 2)}) for i in items]
            result = await deps.tools.budget_calculator.execute(
                BudgetCalculationInput(total_budget=req.budget, currency=currency, items=items)
            )

    return {
        "budget": result.budget,
        "venues": venues,
        "_output_summary": (
            f"Calculated ${result.subtotal:,.0f} subtotal + ${result.contingency:,.0f} contingency "
            f"= ${result.total:,.0f}; remaining ${result.remaining:,.0f}"
        ),
    }


async def budget_node(state: EventState, deps: GraphDeps) -> dict:
    req = _req(state)
    return await run_agent_node(
        "budget",
        "Build deterministic budget",
        state,
        deps,
        _logic,
        input_summary=f"{req.attendees} attendees, ${req.budget:,.0f} {req.currency} budget",
    )

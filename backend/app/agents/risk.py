from app.domain.models import (
    Budget,
    EventRequirements,
    Logistics,
    Risk,
    RiskCheckerInput,
    Schedule,
    VenueCandidate,
    Vendor,
)
from app.domain.state import EventState
from app.graph.deps import GraphDeps
from app.graph.wrapper import run_agent_node
from app.services.intake import weather_date
from app.services.research import research_weather, research_web


def _coerce(model, raw):
    if raw is None:
        return None
    return raw if isinstance(raw, model) else model.model_validate(raw)


async def _logic(state: EventState, deps: GraphDeps) -> dict:
    req = _coerce(EventRequirements, state.get("requirements"))
    loc = (req.location if req else "Cairo") or "Cairo"
    date = weather_date(req)
    weather, _cached = await research_weather(deps, loc, date, event_id=state.get("event_id"))
    local, _ = await research_web(
        deps,
        f"event risks permits crowd safety {loc}",
        kind="risk",
        location=loc,
        event_id=state.get("event_id"),
    )
    venues = []
    for v in state.get("venues") or []:
        venues.append(v if isinstance(v, VenueCandidate) else VenueCandidate.model_validate(v))
    vendors = []
    for v in state.get("vendors") or []:
        vendors.append(v if isinstance(v, Vendor) else Vendor.model_validate(v))
    raw_risks = await deps.tools.risk_checker.execute(
        RiskCheckerInput(
            schedule=_coerce(Schedule, state.get("schedule")),
            budget=_coerce(Budget, state.get("budget")),
            venues=venues,
            vendors=vendors,
            logistics=_coerce(Logistics, state.get("logistics")),
            requirements=req,
            weather=weather,
        )
    )
    risks = []
    for r in raw_risks or []:
        risk = r if isinstance(r, Risk) else Risk.model_validate(r)
        if not risk.mitigation:
            risk = risk.model_copy(update={"mitigation": "Assign an owner and review this risk."})
        risks.append(risk)
    if local.notes and not any(local.notes[:40] in r.description for r in risks):
        from app.domain.enums import IssueType, RiskSeverity

        risks.append(
            Risk(
                title="Local conditions (research)",
                severity=RiskSeverity.low,
                probability=0.2,
                impact="Local traffic, permits, or site access can add time and cost if ignored.",
                description=local.notes,
                explanation=(
                    f"Desk research for {loc} flagged operating notes that are not in the budget math. "
                    f"{local.notes} Treat this as a planning reminder, not a stop."
                ),
                solutions=[
                    "Walk the access road / drop-off on a site visit or with the venue ops manager.",
                    "Put extra transfer time on the guest timetable (especially close of day).",
                    "Confirm permits, generator, and coach access in writing before lock.",
                ],
                mitigation="Walk site access; add transfer buffer; confirm permits in writing.",
                issue_type=IssueType.other,
                owner="Producer",
            )
        )
    top = risks[0].title if risks else "none"
    return {
        "risks": risks,
        "_output_summary": f"{len(risks)} risks; top={top}",
    }


async def risk_node(state: EventState, deps: GraphDeps) -> dict:
    return await run_agent_node(
        "risk",
        "Scan plan for operational risks",
        state,
        deps,
        _logic,
        input_summary="budget, schedule, venue, vendors, logistics",
    )

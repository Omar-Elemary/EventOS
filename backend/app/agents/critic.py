from app.domain.budget import is_over_budget
from app.domain.enums import CriticDecision, IssueType, RiskSeverity
from app.domain.models import (
    Budget,
    CriticIssue,
    CriticLLMView,
    CriticResult,
    EventRequirements,
    Risk,
    Schedule,
    VenueCandidate,
)
from app.domain.state import EventState
from app.graph.deps import GraphDeps
from app.graph.routing import pick_next_agent
from app.graph.wrapper import run_agent_node
from app.llm.base import LLMError, LLMMessage


def _coerce(model, raw):
    if raw is None:
        return None
    return raw if isinstance(raw, model) else model.model_validate(raw)


async def _logic(state: EventState, deps: GraphDeps) -> dict:
    req = _coerce(EventRequirements, state.get("requirements"))
    budget = _coerce(Budget, state.get("budget"))
    schedule = _coerce(Schedule, state.get("schedule"))
    venues = [
        v if isinstance(v, VenueCandidate) else VenueCandidate.model_validate(v) for v in (state.get("venues") or [])
    ]
    selected = next((v for v in venues if v.selected), venues[0] if venues else None)
    issues: list[CriticIssue] = []

    if req and not selected:
        issues.append(
            CriticIssue(
                title="No venue selected",
                severity=RiskSeverity.critical,
                issue_type=IssueType.venue_capacity,
                message="The venue agent did not select a hall that matches this brief.",
            )
        )
    if req and selected and selected.capacity < req.attendees:
        issues.append(
            CriticIssue(
                title="Venue capacity insufficient",
                severity=RiskSeverity.critical,
                issue_type=IssueType.venue_capacity,
                message=f"Selected venue capacity is insufficient ({selected.capacity} < {req.attendees}).",
            )
        )
    if budget and is_over_budget(budget.total_budget, budget.subtotal, budget.contingency):
        issues.append(
            CriticIssue(
                title="Budget not feasible",
                severity=RiskSeverity.high,
                issue_type=IssueType.budget,
                message=f"Plan exceeds budget by {abs(budget.remaining):.0f} {budget.currency}.",
            )
        )
    if schedule and schedule.conflicts:
        issues.append(
            CriticIssue(
                title="Schedule conflicts",
                severity=RiskSeverity.high,
                issue_type=IssueType.schedule,
                message=schedule.conflicts[0],
            )
        )
    for r in state.get("risks") or []:
        try:
            risk = r if isinstance(r, Risk) else Risk.model_validate(r)
        except Exception:
            continue
        if risk.severity in {RiskSeverity.critical, RiskSeverity.high} and risk.issue_type in {
            IssueType.venue_capacity,
            IssueType.budget,
            IssueType.schedule,
        }:
            if risk.issue_type == IssueType.budget and budget and not is_over_budget(
                budget.total_budget, budget.subtotal, budget.contingency
            ):
                continue
            if not any(i.issue_type == risk.issue_type for i in issues):
                issues.append(
                    CriticIssue(
                        title=risk.title,
                        severity=risk.severity,
                        issue_type=risk.issue_type,
                        message=risk.description,
                    )
                )

    score = 100.0
    for i in issues:
        score -= {"critical": 35, "high": 20, "medium": 8, "low": 3}.get(i.severity.value, 5)
    score = max(0, min(100, score))

    if getattr(deps.llm, "name", "") != "mock":
        try:
            view = await deps.llm.complete_structured(
                CriticLLMView,
                [LLMMessage(role="user", content=f"Issues: {[i.model_dump() for i in issues]}")],
            )
            if isinstance(view, CriticLLMView):
                score = round((score + view.score_hint) / 2, 1)
        except (LLMError, Exception):
            pass

    if not issues:
        approved = True
        score = max(score, 70.0)
        next_agent = None
    else:
        approved = False
        next_agent = pick_next_agent(issues)
    iteration = int(state.get("iteration") or 0)
    if not approved:
        iteration += 1
        for issue in issues:
            await deps.sink.emit(
                state["event_id"],
                {
                    "type": "critic_issue",
                    "severity": issue.severity.value,
                    "message": issue.message,
                    "run_id": state["run_id"],
                },
            )

    result = CriticResult(
        approved=approved,
        decision=CriticDecision.approved if approved else CriticDecision.needs_changes,
        issues=issues,
        required_changes=[i.message for i in issues],
        score=score,
        next_agent=next_agent,
    )
    updates = {
        "critic_result": result,
        "iteration": iteration,
        "route_to": None if approved else next_agent,
        "replan_mode": None if approved else next_agent,
        "_output_summary": f"{'Approved' if approved else 'Needs changes'} score={score} next={next_agent}",
    }
    if approved:
        updates["status"] = "approved"
    return updates


async def critic_node(state: EventState, deps: GraphDeps) -> dict:
    return await run_agent_node(
        "critic",
        "Evaluate plan and route replanning",
        state,
        deps,
        _logic,
        input_summary="Feasibility across budget, venue, schedule, vendors, logistics",
    )

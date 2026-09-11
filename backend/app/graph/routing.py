from app.core.config import get_settings
from app.domain.enums import CriticDecision, IssueType, RiskSeverity
from app.domain.models import CriticIssue, CriticResult
from app.domain.state import EventState

SEVERITY_RANK = {
    RiskSeverity.critical: 0,
    RiskSeverity.high: 1,
    RiskSeverity.medium: 2,
    RiskSeverity.low: 3,
}

TYPE_RANK = {
    IssueType.venue_capacity: 0,
    IssueType.budget: 1,
    IssueType.schedule: 2,
    IssueType.vendors: 3,
    IssueType.logistics: 4,
    IssueType.requirements: 5,
    IssueType.other: 6,
}

TYPE_TO_AGENT = {
    IssueType.venue_capacity: "venue",
    IssueType.budget: "budget",
    IssueType.schedule: "schedule",
    IssueType.vendors: "vendor",
    IssueType.logistics: "logistics",
    IssueType.requirements: "requirements",
    IssueType.other: "budget",
}


def route_after_orchestrator(state: EventState) -> str:
    if state.get("status") == "awaiting_input":
        return "end"
    return "venue"


def pick_next_agent(issues: list[CriticIssue]) -> str | None:
    if not issues:
        return None
    ranked = sorted(
        issues,
        key=lambda i: (SEVERITY_RANK.get(i.severity, 9), TYPE_RANK.get(i.issue_type, 9)),
    )
    return TYPE_TO_AGENT.get(ranked[0].issue_type, "budget")


def route_after_critic(state: EventState) -> str:
    critic = state.get("critic_result")
    if isinstance(critic, dict):
        critic = CriticResult.model_validate(critic)
    max_iter = get_settings().max_iterations
    iteration = int(state.get("iteration") or 0)
    if critic and critic.approved:
        return "finalize"
    if iteration >= max_iter:
        return "human"
    nxt = (critic.next_agent if critic else None) or pick_next_agent(critic.issues if critic else [])
    if not nxt and critic and not (critic.issues or []):
        return "finalize"
    if nxt in {"budget", "venue", "schedule", "vendor", "logistics"}:
        return nxt
    return "human"


def route_after_venue(state: EventState) -> str:
    if state.get("replan_mode") == "venue":
        return "logistics"
    return "vendor"

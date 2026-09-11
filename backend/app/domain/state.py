from typing import Annotated, Any, NotRequired, TypedDict

from app.domain.models import (
    AgentMessage,
    Budget,
    CriticResult,
    EventRequirements,
    Logistics,
    Risk,
    Schedule,
    VenueCandidate,
    Vendor,
)


def add_list(left: list[Any] | None, right: list[Any] | None) -> list[Any]:
    return (left or []) + (right or [])


class EventState(TypedDict):
    run_id: str
    event_id: str
    correlation_id: str
    user_request: str
    requirements: EventRequirements | None
    venues: list[VenueCandidate]
    vendors: list[Vendor]
    budget: Budget | None
    schedule: Schedule | None
    logistics: Logistics | None
    risks: list[Risk]
    critic_result: CriticResult | None
    agent_messages: Annotated[list[AgentMessage], add_list]
    iteration: int
    status: str
    errors: Annotated[list[str], add_list]
    route_to: str | None
    missing_fields: list[str]
    replan_mode: str | None
    force_over_budget: NotRequired[bool]

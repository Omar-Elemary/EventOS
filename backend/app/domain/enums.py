from enum import StrEnum


class RiskSeverity(StrEnum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class AgentStatus(StrEnum):
    queued = "queued"
    running = "running"
    completed = "completed"
    failed = "failed"


class VendorCategory(StrEnum):
    catering = "catering"
    photography = "photography"
    videography = "videography"
    security = "security"
    transportation = "transportation"
    decoration = "decoration"
    av = "av"
    lighting = "lighting"
    entertainment = "entertainment"
    staffing = "staffing"
    hotels = "hotels"
    printing = "printing"
    tents = "tents"
    generator = "generator"
    medical = "medical"
    stage = "stage"


class EventStatus(StrEnum):
    draft = "draft"
    planning = "planning"
    awaiting_input = "awaiting_input"
    needs_decision = "needs_decision"
    approved = "approved"
    preparing = "preparing"
    in_progress = "in_progress"
    completed = "completed"
    archived = "archived"
    needs_human_review = "needs_human_review"
    failed = "failed"


class CriticDecision(StrEnum):
    approved = "approved"
    needs_changes = "needs_changes"


class OrchestratorDecision(StrEnum):
    missing_information = "MISSING_INFORMATION"
    proceed = "PROCEED"


class DataSourceType(StrEnum):
    mock = "mock"
    live = "live"
    cached = "cached"


class SourceTier(StrEnum):
    official = "official"
    trusted = "trusted"
    web = "web"
    mock = "mock"


class ResearchProvider(StrEnum):
    brave = "brave"
    nominatim = "nominatim"
    open_meteo = "open_meteo"
    frankfurter = "frankfurter"
    mock = "mock"


class PriceType(StrEnum):
    estimated = "estimated"
    quoted = "quoted"
    starting_from = "starting_from"
    unknown = "unknown"


class DataMode(StrEnum):
    mock = "mock"
    live = "live"


class CandidateStatus(StrEnum):
    considered = "considered"
    shortlist = "shortlist"
    selected = "selected"
    rejected = "rejected"


class DecisionStatus(StrEnum):
    open = "open"
    chosen = "chosen"
    dismissed = "dismissed"


class SimulationStatus(StrEnum):
    pending = "pending"
    applied = "applied"
    discarded = "discarded"
    stale = "stale"


class BudgetItemStatus(StrEnum):
    estimated = "estimated"
    committed = "committed"
    paid = "paid"


class TaskPhase(StrEnum):
    setup = "setup"
    load_in = "load_in"
    event = "event"
    teardown = "teardown"


class RiskStatus(StrEnum):
    open = "open"
    mitigated = "mitigated"
    accepted = "accepted"
    closed = "closed"


class IssueType(StrEnum):
    venue_capacity = "venue_capacity"
    budget = "budget"
    schedule = "schedule"
    vendors = "vendors"
    logistics = "logistics"
    requirements = "requirements"
    other = "other"


def product_status(graph_status: str | None) -> str:
    """Map graph terminal/internal status onto the product lifecycle."""
    if not graph_status:
        return EventStatus.draft.value
    if graph_status in {EventStatus.awaiting_input.value, EventStatus.needs_human_review.value}:
        return EventStatus.needs_decision.value
    if graph_status == "running":
        return EventStatus.planning.value
    return graph_status


def risk_score(probability: float, severity: RiskSeverity | str) -> float:
    weight = {
        RiskSeverity.critical.value: 10.0,
        RiskSeverity.high.value: 8.5,
        RiskSeverity.medium.value: 6.0,
        RiskSeverity.low.value: 3.5,
    }
    key = severity.value if hasattr(severity, "value") else str(severity)
    return round(max(0.0, min(1.0, float(probability))) * weight.get(key, 5.0), 1)

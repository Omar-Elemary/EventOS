from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

from app.domain.enums import (
    AgentStatus,
    BudgetItemStatus,
    CriticDecision,
    DataSourceType,
    IssueType,
    PriceType,
    ResearchProvider,
    RiskSeverity,
    RiskStatus,
    SourceTier,
    VendorCategory,
)


class EventRequirements(BaseModel):
    event_type: str
    location: str | None = None
    attendees: int = 0
    duration_days: int = 0
    budget: float = 0
    currency: str = "EGP"
    preferred_date: datetime | None = None
    date_note: str | None = None
    format: str | None = None
    overnight: bool | None = None
    audience: str | None = None
    requirements: list[str] = Field(default_factory=list)
    raw_request: str | None = None
    audience_type: str | None = None
    vip_count: int | None = None
    speaker_count: int | None = None
    staff_count: int | None = None
    accessibility: str | None = None
    catering: str | None = None
    av: str | None = None
    stage: bool | None = None
    registration: bool | None = None
    parking: bool | None = None
    security: str | None = None
    transport: str | None = None
    accommodation: bool | None = None
    branding: str | None = None
    photo_video: bool | None = None
    internet: str | None = None
    venue_style: str | None = None
    budget_priority: str | None = None
    sustainability_priority: str | None = None
    experience_priority: str | None = None
    preferred_vendors: list[str] = Field(default_factory=list)
    description: str | None = None
    objectives: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    prefer_cheaper: bool = False

    @field_validator("attendees")
    @classmethod
    def attendees_non_negative(cls, v: int) -> int:
        if v < 0:
            raise ValueError("attendees must be >= 0")
        return v

    @field_validator("duration_days")
    @classmethod
    def duration_non_negative(cls, v: int) -> int:
        if v < 0:
            raise ValueError("duration_days must be >= 0")
        return v

    @field_validator("budget")
    @classmethod
    def budget_non_negative(cls, v: float) -> float:
        if v < 0:
            raise ValueError("budget must be >= 0")
        return v


class VenueCandidate(BaseModel):
    name: str
    location: str
    capacity: int
    estimated_cost: float
    facilities: list[str] = Field(default_factory=list)
    suitability_score: float = Field(ge=0, le=100)
    pros: list[str] = Field(default_factory=list)
    cons: list[str] = Field(default_factory=list)
    source: str = "mock dataset"
    source_type: DataSourceType = DataSourceType.mock
    from_cache: bool = False
    selected: bool = False
    source_url: str = ""
    source_tier: SourceTier = SourceTier.mock
    confidence: float = Field(default=0.7, ge=0, le=1)
    retrieved_at: datetime | None = None
    last_checked_at: datetime | None = None
    price_type: PriceType = PriceType.estimated
    requires_quote: bool = False
    provider: ResearchProvider = ResearchProvider.mock
    distance_km: float | None = None

    @field_validator("estimated_cost")
    @classmethod
    def cost_non_negative(cls, v: float) -> float:
        if v < 0:
            raise ValueError("estimated_cost must be >= 0")
        return v


class VendorService(BaseModel):
    name: str
    unit_cost: float = Field(ge=0)
    notes: str | None = None


class Vendor(BaseModel):
    name: str
    category: VendorCategory
    location: str
    estimated_cost: float = Field(ge=0)
    services: list[VendorService] = Field(default_factory=list)
    rating: float = Field(default=4.0, ge=0, le=5)
    coverage_notes: str | None = None
    source_type: DataSourceType = DataSourceType.mock
    from_cache: bool = False
    selected: bool = True
    source_url: str = ""
    source_tier: SourceTier = SourceTier.mock
    confidence: float = Field(default=0.7, ge=0, le=1)
    retrieved_at: datetime | None = None
    last_checked_at: datetime | None = None
    price_type: PriceType = PriceType.estimated
    requires_quote: bool = False
    provider: ResearchProvider = ResearchProvider.mock


class BudgetItem(BaseModel):
    category: str
    description: str
    estimated_cost: float
    actual_cost: float = 0
    status: BudgetItemStatus = BudgetItemStatus.estimated
    vendor_name: str | None = None
    due_date: str | None = None
    deposit: float = 0

    @field_validator("estimated_cost", "actual_cost")
    @classmethod
    def costs_non_negative(cls, v: float) -> float:
        if v < 0:
            raise ValueError("costs must be >= 0")
        return v


class Budget(BaseModel):
    total_budget: float = Field(ge=0)
    currency: str
    items: list[BudgetItem] = Field(default_factory=list)
    contingency: float = Field(ge=0)
    subtotal: float = Field(ge=0)
    remaining: float
    committed: float = 0
    estimated: float = 0


class ScheduleItem(BaseModel):
    id: str
    title: str
    start_time: datetime
    end_time: datetime
    location: str | None = None
    responsible_vendor: str | None = None
    depends_on: list[str] = Field(default_factory=list)
    conflicts: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def end_after_start(self) -> "ScheduleItem":
        if self.end_time <= self.start_time:
            raise ValueError("end_time must be after start_time")
        return self


class Schedule(BaseModel):
    items: list[ScheduleItem] = Field(default_factory=list)
    conflicts: list[str] = Field(default_factory=list)


class LogisticsItem(BaseModel):
    area: str
    detail: str
    owner: str | None = None
    conflict: str | None = None
    proposed_fix: str | None = None


class Logistics(BaseModel):
    items: list[LogisticsItem] = Field(default_factory=list)
    weather_summary: str | None = None
    conflicts: list[str] = Field(default_factory=list)


class Risk(BaseModel):
    title: str
    severity: RiskSeverity
    probability: float
    impact: str
    description: str
    mitigation: str = ""
    issue_type: IssueType = IssueType.other
    score: float = 0
    owner: str | None = None
    status: RiskStatus = RiskStatus.open
    trigger: str | None = None
    ai_recommendation: str | None = None
    explanation: str = ""
    solutions: list[str] = Field(default_factory=list)

    @field_validator("title", "impact", "description", "mitigation", mode="before")
    @classmethod
    def none_to_str(cls, v: Any) -> str:
        return "" if v is None else v

    @field_validator("probability")
    @classmethod
    def prob_range(cls, v: float) -> float:
        if v < 0 or v > 1:
            raise ValueError("probability must be between 0 and 1")
        return v

    @model_validator(mode="after")
    def fill_score(self) -> "Risk":
        if not self.score:
            from app.domain.enums import risk_score

            self.score = risk_score(self.probability, self.severity)
        if not self.ai_recommendation:
            if self.solutions:
                self.ai_recommendation = " ".join(f"{i}. {s}" for i, s in enumerate(self.solutions, 1))
            else:
                self.ai_recommendation = self.mitigation or None
        if not self.explanation:
            self.explanation = self.description
        if not self.solutions and self.mitigation:
            self.solutions = [s.strip() for s in self.mitigation.split(";") if s.strip()]
        if not self.trigger:
            self.trigger = self.description[:180] if self.description else None
        return self


class CriticIssue(BaseModel):
    title: str
    severity: RiskSeverity
    issue_type: IssueType
    message: str


class CriticResult(BaseModel):
    approved: bool
    decision: CriticDecision
    issues: list[CriticIssue] = Field(default_factory=list)
    required_changes: list[str] = Field(default_factory=list)
    score: float = Field(ge=0, le=100)
    next_agent: str | None = None


class AgentMessage(BaseModel):
    agent: str
    status: AgentStatus
    task: str
    input_summary: str
    output_summary: str
    timestamp: datetime
    duration_ms: int
    iteration: int
    errors: list[str] = Field(default_factory=list)


class WeatherResult(BaseModel):
    location: str
    date: str
    condition: str
    temp_c: float
    precipitation_chance: float = Field(ge=0, le=1)
    source_type: DataSourceType = DataSourceType.mock
    from_cache: bool = False
    notes: str | None = None
    wind_kmh: float | None = None
    provider: ResearchProvider = ResearchProvider.mock


class ConversionResult(BaseModel):
    amount: float
    from_currency: str
    to_currency: str
    converted: float
    rate: float
    source_type: DataSourceType = DataSourceType.mock
    from_cache: bool = False


class BudgetCalculationInput(BaseModel):
    total_budget: float = Field(ge=0)
    currency: str = "EGP"
    items: list[BudgetItem]
    contingency_rate: float = Field(default=0.10, ge=0, le=1)


class BudgetCalculationResult(BaseModel):
    subtotal: float
    contingency: float
    total: float
    remaining: float
    variance: float
    over_budget: bool
    budget: Budget


class ScheduleConflictResult(BaseModel):
    conflicts: list[str]
    items: list[ScheduleItem]


class VenueSearchInput(BaseModel):
    location: str
    attendee_count: int = Field(gt=0)
    event_type: str = "conference"
    required_facilities: list[str] = Field(default_factory=list)
    format: str | None = None


class WebResearchInput(BaseModel):
    query: str
    kind: str = "web"
    location: str | None = None
    max_results: int = 5


class WebResearchHit(BaseModel):
    title: str
    url: str = ""
    snippet: str = ""


class WebResearchResult(BaseModel):
    query: str
    hits: list[WebResearchHit] = Field(default_factory=list)
    notes: str | None = None
    source_type: DataSourceType = DataSourceType.mock
    from_cache: bool = False


class VendorSearchInput(BaseModel):
    category: VendorCategory
    location: str
    budget: float = Field(ge=0)
    required_services: list[str] = Field(default_factory=list)


class WeatherLookupInput(BaseModel):
    location: str
    date: str


class CurrencyConversionInput(BaseModel):
    amount: float
    from_currency: str
    to_currency: str


class RiskCheckerInput(BaseModel):
    schedule: Schedule | None = None
    budget: Budget | None = None
    venues: list[VenueCandidate] = Field(default_factory=list)
    vendors: list[Vendor] = Field(default_factory=list)
    logistics: Logistics | None = None
    requirements: EventRequirements | None = None
    weather: WeatherResult | None = None


class ChatReply(BaseModel):
    intent: str
    reply: str
    simulate_patch: dict[str, Any] | None = None


class CriticLLMView(BaseModel):
    narrative: str
    score_hint: float = 70


class ExtractedEntities(BaseModel):
    event_type: str | None = None
    location: str | None = None
    attendees: int | None = None
    duration_days: int | None = None
    budget: float | None = None
    currency: str | None = None
    preferred_date: str | None = None
    date_note: str | None = None
    format: str | None = None
    overnight: bool | None = None


class UnderstoodMessage(BaseModel):
    intent: str = "question"
    entities: ExtractedEntities = Field(default_factory=ExtractedEntities)
    simulate_patch: dict[str, Any] | None = None
    action_id: str | None = None
    raw: str = ""


class CopilotAction(BaseModel):
    id: str
    label: str
    payload: dict[str, Any] = Field(default_factory=dict)


class CopilotState(BaseModel):
    phase: str = "intake"
    requirements: dict[str, Any] = Field(default_factory=dict)
    missing_fields: list[str] = Field(default_factory=list)
    skipped_specialized: bool = False
    graph_status: str = "idle"
    available_actions: list[CopilotAction] = Field(default_factory=list)
    last_simulation: dict[str, Any] | None = None
    pending_apply: dict[str, Any] | None = None
    prompt_field: str | None = None


class PolicyDecision(BaseModel):
    policy: str
    phase: str
    missing_fields: list[str] = Field(default_factory=list)
    actions: list[CopilotAction] = Field(default_factory=list)
    state: CopilotState
    run_graph: bool = False
    simulate_patch: dict[str, Any] | None = None
    answer_facts: dict[str, Any] = Field(default_factory=dict)
    prompt_field: str | None = None


class CopilotSpeech(BaseModel):
    message: str

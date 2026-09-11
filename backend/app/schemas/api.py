from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class EventCreate(BaseModel):
    name: str
    location: str | None = None
    attendees: int = 0
    duration_days: int = 1
    budget: float = 0
    currency: str = "EGP"
    user_request: str | None = None
    start_date: datetime | None = None
    description: str | None = None
    objectives: list[str] | None = None
    tags: list[str] | None = None
    deadline: datetime | None = None
    data_mode: str | None = None


class EventPatch(BaseModel):
    name: str | None = None
    location: str | None = None
    attendees: int | None = None
    duration_days: int | None = None
    budget: float | None = None
    currency: str | None = None
    user_request: str | None = None
    start_date: datetime | None = None
    description: str | None = None
    objectives: list[str] | None = None
    tags: list[str] | None = None
    deadline: datetime | None = None
    data_mode: str | None = None
    status: str | None = None
    requirements: dict[str, Any] | None = None


class EventOut(BaseModel):
    id: str
    name: str
    location: str | None
    attendees: int
    duration_days: int
    budget: float
    currency: str
    status: str
    start_date: datetime | None
    user_request: str | None
    plan_snapshot: dict[str, Any] | None = None
    copilot_state: dict[str, Any] | None = None
    description: str | None = None
    objectives: list[Any] | None = None
    tags: list[Any] | None = None
    deadline: datetime | None = None
    data_mode: str | None = "mock"
    event_state_version: int | None = 0
    created_at: datetime | None = None
    updated_at: datetime | None = None
    archived_at: datetime | None = None
    model_config = ConfigDict(from_attributes=True)


class PlanRequest(BaseModel):
    force_over_budget: bool = False
    user_request: str | None = None


class PlanAccepted(BaseModel):
    run_id: str
    status: str = "queued"


class ChatIn(BaseModel):
    message: str = ""
    event_id: str | None = None
    action_id: str | None = None


class ChatActionOut(BaseModel):
    id: str
    label: str
    payload: dict[str, Any] = Field(default_factory=dict)


class ChatOut(BaseModel):
    reply: str
    intent: str
    run_id: str | None = None
    simulation: dict[str, Any] | None = None
    phase: str | None = None
    policy: str | None = None
    missing_fields: list[str] = Field(default_factory=list)
    actions: list[ChatActionOut] = Field(default_factory=list)


class SimulateIn(BaseModel):
    attendees: int | None = None
    budget: float | None = None
    duration_days: int | None = None
    venue_unavailable: bool = False
    venue_id: str | None = None
    format: str | None = None
    vip_count: int | None = None
    description: str | None = None


class CandidateAction(BaseModel):
    status: str | None = None
    notes: str | None = None


class VendorCreate(BaseModel):
    name: str
    category: str
    location: str = ""
    estimated_cost: float = 0
    notes: str = ""


class DecisionApply(BaseModel):
    option_id: str


class VendorQuery(BaseModel):
    category: str | None = None
    location: str | None = None


class AuthSignup(BaseModel):
    name: str
    email: str
    password: str


class AuthLogin(BaseModel):
    email: str
    password: str


class AuthUserOut(BaseModel):
    id: str
    email: str
    name: str


class AuthOut(BaseModel):
    token: str
    user: AuthUserOut

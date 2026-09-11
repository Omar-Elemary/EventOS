import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


def uid() -> str:
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    name: Mapped[str] = mapped_column(String(255), default="Demo User")
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    events: Mapped[list["Event"]] = relationship(back_populates="owner")


class Event(Base):
    __tablename__ = "events"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    name: Mapped[str] = mapped_column(String(255))
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    start_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    attendees: Mapped[int] = mapped_column(Integer, default=0)
    duration_days: Mapped[int] = mapped_column(Integer, default=1)
    budget: Mapped[float] = mapped_column(Float, default=0)
    currency: Mapped[str] = mapped_column(String(8), default="EGP")
    status: Mapped[str] = mapped_column(String(64), default="draft")
    user_request: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    objectives: Mapped[list[Any]] = mapped_column(JSON, default=list)
    tags: Mapped[list[Any]] = mapped_column(JSON, default=list)
    data_mode: Mapped[str] = mapped_column(String(16), default="mock")
    event_state_version: Mapped[int] = mapped_column(Integer, default=0)
    owner: Mapped[User] = relationship(back_populates="events")
    requirements: Mapped["EventRequirement | None"] = relationship(back_populates="event", uselist=False)
    budgets: Mapped[list["Budget"]] = relationship(back_populates="event")
    schedule_items: Mapped[list["ScheduleItem"]] = relationship(back_populates="event")
    tasks: Mapped[list["Task"]] = relationship(back_populates="event")
    risks: Mapped[list["Risk"]] = relationship(back_populates="event")
    agent_runs: Mapped[list["AgentRun"]] = relationship(back_populates="event")
    documents: Mapped[list["Document"]] = relationship(back_populates="event")
    simulations: Mapped[list["Simulation"]] = relationship(back_populates="event")
    chat_messages: Mapped[list["ChatMessage"]] = relationship(back_populates="event")
    event_venues: Mapped[list["EventVenue"]] = relationship(back_populates="event")
    event_vendors: Mapped[list["EventVendor"]] = relationship(back_populates="event")
    decisions: Mapped[list["Decision"]] = relationship(back_populates="event")
    activity_logs: Mapped[list["ActivityLog"]] = relationship(back_populates="event")
    plan_versions: Mapped[list["PlanSnapshot"]] = relationship(back_populates="event")
    plan_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    copilot_state: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)


class EventRequirement(Base):
    __tablename__ = "event_requirements"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    event_id: Mapped[str] = mapped_column(ForeignKey("events.id"))
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    event: Mapped[Event] = relationship(back_populates="requirements")


class Venue(Base):
    __tablename__ = "venues"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    name: Mapped[str] = mapped_column(String(255))
    location: Mapped[str] = mapped_column(String(255))
    capacity: Mapped[int] = mapped_column(Integer)
    estimated_cost: Mapped[float] = mapped_column(Float)
    facilities: Mapped[list[Any]] = mapped_column(JSON, default=list)
    source_type: Mapped[str] = mapped_column(String(32), default="mock")
    extra: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    source_url: Mapped[str] = mapped_column(String(512), default="")
    source_tier: Mapped[str] = mapped_column(String(32), default="mock")
    confidence: Mapped[float] = mapped_column(Float, default=0.7)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    price_type: Mapped[str] = mapped_column(String(32), default="estimated")
    requires_quote: Mapped[bool] = mapped_column(Boolean, default=False)
    provider: Mapped[str] = mapped_column(String(32), default="mock")


class Vendor(Base):
    __tablename__ = "vendors"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    name: Mapped[str] = mapped_column(String(255))
    category: Mapped[str] = mapped_column(String(64))
    location: Mapped[str] = mapped_column(String(255))
    estimated_cost: Mapped[float] = mapped_column(Float)
    source_type: Mapped[str] = mapped_column(String(32), default="mock")
    rating: Mapped[float] = mapped_column(Float, default=4.0)
    source_url: Mapped[str] = mapped_column(String(512), default="")
    source_tier: Mapped[str] = mapped_column(String(32), default="mock")
    confidence: Mapped[float] = mapped_column(Float, default=0.7)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    price_type: Mapped[str] = mapped_column(String(32), default="estimated")
    requires_quote: Mapped[bool] = mapped_column(Boolean, default=False)
    provider: Mapped[str] = mapped_column(String(32), default="mock")
    services: Mapped[list["VendorService"]] = relationship(back_populates="vendor")


class VendorService(Base):
    __tablename__ = "vendor_services"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    vendor_id: Mapped[str] = mapped_column(ForeignKey("vendors.id"))
    name: Mapped[str] = mapped_column(String(255))
    unit_cost: Mapped[float] = mapped_column(Float, default=0)
    vendor: Mapped[Vendor] = relationship(back_populates="services")


class EventVenue(Base):
    __tablename__ = "event_venues"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    event_id: Mapped[str] = mapped_column(ForeignKey("events.id"), index=True)
    venue_id: Mapped[str | None] = mapped_column(ForeignKey("venues.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(255))
    location: Mapped[str] = mapped_column(String(255), default="")
    capacity: Mapped[int] = mapped_column(Integer, default=0)
    estimated_cost: Mapped[float] = mapped_column(Float, default=0)
    facilities: Mapped[list[Any]] = mapped_column(JSON, default=list)
    suitability_score: Mapped[float] = mapped_column(Float, default=50)
    pros: Mapped[list[Any]] = mapped_column(JSON, default=list)
    cons: Mapped[list[Any]] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(32), default="considered")
    notes: Mapped[str] = mapped_column(Text, default="")
    source_url: Mapped[str] = mapped_column(String(512), default="")
    source_tier: Mapped[str] = mapped_column(String(32), default="mock")
    confidence: Mapped[float] = mapped_column(Float, default=0.7)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    price_type: Mapped[str] = mapped_column(String(32), default="estimated")
    requires_quote: Mapped[bool] = mapped_column(Boolean, default=False)
    provider: Mapped[str] = mapped_column(String(32), default="mock")
    distance_km: Mapped[float | None] = mapped_column(Float, nullable=True)
    extra: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    event: Mapped[Event] = relationship(back_populates="event_venues")


class EventVendor(Base):
    __tablename__ = "event_vendors"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    event_id: Mapped[str] = mapped_column(ForeignKey("events.id"), index=True)
    vendor_id: Mapped[str | None] = mapped_column(ForeignKey("vendors.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(255))
    category: Mapped[str] = mapped_column(String(64), default="")
    location: Mapped[str] = mapped_column(String(255), default="")
    estimated_cost: Mapped[float] = mapped_column(Float, default=0)
    rating: Mapped[float] = mapped_column(Float, default=4.0)
    services: Mapped[list[Any]] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(32), default="considered")
    notes: Mapped[str] = mapped_column(Text, default="")
    quote_status: Mapped[str] = mapped_column(String(32), default="none")
    source_url: Mapped[str] = mapped_column(String(512), default="")
    source_tier: Mapped[str] = mapped_column(String(32), default="mock")
    confidence: Mapped[float] = mapped_column(Float, default=0.7)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    price_type: Mapped[str] = mapped_column(String(32), default="estimated")
    requires_quote: Mapped[bool] = mapped_column(Boolean, default=False)
    provider: Mapped[str] = mapped_column(String(32), default="mock")
    event: Mapped[Event] = relationship(back_populates="event_vendors")


class Budget(Base):
    __tablename__ = "budgets"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    event_id: Mapped[str] = mapped_column(ForeignKey("events.id"))
    total_budget: Mapped[float] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String(8), default="USD")
    subtotal: Mapped[float] = mapped_column(Float, default=0)
    contingency: Mapped[float] = mapped_column(Float, default=0)
    remaining: Mapped[float] = mapped_column(Float, default=0)
    committed: Mapped[float] = mapped_column(Float, default=0)
    estimated: Mapped[float] = mapped_column(Float, default=0)
    event: Mapped[Event] = relationship(back_populates="budgets")
    items: Mapped[list["BudgetItem"]] = relationship(back_populates="budget")


class BudgetItem(Base):
    __tablename__ = "budget_items"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    budget_id: Mapped[str] = mapped_column(ForeignKey("budgets.id"))
    category: Mapped[str] = mapped_column(String(64))
    description: Mapped[str] = mapped_column(Text, default="")
    estimated_cost: Mapped[float] = mapped_column(Float)
    actual_cost: Mapped[float] = mapped_column(Float, default=0)
    status: Mapped[str] = mapped_column(String(32), default="estimated")
    vendor_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    due_date: Mapped[str | None] = mapped_column(String(32), nullable=True)
    deposit: Mapped[float] = mapped_column(Float, default=0)
    budget: Mapped[Budget] = relationship(back_populates="items")


class ScheduleItem(Base):
    __tablename__ = "schedule_items"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    event_id: Mapped[str] = mapped_column(ForeignKey("events.id"))
    title: Mapped[str] = mapped_column(String(255))
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    responsible_vendor: Mapped[str | None] = mapped_column(String(255), nullable=True)
    depends_on: Mapped[list[Any]] = mapped_column(JSON, default=list)
    conflicts: Mapped[list[Any]] = mapped_column(JSON, default=list)
    event: Mapped[Event] = relationship(back_populates="schedule_items")


class Task(Base):
    __tablename__ = "tasks"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    event_id: Mapped[str] = mapped_column(ForeignKey("events.id"))
    title: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(32), default="open")
    start_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    end_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    depends_on: Mapped[list[Any]] = mapped_column(JSON, default=list)
    owner: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phase: Mapped[str] = mapped_column(String(32), default="event")
    event: Mapped[Event] = relationship(back_populates="tasks")


class Risk(Base):
    __tablename__ = "risks"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    event_id: Mapped[str] = mapped_column(ForeignKey("events.id"))
    title: Mapped[str] = mapped_column(String(255))
    severity: Mapped[str] = mapped_column(String(32))
    probability: Mapped[float] = mapped_column(Float)
    impact: Mapped[str] = mapped_column(Text)
    description: Mapped[str] = mapped_column(Text)
    mitigation: Mapped[str] = mapped_column(Text)
    score: Mapped[float] = mapped_column(Float, default=0)
    owner: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="open")
    trigger: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_recommendation: Mapped[str | None] = mapped_column(Text, nullable=True)
    explanation: Mapped[str] = mapped_column(Text, default="")
    solutions: Mapped[list[Any]] = mapped_column(JSON, default=list)
    event: Mapped[Event] = relationship(back_populates="risks")


class AgentRun(Base):
    __tablename__ = "agent_runs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    event_id: Mapped[str] = mapped_column(ForeignKey("events.id"))
    run_id: Mapped[str] = mapped_column(String(36), index=True)
    correlation_id: Mapped[str] = mapped_column(String(36), index=True)
    agent: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32))
    task: Mapped[str] = mapped_column(Text, default="")
    input_summary: Mapped[str] = mapped_column(Text, default="")
    output_summary: Mapped[str] = mapped_column(Text, default="")
    iteration: Mapped[int] = mapped_column(Integer, default=0)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    errors: Mapped[list[Any]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    event: Mapped[Event] = relationship(back_populates="agent_runs")


class Document(Base):
    __tablename__ = "documents"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    event_id: Mapped[str] = mapped_column(ForeignKey("events.id"))
    title: Mapped[str] = mapped_column(String(255))
    body: Mapped[str] = mapped_column(Text, default="")
    embedding: Mapped[list[Any] | None] = mapped_column(JSON, nullable=True)
    event: Mapped[Event] = relationship(back_populates="documents")


class ResearchRecord(Base):
    __tablename__ = "research_records"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    query_key: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    event_id: Mapped[str | None] = mapped_column(ForeignKey("events.id"), nullable=True)
    kind: Mapped[str] = mapped_column(String(32))
    query: Mapped[str] = mapped_column(Text, default="")
    normalized_query: Mapped[str] = mapped_column(Text, default="")
    source_url: Mapped[str] = mapped_column(String(512), default="")
    source_tier: Mapped[str] = mapped_column(String(32), default="mock")
    title: Mapped[str] = mapped_column(String(512), default="")
    extracted_data: Mapped[dict[str, Any] | list[Any]] = mapped_column(JSON, default=dict)
    payload: Mapped[dict[str, Any] | list[Any]] = mapped_column(JSON, default=dict)
    source_type: Mapped[str] = mapped_column(String(32), default="mock")
    fingerprint: Mapped[str] = mapped_column(String(64), default="")
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    retrieved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    provider: Mapped[str] = mapped_column(String(32), default="mock")
    raw_reference: Mapped[str] = mapped_column(Text, default="")


class Simulation(Base):
    __tablename__ = "simulations"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    event_id: Mapped[str] = mapped_column(ForeignKey("events.id"))
    change: Mapped[dict[str, Any]] = mapped_column(JSON)
    original_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON)
    result_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    base_version: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(32), default="pending")
    event: Mapped[Event] = relationship(back_populates="simulations")


class ChatMessage(Base):
    __tablename__ = "chat_messages"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    event_id: Mapped[str] = mapped_column(ForeignKey("events.id"))
    role: Mapped[str] = mapped_column(String(16))
    content: Mapped[str] = mapped_column(Text)
    extra: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    event: Mapped[Event] = relationship(back_populates="chat_messages")


class PlanJob(Base):
    __tablename__ = "plan_jobs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    event_id: Mapped[str] = mapped_column(ForeignKey("events.id"))
    status: Mapped[str] = mapped_column(String(32), default="queued")
    force_over_budget: Mapped[bool] = mapped_column(Boolean, default=False)
    extra: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ActivityLog(Base):
    __tablename__ = "activity_log"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    event_id: Mapped[str] = mapped_column(ForeignKey("events.id"), index=True)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    actor: Mapped[str] = mapped_column(String(64))
    action: Mapped[str] = mapped_column(String(64))
    summary: Mapped[str] = mapped_column(Text, default="")
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    state_version: Mapped[int] = mapped_column(Integer, default=0)
    event: Mapped[Event] = relationship(back_populates="activity_logs")


class Decision(Base):
    __tablename__ = "decisions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    event_id: Mapped[str] = mapped_column(ForeignKey("events.id"), index=True)
    problem: Mapped[str] = mapped_column(Text)
    options: Mapped[list[Any]] = mapped_column(JSON, default=list)
    consequences: Mapped[list[Any]] = mapped_column(JSON, default=list)
    recommendation: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(32), default="open")
    chosen_option: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    event: Mapped[Event] = relationship(back_populates="decisions")


class PlanSnapshot(Base):
    __tablename__ = "plan_snapshots"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    event_id: Mapped[str] = mapped_column(ForeignKey("events.id"), index=True)
    version: Mapped[int] = mapped_column(Integer)
    snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    event: Mapped[Event] = relationship(back_populates="plan_versions")

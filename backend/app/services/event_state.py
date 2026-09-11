from datetime import datetime, timezone
from typing import Any

from app.domain.budget import explain_budget
from app.domain.models import Budget, BudgetItem, VenueCandidate
from app.models import (
    Budget as BudgetRow,
    Decision,
    Event,
    EventVenue,
    EventVendor,
    Risk,
    ScheduleItem,
    Task,
)


def _iso(value: datetime | None) -> str | None:
    if not value:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat()


def credibility(source_tier: str, price_type: str) -> dict[str, str]:
    tier = (source_tier or "mock").lower()
    price = (price_type or "estimated").lower()
    if tier == "official":
        badge, label = "official", "Verified official"
    elif tier == "trusted":
        badge, label = "trusted", "Trusted source"
    elif tier == "mock":
        badge, label = "estimated", "Estimated"
    else:
        badge, label = "web", "Found online — verify"
    if price in {"estimated", "starting_from", "unknown"} and badge != "official":
        price_label = "Estimated"
    elif price == "quoted":
        price_label = "Quoted"
    else:
        price_label = "Estimated" if price != "quoted" else "Quoted"
    return {"badge": badge, "label": label, "price_label": price_label}


def venue_out(row: EventVenue) -> dict[str, Any]:
    cred = credibility(row.source_tier, row.price_type)
    return {
        "id": row.id,
        "venue_id": row.venue_id,
        "name": row.name,
        "location": row.location,
        "capacity": row.capacity,
        "estimated_cost": row.estimated_cost,
        "facilities": row.facilities or [],
        "suitability_score": row.suitability_score,
        "pros": row.pros or [],
        "cons": row.cons or [],
        "status": row.status,
        "notes": row.notes,
        "source_url": row.source_url,
        "source_tier": row.source_tier,
        "confidence": row.confidence,
        "last_checked_at": _iso(row.last_checked_at),
        "price_type": row.price_type,
        "requires_quote": row.requires_quote,
        "provider": row.provider,
        "distance_km": row.distance_km,
        "credibility": cred,
        "selected": row.status == "selected",
    }


def vendor_out(row: EventVendor) -> dict[str, Any]:
    cred = credibility(row.source_tier, row.price_type)
    return {
        "id": row.id,
        "vendor_id": row.vendor_id,
        "name": row.name,
        "category": row.category,
        "location": row.location,
        "estimated_cost": row.estimated_cost,
        "rating": row.rating,
        "services": row.services or [],
        "status": row.status,
        "notes": row.notes,
        "quote_status": row.quote_status,
        "source_url": row.source_url,
        "source_tier": row.source_tier,
        "confidence": row.confidence,
        "last_checked_at": _iso(row.last_checked_at),
        "price_type": row.price_type,
        "requires_quote": row.requires_quote,
        "provider": row.provider,
        "credibility": cred,
        "selected": row.status == "selected",
    }


def budget_out(event: Event, brow: BudgetRow | None) -> dict[str, Any]:
    if not brow:
        return {}
    items = [
        BudgetItem(
            category=i.category,
            description=i.description,
            estimated_cost=i.estimated_cost,
            actual_cost=i.actual_cost,
            status=i.status or "estimated",
            vendor_name=i.vendor_name,
            due_date=i.due_date,
            deposit=i.deposit or 0,
        )
        for i in brow.items or []
    ]
    budget = Budget(
        total_budget=brow.total_budget,
        currency=brow.currency,
        items=items,
        contingency=brow.contingency,
        subtotal=brow.subtotal,
        remaining=brow.remaining,
        committed=brow.committed,
        estimated=brow.estimated,
    )
    venues = [
        VenueCandidate(
            name=v.name,
            location=v.location,
            capacity=v.capacity or 1,
            estimated_cost=v.estimated_cost,
            suitability_score=min(100, max(0, v.suitability_score or 50)),
            selected=v.status == "selected",
        )
        for v in event.event_venues or []
        if v.capacity
    ]
    explained = explain_budget(budget, venues, event.attendees)
    return {
        "total_budget": brow.total_budget,
        "currency": brow.currency,
        "subtotal": brow.subtotal,
        "contingency": brow.contingency,
        "remaining": brow.remaining,
        "committed": brow.committed,
        "estimated": brow.estimated,
        "items": [
            {
                "category": i.category,
                "description": i.description,
                "estimated_cost": i.estimated_cost,
                "actual_cost": i.actual_cost,
                "status": i.status,
                "vendor_name": i.vendor_name,
                "due_date": i.due_date,
                "deposit": i.deposit,
            }
            for i in brow.items or []
        ],
        **explained,
    }


def schedule_out(items: list[ScheduleItem]) -> dict[str, Any]:
    conflicts: list[str] = []
    out_items = []
    for it in items:
        conflicts.extend(it.conflicts or [])
        out_items.append(
            {
                "id": it.id,
                "title": it.title,
                "start_time": _iso(it.start_time),
                "end_time": _iso(it.end_time),
                "location": it.location,
                "responsible_vendor": it.responsible_vendor,
                "depends_on": it.depends_on or [],
                "conflicts": it.conflicts or [],
            }
        )
    return {"items": out_items, "conflicts": conflicts}


def task_out(row: Task) -> dict[str, Any]:
    return {
        "id": row.id,
        "title": row.title,
        "status": row.status,
        "start_time": _iso(row.start_time),
        "end_time": _iso(row.end_time),
        "depends_on": row.depends_on or [],
        "owner": row.owner,
        "phase": row.phase,
    }


def risk_out(row: Risk | dict[str, Any]) -> dict[str, Any]:
    if isinstance(row, dict):
        sols = row.get("solutions") or []
        if isinstance(sols, str):
            sols = [s.strip() for s in sols.split(";") if s.strip()]
        desc = row.get("description") or ""
        mitigation = row.get("mitigation") or ""
        if not sols and mitigation:
            sols = [s.strip() for s in mitigation.split(";") if s.strip()]
        return {
            "id": row.get("id"),
            "title": row.get("title"),
            "severity": row.get("severity"),
            "probability": row.get("probability"),
            "impact": row.get("impact"),
            "description": desc,
            "mitigation": mitigation,
            "score": row.get("score"),
            "owner": row.get("owner"),
            "status": row.get("status") or "open",
            "trigger": row.get("trigger"),
            "ai_recommendation": row.get("ai_recommendation"),
            "explanation": row.get("explanation") or desc,
            "solutions": sols if isinstance(sols, list) else [],
        }
    sols = getattr(row, "solutions", None) or []
    if not sols and row.mitigation:
        sols = [s.strip() for s in row.mitigation.split(";") if s.strip()]
    return {
        "id": row.id,
        "title": row.title,
        "severity": row.severity,
        "probability": row.probability,
        "impact": row.impact,
        "description": row.description,
        "mitigation": row.mitigation,
        "score": row.score,
        "owner": row.owner,
        "status": row.status,
        "trigger": row.trigger,
        "ai_recommendation": row.ai_recommendation,
        "explanation": getattr(row, "explanation", None) or row.description,
        "solutions": sols,
    }


def decision_out(row: Decision) -> dict[str, Any]:
    return {
        "id": row.id,
        "problem": row.problem,
        "options": row.options or [],
        "consequences": row.consequences or [],
        "recommendation": row.recommendation,
        "status": row.status,
        "chosen_option": row.chosen_option,
        "created_at": _iso(row.created_at),
    }

from app.domain.enums import OrchestratorDecision
from app.domain.models import EventRequirements
from app.domain.state import EventState
from app.graph.deps import GraphDeps
from app.graph.wrapper import run_agent_node
from app.llm.base import LLMError, LLMMessage
from app.llm.mock import _parse_requirements
from app.services.intake import extract_specialized, missing_critical, missing_specialized, parse_preferred_date
from app.services.understand import extract_entities
import os


CRITICAL = ("location", "attendees", "duration_days", "budget")


def _as_req(raw) -> EventRequirements | None:
    if raw is None:
        return None
    if isinstance(raw, EventRequirements):
        return raw
    return EventRequirements.model_validate(raw)


def _ground_requirements(req: EventRequirements, text: str) -> EventRequirements:
    hinted = extract_entities(text)
    updates: dict = {}
    raw = text or ""
    compact = raw.replace(",", "").replace(" ", "")
    if req.attendees and str(int(req.attendees)) not in compact:
        updates["attendees"] = hinted.attendees or 0
    if req.duration_days and str(int(req.duration_days)) not in compact:
        updates["duration_days"] = hinted.duration_days or 0
    if req.budget and str(int(req.budget)) not in compact and str(req.budget) not in compact:
        updates["budget"] = hinted.budget or 0
    loc = (req.location or "").strip()
    if loc and loc.lower() not in raw.lower() and not (hinted.location and hinted.location.lower() == loc.lower()):
        updates["location"] = hinted.location
    if updates:
        return req.model_copy(update=updates)
    return req


async def _logic(state: EventState, deps: GraphDeps) -> dict:
    existing = _as_req(state.get("requirements"))
    text = state.get("user_request") or ""
    if existing and not missing_critical(existing.model_dump()):
        req = existing
    else:
        try:
            if getattr(deps.llm, "name", "") == "mock" or os.getenv("VERCEL"):
                req = EventRequirements.model_validate(_parse_requirements(text))
            else:
                req = await deps.llm.complete_structured(
                    EventRequirements,
                    [
                        LLMMessage(
                            role="system",
                            content="Extract event requirements. Do not invent missing critical fields; use 0 or null when unknown.",
                        ),
                        LLMMessage(role="user", content=text),
                    ],
                )
            if isinstance(req, EventRequirements) and not req.location and "cairo" in text.lower():
                req = req.model_copy(update={"location": "Cairo"})
            if isinstance(req, EventRequirements):
                req = _ground_requirements(req, text)
        except (LLMError, Exception):
            req = EventRequirements.model_validate(_parse_requirements(text))
        if existing:
            base = existing.model_dump()
            parsed = req.model_dump()
            for key, value in parsed.items():
                current = base.get(key)
                empty = current in (None, "", []) or (key in {"attendees", "duration_days", "budget"} and not current)
                if empty and value not in (None, "", []):
                    base[key] = value
            req = EventRequirements.model_validate(base)
    spec = extract_specialized(text)
    updates: dict = {}
    if spec.get("format") and not req.format:
        updates["format"] = spec["format"]
    if spec.get("overnight") is not None and req.overnight is None:
        updates["overnight"] = spec["overnight"]
    if spec.get("date_note") and not req.date_note:
        updates["date_note"] = spec["date_note"]
    if spec.get("preferred_date") and req.preferred_date is None:
        parsed = parse_preferred_date(spec["preferred_date"])
        if parsed:
            updates["preferred_date"] = parsed
        elif not req.date_note:
            updates["date_note"] = spec["preferred_date"]
    if updates:
        req = req.model_copy(update=updates)
    payload = req.model_dump()
    missing = missing_critical(payload)
    extras = missing_specialized(payload)
    extra_note = f"; still unknown: {', '.join(extras)}" if extras else ""
    return {
        "requirements": req,
        "_output_summary": (
            f"Parsed {req.event_type} in {req.location} for {req.attendees} / "
            f"{req.duration_days}d / {req.budget} {req.currency}{extra_note}"
        ),
        "missing_fields": missing,
    }


async def requirements_node(state: EventState, deps: GraphDeps) -> dict:
    text = (state.get("user_request") or "")[:180]
    return await run_agent_node(
        "requirements",
        "Parse and validate event requirements",
        state,
        deps,
        _logic,
        input_summary=text,
    )


async def orchestrator_node(state: EventState, deps: GraphDeps) -> dict:
    async def _orch(s: EventState, d: GraphDeps) -> dict:
        req = _as_req(s.get("requirements"))
        payload = req.model_dump() if req else {}
        missing = missing_critical(payload) if req else list(CRITICAL)
        if missing:
            return {
                "status": "awaiting_input",
                "route_to": "requirements",
                "missing_fields": missing,
                "_output_summary": f"{OrchestratorDecision.missing_information.value}: {', '.join(missing)}",
            }
        return {
            "status": "planning",
            "route_to": "venue",
            "missing_fields": [],
            "_output_summary": OrchestratorDecision.proceed.value,
        }

    return await run_agent_node(
        "orchestrator",
        "Decide if requirements are complete",
        state,
        deps,
        _orch,
        input_summary="Check location, attendees, duration, budget",
    )

from __future__ import annotations

import re

from app.domain.models import ExtractedEntities, UnderstoodMessage
from app.llm.base import LLMError, LLMMessage
from app.llm.factory import get_llm_provider
from app.services.chat import extract_simulate_patch, looks_like_event_brief
from app.services.intake import extract_specialized

CONFIRM_RE = re.compile(
    r"^\s*(yes|yep|yeah|ok|okay|sure|proceed|go|go ahead|confirm|do it|start|run it|plan it|plan this|looks good)\s*[.!]?\s*$",
    re.I,
)
WHAT_IF_RE = re.compile(r"\b(what if|simulate|what-if)\b", re.I)
EDIT_RE = re.compile(r"\b(change|actually|update|make it|instead|edit|set )\b", re.I)

PLACE_ALIASES = (
    ("alexendria", "Alexandria"),
    ("alexandria", "Alexandria"),
    ("el sahel", "El Sahel"),
    ("sahel", "El Sahel"),
    ("cairo", "Cairo"),
    ("giza", "Giza"),
    ("hurghada", "Hurghada"),
    ("sharm", "Sharm El Sheikh"),
    ("dubai", "Dubai"),
    ("london", "London"),
    ("new york", "New York"),
    ("riyadh", "Riyadh"),
    ("nairobi", "Nairobi"),
)


def extract_entities(text: str) -> ExtractedEntities:
    t = text.lower()
    attendees = None
    m = re.search(r"(\d[\d,]*)\s*(attendees?|people|guests?|pax|person)", t)
    if m:
        attendees = int(m.group(1).replace(",", ""))
    days = None
    m = re.search(r"(\d+)\s*-?\s*days?", t)
    if m:
        days = int(m.group(1))
    budget = None
    currency = None
    m = (
        re.search(r"\$\s*([\d,]+(?:\.\d+)?)", t)
        or re.search(r"([\d,]+(?:\.\d+)?)\s*\$", t)
        or re.search(r"([\d,]+(?:\.\d+)?)\s*(egp|egb|le|e£)", t)
        or re.search(r"(egp|egb|le|e£)\s*([\d,]+(?:\.\d+)?)", t)
        or re.search(r"budget\s*(?:of\s*|is\s*)?\$?\s*([\d,]+)", t)
    )
    if m:
        nums = [g for g in m.groups() if g and str(g).lower() not in {"egp", "egb", "le", "e£"}]
        budget = float(str(nums[0]).replace(",", ""))
        blob = m.group(0)
        currency = "USD" if "$" in blob else "EGP"
    location = None
    for needle, label in PLACE_ALIASES:
        if needle in t:
            location = label
            break
    if location is None:
        m = re.search(r"\bin\s+([a-z][a-z\s]{2,40}?)(?:\s+for|\s+with|,|$)", t)
        if m:
            location = m.group(1).strip().title()
    if location and location.lower() in {"tbd", "todo", "unknown", "n/a", "none"}:
        location = None
    event_type = None
    if "classic" in t or "classical" in t or "music" in t or "concert" in t:
        event_type = "classical music concert" if "classic" in t or "classical" in t else "music event"
    elif "conference" in t or "summit" in t:
        event_type = "technology conference" if "tech" in t or "ai" in t else "conference"
    elif "marathon" in t or "race" in t:
        event_type = "marathon"
    elif "sport" in t:
        event_type = "sports event"
    elif "wedding" in t:
        event_type = "wedding"
    elif "festival" in t:
        event_type = "festival"
    spec = extract_specialized(text)
    return ExtractedEntities(
        event_type=event_type,
        location=location,
        attendees=attendees,
        duration_days=days,
        budget=budget,
        currency=currency or ("EGP" if budget is not None else None),
        preferred_date=spec.get("preferred_date"),
        date_note=spec.get("date_note"),
        format=spec.get("format"),
        overnight=spec.get("overnight"),
    )


ACTION_ALIASES = {
    "proceed": "proceed",
    "go ahead": "proceed",
    "edit brief": "edit_brief",
    "cheaper": "cheaper_venue",
    "larger venue": "cheaper_venue",
    "raise budget": "raise_budget",
    "registration in the foyer": "registration_foyer",
    "put registration": "registration_foyer",
    "keep this draft": "keep_draft",
    "keep original": "discard_sim",
    "apply to live": "apply_sim",
    "apply_sim": "apply_sim",
    "discard_sim": "discard_sim",
    "what if attendance 800": "whatif_attendance",
    "skip extras": "skip_extras",
    "use defaults": "skip_extras",
    "skip": "skip_extras",
    "no extras": "skip_extras",
}


def _action_from_text(text: str) -> str | None:
    t = text.lower().strip()
    if t in ACTION_ALIASES:
        return ACTION_ALIASES[t]
    for needle, aid in ACTION_ALIASES.items():
        if needle in t and len(t) < 80:
            return aid
    return None


def heuristic_understand(text: str, *, action_id: str | None = None) -> UnderstoodMessage:
    raw = text or ""
    t = raw.lower().strip()
    entities = extract_entities(raw)
    mapped = action_id or _action_from_text(raw)
    if mapped:
        intent = "confirm" if mapped == "proceed" else "decide"
        if mapped == "whatif_attendance":
            intent = "what_if"
        return UnderstoodMessage(intent=intent, entities=entities, action_id=mapped, raw=raw)
    if CONFIRM_RE.match(t):
        return UnderstoodMessage(intent="confirm", entities=entities, action_id="proceed", raw=raw)
    if WHAT_IF_RE.search(t):
        patch = extract_simulate_patch(raw)
        return UnderstoodMessage(intent="what_if", entities=entities, simulate_patch=patch or None, raw=raw)
    if looks_like_event_brief(t) or any(v is not None for v in entities.model_dump().values()):
        intent = "edit" if EDIT_RE.search(t) else "plan"
        return UnderstoodMessage(intent=intent, entities=entities, raw=raw)
    return UnderstoodMessage(intent="question", entities=entities, raw=raw)


def _number_in_text(value: int | float, raw: str) -> bool:
    as_int = str(int(value)) if float(value).is_integer() else None
    compact = re.sub(r"[,\s]", "", raw)
    if as_int and as_int in compact:
        return True
    return str(value) in compact


def _ground_entities(ent: ExtractedEntities, raw: str) -> ExtractedEntities:
    attendees = ent.attendees if ent.attendees and ent.attendees > 0 else None
    days = ent.duration_days if ent.duration_days and ent.duration_days > 0 else None
    budget = ent.budget if ent.budget is not None and ent.budget > 0 else None
    if attendees is not None and raw and not _number_in_text(attendees, raw):
        attendees = None
    if days is not None and raw and not _number_in_text(days, raw):
        days = None
    if budget is not None and raw and not _number_in_text(budget, raw):
        budget = None
    loc = (ent.location or "").strip() or None
    if loc and loc.lower() in {"tbd", "todo", "unknown", "n/a", "none"}:
        loc = None
    spec = extract_specialized(raw)
    overnight = ent.overnight if ent.overnight is not None else spec.get("overnight")
    return ExtractedEntities(
        event_type=ent.event_type or None,
        location=loc,
        attendees=attendees,
        duration_days=days,
        budget=budget,
        currency=ent.currency or ("EGP" if budget is not None else None),
        preferred_date=ent.preferred_date or spec.get("preferred_date"),
        date_note=ent.date_note or spec.get("date_note"),
        format=ent.format or spec.get("format"),
        overnight=overnight,
    )


def _validate_entities(ent: ExtractedEntities, raw: str = "") -> ExtractedEntities:
    return _ground_entities(ent, raw)


async def understand_message(text: str, *, action_id: str | None = None) -> UnderstoodMessage:
    fallback = heuristic_understand(text, action_id=action_id)
    if action_id:
        fallback.entities = _validate_entities(fallback.entities, fallback.raw)
        return fallback
    llm = get_llm_provider()
    if getattr(llm, "name", "") == "mock":
        fallback.entities = _validate_entities(fallback.entities, fallback.raw)
        return fallback
    if CONFIRM_RE.match((text or "").strip()):
        fallback.entities = _validate_entities(fallback.entities, fallback.raw)
        return fallback
    try:
        view = await llm.complete_structured(
            UnderstoodMessage,
            [
                LLMMessage(
                    role="system",
                    content=(
                        "Extract EventOS user intent as JSON. "
                        "intent must be one of: plan, confirm, edit, question, what_if, decide. "
                        "entities: event_type, location, attendees, duration_days, budget, currency, preferred_date, format, overnight — use null if not stated. "
                        "Do not invent numbers, a city, a date, or indoor/outdoor. "
                        "simulate_patch only for what-if (attendees, budget, duration_days, venue_unavailable). "
                        "action_id if they chose a chip (proceed, cheaper_venue, raise_budget, registration_foyer, keep_draft, apply_sim, discard_sim)."
                    ),
                ),
                LLMMessage(role="user", content=text or ""),
            ],
        )
        if isinstance(view, UnderstoodMessage):
            view.raw = text or view.raw
            view.entities = _validate_entities(view.entities, view.raw)
            if action_id:
                view.action_id = action_id
                if action_id == "proceed":
                    view.intent = "confirm"
                else:
                    view.intent = "decide"
            if not view.action_id and fallback.action_id:
                view.action_id = fallback.action_id
            if view.intent == "simulate":
                view.intent = "what_if"
            if view.intent not in {"plan", "confirm", "edit", "question", "what_if", "decide"}:
                view.intent = fallback.intent
            if not view.simulate_patch and fallback.simulate_patch:
                view.simulate_patch = fallback.simulate_patch
            merged = fallback.entities.model_dump()
            for k, v in view.entities.model_dump().items():
                if merged.get(k) is None and v is not None:
                    merged[k] = v
            view.entities = _validate_entities(ExtractedEntities.model_validate(merged), view.raw)
            return view
    except (LLMError, Exception):
        pass
    fallback.entities = _validate_entities(fallback.entities, fallback.raw)
    return fallback

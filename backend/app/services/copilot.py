from __future__ import annotations

import re
from typing import Any

from app.domain.models import CopilotAction, CopilotState, PolicyDecision, UnderstoodMessage
from app.models import Event
from app.services.intake import missing_critical, missing_fields as intake_missing, parse_preferred_date
# hydrate seeds city/type from the event title when those fields were never collected.

DEFAULT_CURRENCY = "EGP"

ASK_FOCUS = {
    "add_location": "location",
    "add_attendees": "attendees",
    "add_days": "duration_days",
    "add_budget": "budget",
    "add_date": "preferred_date",
    "add_format": "format",
    "add_overnight": "overnight",
    "write_location": "location",
    "write_attendees": "attendees",
    "write_days": "duration_days",
    "write_budget": "budget",
    "write_date": "preferred_date",
    "write_format": "format",
    "write_overnight": "overnight",
}

CHIP_ECHO = {
    "add a city",
    "add headcount",
    "add duration",
    "add budget",
    "add a date or month",
    "indoor / outdoor / hybrid",
    "need hotels?",
    "skip extras — use defaults",
    "write your own",
}

WRITE_IDS = {f"write_{key}" for key in ("location", "attendees", "days", "budget", "date", "format", "overnight")}

FIELD_CHOICES: dict[str, list[tuple[str, str, Any]]] = {
    "location": [
        ("pick_location_Cairo", "Cairo", "Cairo"),
        ("pick_location_Alexandria", "Alexandria", "Alexandria"),
        ("pick_location_Giza", "Giza", "Giza"),
        ("pick_location_Hurghada", "Hurghada", "Hurghada"),
    ],
    "attendees": [
        ("pick_attendees_100", "100 people", 100),
        ("pick_attendees_250", "250 people", 250),
        ("pick_attendees_500", "500 people", 500),
        ("pick_attendees_1000", "1,000 people", 1000),
    ],
    "duration_days": [
        ("pick_days_1", "1 day", 1),
        ("pick_days_2", "2 days", 2),
        ("pick_days_3", "3 days", 3),
    ],
    "budget": [
        ("pick_budget_50000", "50,000 EGP", 50_000),
        ("pick_budget_150000", "150,000 EGP", 150_000),
        ("pick_budget_400000", "400,000 EGP", 400_000),
        ("pick_budget_800000", "800,000 EGP", 800_000),
    ],
    "preferred_date": [
        ("pick_date_2026-11-01", "November 2026", "2026-11-01"),
        ("pick_date_flexible", "Flexible / TBD", "flexible"),
    ],
    "format": [
        ("pick_format_indoor", "Indoor", "indoor"),
        ("pick_format_outdoor", "Outdoor", "outdoor"),
        ("pick_format_hybrid", "Hybrid", "hybrid"),
    ],
    "overnight": [
        ("pick_overnight_yes", "Need hotels", True),
        ("pick_overnight_no", "Daytime only", False),
    ],
}

WRITE_FOR_FIELD = {
    "location": ("write_location", "Write your own"),
    "attendees": ("write_attendees", "Write your own"),
    "duration_days": ("write_days", "Write your own"),
    "budget": ("write_budget", "Write your own"),
    "preferred_date": ("write_date", "Write your own"),
    "format": ("write_format", "Write your own"),
    "overnight": ("write_overnight", "Write your own"),
}


def normalize_currency(code: str | None) -> str:
    c = (code or DEFAULT_CURRENCY).upper().strip()
    if c in {"EGB", "EGP", "LE", "E£", "EG£"}:
        return "EGP"
    return c or DEFAULT_CURRENCY


def format_money(amount: Any, currency: str | None = None) -> str:
    cur = normalize_currency(currency)
    n = float(amount)
    shown = f"{n:,.0f}" if n >= 100 or n.is_integer() else f"{n:,.2f}"
    if cur == "USD":
        return f"${shown}"
    return f"{shown} {cur}"


def empty_state() -> CopilotState:
    return CopilotState()


def load_state(event: Event | None) -> CopilotState:
    if event is None:
        return empty_state()
    raw = getattr(event, "copilot_state", None) or {}
    try:
        st = CopilotState.model_validate(raw) if raw else empty_state()
    except Exception:
        st = empty_state()
    return hydrate_from_event(event, st)


def persist_state(event: Event, state: CopilotState) -> None:
    event.copilot_state = state.model_dump(mode="json")
    req = state.requirements or {}
    if req.get("location"):
        event.location = str(req["location"])
    if req.get("attendees"):
        event.attendees = int(req["attendees"])
    if req.get("duration_days"):
        event.duration_days = int(req["duration_days"])
    if req.get("budget") is not None:
        event.budget = float(req["budget"])
    if req.get("currency"):
        event.currency = normalize_currency(str(req["currency"]))
    else:
        event.currency = normalize_currency(event.currency)
    event.user_request = user_request_from_state(state)


def _brief_keys_filled(req: dict[str, Any] | None) -> int:
    data = req or {}
    n = 0
    if data.get("location"):
        n += 1
    if data.get("attendees"):
        n += 1
    if data.get("duration_days"):
        n += 1
    budget = data.get("budget")
    if budget not in (None, "", 0, 0.0):
        n += 1
    if data.get("event_type"):
        n += 1
    return n


def adopt_client_state(server: CopilotState, client: dict[str, Any] | None) -> CopilotState:
    """Keep the brief when serverless SQLite lost the event row."""
    if not client or not isinstance(client, dict):
        return server
    try:
        incoming = CopilotState.model_validate(client)
    except Exception:
        return server
    if _brief_keys_filled(server.requirements) >= _brief_keys_filled(incoming.requirements):
        if server.phase not in {"intake", ""} or _brief_keys_filled(server.requirements):
            return server
    if _brief_keys_filled(incoming.requirements) or incoming.phase not in {"intake", ""}:
        return incoming
    return server


def hydrate_from_event(event: Event, state: CopilotState | None = None) -> CopilotState:
    st = state or empty_state()
    req = dict(st.requirements or {})
    if event.location and not req.get("location"):
        req["location"] = event.location
    if event.attendees and event.attendees > 0 and not req.get("attendees"):
        req["attendees"] = event.attendees
    if event.budget and event.budget > 0 and not req.get("budget"):
        req["budget"] = event.budget
    if not req.get("duration_days"):
        sized = bool(req.get("attendees") or req.get("budget") or event.location)
        if event.duration_days and event.duration_days > 1:
            req["duration_days"] = event.duration_days
        elif event.duration_days and sized and event.attendees > 0 and event.budget > 0:
            req["duration_days"] = event.duration_days
    if not req.get("budget") and (not event.budget or float(event.budget) <= 0):
        req["currency"] = DEFAULT_CURRENCY
    elif event.currency:
        req.setdefault("currency", normalize_currency(event.currency))
    else:
        req.setdefault("currency", DEFAULT_CURRENCY)
    req["currency"] = normalize_currency(req.get("currency"))
    if event.start_date and not req.get("preferred_date") and not req.get("date_note"):
        req["preferred_date"] = event.start_date.date().isoformat()
        req["date_note"] = req["preferred_date"]
    if event.user_request:
        req.setdefault("raw_request", event.user_request)
    if not req.get("location") or not req.get("event_type"):
        hint = " ".join(part for part in (event.name, event.user_request) if part)
        if hint:
            from app.services.understand import extract_entities

            ent = extract_entities(hint)
            if ent.location and not req.get("location"):
                req["location"] = ent.location
            if ent.event_type and not req.get("event_type"):
                req["event_type"] = ent.event_type
    st.requirements = req
    st.missing_fields = missing_fields(req, skipped_specialized=st.skipped_specialized)
    status = event.status or "draft"
    if st.graph_status in {"idle", ""}:
        if status == "planning":
            st.graph_status = "running"
        elif status == "draft":
            st.graph_status = "idle"
        elif status in {"approved", "awaiting_input", "needs_human_review", "needs_decision"}:
            st.graph_status = "needs_human_review" if status in {"needs_human_review", "needs_decision"} else status
    if st.graph_status in {"running", "queued"}:
        st.phase = "running"
    elif st.graph_status == "approved":
        st.phase = "done"
    elif st.graph_status in {"awaiting_input", "needs_human_review", "needs_decision"}:
        st.phase = "decide" if st.graph_status in {"needs_human_review", "needs_decision"} else "intake"
    elif not st.missing_fields:
        st.phase = "confirm"
    else:
        st.phase = "intake"
    snap = event.plan_snapshot or {}
    if st.phase == "intake":
        st.prompt_field = st.missing_fields[0] if st.missing_fields else None
        st.available_actions = _ask_actions(st.missing_fields, specialized=not missing_critical(req))
    elif st.phase == "confirm":
        st.available_actions = _confirm_actions()
    elif st.phase == "decide" and not st.available_actions:
        st.available_actions = _decide_actions(snap, st.missing_fields)
    elif st.phase == "done" and not st.available_actions:
        st.available_actions = _done_actions()
    return st


def missing_fields(req: dict[str, Any], *, skipped_specialized: bool = False) -> list[str]:
    return intake_missing(req, skipped_specialized=skipped_specialized)


def merge_entities(req: dict[str, Any], understood: UnderstoodMessage) -> dict[str, Any]:
    out = dict(req)
    data = understood.entities.model_dump()
    for key in ("event_type", "location", "attendees", "duration_days", "budget", "currency", "preferred_date", "date_note", "format"):
        val = data.get(key)
        if val is not None and val != "":
            out[key] = val
    if data.get("overnight") is not None:
        out["overnight"] = data["overnight"]
    if understood.raw and understood.intent not in {"confirm", "question", "decide"}:
        out["raw_request"] = understood.raw
    elif understood.raw and not out.get("raw_request"):
        out["raw_request"] = understood.raw
    return out


def is_prompt_chip(action_id: str | None, text: str | None) -> bool:
    if not action_id:
        return False
    if action_id in WRITE_IDS or action_id.startswith("write_"):
        return True
    if action_id not in ASK_FOCUS:
        return False
    t = (text or "").strip().lower()
    return not t or t in CHIP_ECHO or t.replace("_", " ") == action_id.replace("_", " ")


def placeholder_brief(text: str | None) -> bool:
    t = (text or "").strip().lower()
    if not t:
        return True
    return "?-day" in t or " in tbd" in t or "for ? people" in t or t == "event"


def brief_line(req: dict[str, Any], *, name: str | None = None) -> str:
    kind = req.get("event_type") or name or "event"
    loc = req.get("location")
    att = req.get("attendees")
    days = req.get("duration_days")
    budget = req.get("budget")
    bits: list[str] = []
    if days:
        bits.append(f"{int(days)}-day {kind}")
    else:
        bits.append(str(kind))
    if loc:
        bits.append(f"in {loc}")
    if att:
        bits.append(f"for {att} people")
    if budget is not None and float(budget) > 0:
        bits.append(f"{format_money(budget, req.get('currency'))} budget")
    line = " ".join(bits)
    if line == "event" and name:
        return name
    return line


def seed_from_title(name: str, note: str | None = None) -> CopilotState:
    from app.services.understand import extract_entities

    text = " ".join(part.strip() for part in (name, note) if part and part.strip())
    ent = extract_entities(text)
    st = empty_state()
    req: dict[str, Any] = {"raw_request": (note or name or "").strip()}
    for key, val in ent.model_dump().items():
        if val is not None and val != "":
            req[key] = val
    req["currency"] = normalize_currency(req.get("currency") or DEFAULT_CURRENCY)
    st.requirements = req
    st.missing_fields = missing_fields(req)
    if st.missing_fields:
        st.phase = "intake"
        st.prompt_field = st.missing_fields[0]
        st.available_actions = _ask_actions(st.missing_fields, specialized=not missing_critical(req))
    else:
        st.phase = "confirm"
        st.available_actions = _confirm_actions()
    return st


def welcome_decision(state: CopilotState) -> PolicyDecision:
    if state.missing_fields:
        return PolicyDecision(
            policy="ASK",
            phase=state.phase,
            missing_fields=state.missing_fields,
            actions=state.available_actions,
            state=state,
            prompt_field=state.prompt_field or state.missing_fields[0],
        )
    return PolicyDecision(
        policy="CONFIRM",
        phase=state.phase,
        missing_fields=[],
        actions=state.available_actions,
        state=state,
    )


def _ask_actions(missing: list[str], *, specialized: bool = False, focus: str | None = None) -> list[CopilotAction]:
    if not missing:
        return []
    field = focus if focus in missing else missing[0]
    actions: list[CopilotAction] = []
    for action_id, label, value in FIELD_CHOICES.get(field, []):
        actions.append(CopilotAction(id=action_id, label=label, payload={"field": field, "value": value}))
    write = WRITE_FOR_FIELD.get(field)
    if write:
        actions.append(CopilotAction(id=write[0], label=write[1], payload={"field": field}))
    if specialized:
        actions.append(CopilotAction(id="skip_extras", label="Skip extras — use defaults", payload={}))
    return actions


def _confirm_actions() -> list[CopilotAction]:
    return [
        CopilotAction(id="proceed", label="Proceed", payload={}),
        CopilotAction(id="edit_brief", label="Edit brief", payload={}),
    ]


def _decide_actions(snapshot: dict[str, Any] | None, missing: list[str]) -> list[CopilotAction]:
    actions: list[CopilotAction] = []
    snap = snapshot or {}
    critic = snap.get("critic_result") or {}
    issues = critic.get("issues") or []
    types = {i.get("issue_type") for i in issues if isinstance(i, dict)}
    messages = " ".join(str(i.get("message", "")) for i in issues if isinstance(i, dict)).lower()
    if "venue_capacity" in types or "venue" in messages:
        actions.append(CopilotAction(id="cheaper_venue", label="Use cheaper / larger venue", payload={}))
    if "budget" in types or "exceeds budget" in messages:
        actions.append(CopilotAction(id="raise_budget", label="Raise budget to fit the plan", payload={}))
    if "schedule" in types or "overlap" in messages or "conflict" in messages:
        actions.append(CopilotAction(id="registration_foyer", label="Put registration in the foyer", payload={}))
    if missing:
        actions.extend(_ask_actions(missing))
    if not actions:
        errors = snap.get("errors") or []
        if errors:
            actions.extend(
                [
                    CopilotAction(id="search_broader", label="Search broader", payload={}),
                    CopilotAction(id="add_vendor_manual", label="Add vendor manually", payload={}),
                    CopilotAction(id="continue_without", label="Continue without this category", payload={}),
                    CopilotAction(id="ask_me", label="Ask me", payload={}),
                ]
            )
        else:
            actions.append(CopilotAction(id="proceed", label="Retry planning", payload={}))
    actions.append(CopilotAction(id="keep_draft", label="Keep this draft", payload={}))
    # unique by id
    seen: set[str] = set()
    uniq: list[CopilotAction] = []
    for a in actions:
        if a.id not in seen:
            seen.add(a.id)
            uniq.append(a)
    return uniq


def _sim_actions() -> list[CopilotAction]:
    return [
        CopilotAction(id="apply_sim", label="Apply to live plan", payload={}),
        CopilotAction(id="discard_sim", label="Keep original plan", payload={}),
    ]


def _done_actions() -> list[CopilotAction]:
    return [
        CopilotAction(id="whatif_attendance", label="What if attendance 800?", payload={}),
        CopilotAction(id="view_budget", label="Review budget", payload={}),
    ]


def _answer_facts(event: Event | None, state: CopilotState, snapshot: dict[str, Any] | None = None) -> dict[str, Any]:
    snap = snapshot or ((event.plan_snapshot if event else None) or {})
    budget = snap.get("budget") or {}
    venues = snap.get("venues") or []
    selected = next((v for v in venues if v.get("selected")), venues[0] if venues else None)
    risks = snap.get("risks") or []
    return {
        "status": event.status if event else state.graph_status,
        "brief": brief_line(state.requirements),
        "remaining": budget.get("remaining"),
        "venue": (selected or {}).get("name"),
        "risks": [r.get("title") for r in risks[:3] if isinstance(r, dict)],
        "graph_status": state.graph_status,
    }


def apply_pick(action_id: str, req: dict[str, Any]) -> dict[str, Any]:
    if not action_id.startswith("pick_"):
        return req
    body = action_id[5:]
    key, _, raw = body.partition("_")
    field = {
        "attendees": "attendees",
        "days": "duration_days",
        "budget": "budget",
        "location": "location",
        "date": "preferred_date",
        "format": "format",
        "overnight": "overnight",
    }.get(key)
    if not field or not raw:
        return req
    if field in {"attendees", "duration_days"}:
        req[field] = int(raw.replace(",", ""))
    elif field == "budget":
        req[field] = float(raw.replace(",", ""))
        req["currency"] = DEFAULT_CURRENCY
    elif field == "overnight":
        req[field] = raw.lower() in {"yes", "true", "hotels"}
    elif field == "preferred_date":
        req["preferred_date"] = raw
        req["date_note"] = raw
    else:
        req[field] = raw.replace("_", " ")
    return req


def _first_number(text: str) -> float | None:
    m = re.search(r"(\d[\d,]*(?:\.\d+)?)", text or "")
    if not m:
        return None
    try:
        return float(m.group(1).replace(",", ""))
    except ValueError:
        return None


def fill_prompt_answer(state: CopilotState, understood: UnderstoodMessage) -> CopilotState:
    field = state.prompt_field
    raw = (understood.raw or "").strip()
    if not field or not raw:
        return state
    req = dict(state.requirements)
    ent = understood.entities
    if field == "attendees" and not req.get("attendees"):
        n = ent.attendees if ent.attendees else _first_number(raw)
        if n and n > 0:
            req["attendees"] = int(n)
    elif field == "duration_days" and not req.get("duration_days"):
        n = ent.duration_days if ent.duration_days else _first_number(raw)
        if n and n > 0:
            req["duration_days"] = int(n)
    elif field == "budget" and (req.get("budget") is None or float(req.get("budget") or 0) <= 0):
        n = ent.budget if ent.budget is not None else _first_number(raw)
        if n is not None and n > 0:
            req["budget"] = float(n)
            req["currency"] = DEFAULT_CURRENCY
    elif field == "location" and not req.get("location"):
        if re.fullmatch(r"[\d,.\s]+", raw):
            n = _first_number(raw)
            if n and 15 <= n <= 20000 and not req.get("attendees"):
                req["attendees"] = int(n)
            elif n and n > 20000 and (req.get("budget") is None or float(req.get("budget") or 0) <= 0):
                req["budget"] = float(n)
                req["currency"] = DEFAULT_CURRENCY
        else:
            loc = ent.location or raw.title()
            if loc and loc.lower() not in CHIP_ECHO:
                req["location"] = loc
    elif field == "preferred_date" and not req.get("preferred_date") and not req.get("date_note"):
        req["date_note"] = raw
        req["preferred_date"] = raw
    elif field == "format" and not req.get("format"):
        req["format"] = (ent.format or raw).lower()
    elif field == "overnight" and req.get("overnight") is None and ent.overnight is not None:
        req["overnight"] = ent.overnight
    state.requirements = req
    return state


def apply_decision_action(state: CopilotState, action_id: str, event: Event | None) -> CopilotState:
    req = dict(state.requirements)
    if action_id.startswith("pick_"):
        req = apply_pick(action_id, req)
        state.requirements = req
        state.missing_fields = missing_fields(req, skipped_specialized=state.skipped_specialized)
        return state
    snap = (event.plan_snapshot if event else None) or {}
    if action_id == "cheaper_venue":
        req["prefer_cheaper"] = True
        raw = req.get("raw_request") or ""
        req["raw_request"] = f"{raw} Prefer the cheapest suitable venue that still fits capacity."
        state.pending_apply = {"replan_mode": "venue"}
    elif action_id == "raise_budget":
        budget = snap.get("budget") or {}
        needed = budget.get("subtotal") or 0
        cont = budget.get("contingency") or 0
        current = float(req.get("budget") or 0)
        req["budget"] = max(current, float(needed) + float(cont) + 1, current * 1.2)
    elif action_id == "registration_foyer":
        raw = req.get("raw_request") or ""
        req["raw_request"] = f"{raw} Put registration in the foyer, not the main hall."
        state.pending_apply = {"replan_mode": "schedule"}
    elif action_id == "apply_sim" and state.last_simulation:
        change = (state.last_simulation.get("change") or {}) if isinstance(state.last_simulation, dict) else {}
        for k in ("attendees", "budget", "duration_days"):
            if change.get(k) is not None:
                req[k] = change[k]
        state.pending_apply = None
    elif action_id == "discard_sim":
        state.last_simulation = None
        state.pending_apply = None
    elif action_id == "keep_draft":
        state.graph_status = state.graph_status or "needs_human_review"
    elif action_id == "whatif_attendance":
        state.pending_apply = {"simulate": {"attendees": 800}}
    elif action_id == "skip_extras":
        state.skipped_specialized = True
    elif action_id in {"search_broader", "continue_without", "add_vendor_manual", "ask_me"}:
        raw = req.get("raw_request") or ""
        req["raw_request"] = f"{raw} Search a broader vendor/venue set if coverage is missing."
    state.requirements = req
    state.missing_fields = missing_fields(req, skipped_specialized=state.skipped_specialized)
    return state


def policy(state: CopilotState, understood: UnderstoodMessage, *, event: Event | None = None) -> PolicyDecision:
    if understood.action_id:
        state = apply_decision_action(state, understood.action_id, event)
    if understood.intent in {"plan", "edit"} or any(
        v is not None for v in understood.entities.model_dump().values()
    ):
        state.requirements = merge_entities(state.requirements, understood)
    if not understood.action_id or understood.action_id in ASK_FOCUS or understood.action_id in WRITE_IDS:
        state = fill_prompt_answer(state, understood)
    state.missing_fields = missing_fields(state.requirements, skipped_specialized=state.skipped_specialized)

    action_id = understood.action_id
    intent = understood.intent
    snapshot = (event.plan_snapshot if event else None) or {}

    if action_id == "keep_draft":
        state.phase = "done"
        state.available_actions = _done_actions()
        return PolicyDecision(policy="DONE", phase=state.phase, actions=state.available_actions, state=state)

    if action_id == "whatif_attendance" or (
        intent == "what_if" and not (understood.simulate_patch or {})
    ):
        if action_id == "whatif_attendance":
            understood.simulate_patch = {"attendees": 800}
            intent = "what_if"

    if intent == "what_if":
        patch = understood.simulate_patch or {}
        if not patch:
            state.phase = "decide"
            state.available_actions = [
                CopilotAction(id="whatif_attendance", label="Attendance 800", payload={"attendees": 800}),
                CopilotAction(id="proceed", label="Keep planning", payload={}),
            ]
            return PolicyDecision(
                policy="ASK",
                phase=state.phase,
                missing_fields=[],
                actions=state.available_actions,
                state=state,
            )
        state.phase = "decide"
        state.available_actions = _sim_actions()
        return PolicyDecision(
            policy="SIMULATE",
            phase=state.phase,
            actions=state.available_actions,
            state=state,
            simulate_patch=patch,
        )

    if action_id == "apply_sim":
        state.phase = "running"
        state.graph_status = "queued"
        state.available_actions = []
        return PolicyDecision(policy="RUN", phase=state.phase, actions=[], state=state, run_graph=True)

    if action_id == "discard_sim":
        state.phase = "done" if state.graph_status == "approved" else "confirm"
        state.available_actions = _confirm_actions() if state.phase == "confirm" else _done_actions()
        return PolicyDecision(policy="DONE" if state.phase == "done" else "CONFIRM", phase=state.phase, actions=state.available_actions, state=state)

    if state.graph_status in {"running", "queued"} and action_id not in {
        "proceed",
        "cheaper_venue",
        "raise_budget",
        "registration_foyer",
        "search_broader",
        "continue_without",
        "add_vendor_manual",
        "apply_sim",
    } and intent != "confirm":
        state.phase = "running"
        state.available_actions = []
        return PolicyDecision(
            policy="ANSWER",
            phase=state.phase,
            actions=[],
            state=state,
            answer_facts=_answer_facts(event, state) | {"note": "planning_in_progress"},
        )

    if intent == "question" and action_id not in {
        "proceed",
        "cheaper_venue",
        "raise_budget",
        "registration_foyer",
        "skip_extras",
    } and not (action_id or "").startswith("pick_") and not (action_id or "").startswith("write_"):
        answered = bool(_first_number(understood.raw or "")) or any(
            understood.entities.model_dump().get(k) is not None
            for k in ("attendees", "duration_days", "budget", "location", "format", "overnight")
        )
        if not answered:
            state.available_actions = state.available_actions or (
                _confirm_actions()
                if not state.missing_fields
                else _ask_actions(state.missing_fields, specialized=not missing_critical(state.requirements))
            )
            if state.graph_status == "approved":
                state.phase = "done"
                state.available_actions = _done_actions()
            return PolicyDecision(
                policy="ANSWER",
                phase=state.phase,
                missing_fields=state.missing_fields,
                actions=state.available_actions,
                state=state,
                answer_facts=_answer_facts(event, state),
            )

    if state.missing_fields and action_id not in {
        "cheaper_venue",
        "raise_budget",
        "registration_foyer",
        "search_broader",
        "continue_without",
        "add_vendor_manual",
    }:
        state.phase = "intake"
        prompt_field = ASK_FOCUS.get(action_id or "") or (
            state.missing_fields[0] if state.missing_fields else None
        )
        if prompt_field and prompt_field not in state.missing_fields:
            prompt_field = state.missing_fields[0]
        state.prompt_field = prompt_field
        state.available_actions = _ask_actions(
            state.missing_fields,
            specialized=not missing_critical(state.requirements),
            focus=prompt_field,
        )
        return PolicyDecision(
            policy="ASK",
            phase=state.phase,
            missing_fields=state.missing_fields,
            actions=state.available_actions,
            state=state,
            prompt_field=prompt_field,
        )

    run_ids = {
        "proceed",
        "cheaper_venue",
        "raise_budget",
        "registration_foyer",
        "search_broader",
        "continue_without",
        "add_vendor_manual",
    }
    if intent == "confirm" or action_id in run_ids:
        state.phase = "running"
        state.graph_status = "queued"
        state.available_actions = []
        return PolicyDecision(policy="RUN", phase=state.phase, actions=[], state=state, run_graph=True)

    if state.graph_status in {"awaiting_input", "needs_human_review"}:
        return policy_after_graph(state, snapshot)

    state.phase = "confirm"
    state.available_actions = _confirm_actions()
    return PolicyDecision(
        policy="CONFIRM",
        phase=state.phase,
        missing_fields=[],
        actions=state.available_actions,
        state=state,
    )


def policy_after_graph(state: CopilotState, snapshot: dict[str, Any]) -> PolicyDecision:
    status = (snapshot or {}).get("status") or state.graph_status
    state.graph_status = status
    snap_missing = list((snapshot or {}).get("missing_fields") or [])
    if snap_missing:
        for f, v in (snapshot.get("requirements") or {}).items():
            if v is not None and v != "":
                state.requirements[f] = v
        state.missing_fields = missing_fields(state.requirements, skipped_specialized=state.skipped_specialized) or snap_missing
    facts = _answer_facts(None, state, snapshot)
    if status == "approved":
        state.phase = "done"
        state.available_actions = _done_actions()
        return PolicyDecision(
            policy="DONE",
            phase=state.phase,
            actions=state.available_actions,
            state=state,
            answer_facts=facts,
        )
    if status == "awaiting_input" or (snap_missing and status not in {"needs_human_review", "needs_decision", "approved"}):
        state.phase = "intake"
        state.graph_status = "awaiting_input"
        miss = state.missing_fields or snap_missing
        state.available_actions = _ask_actions(miss, specialized=not missing_critical(state.requirements))
        return PolicyDecision(
            policy="ASK",
            phase=state.phase,
            missing_fields=miss,
            actions=state.available_actions,
            state=state,
            answer_facts=facts,
        )
    state.phase = "decide"
    state.graph_status = status or "needs_human_review"
    state.available_actions = _decide_actions(snapshot, state.missing_fields)
    return PolicyDecision(
        policy="DECIDE",
        phase=state.phase,
        missing_fields=state.missing_fields,
        actions=state.available_actions,
        state=state,
        answer_facts=facts,
    )


def requirements_for_graph(state: CopilotState) -> dict[str, Any]:
    req = state.requirements
    parsed = parse_preferred_date(req.get("preferred_date") or req.get("date_note"))
    date_note = req.get("date_note") or (req.get("preferred_date") if isinstance(req.get("preferred_date"), str) else None)
    return {
        "event_type": req.get("event_type") or "event",
        "location": req.get("location"),
        "attendees": int(req.get("attendees") or 1),
        "duration_days": int(req.get("duration_days") or 1),
        "budget": float(req.get("budget") or 0),
        "currency": normalize_currency(req.get("currency") or DEFAULT_CURRENCY),
        "preferred_date": parsed.isoformat() if parsed else None,
        "date_note": date_note,
        "format": req.get("format"),
        "overnight": req.get("overnight"),
        "audience": req.get("audience"),
        "requirements": req.get("requirements") or [],
        "raw_request": req.get("raw_request") or brief_line(req),
        "audience_type": req.get("audience_type"),
        "vip_count": req.get("vip_count"),
        "speaker_count": req.get("speaker_count"),
        "staff_count": req.get("staff_count"),
        "accessibility": req.get("accessibility"),
        "catering": req.get("catering"),
        "av": req.get("av"),
        "stage": req.get("stage"),
        "registration": req.get("registration"),
        "parking": req.get("parking"),
        "security": req.get("security"),
        "transport": req.get("transport"),
        "accommodation": req.get("accommodation"),
        "branding": req.get("branding"),
        "photo_video": req.get("photo_video"),
        "internet": req.get("internet"),
        "venue_style": req.get("venue_style"),
        "budget_priority": req.get("budget_priority"),
        "preferred_vendors": req.get("preferred_vendors") or [],
        "description": req.get("description"),
        "objectives": req.get("objectives") or [],
        "tags": req.get("tags") or [],
        "prefer_cheaper": bool(req.get("prefer_cheaper")),
    }


def user_request_from_state(state: CopilotState) -> str:
    raw = (state.requirements.get("raw_request") or "").strip()
    line = brief_line(state.requirements)
    if placeholder_brief(line):
        return raw
    if raw and not placeholder_brief(raw) and line.lower() not in raw.lower():
        return f"{raw}\n{line}"
    return raw or line

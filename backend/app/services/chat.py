from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, Field

from app.domain.models import ChatReply
from app.llm.base import LLMError, LLMMessage
from app.llm.factory import get_llm_provider
from app.llm.mock import _parse_requirements


class ClassifiedChat(BaseModel):
    intent: str
    reply: str = ""
    simulate_patch: dict[str, Any] | None = None


BRIEF_HINTS = (
    "sports",
    "wedding",
    "conference",
    "summit",
    "festival",
    "concert",
    "gala",
    "retreat",
    "workshop",
    "party",
    "tournament",
    "music",
    "classic",
    "classical",
    "making a",
    "organize",
    "organise",
    "plan a",
    "planning a",
    "we are making",
    "i want to",
    "need to plan",
)

PLACE_HINTS = (
    "cairo",
    "alexandria",
    "alexendria",
    "alex",
    "sahel",
    "giza",
    "dubai",
    "egypt",
    "london",
    "riyadh",
)


def extract_simulate_patch(text: str) -> dict[str, Any]:
    t = text.lower()
    patch: dict[str, Any] = {}
    m = re.search(r"(?:attendance|attendees|guests|people)\D{0,20}(\d[\d,]*)", t)
    if m:
        patch["attendees"] = int(m.group(1).replace(",", ""))
    else:
        m = re.search(r"(?:increases?|drops?|to)\s+(\d[\d,]*)", t)
        if m and ("what if" in t or "simulate" in t):
            n = int(m.group(1).replace(",", ""))
            if n >= 20:
                patch["attendees"] = n
    m = re.search(r"\$\s*([\d,]+)", t)
    if m and ("budget" in t or "what if" in t or "simulate" in t):
        patch["budget"] = float(m.group(1).replace(",", ""))
    m = re.search(r"(\d+)\s*-?\s*days?", t)
    if m and ("what if" in t or "simulate" in t or "becomes" in t):
        patch["duration_days"] = int(m.group(1))
    if "unavailable" in t or "venue becomes" in t:
        patch["venue_unavailable"] = True
    return patch


def looks_like_event_brief(text: str) -> bool:
    t = text.lower()
    if len(t) < 8:
        return False
    if t.startswith(("what if", "simulate", "why ", "how ", "status", "what is", "what's")):
        return False
    if any(h in t for h in BRIEF_HINTS):
        return True
    has_place = bool(re.search(r"\bin\s+[a-z]", t)) or any(p in t for p in PLACE_HINTS)
    has_event_word = any(w in t for w in ("event", "show", "gig", "recital", "ceremony"))
    has_sizing = bool(
        re.search(r"\d+\s*(attendee|guest|people|person|day)", t)
        or re.search(r"budget|\$\s*\d|\d[\d,]*\s*\$", t)
    )
    return (has_place and has_event_word) or (has_sizing and (has_place or has_event_word))


def heuristic_intent(text: str) -> ClassifiedChat:
    t = text.lower().strip()
    if "what if" in t or "simulate" in t or t.startswith("run a what"):
        patch = extract_simulate_patch(text)
        if not patch:
            return ClassifiedChat(
                intent="clarify",
                reply=(
                    "I can run a what-if, but I need a specific change. "
                    "For example: “What if attendance increases to 800?”, "
                    "“What if the budget drops to $20,000?”, or "
                    "“What if the event becomes 5 days?”"
                ),
            )
        return ClassifiedChat(intent="simulate", simulate_patch=patch)
    if any(k in t for k in ("replan", "start planning", "run the agents", "plan this", "run planning")):
        return ClassifiedChat(intent="plan")
    if looks_like_event_brief(t):
        return ClassifiedChat(intent="plan")
    return ClassifiedChat(intent="question")


async def classify_and_reply(text: str, *, event_status: str | None, budget_remaining: Any) -> ClassifiedChat:
    classified = heuristic_intent(text)
    try:
        llm = get_llm_provider()
        view = await llm.complete_structured(
            ChatReply,
            [
                LLMMessage(
                    role="system",
                    content=(
                        "You are EventOS, an event-planning orchestration assistant. "
                        "Return JSON: intent (plan|simulate|question|clarify), reply, "
                        "simulate_patch (object or null with optional attendees, budget, duration_days, venue_unavailable). "
                        "Use plan when the user describes an event to plan. "
                        "Use simulate only when they specify a concrete what-if change. "
                        "Use clarify when they say what-if without a change. "
                        "Do not invent that a simulation already ran."
                    ),
                ),
                LLMMessage(role="user", content=text),
            ],
        )
        if isinstance(view, ChatReply):
            llm_intent = (view.intent or "").lower().strip()
            if classified.intent == "question" and llm_intent in {"plan", "simulate", "clarify", "question"}:
                classified.intent = llm_intent
                if view.simulate_patch:
                    classified.simulate_patch = view.simulate_patch
            if classified.intent == "simulate" and not classified.simulate_patch and view.simulate_patch:
                classified.simulate_patch = view.simulate_patch
            if view.reply and classified.intent in {"question", "clarify"}:
                classified.reply = view.reply
    except (LLMError, Exception):
        pass

    if classified.intent == "question" and not classified.reply:
        remaining = budget_remaining if budget_remaining is not None else "n/a"
        classified.reply = (
            f"This event is currently “{event_status or 'unknown'}”"
            + (f" with ${remaining:,.0f} remaining in the planned budget." if isinstance(remaining, (int, float)) else f". Planned remaining budget: {remaining}.")
            + " Describe the event you want (type, city, attendees, days, budget) and I will run the planning agents. "
            "Or ask a what-if with a specific number, e.g. attendance 800."
        )
    if classified.intent == "plan" and not classified.reply:
        req = _parse_requirements(text)
        loc = req.get("location") or "the location you named"
        classified.reply = (
            f"Understood — I'll run the planning agents for a {req.get('event_type', 'event')} "
            f"in {loc}. Watch Live Agents for Requirements → Venue → Vendors → Budget → Critic."
        )
    if classified.intent == "simulate" and not classified.reply:
        classified.reply = "Running a what-if simulation on a copy of the plan. The original plan is unchanged."
    return classified

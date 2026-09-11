import json
from typing import Any

from pydantic import BaseModel, ValidationError

from app.llm.base import LLMError, LLMMessage, LLMProvider
from app.services.intake import extract_specialized, parse_preferred_date


class MockLLMProvider(LLMProvider):
    """Deterministic structured output for tests and no-key demos."""

    name = "mock"

    async def complete_structured(
        self,
        schema: type[BaseModel],
        messages: list[LLMMessage],
        *,
        tools: list[dict[str, Any]] | None = None,
    ) -> BaseModel:
        user = " ".join(m.content for m in messages if m.role == "user")
        name = schema.__name__
        try:
            if name == "EventRequirements":
                return schema.model_validate(_parse_requirements(user))
            if name == "CriticLLMView":
                return schema.model_validate(
                    {
                        "narrative": "Rule-based critic applied; see structured issues.",
                        "score_hint": 80,
                    }
                )
            if name == "ChatReply":
                classified_intent = "question"
                tl = user.lower()
                if "what if" in tl or "simulate" in tl:
                    classified_intent = "simulate"
                elif any(k in tl for k in ("sports", "wedding", "conference", "making a", "plan a")):
                    classified_intent = "plan"
                return schema.model_validate(
                    {
                        "intent": classified_intent,
                        "reply": "Acknowledged.",
                        "simulate_patch": None,
                    }
                )
            if name == "UnderstoodMessage":
                from app.services.understand import heuristic_understand

                return heuristic_understand(user)
            if name == "CopilotSpeech":
                return schema.model_validate({"message": ""})
        except ValidationError as exc:
            raise LLMError(str(exc)) from exc
        # Best-effort empty structured object
        try:
            return schema.model_validate({})
        except ValidationError as exc:
            raise LLMError(f"Mock LLM cannot satisfy {name}: {exc}") from exc


def _parse_requirements(text: str) -> dict[str, Any]:
    import re

    t = text.lower()
    attendees = 0
    m = re.search(r"(\d[\d,]*)\s*(attendees?|people|guests?)", t)
    if m:
        attendees = int(m.group(1).replace(",", ""))
    days = 0
    m = re.search(r"(\d+)\s*-?\s*days?", t)
    if m:
        days = int(m.group(1))
    budget = 0.0
    currency = "EGP"
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
        currency = "USD" if "$" in m.group(0) else "EGP"
    location = None
    aliases = (
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
    for needle, label in aliases:
        if needle in t:
            location = label
            break
    if location is None:
        m = re.search(r"\bin\s+([a-z][a-z\s]{2,40}?)(?:\s+for|\s+with|$)", t)
        if m:
            location = m.group(1).strip().title()
    event_type = "event"
    if "classic" in t or "classical" in t or "music" in t or "concert" in t:
        event_type = "classical music concert" if "classic" in t or "classical" in t else "music event"
    elif "conference" in t or "summit" in t:
        event_type = "technology conference" if "tech" in t or "ai" in t else "conference"
    elif "sport" in t:
        event_type = "sports event"
    elif "wedding" in t:
        event_type = "wedding"
    spec = extract_specialized(text)
    return {
        "event_type": event_type,
        "location": location,
        "attendees": attendees,
        "duration_days": days,
        "budget": budget,
        "currency": currency,
        "preferred_date": parse_preferred_date(spec.get("preferred_date")),
        "date_note": spec.get("date_note"),
        "format": spec.get("format"),
        "overnight": spec.get("overnight"),
        "audience": "technology professionals" if "tech" in t or "ai" in t else "general",
        "requirements": ["WiFi", "AV equipment", "catering", "registration area"],
        "raw_request": text[:2000],
    }


def dumps(obj: Any) -> str:
    return json.dumps(obj)

"""First-agent intake: extract what was said, then ask for the rest.

Critical fields block planning. Specialized fields (date, format, overnight)
are asked next; the organizer can skip them and use defaults.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

CRITICAL = ("location", "attendees", "duration_days", "budget")

SPECIALIZED_ALWAYS = ("preferred_date", "format")
SPECIALIZED_CONFERENCE = ("overnight",)

FIELD_LABELS = {
    "location": "city",
    "attendees": "headcount",
    "duration_days": "duration in days",
    "budget": "budget",
    "preferred_date": "date or month",
    "format": "indoor / outdoor / hybrid",
    "overnight": "whether attendees need hotels",
}

MONTHS = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
}


def missing_critical(req: dict[str, Any] | None) -> list[str]:
    req = req or {}
    missing: list[str] = []
    if not str(req.get("location") or "").strip():
        missing.append("location")
    att = req.get("attendees")
    if not att or int(att) <= 0:
        missing.append("attendees")
    days = req.get("duration_days")
    if not days or int(days) <= 0:
        missing.append("duration_days")
    budget = req.get("budget")
    if budget is None or float(budget) <= 0:
        missing.append("budget")
    return missing


def _event_kind(req: dict[str, Any]) -> str:
    return str(req.get("event_type") or "").lower()


def specialized_fields_for(req: dict[str, Any] | None) -> tuple[str, ...]:
    req = req or {}
    fields = list(SPECIALIZED_ALWAYS)
    kind = _event_kind(req)
    if any(x in kind for x in ("conference", "summit", "workshop", "tech")):
        fields.extend(SPECIALIZED_CONFERENCE)
    return tuple(fields)


def missing_specialized(req: dict[str, Any] | None) -> list[str]:
    req = req or {}
    missing: list[str] = []
    if not str(req.get("preferred_date") or req.get("date_note") or "").strip():
        missing.append("preferred_date")
    if not str(req.get("format") or "").strip():
        missing.append("format")
    if "overnight" in specialized_fields_for(req) and req.get("overnight") is None:
        missing.append("overnight")
    return missing


def missing_fields(req: dict[str, Any] | None, *, skipped_specialized: bool = False) -> list[str]:
    crit = missing_critical(req)
    if crit:
        return crit
    if skipped_specialized:
        return []
    return missing_specialized(req)


def extract_specialized(text: str) -> dict[str, Any]:
    t = (text or "").lower()
    out: dict[str, Any] = {}
    if "hybrid" in t:
        out["format"] = "hybrid"
    elif "outdoor" in t or "open air" in t or "open-air" in t:
        out["format"] = "outdoor"
    elif "indoor" in t:
        out["format"] = "indoor"

    if re.search(r"\bno\s+(hotels?|overnight|rooms?)\b", t) or "daytime only" in t:
        out["overnight"] = False
    elif "overnight" in t or "hotel" in t or "rooms for attendees" in t:
        out["overnight"] = True

    date_note = _date_note(t)
    if date_note:
        out["preferred_date"] = date_note
        out["date_note"] = date_note
    return out


def _date_note(t: str) -> str | None:
    iso = re.search(r"\b(20\d{2}-\d{2}-\d{2})\b", t)
    if iso:
        return iso.group(1)
    for name, month in MONTHS.items():
        if name in t:
            year = None
            ym = re.search(rf"{name}\s+(20\d{{2}})", t)
            my = re.search(rf"(20\d{{2}})\s+{name}", t)
            if ym:
                year = int(ym.group(1))
            elif my:
                year = int(my.group(1))
            else:
                year = 2026
            return f"{year:04d}-{month:02d}-01"
    return None


def parse_preferred_date(value: Any) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value
    text = str(value).strip()
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        pass
    spec = extract_specialized(text)
    note = spec.get("preferred_date")
    if note:
        try:
            return datetime.fromisoformat(note)
        except ValueError:
            return None
    return None


def weather_date(req: Any) -> str:
    """ISO date string for weather lookup, with a stable demo default."""
    if req is None:
        return "2026-11-15"
    preferred = getattr(req, "preferred_date", None)
    if preferred is None and isinstance(req, dict):
        preferred = parse_preferred_date(req.get("preferred_date") or req.get("date_note"))
    if isinstance(preferred, datetime):
        return preferred.date().isoformat()
    note = getattr(req, "date_note", None)
    if note is None and isinstance(req, dict):
        note = req.get("date_note") or req.get("preferred_date")
    parsed = parse_preferred_date(note)
    if parsed:
        return parsed.date().isoformat()
    return "2026-11-15"

from typing import Any

from app.domain.models import EventRequirements
from app.domain.state import EventState


def _dump(obj: Any) -> Any:
    if obj is None:
        return None
    if hasattr(obj, "model_dump"):
        return obj.model_dump(mode="json")
    if isinstance(obj, list):
        return [_dump(x) for x in obj]
    return obj


def snapshot_state(state: EventState) -> dict[str, Any]:
    return {
        "event_id": state.get("event_id"),
        "run_id": state.get("run_id"),
        "status": state.get("status"),
        "iteration": state.get("iteration"),
        "requirements": _dump(state.get("requirements")),
        "venues": _dump(state.get("venues") or []),
        "vendors": _dump(state.get("vendors") or []),
        "budget": _dump(state.get("budget")),
        "schedule": _dump(state.get("schedule")),
        "logistics": _dump(state.get("logistics")),
        "risks": _dump(state.get("risks") or []),
        "critic_result": _dump(state.get("critic_result")),
        "missing_fields": state.get("missing_fields") or [],
        "errors": list(state.get("errors") or []),
    }


def hydrate_requirements(raw: Any) -> EventRequirements | None:
    if raw is None:
        return None
    return raw if isinstance(raw, EventRequirements) else EventRequirements.model_validate(raw)

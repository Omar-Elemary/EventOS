from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ActivityLog


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def add_activity(
    session: AsyncSession,
    event_id: str,
    *,
    actor: str,
    action: str,
    summary: str,
    payload: dict[str, Any] | None = None,
    state_version: int = 0,
) -> ActivityLog:
    """Append-only. Callers must not update or delete ActivityLog rows."""
    row = ActivityLog(
        event_id=event_id,
        at=utcnow(),
        actor=actor,
        action=action,
        summary=summary,
        payload=payload or {},
        state_version=state_version,
    )
    session.add(row)
    return row

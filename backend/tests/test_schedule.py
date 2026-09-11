from datetime import datetime, timezone

import pytest

from app.domain.models import Schedule, ScheduleItem
from app.tools.schedule_conflicts import detect_conflicts, ScheduleConflictCheckerTool


def _item(i, title, h0, h1, loc="Hall", deps=None):
    base = datetime(2026, 11, 15, tzinfo=timezone.utc)
    return ScheduleItem(
        id=i,
        title=title,
        start_time=base.replace(hour=h0),
        end_time=base.replace(hour=h1),
        location=loc,
        depends_on=deps or [],
    )


def test_overlap_conflict():
    s = Schedule(items=[_item("a", "A", 9, 11), _item("b", "B", 10, 12)])
    r = detect_conflicts(s)
    assert r.conflicts


def test_dependency_conflict():
    s = Schedule(items=[_item("a", "Setup", 9, 11), _item("b", "Keynote", 10, 12, deps=["a"])])
    r = detect_conflicts(s)
    assert any("starts before dependency" in c for c in r.conflicts)


def test_clean_schedule():
    s = Schedule(items=[_item("a", "Setup", 7, 8), _item("b", "Keynote", 8, 10, deps=["a"])])
    r = detect_conflicts(s)
    assert r.conflicts == []


@pytest.mark.asyncio
async def test_tool_interface():
    tool = ScheduleConflictCheckerTool()
    r = await tool.execute(Schedule(items=[_item("a", "Setup", 7, 8)]))
    assert r.conflicts == []


@pytest.mark.asyncio
async def test_default_multiday_program_uses_foyer_and_is_clean():
    from app.agents.schedule import _logic
    from app.domain.models import EventRequirements, VenueCandidate
    from app.graph.deps import NullSink, build_deps

    deps = build_deps(sink=NullSink())
    venue = VenueCandidate(
        name="Cairo Conference Centre",
        location="Cairo",
        capacity=800,
        estimated_cost=12000,
        suitability_score=90,
        selected=True,
    )
    req = EventRequirements(
        event_type="conference",
        location="Cairo",
        attendees=500,
        duration_days=3,
        budget=30000,
    )
    out = await _logic({"requirements": req, "venues": [venue]}, deps)
    schedule = out["schedule"]
    assert schedule.conflicts == []
    regs = [i for i in schedule.items if "Registration" in i.title]
    assert len(regs) == 3
    assert all("foyer" in (i.location or "").lower() for i in regs)
    lunches = [i for i in schedule.items if "Lunch" in i.title or "Catering" in i.title]
    assert lunches
    assert all("dining" in (i.location or "").lower() for i in lunches)

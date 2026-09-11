"""End-to-end agent graph: every specialist runs, no silent failures."""

import pytest

from app.workers.planner import run_graph_memory


BRIEFS = [
    ("cairo_summit", "Plan a 3-day technology conference in Cairo for 500 attendees with a $30,000 budget indoor November 2026.", "approved", "cairo"),
    (
        "hurghada_koftas",
        "Plan a 1-day Koftas day in Hurghada for 1000 people with an 800000 EGP budget indoor November 2026.",
        "approved",
        "hurghada",
    ),
    (
        "alexandria_music",
        "Plan a 2-day classical music concert in Alexandria for 400 attendees with a $2000 budget indoor.",
        "approved",
        "alexandria",
    ),
    (
        "london_fallback",
        "Plan a 1-day conference in London for 200 attendees with a $15000 budget indoor.",
        "approved",
        "london",
    ),
]


@pytest.mark.asyncio
@pytest.mark.parametrize("name,brief,status,city", BRIEFS)
async def test_agent_graph_completes_without_errors(name, brief, status, city):
    result = await run_graph_memory(brief)
    assert result.get("status") == status, (name, result.get("status"), result.get("errors"), result.get("missing_fields"))
    errors = result.get("errors") or []
    assert not errors, (name, errors)
    agents = [m.agent for m in result.get("agent_messages") or []]
    failed = [m for m in (result.get("agent_messages") or []) if getattr(m, "status", None) and getattr(m.status, "value", m.status) == "failed"]
    assert not failed, (name, [(m.agent, m.errors) for m in failed])
    for required in ("requirements", "orchestrator", "venue", "vendor", "budget", "schedule", "logistics", "risk", "critic"):
        assert required in agents, (name, required, agents)
    venues = result.get("venues") or []
    selected = next((v for v in venues if getattr(v, "selected", False)), venues[0] if venues else None)
    assert selected is not None
    assert city in selected.location.lower() or city in selected.name.lower()
    budget = result.get("budget")
    assert budget is not None
    assert budget.remaining >= -1
    critic = result.get("critic_result")
    assert critic is not None
    assert critic.approved is True
    schedule = result.get("schedule")
    assert schedule is not None
    assert not (schedule.conflicts or [])


@pytest.mark.asyncio
async def test_incomplete_brief_stops_before_specialists():
    result = await run_graph_memory("Plan a workshop for 40 attendees with a $5000 budget.")
    assert result.get("status") == "awaiting_input"
    agents = [m.agent for m in result.get("agent_messages") or []]
    assert "requirements" in agents
    assert "venue" not in agents
    assert not (result.get("errors") or [])

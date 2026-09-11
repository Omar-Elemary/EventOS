import pytest

from app.workers.planner import run_graph_memory


@pytest.mark.asyncio
async def test_happy_path_full_graph():
    result = await run_graph_memory(
        "Plan a 3-day technology conference in Cairo for 500 attendees with a $30,000 budget."
    )
    assert result.get("requirements") is not None
    assert result.get("venues")
    assert result.get("vendors")
    assert result.get("budget") is not None
    assert result.get("schedule") is not None
    assert result.get("logistics") is not None
    assert result.get("critic_result") is not None
    assert result.get("status") == "approved"
    agents = [m.agent for m in result.get("agent_messages") or []]
    for name in ("requirements", "venue", "vendor", "budget", "schedule", "logistics", "risk", "critic"):
        assert name in agents


@pytest.mark.asyncio
async def test_over_budget_replan_then_approve():
    result = await run_graph_memory(
        "Plan a 3-day technology conference in Cairo for 500 attendees with a $30,000 budget.",
        force_over_budget=True,
    )
    critic = result.get("critic_result")
    assert critic is not None
    assert result.get("status") == "approved"
    assert result["budget"].remaining >= 0
    assert critic.approved is True


@pytest.mark.asyncio
async def test_incomplete_brief_does_not_invent_numbers():
    result = await run_graph_memory("Plan a conference in Cairo")
    assert result.get("status") == "awaiting_input"
    missing = result.get("missing_fields") or []
    assert "attendees" in missing
    assert "budget" in missing
    req = result.get("requirements")
    attendees = req.attendees if hasattr(req, "attendees") else (req or {}).get("attendees")
    assert not attendees


@pytest.mark.asyncio
async def test_hurghada_koftas_day_approves():
    result = await run_graph_memory(
        "Plan a 1-day Koftas day in Hurghada for 1000 people with an 800000 EGP budget indoor November 2026."
    )
    assert result.get("status") == "approved"
    venues = result.get("venues") or []
    selected = next((v for v in venues if getattr(v, "selected", False)), venues[0] if venues else None)
    assert selected is not None
    assert "cairo" not in selected.location.lower()
    assert "hurghada" in selected.location.lower()
    assert selected.capacity >= 1000
    budget = result.get("budget")
    assert budget is not None
    assert budget.remaining >= -1


@pytest.mark.asyncio
async def test_missing_location_awaits_input():
    result = await run_graph_memory("Plan a 2-day workshop for 40 attendees with a $5000 budget.")
    assert result.get("status") == "awaiting_input"
    assert "location" in (result.get("missing_fields") or [])

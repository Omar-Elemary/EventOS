import pytest

from app.domain.models import EventRequirements
from app.graph.deps import build_deps
from app.services.research import InMemoryResearchMemory, research_venues, research_weather
from app.tools.venue_search import MockVenueSearchTool


@pytest.mark.asyncio
async def test_venue_search_is_cached_until_inputs_change():
    deps = build_deps(research=InMemoryResearchMemory())
    calls = {"n": 0}
    inner = MockVenueSearchTool()

    class Counting(MockVenueSearchTool):
        async def _run(self, payload):
            calls["n"] += 1
            return await inner._run(payload)

    deps.tools.venue_search = Counting()
    req = EventRequirements(
        event_type="conference",
        location="Cairo",
        attendees=500,
        duration_days=3,
        budget=30000,
    )
    first, cached_first = await research_venues(deps, req, event_id="e1")
    second, cached_second = await research_venues(deps, req, event_id="e1")
    assert calls["n"] == 1
    assert cached_first is False
    assert cached_second is True
    assert first and second
    assert second[0].from_cache is True

    elsewhere = req.model_copy(update={"location": "London"})
    await research_venues(deps, elsewhere, event_id="e1")
    assert calls["n"] == 2


@pytest.mark.asyncio
async def test_weather_cache_hit():
    deps = build_deps(research=InMemoryResearchMemory())
    calls = {"n": 0}
    original = deps.tools.weather_lookup.execute

    async def wrapped(raw):
        calls["n"] += 1
        return await original(raw)

    deps.tools.weather_lookup.execute = wrapped  # type: ignore[method-assign]
    w1, c1 = await research_weather(deps, "Cairo", "2026-11-15")
    w2, c2 = await research_weather(deps, "Cairo", "2026-11-15")
    assert calls["n"] == 1
    assert c1 is False and c2 is True
    assert w2.from_cache is True
    assert w1.condition == w2.condition

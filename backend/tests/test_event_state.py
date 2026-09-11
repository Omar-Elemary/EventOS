import pytest

from app.core.db import Base, init_engine, session_maker
from app.domain.budget import explain_budget
from app.domain.models import Budget, BudgetItem, VenueCandidate
from app.models import Event, User
from app.services.persistence import persist_plan
from app.services.simulate import impact_diff


@pytest.mark.asyncio
async def test_persist_increments_version_and_writes_event_venues():
    engine = init_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with session_maker()() as session:
        session.add(User(id="u1", email="a@b.c", name="A"))
        session.add(Event(id="e1", owner_id="u1", name="Summit", location="Cairo", attendees=500, budget=30000, status="draft"))
        await session.commit()
        snap = {
            "status": "approved",
            "requirements": {"event_type": "conference", "location": "Cairo", "attendees": 500, "duration_days": 3, "budget": 30000, "currency": "USD"},
            "venues": [
                {
                    "name": "Hall A",
                    "location": "Cairo",
                    "capacity": 600,
                    "estimated_cost": 8000,
                    "facilities": ["WiFi"],
                    "suitability_score": 90,
                    "selected": True,
                    "source_tier": "official",
                    "provider": "mock",
                    "price_type": "estimated",
                    "requires_quote": False,
                }
            ],
            "vendors": [],
            "budget": {
                "total_budget": 30000,
                "currency": "USD",
                "subtotal": 8000,
                "contingency": 800,
                "remaining": 21200,
                "committed": 0,
                "estimated": 8000,
                "items": [{"category": "venue", "description": "Hall A", "estimated_cost": 8000, "actual_cost": 0, "status": "estimated"}],
            },
            "schedule": {"items": [], "conflicts": []},
            "risks": [],
            "critic_result": {"approved": True, "score": 90, "issues": []},
        }
        await persist_plan(session, "e1", snap)
        ev = await session.get(Event, "e1")
        assert ev.event_state_version == 1
        assert ev.status == "approved"
        await persist_plan(session, "e1", snap)
        ev = await session.get(Event, "e1")
        assert ev.event_state_version == 2


def test_budget_explainer_names_venue_share():
    budget = Budget(
        total_budget=8000,
        currency="USD",
        items=[
            BudgetItem(category="venue", description="Hall A", estimated_cost=5000),
            BudgetItem(category="av", description="AV", estimated_cost=4000),
        ],
        contingency=900,
        subtotal=9000,
        remaining=-1900,
        committed=0,
        estimated=9000,
    )
    venues = [
        VenueCandidate(name="Hall A", location="Cairo", capacity=500, estimated_cost=5000, suitability_score=80, selected=True),
        VenueCandidate(name="Hall B", location="Cairo", capacity=500, estimated_cost=3000, suitability_score=75, selected=False),
    ]
    explained = explain_budget(budget, venues, attendees=500)
    assert explained["over_budget"] is True
    assert any("Venue consumes" in line for line in explained["explanation"])
    assert explained["cheapest_alternatives"]


def test_impact_diff_budget_and_venue():
    original = {
        "budget": {"subtotal": 100, "contingency": 10, "items": [{"category": "catering", "estimated_cost": 40}]},
        "venues": [{"name": "A", "selected": True}],
        "schedule": {"items": [1, 2]},
        "risks": [1],
    }
    new = {
        "budget": {"subtotal": 180, "contingency": 18, "items": [{"category": "catering", "estimated_cost": 70}]},
        "venues": [{"name": "B", "selected": True}],
        "schedule": {"items": [1, 2, 3]},
        "risks": [1, 2],
    }
    diff = impact_diff(original, new, {"attendees": 800})
    assert diff["budget"] == 88
    assert diff["venue"] == "Changed"
    assert diff["catering"] == 30
    assert diff["schedule"] == 1

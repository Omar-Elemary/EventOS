from app.domain.enums import DataSourceType, IssueType, RiskSeverity, VendorCategory
from app.domain.models import (
    Budget,
    BudgetItem,
    CriticIssue,
    EventRequirements,
    RiskCheckerInput,
    VenueCandidate,
    Vendor,
)
from app.graph.routing import pick_next_agent, route_after_critic
from app.tools.risk_checker import evaluate_risks
from app.tools.venue_search import MockVenueSearchTool
from app.domain.models import VenueSearchInput
import pytest


@pytest.mark.asyncio
async def test_hurghada_does_not_fall_back_to_cairo():
    tool = MockVenueSearchTool()
    venues = await tool.execute(
        VenueSearchInput(location="Hurghada", attendee_count=1000, event_type="event", required_facilities=[])
    )
    assert venues
    assert all("hurghada" in v.location.lower() for v in venues)
    selected = next(v for v in venues if v.selected)
    assert selected.capacity >= 1000
    assert "cairo" not in selected.name.lower()


@pytest.mark.asyncio
async def test_venue_search_tagged_mock():
    tool = MockVenueSearchTool()
    venues = await tool.execute(
        VenueSearchInput(location="Cairo", attendee_count=500, event_type="conference", required_facilities=["WiFi"])
    )
    assert venues
    assert all(v.source_type == DataSourceType.mock for v in venues)
    assert any(v.capacity >= 500 and v.selected for v in venues)


def test_risk_logistics_conflict_without_proposed_fix():
    from app.domain.models import Logistics, LogisticsItem

    req = EventRequirements(event_type="c", location="Cairo", attendees=500, duration_days=3, budget=30000)
    risks = evaluate_risks(
        RiskCheckerInput(
            requirements=req,
            vendors=[],
            logistics=Logistics(
                items=[LogisticsItem(area="transport", detail="shuttles", proposed_fix=None)],
                conflicts=["Shuttle capacity tight at day-1 close"],
            ),
        )
    )
    types = {r.issue_type for r in risks}
    assert IssueType.logistics in types
    log = next(r for r in risks if r.issue_type == IssueType.logistics)
    assert log.explanation
    assert log.solutions
    assert all(isinstance(r.mitigation, str) and r.mitigation for r in risks)


def test_risk_capacity_and_budget():
    req = EventRequirements(event_type="c", location="Cairo", attendees=800, duration_days=3, budget=1000)
    venue = VenueCandidate(
        name="Small",
        location="Cairo",
        capacity=400,
        estimated_cost=100,
        suitability_score=10,
        selected=True,
        source_type=DataSourceType.mock,
    )
    budget = Budget(
        total_budget=1000,
        currency="USD",
        items=[BudgetItem(category="venue", description="x", estimated_cost=2000)],
        contingency=200,
        subtotal=2000,
        remaining=-1200,
    )
    risks = evaluate_risks(RiskCheckerInput(requirements=req, venues=[venue], budget=budget, vendors=[]))
    types = {r.issue_type for r in risks}
    assert IssueType.venue_capacity in types
    assert IssueType.budget in types
    cap = next(r for r in risks if r.title == "Venue capacity shortfall")
    assert "400" in cap.explanation and cap.solutions
    bud = next(r for r in risks if r.title == "Budget overrun")
    assert "1200" in bud.explanation.replace(",", "") or "1,200" in bud.explanation
    assert any("Raise the live budget" in s for s in bud.solutions)


def test_critic_routing_priority():
    issues = [
        CriticIssue(title="b", severity=RiskSeverity.high, issue_type=IssueType.budget, message="b"),
        CriticIssue(title="v", severity=RiskSeverity.critical, issue_type=IssueType.venue_capacity, message="v"),
    ]
    assert pick_next_agent(issues) == "venue"


def test_max_iterations_human_review():
    state = {
        "iteration": 5,
        "critic_result": {
            "approved": False,
            "decision": "needs_changes",
            "issues": [
                {
                    "title": "b",
                    "severity": "high",
                    "issue_type": "budget",
                    "message": "over",
                }
            ],
            "required_changes": ["over"],
            "score": 40,
            "next_agent": "budget",
        },
    }
    assert route_after_critic(state) == "human"

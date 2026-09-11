import pytest
from pydantic import ValidationError

from app.domain.models import EventRequirements, Risk
from app.domain.enums import RiskSeverity, IssueType


def test_unknown_counts_allowed_as_zero():
    req = EventRequirements(event_type="x", attendees=0, duration_days=0, budget=0)
    assert req.attendees == 0


def test_attendees_must_be_non_negative():
    with pytest.raises(ValidationError):
        EventRequirements(event_type="x", attendees=-1, duration_days=1, budget=1)


def test_budget_non_negative():
    with pytest.raises(ValidationError):
        EventRequirements(event_type="x", attendees=10, duration_days=1, budget=-1)


def test_duration_non_negative():
    with pytest.raises(ValidationError):
        EventRequirements(event_type="x", attendees=10, duration_days=-1, budget=1)


def test_risk_probability():
    with pytest.raises(ValidationError):
        Risk(
            title="t",
            severity=RiskSeverity.low,
            probability=1.2,
            impact="i",
            description="d",
            mitigation="m",
            issue_type=IssueType.other,
        )


def test_risk_mitigation_none_coerces():
    risk = Risk(
        title="t",
        severity=RiskSeverity.low,
        probability=0.2,
        impact="i",
        description="d",
        mitigation=None,  # type: ignore[arg-type]
        issue_type=IssueType.other,
    )
    assert risk.mitigation == ""

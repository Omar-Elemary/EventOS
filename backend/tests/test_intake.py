from app.services.intake import extract_specialized, missing_critical, missing_specialized


def test_critical_only_when_budget_missing():
    req = {"location": "Cairo", "attendees": 400, "duration_days": 2}
    assert missing_critical(req) == ["budget"]
    assert "preferred_date" not in missing_critical(req)


def test_specialized_after_critical():
    req = {"location": "Cairo", "attendees": 400, "duration_days": 2, "budget": 2000, "event_type": "music event"}
    assert missing_specialized(req) == ["preferred_date", "format"]


def test_conference_asks_overnight():
    req = {
        "location": "Cairo",
        "attendees": 400,
        "duration_days": 2,
        "budget": 2000,
        "event_type": "technology conference",
        "preferred_date": "2026-11-01",
        "format": "indoor",
    }
    assert missing_specialized(req) == ["overnight"]


def test_extract_indoor_november():
    spec = extract_specialized("indoor in November 2026, no hotels")
    assert spec["format"] == "indoor"
    assert spec["preferred_date"] == "2026-11-01"
    assert spec["overnight"] is False

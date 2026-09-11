from app.services.chat import extract_simulate_patch, heuristic_intent, looks_like_event_brief


def test_sports_brief_is_plan():
    c = heuristic_intent("we are making a sports event in el sahel")
    assert c.intent == "plan"


def test_what_if_without_change_is_clarify():
    c = heuristic_intent("run a what if")
    assert c.intent == "clarify"


def test_what_if_attendance():
    c = heuristic_intent("What if attendance increases to 800?")
    assert c.intent == "simulate"
    assert c.simulate_patch == {"attendees": 800}


def test_extract_budget_patch():
    p = extract_simulate_patch("what if the budget drops to $20000")
    assert p.get("budget") == 20000


def test_looks_like_brief():
    assert looks_like_event_brief("organize a wedding in cairo for 200 guests")
    assert not looks_like_event_brief("what is the status")


def test_alexandria_music_brief_is_plan():
    assert heuristic_intent("event in Alexandria for classic music").intent == "plan"


def test_typed_brief_with_attendees_is_plan():
    c = heuristic_intent("music , alexendria egypt, 400 attendee, 2 days ,budget 2000$")
    assert c.intent == "plan"

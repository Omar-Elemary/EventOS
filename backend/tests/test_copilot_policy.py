from app.services.copilot import empty_state, policy
from app.services.understand import extract_entities, heuristic_understand


def test_cairo_marathon_title_seeds_city():
    from app.services.copilot import seed_from_title
    from app.services.understand import extract_entities

    ent = extract_entities("cairo Marathon")
    assert ent.location == "Cairo"
    assert ent.event_type == "marathon"
    st = seed_from_title("cairo Marathon")
    assert st.requirements["location"] == "Cairo"
    assert st.requirements["event_type"] == "marathon"
    assert st.requirements["currency"] == "EGP"
    assert "location" not in st.missing_fields
    assert set(st.missing_fields) == {"attendees", "duration_days", "budget"}
    assert any(a.id == "pick_attendees_500" for a in st.available_actions)
    assert any(a.id == "write_attendees" for a in st.available_actions)


def test_pick_headcount_then_asks_days():
    from app.domain.models import UnderstoodMessage, ExtractedEntities
    from app.services.copilot import empty_state, policy

    state = empty_state()
    state.requirements = {"location": "Cairo", "event_type": "marathon", "currency": "EGP"}
    first = policy(state, UnderstoodMessage(intent="decide", entities=ExtractedEntities(), action_id="pick_attendees_500"))
    assert first.state.requirements["attendees"] == 500
    assert first.prompt_field == "duration_days"
    assert any(a.id == "pick_days_1" for a in first.actions)
    assert any(a.id == "write_days" for a in first.actions)
    second = policy(first.state, UnderstoodMessage(intent="decide", entities=ExtractedEntities(), action_id="pick_days_1"))
    assert second.state.requirements["duration_days"] == 1
    assert second.prompt_field == "budget"
    assert any(a.id.startswith("pick_budget_") for a in second.actions)
    assert any(a.id == "write_budget" for a in second.actions)


def test_typed_number_fills_current_prompt():
    from app.domain.models import CopilotState
    from app.services.copilot import policy
    from app.services.understand import heuristic_understand

    state = CopilotState(
        phase="intake",
        prompt_field="budget",
        skipped_specialized=True,
        requirements={"location": "Cairo", "attendees": 500, "duration_days": 1, "currency": "EGP"},
    )
    decision = policy(state, heuristic_understand("8000 egp"))
    assert decision.state.requirements["budget"] == 8000
    assert decision.state.requirements["currency"] == "EGP"
    assert decision.policy == "CONFIRM"


def test_add_duration_chip_focuses_ask():
    from app.domain.models import UnderstoodMessage, ExtractedEntities
    from app.services.copilot import empty_state, policy
    from app.services.copilot_speak import template_message

    state = empty_state()
    state.requirements = {"location": "Cairo", "event_type": "marathon"}
    understood = UnderstoodMessage(intent="decide", entities=ExtractedEntities(), action_id="add_days", raw="")
    decision = policy(state, understood)
    assert decision.policy == "ASK"
    assert decision.prompt_field == "duration_days"
    assert "How many days" in template_message(decision)
    assert "duration_days" not in template_message(decision)


def test_brief_line_omits_unknowns():
    from app.services.copilot import brief_line, placeholder_brief, user_request_from_state
    from app.domain.models import CopilotState

    assert brief_line({"event_type": "marathon", "location": "Cairo"}) == "marathon in Cairo"
    assert not placeholder_brief("marathon in Cairo")
    assert placeholder_brief("?-day event in TBD for ? people, TBD budget")
    st = CopilotState(requirements={"raw_request": "cairo Marathon", "event_type": "marathon", "location": "Cairo"})
    assert "TBD" not in user_request_from_state(st)


def test_ask_uses_friendly_field_names():
    from app.services.copilot import empty_state, policy
    from app.services.copilot_speak import template_message
    from app.services.understand import heuristic_understand

    decision = policy(empty_state(), heuristic_understand("plan a music event"))
    msg = template_message(decision)
    assert "city" in msg
    assert "location" not in msg
    assert "duration_days" not in msg
    ent = extract_entities("music , alexendria egypt, 400 attendee, 2 days ,budget 2000$")
    assert ent.location == "Alexandria"
    assert ent.attendees == 400
    assert ent.duration_days == 2
    assert ent.budget == 2000
    assert heuristic_understand("music , alexendria egypt, 400 attendee, 2 days ,budget 2000$").intent == "plan"


def test_full_brief_asks_specialized_not_run():
    understood = heuristic_understand("music , alexendria egypt, 400 attendee, 2 days ,budget 2000$")
    decision = policy(empty_state(), understood)
    assert decision.policy == "ASK"
    assert decision.run_graph is False
    assert "preferred_date" in decision.missing_fields
    assert "format" in decision.missing_fields
    assert {a.id for a in decision.actions} >= {"skip_extras"}


def test_missing_budget_asks_only_budget():
    understood = heuristic_understand("conference in cairo for 400 attendees, 2 days")
    decision = policy(empty_state(), understood)
    assert decision.policy == "ASK"
    assert decision.missing_fields == ["budget"]
    assert decision.run_graph is False


def test_confirm_then_run():
    first = policy(
        empty_state(),
        heuristic_understand("cairo conference 400 attendees 2 days $2000 indoor november no hotels"),
    )
    assert first.policy == "CONFIRM"
    second = policy(first.state, heuristic_understand("yes"))
    assert second.policy == "RUN"
    assert second.run_graph is True


def test_skip_extras_confirms():
    first = policy(
        empty_state(),
        heuristic_understand("music , alexendria egypt, 400 attendee, 2 days ,budget 2000$"),
    )
    assert first.policy == "ASK"
    second = policy(first.state, heuristic_understand("skip extras"))
    assert second.policy == "CONFIRM"
    assert second.run_graph is False
    assert second.state.skipped_specialized is True


def test_plan_intent_cannot_run_when_fields_missing():
    understood = heuristic_understand("plan a music event")
    understood.intent = "plan"
    decision = policy(empty_state(), understood)
    assert decision.policy == "ASK"
    assert decision.run_graph is False


def test_graph_review_is_decide():
    from app.domain.models import CopilotState

    state = CopilotState(
        phase="running",
        requirements={"location": "Cairo", "attendees": 500, "duration_days": 3, "budget": 30000},
        graph_status="needs_human_review",
    )
    from app.services.copilot import policy_after_graph

    decision = policy_after_graph(
        state,
        {
            "status": "needs_human_review",
            "critic_result": {
                "issues": [{"issue_type": "schedule", "message": "Overlap: Registration and AV at hall"}]
            },
        },
    )
    assert decision.policy == "DECIDE"
    assert any(a.id == "registration_foyer" for a in decision.actions)


def test_cheaper_venue_replans_venue():
    from app.domain.models import CopilotState, ExtractedEntities, UnderstoodMessage

    state = CopilotState(
        phase="decide",
        graph_status="needs_human_review",
        skipped_specialized=True,
        requirements={"location": "Cairo", "attendees": 500, "duration_days": 3, "budget": 30000, "currency": "EGP"},
    )
    decision = policy(
        state,
        UnderstoodMessage(intent="decide", entities=ExtractedEntities(), action_id="cheaper_venue"),
    )
    assert decision.policy == "RUN"
    assert decision.state.requirements["prefer_cheaper"] is True
    assert (decision.state.pending_apply or {}).get("replan_mode") == "venue"


def test_approved_is_done():
    from app.domain.models import CopilotState
    from app.services.copilot import policy_after_graph

    state = CopilotState(
        requirements={"location": "Cairo", "attendees": 500, "duration_days": 3, "budget": 30000},
        graph_status="running",
    )
    decision = policy_after_graph(state, {"status": "approved"})
    assert decision.policy == "DONE"


def test_what_if_attendance_simulates():
    understood = heuristic_understand("What if attendance increases to 800?")
    from app.domain.models import CopilotState

    state = CopilotState(
        phase="done",
        requirements={"location": "Cairo", "attendees": 500, "duration_days": 3, "budget": 30000},
        graph_status="approved",
    )
    decision = policy(state, understood)
    assert decision.policy == "SIMULATE"
    assert decision.simulate_patch == {"attendees": 800}
    assert {a.id for a in decision.actions} == {"apply_sim", "discard_sim"}


def test_proceed_retries_when_queued_after_failed_start():
    from app.domain.models import CopilotState, ExtractedEntities, UnderstoodMessage

    state = CopilotState(
        phase="running",
        graph_status="queued",
        requirements={
            "location": "Cairo",
            "attendees": 100,
            "duration_days": 3,
            "budget": 1000,
            "currency": "EGP",
            "preferred_date": "November 2026",
            "format": "hybrid",
        },
    )
    decision = policy(
        state,
        UnderstoodMessage(intent="confirm", entities=ExtractedEntities(), action_id="proceed"),
    )
    assert decision.policy == "RUN"
    assert decision.run_graph is True


def test_requirements_for_graph_json_serializable():
    import json
    from app.domain.models import CopilotState, EventRequirements
    from app.services.copilot import requirements_for_graph

    state = CopilotState(
        requirements={
            "event_type": "team event",
            "location": "Cairo",
            "attendees": 100,
            "duration_days": 3,
            "budget": 1000,
            "currency": "EGP",
            "preferred_date": "November 2026",
            "date_note": "November 2026",
            "format": "hybrid",
        }
    )
    payload = requirements_for_graph(state)
    json.dumps(payload)
    assert isinstance(payload["preferred_date"], str)
    EventRequirements.model_validate(payload)

from __future__ import annotations

import json

from app.domain.models import CopilotSpeech, PolicyDecision
from app.llm.base import LLMError, LLMMessage
from app.llm.factory import get_llm_provider
from app.services.copilot import brief_line, format_money
from app.services.intake import FIELD_LABELS

FOCUS_PROMPTS = {
    "location": "Which city is this in?",
    "attendees": "How many people are you expecting?",
    "duration_days": "How many days will it run?",
    "budget": "What’s the total budget in EGP?",
    "preferred_date": "What date or month are you aiming for?",
    "format": "Indoor, outdoor, or hybrid?",
    "overnight": "Do attendees need hotels, or is it daytime only?",
}


def _friendly_fields(fields: list[str]) -> str:
    labels = [FIELD_LABELS.get(f, f.replace("_", " ")) for f in fields]
    if not labels:
        return "a few details"
    if len(labels) == 1:
        return labels[0]
    if len(labels) == 2:
        return f"{labels[0]} and {labels[1]}"
    return ", ".join(labels[:-1]) + f", and {labels[-1]}"


def template_message(decision: PolicyDecision) -> str:
    req = decision.state.requirements
    brief = brief_line(req)
    if decision.policy == "ASK":
        skip = any(a.id == "skip_extras" for a in decision.actions)
        extra = " You can skip extras and I’ll use sensible defaults." if skip else ""
        focus = decision.prompt_field or (decision.missing_fields[0] if decision.missing_fields else None)
        if focus and focus in FOCUS_PROMPTS:
            return f"{FOCUS_PROMPTS[focus]} Pick a choice, or write your own.{extra}"
        return f"I can plan this, but I still need {_friendly_fields(decision.missing_fields)}. Pick a choice, or write your own.{extra}"
    if decision.policy == "CONFIRM":
        return f"Here’s what I’ll plan: {brief}. Proceed when that looks right, or tell me what to change."
    if decision.policy == "RUN":
        return f"Planning now for {brief}. I’ll come back with a result or a choice — watch the agent strip while I work."
    if decision.policy == "SIMULATE":
        patch = decision.simulate_patch or {}
        facts = decision.answer_facts or {}
        delta = facts.get("cost_difference")
        extra = f" Cost difference vs the live plan: {delta}." if delta is not None else ""
        return (
            f"What-if finished on a copy of the plan ({patch}).{extra} "
            "Apply it to the live plan or keep the original."
        )
    if decision.policy == "DECIDE":
        return (
            "The planners hit a blocker. Pick one of the actions below and I’ll apply it — "
            "I won’t keep looping in the background."
        )
    if decision.policy == "DONE":
        facts = decision.answer_facts
        venue = facts.get("venue")
        remaining = facts.get("remaining")
        extra = ""
        if venue:
            extra += f" Venue: {venue}."
        if remaining is not None:
            extra += f" Remaining budget: {format_money(remaining, (decision.state.requirements or {}).get('currency'))}."
        return f"Plan is ready ({brief}).{extra} Ask a what-if or open Budget / Risks."
    facts = decision.answer_facts
    if facts.get("note") == "planning_in_progress":
        return "Agents are still running. I’ll message you when they finish or need a decision."
    status = facts.get("status") or decision.state.graph_status
    remaining = facts.get("remaining")
    venue = facts.get("venue")
    bits = [f"Status is “{status}”."]
    if venue:
        bits.append(f"Selected venue: {venue}.")
    if remaining is not None:
        bits.append(f"Remaining budget: {format_money(remaining, (decision.state.requirements or {}).get('currency'))}.")
    risks = facts.get("risks") or []
    if risks:
        bits.append("Top risks: " + "; ".join(str(r) for r in risks if r) + ".")
    bits.append(f"Current brief: {brief}.")
    return " ".join(bits)


async def speak(decision: PolicyDecision) -> str:
    fallback = template_message(decision)
    llm = get_llm_provider()
    if getattr(llm, "name", "") == "mock":
        return fallback
    try:
        payload = {
            "policy": decision.policy,
            "phase": decision.phase,
            "brief": brief_line(decision.state.requirements),
            "missing_fields": decision.missing_fields,
            "actions": [a.model_dump() for a in decision.actions],
            "facts": decision.answer_facts,
            "simulate_patch": decision.simulate_patch,
            "graph_status": decision.state.graph_status,
        }
        view = await llm.complete_structured(
            CopilotSpeech,
            [
                LLMMessage(
                    role="system",
                    content=(
                        "You are EventOS speaking to the organizer. "
                        "Write one short message from the structured state. "
                        "Do not invent venues, numbers, or extra action buttons. "
                        "Do not claim a plan finished unless policy is DONE. "
                        "If policy is ASK, only ask for missing_fields. "
                        "If CONFIRM, restate the brief and wait. "
                        "If RUN, say you started planning. "
                        "If DECIDE, ask them to pick an existing action."
                    ),
                ),
                LLMMessage(role="user", content=json.dumps(payload, default=str)),
            ],
        )
        if isinstance(view, CopilotSpeech) and (view.message or "").strip():
            return view.message.strip()
    except (LLMError, Exception):
        pass
    return fallback

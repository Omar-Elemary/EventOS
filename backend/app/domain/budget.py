from app.domain.enums import BudgetItemStatus
from app.domain.models import Budget, BudgetItem, VenueCandidate

# Tiny float leftovers (e.g. remaining $-0) are not a real overrun.
OVER_BUDGET_EPS = 1.0


def compute_subtotal(items: list[BudgetItem]) -> float:
    return round(sum(i.estimated_cost for i in items), 2)


def compute_contingency(subtotal: float, rate: float = 0.10) -> float:
    return round(subtotal * rate, 2)


def compute_remaining(total_budget: float, subtotal: float, contingency: float) -> float:
    remaining = round(float(total_budget) - float(subtotal) - float(contingency), 2)
    if remaining < 0 and remaining >= -OVER_BUDGET_EPS:
        return 0.0
    return remaining


def budget_variance(total_budget: float, subtotal: float, contingency: float) -> float:
    """Positive means remaining (under budget); negative is overrun."""
    return compute_remaining(total_budget, subtotal, contingency)


def is_over_budget(total_budget: float, subtotal: float, contingency: float) -> bool:
    return compute_remaining(total_budget, subtotal, contingency) < -OVER_BUDGET_EPS


def committed_total(items: list[BudgetItem]) -> float:
    total = 0.0
    for item in items:
        status = item.status.value if hasattr(item.status, "value") else str(item.status)
        if status in {BudgetItemStatus.committed.value, BudgetItemStatus.paid.value}:
            total += item.actual_cost or item.estimated_cost
    return round(total, 2)


def estimated_only_total(items: list[BudgetItem]) -> float:
    total = 0.0
    for item in items:
        status = item.status.value if hasattr(item.status, "value") else str(item.status)
        if status == BudgetItemStatus.estimated.value:
            total += item.estimated_cost
    return round(total, 2)


def build_budget(
    total_budget: float,
    currency: str,
    items: list[BudgetItem],
    contingency_rate: float = 0.10,
) -> Budget:
    subtotal = compute_subtotal(items)
    contingency = compute_contingency(subtotal, contingency_rate)
    remaining = compute_remaining(total_budget, subtotal, contingency)
    return Budget(
        total_budget=total_budget,
        currency=currency,
        items=items,
        contingency=contingency,
        subtotal=subtotal,
        remaining=remaining,
        committed=committed_total(items),
        estimated=estimated_only_total(items),
    )


def explain_budget(
    budget: Budget,
    venues: list[VenueCandidate] | None = None,
    attendees: int = 0,
) -> dict:
    """Deterministic over-budget / allocation explainer. No LLM math."""
    items = budget.items or []
    denom = budget.total_budget or 1
    shares = []
    for item in items:
        pct = round(100 * item.estimated_cost / denom, 1)
        shares.append(
            {
                "category": item.category,
                "description": item.description,
                "amount": item.estimated_cost,
                "pct": pct,
                "status": item.status.value if hasattr(item.status, "value") else str(item.status),
            }
        )
    shares.sort(key=lambda s: -s["amount"])
    venue_share = next((s for s in shares if s["category"] == "venue"), None)
    selected = next((v for v in (venues or []) if getattr(v, "selected", False)), None)
    alternatives = []
    if selected and venues:
        cheaper = sorted(
            [v for v in venues if v.name != selected.name and v.capacity >= (selected.capacity * 0.8)],
            key=lambda v: v.estimated_cost,
        )
        for alt in cheaper[:2]:
            savings = round(selected.estimated_cost - alt.estimated_cost, 2)
            if savings > 0:
                alternatives.append(
                    {
                        "name": alt.name,
                        "savings": savings,
                        "capacity": alt.capacity,
                        "estimated_cost": alt.estimated_cost,
                    }
                )
    lines: list[str] = []
    if venue_share:
        lines.append(f"Venue consumes {venue_share['pct']}% of the budget ({venue_share['description']}).")
    if is_over_budget(budget.total_budget, budget.subtotal, budget.contingency):
        lines.append(f"Plan is over budget by {abs(budget.remaining):,.0f} {budget.currency}.")
        if alternatives:
            alt = alternatives[0]
            lines.append(
                f"Switching to {alt['name']} saves {alt['savings']:,.0f} {budget.currency} "
                f"with capacity {alt['capacity']}."
            )
        av = next((s for s in shares if s["category"] == "av"), None)
        if av and av["amount"] > 0:
            cut = round(av["amount"] * 0.35, 2)
            lines.append(
                f"Reducing the AV package from Premium to Standard would save about "
                f"{cut:,.0f} {budget.currency} with little schedule impact."
            )
    elif shares:
        lines.append("Budget is within the cap. Largest line items are listed by share.")
    per_attendee = round(budget.subtotal / attendees, 2) if attendees else None
    return {
        "committed": budget.committed,
        "estimated": budget.estimated,
        "contingency": budget.contingency,
        "remaining": budget.remaining,
        "cost_per_attendee": per_attendee,
        "shares": shares,
        "over_budget": is_over_budget(budget.total_budget, budget.subtotal, budget.contingency),
        "cheapest_alternatives": alternatives,
        "explanation": lines,
    }

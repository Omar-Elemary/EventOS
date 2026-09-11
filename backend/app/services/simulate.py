from typing import Any


def impact_diff(original: dict[str, Any], new_plan: dict[str, Any], change: dict[str, Any]) -> dict[str, Any]:
    ob = original.get("budget") or {}
    nb = new_plan.get("budget") or {}
    orig_total = (ob.get("subtotal") or 0) + (ob.get("contingency") or 0)
    new_total = (nb.get("subtotal") or 0) + (nb.get("contingency") or 0)
    orig_venue = _selected_name(original.get("venues") or [])
    new_venue = _selected_name(new_plan.get("venues") or [])
    orig_sched = len((original.get("schedule") or {}).get("items") or [])
    new_sched = len((new_plan.get("schedule") or {}).get("items") or [])
    orig_risks = original.get("risks") or []
    new_risks = new_plan.get("risks") or []
    orig_risk_n = len(orig_risks)
    new_risk_n = len(new_risks)
    catering_delta = _category_delta(ob, nb, "catering")
    staff_delta = _category_delta(ob, nb, "staffing")
    security_delta = _category_delta(ob, nb, "security")
    return {
        "budget": round(new_total - orig_total, 2),
        "venue": "Changed" if orig_venue != new_venue else "Unchanged",
        "venue_from": orig_venue,
        "venue_to": new_venue,
        "catering": catering_delta,
        "staff": staff_delta,
        "security": security_delta,
        "risk": round(100 * ((new_risk_n - orig_risk_n) / max(orig_risk_n, 1)), 1),
        "schedule": abs(new_sched - orig_sched),
        "change": change,
    }


def _selected_name(venues: list[Any]) -> str | None:
    for v in venues:
        if isinstance(v, dict) and v.get("selected"):
            return v.get("name")
        if getattr(v, "selected", False):
            return getattr(v, "name", None)
    if venues:
        v = venues[0]
        return v.get("name") if isinstance(v, dict) else getattr(v, "name", None)
    return None


def _category_delta(old_b: dict, new_b: dict, category: str) -> float:
    def total(budget: dict) -> float:
        return round(sum(i.get("estimated_cost") or 0 for i in budget.get("items") or [] if i.get("category") == category), 2)

    return round(total(new_b) - total(old_b), 2)

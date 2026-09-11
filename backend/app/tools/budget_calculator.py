from app.core.config import get_settings
from app.domain.budget import (
    budget_variance,
    build_budget,
    compute_contingency,
    compute_subtotal,
    is_over_budget,
)
from app.domain.models import BudgetCalculationInput, BudgetCalculationResult
from app.tools.base import Tool


class BudgetCalculatorTool(Tool[BudgetCalculationInput, BudgetCalculationResult]):
    name = "budget_calculator"
    description = "Deterministic budget arithmetic. Does not call an LLM."
    input_model = BudgetCalculationInput

    async def _run(self, payload: BudgetCalculationInput) -> BudgetCalculationResult:
        rate = payload.contingency_rate or get_settings().contingency_rate
        budget = build_budget(payload.total_budget, payload.currency, payload.items, rate)
        subtotal = compute_subtotal(payload.items)
        contingency = compute_contingency(subtotal, rate)
        remaining = budget.remaining
        return BudgetCalculationResult(
            subtotal=subtotal,
            contingency=contingency,
            total=round(subtotal + contingency, 2),
            remaining=remaining,
            variance=budget_variance(payload.total_budget, subtotal, contingency),
            over_budget=is_over_budget(payload.total_budget, subtotal, contingency),
            budget=budget,
        )

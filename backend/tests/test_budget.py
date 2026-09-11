import pytest

from app.domain.budget import build_budget, compute_contingency, compute_subtotal, is_over_budget
from app.domain.models import BudgetCalculationInput, BudgetItem, CurrencyConversionInput
from app.tools.budget_calculator import BudgetCalculatorTool
from app.tools.currency import MockCurrencyConversionTool


@pytest.mark.asyncio
async def test_budget_calculator_deterministic():
    items = [
        BudgetItem(category="venue", description="Hall", estimated_cost=7000),
        BudgetItem(category="catering", description="Food", estimated_cost=9000),
        BudgetItem(category="av", description="AV", estimated_cost=3000),
        BudgetItem(category="photography", description="Photo", estimated_cost=2000),
        BudgetItem(category="transportation", description="Coaches", estimated_cost=1500),
        BudgetItem(category="security", description="Guards", estimated_cost=1000),
        BudgetItem(category="decoration", description="Decor", estimated_cost=2000),
    ]
    tool = BudgetCalculatorTool()
    result = await tool.execute(
        BudgetCalculationInput(total_budget=30000, currency="USD", items=items, contingency_rate=0.10)
    )
    assert result.subtotal == 25500
    assert result.contingency == 2550
    assert result.total == 28050
    assert result.remaining == 1950
    assert result.over_budget is False


def test_tiny_remaining_is_not_over_budget():
    from app.domain.budget import OVER_BUDGET_EPS, build_budget, is_over_budget

    items = [BudgetItem(category="x", description="x", estimated_cost=727272.73)]
    b = build_budget(800000, "EGP", items, 0.10)
    assert b.remaining >= 0 or abs(b.remaining) <= OVER_BUDGET_EPS
    assert is_over_budget(800000, b.subtotal, b.contingency) is False


def test_over_budget_detection():
    items = [BudgetItem(category="x", description="x", estimated_cost=100)]
    b = build_budget(50, "USD", items, 0.10)
    assert is_over_budget(50, compute_subtotal(items), compute_contingency(100, 0.10))
    assert b.remaining < 0


@pytest.mark.asyncio
async def test_currency_conversion_mock():
    tool = MockCurrencyConversionTool()
    r = await tool.execute(CurrencyConversionInput(amount=100, from_currency="USD", to_currency="EGP"))
    assert r.source_type.value == "mock"
    assert r.converted == 4850

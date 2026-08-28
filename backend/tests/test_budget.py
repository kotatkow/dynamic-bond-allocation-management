from datetime import date
from decimal import Decimal

from app.services.budget import (
    BillSnapshot,
    GoalSnapshot,
    IncomeSnapshot,
    calculate_budget,
    calculate_budgetable_income,
    required_goal_contribution,
)


def income(month: int, amount: str, classification: str) -> IncomeSnapshot:
    return IncomeSnapshot(date(2026, month, 25), Decimal(amount), classification)


def test_exceptional_income_does_not_raise_budgetable_income() -> None:
    incomes = [
        income(4, "3000000", "guaranteed"),
        income(5, "3000000", "guaranteed"),
        income(6, "3000000", "guaranteed"),
        income(6, "20000000", "exceptional"),
    ]

    baseline = calculate_budgetable_income(incomes, date(2026, 7, 15))

    assert baseline.budgetable == Decimal("3000000")
    assert baseline.guaranteed_median == Decimal("3000000")
    assert baseline.variable_median == Decimal("0")


def test_variable_income_is_haircut_and_capped_by_lower_recent_month() -> None:
    incomes = [
        income(4, "3000000", "guaranteed"),
        income(4, "1000000", "variable"),
        income(5, "3000000", "guaranteed"),
        income(5, "2000000", "variable"),
        income(6, "3000000", "guaranteed"),
        income(6, "10000000", "variable"),
    ]

    baseline = calculate_budgetable_income(incomes, date(2026, 7, 15))

    assert baseline.guaranteed_median == Decimal("3000000")
    assert baseline.variable_median == Decimal("2000000")
    assert baseline.lower_recent == Decimal("4000000")
    assert baseline.budgetable == Decimal("4000000")


def test_goal_contribution_uses_deadline_and_minimum() -> None:
    goal = GoalSnapshot(
        target_amount=Decimal("1200000"),
        current_amount=Decimal("200000"),
        target_date=date(2026, 11, 30),
        minimum_contribution=Decimal("100000"),
        status="active",
        created_date=date(2026, 1, 1),
    )

    assert required_goal_contribution(goal, date(2026, 7, 1)) == Decimal("200000")


def test_weekly_recommendations_use_decimal_krw_math() -> None:
    incomes = [income(6, "4000000", "guaranteed")]
    bills = [
        BillSnapshot(Decimal("1000000"), "monthly", True, date(2026, 1, 1)),
        BillSnapshot(Decimal("1200000"), "annual", True, date(2026, 1, 1)),
    ]
    goals = [
        GoalSnapshot(
            target_amount=Decimal("1200000"),
            current_amount=Decimal("200000"),
            target_date=date(2026, 11, 30),
            minimum_contribution=Decimal("100000"),
            status="active",
            created_date=date(2026, 1, 1),
        )
    ]

    result = calculate_budget(incomes, bills, goals, date(2026, 7, 15))

    assert result.recurring_bills_monthly == Decimal("1100000")
    assert result.required_goal_contributions == Decimal("200000")
    assert result.sustainable_discretionary_monthly == Decimal("2700000")
    assert result.comfortable_weekly == Decimal("560769")
    assert result.target_weekly == Decimal("467308")
    assert result.aggressive_weekly == Decimal("373846")

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import ROUND_CEILING, ROUND_HALF_UP, Decimal
from statistics import median

ZERO = Decimal("0")
ONE_KRW = Decimal("1")


@dataclass(frozen=True)
class IncomeSnapshot:
    received_date: date
    net_amount: Decimal
    classification: str


@dataclass(frozen=True)
class BillSnapshot:
    amount: Decimal
    frequency: str
    active: bool
    effective_from: date
    effective_to: date | None = None


@dataclass(frozen=True)
class GoalSnapshot:
    target_amount: Decimal
    current_amount: Decimal
    target_date: date
    minimum_contribution: Decimal
    status: str
    created_date: date


@dataclass(frozen=True)
class IncomeBaseline:
    budgetable: Decimal
    guaranteed_median: Decimal
    variable_median: Decimal
    lower_recent: Decimal
    months_used: int


@dataclass(frozen=True)
class BudgetResult:
    as_of: date
    budgetable_income: Decimal
    guaranteed_income_baseline: Decimal
    variable_income_baseline: Decimal
    lower_recent_income: Decimal
    income_months_used: int
    recurring_bills_monthly: Decimal
    required_goal_contributions: Decimal
    sustainable_discretionary_monthly: Decimal
    comfortable_weekly: Decimal
    target_weekly: Decimal
    aggressive_weekly: Decimal


def round_krw(value: Decimal) -> Decimal:
    return value.quantize(ONE_KRW, rounding=ROUND_HALF_UP)


def _median(values: list[Decimal]) -> Decimal:
    return round_krw(Decimal(median(values))) if values else ZERO


def calculate_budgetable_income(incomes: list[IncomeSnapshot], as_of: date) -> IncomeBaseline:
    eligible = [income for income in incomes if income.received_date <= as_of]
    if not eligible:
        return IncomeBaseline(ZERO, ZERO, ZERO, ZERO, 0)

    monthly: dict[tuple[int, int], dict[str, Decimal]] = defaultdict(
        lambda: {"guaranteed": ZERO, "variable": ZERO, "exceptional": ZERO}
    )
    for income in eligible:
        key = (income.received_date.year, income.received_date.month)
        monthly[key][income.classification] += income.net_amount

    current_key = (as_of.year, as_of.month)
    completed_keys = sorted(key for key in monthly if key < current_key)
    selected_keys = completed_keys[-6:]
    if not selected_keys:
        selected_keys = sorted(monthly)[-1:]

    guaranteed_values = [monthly[key]["guaranteed"] for key in selected_keys]
    variable_values = [monthly[key]["variable"] for key in selected_keys]
    ordinary_values = [
        monthly[key]["guaranteed"] + monthly[key]["variable"] for key in selected_keys
    ]

    guaranteed_median = _median(guaranteed_values)
    variable_median = _median(variable_values)
    lower_recent = min(ordinary_values[-3:])
    candidate = guaranteed_median + (variable_median * Decimal("0.50"))
    budgetable = round_krw(min(candidate, lower_recent))

    return IncomeBaseline(
        budgetable=budgetable,
        guaranteed_median=guaranteed_median,
        variable_median=variable_median,
        lower_recent=round_krw(lower_recent),
        months_used=len(selected_keys),
    )


def monthly_bill_amount(bill: BillSnapshot) -> Decimal:
    multipliers = {
        "weekly": Decimal(52) / Decimal(12),
        "monthly": Decimal(1),
        "quarterly": Decimal(1) / Decimal(3),
        "annual": Decimal(1) / Decimal(12),
    }
    return round_krw(bill.amount * multipliers[bill.frequency])


def calculate_monthly_bills(bills: list[BillSnapshot], as_of: date) -> Decimal:
    applicable = (
        bill
        for bill in bills
        if bill.active
        and bill.effective_from <= as_of
        and (bill.effective_to is None or bill.effective_to >= as_of)
    )
    return sum((monthly_bill_amount(bill) for bill in applicable), start=ZERO)


def months_inclusive(start: date, end: date) -> int:
    return max(1, (end.year - start.year) * 12 + end.month - start.month + 1)


def required_goal_contribution(goal: GoalSnapshot, as_of: date) -> Decimal:
    if goal.status != "active" or goal.created_date > as_of:
        return ZERO
    remaining = max(ZERO, goal.target_amount - goal.current_amount)
    if remaining == ZERO:
        return ZERO
    deadline_amount = (remaining / months_inclusive(as_of, goal.target_date)).quantize(
        ONE_KRW, rounding=ROUND_CEILING
    )
    return min(remaining, max(goal.minimum_contribution, deadline_amount))


def calculate_required_goal_contributions(goals: list[GoalSnapshot], as_of: date) -> Decimal:
    return sum((required_goal_contribution(goal, as_of) for goal in goals), start=ZERO)


def calculate_budget(
    incomes: list[IncomeSnapshot],
    bills: list[BillSnapshot],
    goals: list[GoalSnapshot],
    as_of: date,
) -> BudgetResult:
    baseline = calculate_budgetable_income(incomes, as_of)
    monthly_bills = calculate_monthly_bills(bills, as_of)
    goal_contributions = calculate_required_goal_contributions(goals, as_of)
    discretionary = max(ZERO, baseline.budgetable - monthly_bills - goal_contributions)

    def weekly(reserve_factor: str) -> Decimal:
        spendable = discretionary * Decimal(reserve_factor)
        return round_krw(spendable * Decimal(12) / Decimal(52))

    return BudgetResult(
        as_of=as_of,
        budgetable_income=baseline.budgetable,
        guaranteed_income_baseline=baseline.guaranteed_median,
        variable_income_baseline=baseline.variable_median,
        lower_recent_income=baseline.lower_recent,
        income_months_used=baseline.months_used,
        recurring_bills_monthly=monthly_bills,
        required_goal_contributions=goal_contributions,
        sustainable_discretionary_monthly=discretionary,
        comfortable_weekly=weekly("0.90"),
        target_weekly=weekly("0.75"),
        aggressive_weekly=weekly("0.60"),
    )


def previous_month_end(as_of: date) -> date:
    return as_of.replace(day=1) - timedelta(days=1)


def explain_budget(current: BudgetResult, previous: BudgetResult | None) -> list[str]:
    explanations = [
        "Budgetable Income uses up to six completed income-bearing months: median "
        "guaranteed net income plus 50% of median variable net income, capped at the "
        "lowest ordinary-income month among the three most recent observations. "
        "Exceptional income is excluded.",
        f"Monthly capacity is ₩{current.budgetable_income:,.0f} minus "
        f"₩{current.recurring_bills_monthly:,.0f} of recurring bills and "
        f"₩{current.required_goal_contributions:,.0f} of required goal contributions.",
        "Comfortable, Target, and Aggressive use 90%, 75%, and 60% of sustainable "
        "monthly discretionary capacity, converted with 52 weeks per year.",
    ]
    if current.income_months_used == 1:
        explanations.append(
            "Only one observed income month is available, so the estimate is provisional."
        )
    if previous is None or previous.income_months_used == 0:
        explanations.append("No prior-month recommendation is available for comparison.")
        return explanations

    changes = (
        ("Budgetable Income", current.budgetable_income - previous.budgetable_income),
        ("Recurring bills", current.recurring_bills_monthly - previous.recurring_bills_monthly),
        (
            "Required goal contributions",
            current.required_goal_contributions - previous.required_goal_contributions,
        ),
    )
    changed = False
    for label, delta in changes:
        if delta != ZERO:
            direction = "increased" if delta > ZERO else "decreased"
            explanations.append(f"{label} {direction} by ₩{abs(delta):,.0f} versus last month.")
            changed = True
    if not changed:
        explanations.append("The main recommendation inputs are unchanged versus last month.")
    return explanations

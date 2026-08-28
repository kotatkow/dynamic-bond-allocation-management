import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

KrwAmount = Annotated[Decimal, Field(ge=0, max_digits=18, decimal_places=0)]
PositiveKrwAmount = Annotated[Decimal, Field(gt=0, max_digits=18, decimal_places=0)]

IncomeClassification = Literal["guaranteed", "variable", "exceptional"]
BillFrequency = Literal["weekly", "monthly", "quarterly", "annual"]
GoalStatus = Literal["active", "paused", "completed"]


class IncomeEventCreate(BaseModel):
    received_date: date
    gross_amount: KrwAmount
    net_amount: KrwAmount
    income_type: str = Field(min_length=1, max_length=50)
    source: str = Field(min_length=1, max_length=120)
    classification: IncomeClassification
    notes: str | None = None

    @model_validator(mode="after")
    def gross_must_cover_net(self) -> "IncomeEventCreate":
        if self.gross_amount < self.net_amount:
            raise ValueError("gross_amount must be greater than or equal to net_amount")
        return self


class IncomeEventRead(IncomeEventCreate):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime


class RecurringBillCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    amount: KrwAmount
    category: str = Field(min_length=1, max_length=50)
    frequency: BillFrequency = "monthly"
    expected_payment_day: int | None = Field(default=None, ge=1, le=31)
    essential: bool = True
    active: bool = True
    effective_from: date
    effective_to: date | None = None
    notes: str | None = None

    @model_validator(mode="after")
    def effective_dates_are_ordered(self) -> "RecurringBillCreate":
        if self.effective_to is not None and self.effective_to < self.effective_from:
            raise ValueError("effective_to must be on or after effective_from")
        return self


class RecurringBillRead(RecurringBillCreate):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime


class FinancialGoalCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    target_amount: PositiveKrwAmount
    current_amount: KrwAmount
    target_date: date
    priority: int = Field(ge=1, le=5)
    minimum_contribution: KrwAmount = Decimal("0")
    preferred_contribution: KrwAmount = Decimal("0")
    category: str = Field(min_length=1, max_length=50)
    status: GoalStatus = "active"
    notes: str | None = None
    progress_date: date


class GoalProgressCreate(BaseModel):
    recorded_date: date
    current_amount: KrwAmount
    notes: str | None = None


class GoalProgressRead(GoalProgressCreate):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    goal_id: uuid.UUID
    created_at: datetime


class FinancialGoalRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    target_amount: Decimal
    current_amount: Decimal
    target_date: date
    priority: int
    minimum_contribution: Decimal
    preferred_contribution: Decimal
    category: str
    status: GoalStatus
    notes: str | None
    latest_progress_date: date
    created_at: datetime


class BudgetRecommendationRead(BaseModel):
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
    previous_target_weekly: Decimal | None
    target_weekly_change: Decimal | None
    explanations: list[str]

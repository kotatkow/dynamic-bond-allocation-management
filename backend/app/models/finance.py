import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class IncomeEvent(Base):
    __tablename__ = "income_events"
    __table_args__ = (
        CheckConstraint("gross_amount >= 0", name="ck_income_gross_nonnegative"),
        CheckConstraint("net_amount >= 0", name="ck_income_net_nonnegative"),
        CheckConstraint("gross_amount >= net_amount", name="ck_income_gross_gte_net"),
        CheckConstraint(
            "classification IN ('guaranteed', 'variable', 'exceptional')",
            name="ck_income_classification",
        ),
        Index("ix_income_events_received_date", "received_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    received_date: Mapped[date] = mapped_column(Date, nullable=False)
    gross_amount: Mapped[Decimal] = mapped_column(Numeric(18, 0), nullable=False)
    net_amount: Mapped[Decimal] = mapped_column(Numeric(18, 0), nullable=False)
    income_type: Mapped[str] = mapped_column(String(50), nullable=False)
    source: Mapped[str] = mapped_column(String(120), nullable=False)
    classification: Mapped[str] = mapped_column(String(20), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class RecurringBill(Base):
    __tablename__ = "recurring_bills"
    __table_args__ = (
        CheckConstraint("amount >= 0", name="ck_bill_amount_nonnegative"),
        CheckConstraint(
            "frequency IN ('weekly', 'monthly', 'quarterly', 'annual')",
            name="ck_bill_frequency",
        ),
        CheckConstraint(
            "expected_payment_day IS NULL OR "
            "(expected_payment_day >= 1 AND expected_payment_day <= 31)",
            name="ck_bill_payment_day",
        ),
        CheckConstraint(
            "effective_to IS NULL OR effective_to >= effective_from",
            name="ck_bill_effective_range",
        ),
        Index("ix_recurring_bills_effective_dates", "effective_from", "effective_to"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 0), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    frequency: Mapped[str] = mapped_column(String(20), nullable=False, default="monthly")
    expected_payment_day: Mapped[int | None]
    essential: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[date | None] = mapped_column(Date)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class FinancialGoal(Base):
    __tablename__ = "financial_goals"
    __table_args__ = (
        CheckConstraint("target_amount > 0", name="ck_goal_target_positive"),
        CheckConstraint("minimum_contribution >= 0", name="ck_goal_minimum_nonnegative"),
        CheckConstraint("preferred_contribution >= 0", name="ck_goal_preferred_nonnegative"),
        CheckConstraint("priority >= 1 AND priority <= 5", name="ck_goal_priority"),
        CheckConstraint("status IN ('active', 'paused', 'completed')", name="ck_goal_status"),
        Index("ix_financial_goals_target_date", "target_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    target_amount: Mapped[Decimal] = mapped_column(Numeric(18, 0), nullable=False)
    target_date: Mapped[date] = mapped_column(Date, nullable=False)
    priority: Mapped[int] = mapped_column(nullable=False)
    minimum_contribution: Mapped[Decimal] = mapped_column(Numeric(18, 0), nullable=False)
    preferred_contribution: Mapped[Decimal] = mapped_column(Numeric(18, 0), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    progress_entries: Mapped[list["GoalProgressEntry"]] = relationship(
        back_populates="goal",
        cascade="all, delete-orphan",
        order_by="GoalProgressEntry.recorded_date",
    )


class GoalProgressEntry(Base):
    __tablename__ = "goal_progress_entries"
    __table_args__ = (
        CheckConstraint("current_amount >= 0", name="ck_goal_progress_nonnegative"),
        Index("ix_goal_progress_goal_date", "goal_id", "recorded_date", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    goal_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("financial_goals.id", ondelete="CASCADE"), nullable=False
    )
    recorded_date: Mapped[date] = mapped_column(Date, nullable=False)
    current_amount: Mapped[Decimal] = mapped_column(Numeric(18, 0), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    goal: Mapped[FinancialGoal] = relationship(back_populates="progress_entries")

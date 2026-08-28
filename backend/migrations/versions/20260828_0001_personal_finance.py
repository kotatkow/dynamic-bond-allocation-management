"""Create personal-finance tables.

Revision ID: 20260828_0001
Revises:
Create Date: 2026-08-28
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260828_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "income_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("received_date", sa.Date(), nullable=False),
        sa.Column("gross_amount", sa.Numeric(18, 0), nullable=False),
        sa.Column("net_amount", sa.Numeric(18, 0), nullable=False),
        sa.Column("income_type", sa.String(length=50), nullable=False),
        sa.Column("source", sa.String(length=120), nullable=False),
        sa.Column("classification", sa.String(length=20), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("gross_amount >= 0", name="ck_income_gross_nonnegative"),
        sa.CheckConstraint("net_amount >= 0", name="ck_income_net_nonnegative"),
        sa.CheckConstraint("gross_amount >= net_amount", name="ck_income_gross_gte_net"),
        sa.CheckConstraint(
            "classification IN ('guaranteed', 'variable', 'exceptional')",
            name="ck_income_classification",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_income_events_received_date", "income_events", ["received_date"])

    op.create_table(
        "recurring_bills",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("amount", sa.Numeric(18, 0), nullable=False),
        sa.Column("category", sa.String(length=50), nullable=False),
        sa.Column("frequency", sa.String(length=20), nullable=False),
        sa.Column("expected_payment_day", sa.Integer(), nullable=True),
        sa.Column("essential", sa.Boolean(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("amount >= 0", name="ck_bill_amount_nonnegative"),
        sa.CheckConstraint(
            "frequency IN ('weekly', 'monthly', 'quarterly', 'annual')",
            name="ck_bill_frequency",
        ),
        sa.CheckConstraint(
            "expected_payment_day IS NULL OR "
            "(expected_payment_day >= 1 AND expected_payment_day <= 31)",
            name="ck_bill_payment_day",
        ),
        sa.CheckConstraint(
            "effective_to IS NULL OR effective_to >= effective_from",
            name="ck_bill_effective_range",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_recurring_bills_effective_dates",
        "recurring_bills",
        ["effective_from", "effective_to"],
    )

    op.create_table(
        "financial_goals",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("target_amount", sa.Numeric(18, 0), nullable=False),
        sa.Column("target_date", sa.Date(), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("minimum_contribution", sa.Numeric(18, 0), nullable=False),
        sa.Column("preferred_contribution", sa.Numeric(18, 0), nullable=False),
        sa.Column("category", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("target_amount > 0", name="ck_goal_target_positive"),
        sa.CheckConstraint("minimum_contribution >= 0", name="ck_goal_minimum_nonnegative"),
        sa.CheckConstraint("preferred_contribution >= 0", name="ck_goal_preferred_nonnegative"),
        sa.CheckConstraint("priority >= 1 AND priority <= 5", name="ck_goal_priority"),
        sa.CheckConstraint("status IN ('active', 'paused', 'completed')", name="ck_goal_status"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_financial_goals_target_date", "financial_goals", ["target_date"])

    op.create_table(
        "goal_progress_entries",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("goal_id", sa.Uuid(), nullable=False),
        sa.Column("recorded_date", sa.Date(), nullable=False),
        sa.Column("current_amount", sa.Numeric(18, 0), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("current_amount >= 0", name="ck_goal_progress_nonnegative"),
        sa.ForeignKeyConstraint(["goal_id"], ["financial_goals.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_goal_progress_goal_date",
        "goal_progress_entries",
        ["goal_id", "recorded_date", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_goal_progress_goal_date", table_name="goal_progress_entries")
    op.drop_table("goal_progress_entries")
    op.drop_index("ix_financial_goals_target_date", table_name="financial_goals")
    op.drop_table("financial_goals")
    op.drop_index("ix_recurring_bills_effective_dates", table_name="recurring_bills")
    op.drop_table("recurring_bills")
    op.drop_index("ix_income_events_received_date", table_name="income_events")
    op.drop_table("income_events")

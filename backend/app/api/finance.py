import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models.finance import FinancialGoal, GoalProgressEntry, IncomeEvent, RecurringBill
from app.schemas.finance import (
    BudgetRecommendationRead,
    FinancialGoalCreate,
    FinancialGoalRead,
    GoalProgressCreate,
    GoalProgressRead,
    IncomeEventCreate,
    IncomeEventRead,
    RecurringBillCreate,
    RecurringBillRead,
)
from app.services.budget import (
    BillSnapshot,
    GoalSnapshot,
    IncomeSnapshot,
    calculate_budget,
    explain_budget,
    previous_month_end,
)

router = APIRouter()


@router.post("/incomes", response_model=IncomeEventRead, status_code=status.HTTP_201_CREATED)
def create_income(payload: IncomeEventCreate, db: Session = Depends(get_db)) -> IncomeEvent:
    income = IncomeEvent(**payload.model_dump())
    db.add(income)
    db.commit()
    db.refresh(income)
    return income


@router.get("/incomes", response_model=list[IncomeEventRead])
def list_incomes(db: Session = Depends(get_db)) -> list[IncomeEvent]:
    return list(db.scalars(select(IncomeEvent).order_by(IncomeEvent.received_date.desc())).all())


@router.post(
    "/recurring-bills",
    response_model=RecurringBillRead,
    status_code=status.HTTP_201_CREATED,
)
def create_recurring_bill(
    payload: RecurringBillCreate, db: Session = Depends(get_db)
) -> RecurringBill:
    bill = RecurringBill(**payload.model_dump())
    db.add(bill)
    db.commit()
    db.refresh(bill)
    return bill


@router.get("/recurring-bills", response_model=list[RecurringBillRead])
def list_recurring_bills(db: Session = Depends(get_db)) -> list[RecurringBill]:
    return list(
        db.scalars(select(RecurringBill).order_by(RecurringBill.effective_from.desc())).all()
    )


def _goal_read(goal: FinancialGoal, as_of: date | None = None) -> FinancialGoalRead:
    eligible = [
        entry for entry in goal.progress_entries if as_of is None or entry.recorded_date <= as_of
    ]
    if not eligible:
        current_amount = 0
        latest_date = goal.created_at.date()
    else:
        latest = max(eligible, key=lambda entry: (entry.recorded_date, entry.created_at))
        current_amount = latest.current_amount
        latest_date = latest.recorded_date
    return FinancialGoalRead(
        id=goal.id,
        name=goal.name,
        target_amount=goal.target_amount,
        current_amount=current_amount,
        target_date=goal.target_date,
        priority=goal.priority,
        minimum_contribution=goal.minimum_contribution,
        preferred_contribution=goal.preferred_contribution,
        category=goal.category,
        status=goal.status,
        notes=goal.notes,
        latest_progress_date=latest_date,
        created_at=goal.created_at,
    )


@router.post("/goals", response_model=FinancialGoalRead, status_code=status.HTTP_201_CREATED)
def create_goal(payload: FinancialGoalCreate, db: Session = Depends(get_db)) -> FinancialGoalRead:
    goal_fields = payload.model_dump(exclude={"current_amount", "progress_date"})
    goal = FinancialGoal(**goal_fields)
    goal.progress_entries.append(
        GoalProgressEntry(
            recorded_date=payload.progress_date,
            current_amount=payload.current_amount,
            notes="Initial progress",
        )
    )
    db.add(goal)
    db.commit()
    db.refresh(goal)
    return _goal_read(goal)


@router.get("/goals", response_model=list[FinancialGoalRead])
def list_goals(db: Session = Depends(get_db)) -> list[FinancialGoalRead]:
    goals = db.scalars(
        select(FinancialGoal)
        .options(selectinload(FinancialGoal.progress_entries))
        .order_by(FinancialGoal.priority, FinancialGoal.target_date)
    ).all()
    return [_goal_read(goal) for goal in goals]


@router.post(
    "/goals/{goal_id}/progress",
    response_model=GoalProgressRead,
    status_code=status.HTTP_201_CREATED,
)
def record_goal_progress(
    goal_id: uuid.UUID, payload: GoalProgressCreate, db: Session = Depends(get_db)
) -> GoalProgressEntry:
    if db.get(FinancialGoal, goal_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Goal not found")
    entry = GoalProgressEntry(goal_id=goal_id, **payload.model_dump())
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def _load_budget_inputs(
    db: Session, as_of: date
) -> tuple[list[IncomeSnapshot], list[BillSnapshot], list[GoalSnapshot]]:
    incomes = db.scalars(select(IncomeEvent).where(IncomeEvent.received_date <= as_of)).all()
    bills = db.scalars(select(RecurringBill)).all()
    goals = db.scalars(
        select(FinancialGoal).options(selectinload(FinancialGoal.progress_entries))
    ).all()

    income_snapshots = [
        IncomeSnapshot(item.received_date, item.net_amount, item.classification) for item in incomes
    ]
    bill_snapshots = [
        BillSnapshot(
            item.amount, item.frequency, item.active, item.effective_from, item.effective_to
        )
        for item in bills
    ]
    goal_snapshots: list[GoalSnapshot] = []
    for goal in goals:
        read_goal = _goal_read(goal, as_of)
        goal_snapshots.append(
            GoalSnapshot(
                target_amount=goal.target_amount,
                current_amount=read_goal.current_amount,
                target_date=goal.target_date,
                minimum_contribution=goal.minimum_contribution,
                status=goal.status,
                created_date=goal.created_at.date(),
            )
        )
    return income_snapshots, bill_snapshots, goal_snapshots


@router.get("/budget/recommendation", response_model=BudgetRecommendationRead)
def budget_recommendation(
    as_of: date = Query(default_factory=date.today), db: Session = Depends(get_db)
) -> BudgetRecommendationRead:
    inputs = _load_budget_inputs(db, as_of)
    current = calculate_budget(*inputs, as_of)

    previous_date = previous_month_end(as_of)
    previous_inputs = _load_budget_inputs(db, previous_date)
    previous = calculate_budget(*previous_inputs, previous_date)
    has_previous = previous.income_months_used > 0
    previous_value = previous if has_previous else None
    target_change = current.target_weekly - previous.target_weekly if has_previous else None

    return BudgetRecommendationRead(
        **current.__dict__,
        previous_target_weekly=previous.target_weekly if has_previous else None,
        target_weekly_change=target_change,
        explanations=explain_budget(current, previous_value),
    )

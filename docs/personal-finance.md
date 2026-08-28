# Personal-finance model

All currency inputs are whole Korean won. PostgreSQL stores them as `NUMERIC(18, 0)`, the backend calculates with `Decimal`, and the browser transports currency as strings and formats it with `BigInt`.

## Budgetable Income

The initial formula uses up to the six most recent completed months that contain at least one income event. It does not invent zero-income months where no observation exists. If there is no completed month yet, the current observed month is used provisionally.

```text
guaranteed baseline = median(monthly guaranteed net income)
variable baseline   = median(monthly variable net income)
candidate           = guaranteed baseline + 50% × variable baseline
stability cap       = lowest ordinary income among the latest 3 observed months
Budgetable Income   = min(candidate, stability cap)
```

Ordinary income is guaranteed plus variable income. Exceptional income is excluded from every Budgetable Income component.

## Monthly commitments

Recurring bills are effective-dated. Active records whose effective range covers the requested date are normalized to a monthly amount:

```text
weekly    = amount × 52 / 12
monthly   = amount
quarterly = amount / 3
annual    = amount / 12
```

Each active financial goal has a required monthly contribution:

```text
remaining amount   = max(0, target - latest dated progress)
deadline pace      = ceil(remaining amount / inclusive months to target)
required amount    = min(remaining amount, max(minimum contribution, deadline pace))
```

Paused, completed, not-yet-created, and fully funded goals require zero.

## Weekly recommendation

```text
sustainable monthly discretionary =
  max(0, Budgetable Income - monthly bills - required goal contributions)

Comfortable weekly = round(discretionary × 90% × 12 / 52)
Target weekly      = round(discretionary × 75% × 12 / 52)
Aggressive weekly  = round(discretionary × 60% × 12 / 52)
```

The unused 10%, 25%, or 40% is an implicit conservatism reserve at this stage, not a posted account transaction. The API also recalculates the previous month and reports which input components changed.

## API

- `POST/GET /api/v1/incomes`
- `POST/GET /api/v1/recurring-bills`
- `POST/GET /api/v1/goals`
- `POST /api/v1/goals/{goal_id}/progress`
- `GET /api/v1/budget/recommendation?as_of=YYYY-MM-DD`

The create-only record endpoints intentionally avoid destructive historical edits in this first slice. Future update workflows should close an effective record and append its replacement rather than rewriting history.

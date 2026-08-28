# Architecture

The Personal Portfolio Intelligence Platform is a small three-service application:

```text
Browser -> Next.js frontend -> FastAPI JSON API -> PostgreSQL
                                      |
                                      +-> deterministic finance services
```

- `frontend/` contains the Next.js, React, and TypeScript interface. Browser requests use `NEXT_PUBLIC_API_URL` to reach the backend.
- `backend/` contains the FastAPI application, SQLAlchemy persistence layer, deterministic domain services, and Alembic migrations.
- PostgreSQL is the source of truth for entered and calculated-input financial data. Currency is stored as whole-KRW `NUMERIC(18, 0)` values; calculations use Python `Decimal`, never binary floating point.
- `compose.yaml` starts all three services. Its named database volume survives container recreation.

Raw user-entered records remain separate from calculated recommendations. API response models expose derived values and explanations, while calculation services contain the inspectable formulas. Future portfolio, mortgage, Global Ledger, macro, housing, and research modules should be added as sibling backend modules and frontend routes without changing this boundary.

The root-level Streamlit files are the pre-existing bond-allocation dashboard and are not part of the new Compose application.

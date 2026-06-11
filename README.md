# Dynamic Bond Allocation Management Assistant

A local assistant for exploring fixed-income allocation decisions across short duration, intermediate bonds, long duration, inflation-linked bonds, credit, high yield, and cash.

This is decision-support software, not investment advice. Outputs are model-driven estimates based on user-entered assumptions and should be reviewed by a qualified professional before use with real capital.

## Run The App

```powershell
npm start
```

Then open `http://localhost:3000`.

If `npm` is not available on your Windows PATH, use the helper script:

```powershell
.\start-app.cmd
```

The static `index.html` can still be opened directly, but backend features such as market data, scenario history, and audit logs require the server.

## What It Does

- Captures investor constraints, current allocation, and macro signals.
- Computes a risk-aware target allocation using a tested allocation engine and policy constraints.
- Shows rebalance trades, duration posture, credit posture, and key risks.
- Provides an assistant panel that explains the recommendation in plain English.
- Loads market data through authenticated provider hooks when API keys are configured.
- Saves scenarios and audit events to local JSON storage.

## Market Data

The backend supports authenticated data providers through environment variables:

```powershell
$env:FRED_API_KEY="your-fred-key"
$env:ALPHA_VANTAGE_API_KEY="your-alpha-vantage-key"
npm start
```

When keys are not configured, the backend serves a clearly marked demo snapshot so development remains usable.

Covered data types:

- U.S. Treasury yields from FRED series such as `DGS2`, `DGS10`, and `DGS30`.
- Credit spreads from FRED corporate spread series.
- Inflation expectations from FRED breakeven inflation series.
- ETF/fund prices for `SGOV`, `SHY`, `IEF`, and `TLT` through Alpha Vantage.

## Backend Endpoints

- `GET /api/market-data`
- `POST /api/allocate`
- `GET /api/portfolios`
- `POST /api/portfolios`
- `GET /api/scenarios`
- `POST /api/scenarios`
- `GET /api/audit`

Local persistence lives in `data/store.json`, which is intentionally ignored by Git.

## Tests

```powershell
npm test
```

If `npm` is not available:

```powershell
.\test-app.cmd
```

Regression tests cover allocation normalization, policy caps, signal-driven duration changes, inflation tilts, and rebalance math.

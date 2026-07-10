# Dynamic Bond Allocation Management Assistant

A Streamlit assistant for exploring fixed-income allocation decisions across short duration, intermediate bonds, long duration, inflation-linked bonds, credit, high yield, and cash.

This is decision-support software, not investment advice. Outputs are model-driven estimates based on user-entered assumptions and should be reviewed by a qualified professional before use with real capital.

## Run The App

```powershell
streamlit run streamlit_app.py
```

If Streamlit is not installed locally:

```powershell
python -m pip install -r requirements.txt
python -m streamlit run streamlit_app.py
```

## What It Does

- Captures investor constraints, current allocation, and macro signals.
- Computes a risk-aware target allocation using policy constraints.
- Shows rebalance trades, duration posture, credit posture, and key risks.
- Provides an assistant panel that explains the recommendation in plain English.
- Loads market data through authenticated provider hooks when API keys are configured.

## Market Data

The Streamlit app supports authenticated data providers through Streamlit secrets or environment variables:

```powershell
$env:FRED_API_KEY="your-fred-key"
$env:ALPHA_VANTAGE_API_KEY="your-alpha-vantage-key"
streamlit run streamlit_app.py
```

When keys are not configured, the app uses a clearly marked demo snapshot so development remains usable.

Covered data types:

- U.S. Treasury yields from FRED series such as `DGS2`, `DGS10`, and `DGS30`.
- Credit spreads from FRED corporate spread series.
- Inflation expectations from FRED breakeven inflation series.
- ETF/fund prices for `SGOV`, `SHY`, `IEF`, and `TLT` through Alpha Vantage.

## Deployment

For Streamlit Community Cloud deployment notes, see `STREAMLIT_DEPLOY.md`.

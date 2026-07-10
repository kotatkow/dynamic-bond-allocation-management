# Dynamic Bond Allocation Assistant

A Streamlit-only advisory dashboard for exploring general fixed-income allocation decisions across cash/T-bills, short duration, core bonds, long Treasuries, TIPS, investment-grade credit, and high yield.

This is decision-support software, not investment advice. Outputs are model-driven estimates based on mandate assumptions and macro data, and should be reviewed by a qualified professional before use with real capital.

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

- Captures advisory inputs such as investment horizon, risk tolerance, and high-yield allocation cap.
- Prefills macro signals from market data where available.
- Computes a general target bond allocation using rule-based tilts and policy constraints.
- Shows recommended allocation, duration posture, credit-risk posture, and cash/T-bill weight.
- Explains the recommendation using current yield-curve conditions, credit spreads, inflation expectations, and recession-risk data.
- Loads market data through authenticated FRED and Alpha Vantage hooks when API keys are configured.

The app does not track a user's current portfolio, calculate trade orders, save scenarios, or maintain allocation history.

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

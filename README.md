# Dynamic Bond Allocation Management Assistant

A local prototype for exploring fixed-income allocation decisions across short duration, intermediate bonds, long duration, inflation-linked bonds, credit, high yield, and cash.

This is decision-support software, not investment advice. Outputs are model-driven estimates based on user-entered assumptions and should be reviewed by a qualified professional before use with real capital.

## Open The Prototype

Open `index.html` in a browser.

## What It Does

- Captures investor constraints, current allocation, and macro signals.
- Computes a risk-aware target allocation using transparent heuristics.
- Shows rebalance trades, duration posture, credit posture, and key risks.
- Provides an assistant panel that explains the recommendation in plain English.

## Suggested Next Steps

- Add authenticated market data for yields, spreads, inflation expectations, and ETF/fund prices.
- Add a backend for portfolios, scenario history, and audit trails.
- Replace heuristic scoring with a tested allocation engine and policy constraints.
- Add regression tests around allocation rules and rebalance calculations.

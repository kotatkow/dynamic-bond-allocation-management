from __future__ import annotations

import json
import math
import os
from datetime import datetime, timezone
from urllib.parse import urlencode
from urllib.request import urlopen

import streamlit as st


ASSETS = [
    {"key": "cash", "label": "Cash / T-Bills", "duration": 0.2, "credit": 0},
    {"key": "short", "label": "Short Duration", "duration": 1.8, "credit": 10},
    {"key": "core", "label": "Core Bonds", "duration": 5.6, "credit": 25},
    {"key": "long", "label": "Long Treasuries", "duration": 15.5, "credit": 0},
    {"key": "tips", "label": "Inflation Linked", "duration": 6.7, "credit": 5},
    {"key": "credit", "label": "Investment Grade Credit", "duration": 6.8, "credit": 55},
    {"key": "yield", "label": "High Yield", "duration": 3.7, "credit": 95},
]

DEFAULT_WEIGHTS = {
    "cash": 8.0,
    "short": 18.0,
    "core": 34.0,
    "long": 10.0,
    "tips": 10.0,
    "credit": 16.0,
    "yield": 4.0,
}

DEFAULT_POLICY = {
    "cash": {"min": 2.0, "max": 30.0},
    "short": {"min": 5.0, "max": 45.0},
    "core": {"min": 15.0, "max": 55.0},
    "long": {"min": 0.0, "max": 30.0},
    "tips": {"min": 0.0, "max": 25.0},
    "credit": {"min": 0.0, "max": 30.0},
    "yield": {"min": 0.0, "max": 10.0},
}

DEMO_MARKET_DATA = {
    "asOf": "2026-06-10",
    "provider": "demo-fallback",
    "authStatus": "missing-api-keys",
    "yields": {"us3m": 3.82, "us2y": 4.13, "us5y": 4.26, "us10y": 4.53, "us30y": 5.01},
    "spreads": {"investmentGrade": 1.05, "highYield": 3.75},
    "inflationExpectations": {"us5yBreakeven": 2.38, "us10yBreakeven": 2.31},
    "etfs": {
        "SGOV": {"price": 100.42, "changePct": 0.01},
        "SHY": {"price": 82.18, "changePct": -0.04},
        "IEF": {"price": 92.35, "changePct": -0.18},
        "TLT": {"price": 87.62, "changePct": -0.42},
    },
}


def get_secret(name: str) -> str | None:
    try:
        return st.secrets.get(name) or os.environ.get(name)
    except Exception:
        return os.environ.get(name)


def fetch_json(url: str, timeout: int = 12) -> dict:
    with urlopen(url, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_fred_latest(series_id: str, api_key: str) -> tuple[float | None, str | None]:
    query = urlencode(
        {
            "series_id": series_id,
            "api_key": api_key,
            "file_type": "json",
            "sort_order": "desc",
            "limit": 1,
        }
    )
    payload = fetch_json(f"https://api.stlouisfed.org/fred/series/observations?{query}")
    observation = (payload.get("observations") or [{}])[0]
    raw_value = observation.get("value")
    value = None if raw_value in (None, ".") else float(raw_value)
    return value, observation.get("date")


def fetch_alpha_vantage_quote(symbol: str, api_key: str) -> dict:
    query = urlencode({"function": "GLOBAL_QUOTE", "symbol": symbol, "apikey": api_key})
    payload = fetch_json(f"https://www.alphavantage.co/query?{query}")
    quote = payload.get("Global Quote") or {}
    price = quote.get("05. price")
    change_pct = (quote.get("10. change percent") or "").replace("%", "")
    return {
        "price": float(price) if price else None,
        "changePct": float(change_pct) if change_pct else None,
    }


@st.cache_data(ttl=900, show_spinner=False)
def fetch_market_data(fred_key: str | None, alpha_key: str | None) -> dict:
    if not fred_key and not alpha_key:
        return {**DEMO_MARKET_DATA, "retrievedAt": datetime.now(timezone.utc).isoformat()}

    data = {
        "asOf": None,
        "provider": "fred-alpha-vantage",
        "authStatus": "authenticated",
        "yields": {},
        "spreads": {},
        "inflationExpectations": {},
        "etfs": {},
        "retrievedAt": datetime.now(timezone.utc).isoformat(),
    }

    if fred_key:
        fred_series = {
            "us3m": "DGS3MO",
            "us2y": "DGS2",
            "us5y": "DGS5",
            "us10y": "DGS10",
            "us30y": "DGS30",
            "highYield": "BAMLH0A0HYM2",
            "investmentGrade": "BAMLC0A0CM",
            "us5yBreakeven": "T5YIE",
            "us10yBreakeven": "T10YIE",
        }
        for key, series_id in fred_series.items():
            value, date = fetch_fred_latest(series_id, fred_key)
            if key in ("highYield", "investmentGrade"):
                data["spreads"][key] = value
            elif key in ("us5yBreakeven", "us10yBreakeven"):
                data["inflationExpectations"][key] = value
            else:
                data["yields"][key] = value
            data["asOf"] = data["asOf"] or date

    if alpha_key:
        for symbol in ("SGOV", "SHY", "IEF", "TLT"):
            data["etfs"][symbol] = fetch_alpha_vantage_quote(symbol, alpha_key)

    return data


def normalize(weights: dict[str, float]) -> dict[str, float]:
    total = sum(float(value or 0) for value in weights.values())
    if not total:
        return DEFAULT_WEIGHTS.copy()
    return {key: float(value or 0) / total * 100 for key, value in weights.items()}


def weighted_metric(weights: dict[str, float], field: str) -> float:
    return sum((weights.get(asset["key"], 0) / 100) * asset[field] for asset in ASSETS)


def infer_market_signals(market_data: dict) -> dict:
    signals = {}
    yields = market_data.get("yields") or {}
    spreads = market_data.get("spreads") or {}
    inflation = market_data.get("inflationExpectations") or {}

    if isinstance(yields.get("us10y"), (int, float)) and isinstance(yields.get("us2y"), (int, float)):
        slope = yields["us10y"] - yields["us2y"]
        signals["yieldTrend"] = "rising" if slope > 0.5 else "falling" if slope < -0.25 else "stable"

    if isinstance(spreads.get("highYield"), (int, float)):
        high_yield = spreads["highYield"]
        signals["creditSpreads"] = "wide" if high_yield > 5 else "tight" if high_yield < 3.2 else "normal"

    if isinstance(inflation.get("us10yBreakeven"), (int, float)):
        breakeven = inflation["us10yBreakeven"]
        signals["inflation"] = "hot" if breakeven > 2.6 else "cooling" if breakeven < 2 else "normal"

    return signals


def base_weights(risk_tolerance: str, horizon: str) -> dict[str, float]:
    return {
        "cash": 12.0 if risk_tolerance == "defensive" else 5.0 if risk_tolerance == "growth" else 8.0,
        "short": 18.0,
        "core": 34.0,
        "long": 13.0 if horizon == "long" else 5.0 if horizon == "short" else 10.0,
        "tips": 10.0,
        "credit": 19.0 if risk_tolerance == "growth" else 12.0 if risk_tolerance == "defensive" else 16.0,
        "yield": 7.0 if risk_tolerance == "growth" else 2.0 if risk_tolerance == "defensive" else 4.0,
    }


def apply_tilts(target: dict[str, float], risk_tolerance: str, signals: dict, rationale: list[str]) -> None:
    if signals["yieldTrend"] == "rising":
        target["short"] += 8
        target["cash"] += 3
        target["long"] -= 7
        target["core"] -= 4
        rationale.append("Rising-yield signal reduced long-duration exposure and increased short-duration liquidity.")
    elif signals["yieldTrend"] == "falling":
        target["long"] += 7
        target["core"] += 4
        target["short"] -= 6
        target["cash"] -= 2
        rationale.append("Falling-yield signal increased duration through long Treasuries and core bonds.")

    if signals["creditSpreads"] == "wide":
        target["credit"] += 3
        target["yield"] += 0 if risk_tolerance == "defensive" else 2
        target["cash"] += 2
        target["core"] -= 4
        target["short"] -= 3
        rationale.append("Wide credit-spread signal added selective credit exposure while preserving extra cash.")
    elif signals["creditSpreads"] == "tight":
        target["credit"] -= 4
        target["yield"] -= 3
        target["core"] += 4
        target["cash"] += 3
        rationale.append("Tight credit-spread signal reduced lower-quality credit because compensation is thinner.")

    if signals["inflation"] == "hot":
        target["tips"] += 7
        target["long"] -= 4
        target["core"] -= 3
        rationale.append("Hot-inflation signal increased inflation-linked exposure and reduced nominal duration.")
    elif signals["inflation"] == "cooling":
        target["tips"] -= 4
        target["core"] += 2
        target["long"] += 2
        rationale.append("Cooling-inflation signal shifted some TIPS weight into nominal core and long bonds.")

    if signals["recession"] == "high":
        target["cash"] += 5
        target["long"] += 4
        target["yield"] -= 5
        target["credit"] -= 3
        target["core"] -= 1
        rationale.append("High-recession signal increased liquidity and high-quality duration while reducing credit beta.")
    elif signals["recession"] == "low" and risk_tolerance != "defensive":
        target["cash"] -= 2
        target["credit"] += 3
        target["yield"] += 2
        target["short"] -= 3
        rationale.append("Low-recession signal allowed more credit exposure for income.")


def enforce_policy(weights: dict[str, float], max_high_yield: float) -> tuple[dict[str, float], list[str]]:
    policy = {key: bounds.copy() for key, bounds in DEFAULT_POLICY.items()}
    policy["yield"]["max"] = min(policy["yield"]["max"], float(max_high_yield))
    adjusted = weights.copy()
    policy_notes = []

    for asset in ASSETS:
        key = asset["key"]
        before = adjusted[key]
        adjusted[key] = min(max(before, policy[key]["min"]), policy[key]["max"])
        if adjusted[key] != before:
            policy_notes.append(f"{asset['label']} constrained from {before:.1f}% to {adjusted[key]:.1f}%.")

    for _ in range(12):
        diff = 100 - sum(adjusted.values())
        if abs(diff) < 0.0001:
            break
        direction = 1 if diff > 0 else -1
        candidates = []
        for asset in ASSETS:
            key = asset["key"]
            if direction > 0 and adjusted[key] < policy[key]["max"]:
                candidates.append(key)
            if direction < 0 and adjusted[key] > policy[key]["min"]:
                candidates.append(key)
        if not candidates:
            break
        capacity = sum(
            (policy[key]["max"] - adjusted[key]) if direction > 0 else (adjusted[key] - policy[key]["min"])
            for key in candidates
        )
        if capacity <= 0:
            break
        for key in candidates:
            room = (policy[key]["max"] - adjusted[key]) if direction > 0 else (adjusted[key] - policy[key]["min"])
            move = min(abs(diff) * (room / capacity), room)
            adjusted[key] += direction * move

    rounded = {key: round(value, 1) for key, value in adjusted.items()}
    diff = round(100 - sum(rounded.values()), 1)
    while abs(diff) >= 0.1:
        for asset in ASSETS:
            key = asset["key"]
            if diff > 0 and rounded[key] + 0.1 <= policy[key]["max"]:
                rounded[key] = round(rounded[key] + 0.1, 1)
                break
            if diff < 0 and rounded[key] - 0.1 >= policy[key]["min"]:
                rounded[key] = round(rounded[key] - 0.1, 1)
                break
        diff = round(100 - sum(rounded.values()), 1)

    return rounded, policy_notes


def calculate_rebalance(current: dict[str, float], target: dict[str, float], portfolio_size: float) -> tuple[list[dict], float]:
    current_normalized = normalize(current)
    trades = []
    for asset in ASSETS:
        key = asset["key"]
        diff = target[key] - current_normalized.get(key, 0)
        dollars = diff / 100 * portfolio_size
        action = "Hold" if abs(diff) < 0.25 else "Buy" if diff > 0 else "Sell"
        trades.append(
            {
                "Segment": asset["label"],
                "Action": action,
                "Current %": round(current_normalized.get(key, 0), 1),
                "Target %": round(target[key], 1),
                "Trade $": dollars,
            }
        )
    turnover = sum(abs(trade["Trade $"]) for trade in trades) / 2
    return trades, turnover


def allocate(mandate: dict, user_signals: dict, current: dict[str, float], market_data: dict) -> dict:
    market_signals = infer_market_signals(market_data)
    signals = {**market_signals, **user_signals}
    rationale = [f"Base allocation selected for {mandate['riskTolerance']} risk and {mandate['horizon']} horizon."]
    target = base_weights(mandate["riskTolerance"], mandate["horizon"])
    apply_tilts(target, mandate["riskTolerance"], signals, rationale)
    target, policy_notes = enforce_policy(target, mandate["maxHighYield"])
    trades, turnover = calculate_rebalance(current, target, mandate["portfolioSize"])
    return {
        "target": target,
        "trades": trades,
        "turnover": turnover,
        "duration": weighted_metric(target, "duration"),
        "creditRisk": round(weighted_metric(target, "credit")),
        "cashBuffer": target["cash"],
        "signals": signals,
        "rationale": rationale,
        "policyNotes": policy_notes,
    }


def init_session() -> None:
    if "current" not in st.session_state:
        st.session_state.current = DEFAULT_WEIGHTS.copy()
    if "scenarios" not in st.session_state:
        st.session_state.scenarios = []


def money(value: float) -> str:
    return f"${value:,.0f}"


def percent_or_na(value: float | None) -> str:
    return "n/a" if value is None or (isinstance(value, float) and math.isnan(value)) else f"{value:.2f}%"


st.set_page_config(page_title="Dynamic Bond Allocation Assistant", layout="wide")
init_session()

st.title("Dynamic Bond Allocation Assistant")
st.caption("Fixed-income decision support. This is not personalized financial advice.")

fred_key = get_secret("FRED_API_KEY")
alpha_key = get_secret("ALPHA_VANTAGE_API_KEY")
market_data = fetch_market_data(fred_key, alpha_key)

with st.sidebar:
    st.header("Mandate")
    portfolio_size = st.number_input("Portfolio size", min_value=1000, step=1000, value=1_000_000)
    horizon = st.selectbox("Investment horizon", ["short", "medium", "long"], index=1, format_func=lambda value: {"short": "0-2 years", "medium": "3-7 years", "long": "8+ years"}[value])
    risk_tolerance = st.selectbox("Risk tolerance", ["defensive", "balanced", "growth"], index=1, format_func=lambda value: {"defensive": "Defensive", "balanced": "Balanced", "growth": "Income seeking"}[value])
    max_high_yield = st.slider("Max high yield", min_value=0, max_value=20, value=8)

    st.header("Market Signals")
    inferred = infer_market_signals(market_data)
    yield_trend = st.selectbox("Yield trend", ["falling", "stable", "rising"], index=["falling", "stable", "rising"].index(inferred.get("yieldTrend", "stable")))
    credit_spreads = st.selectbox("Credit spreads", ["tight", "normal", "wide"], index=["tight", "normal", "wide"].index(inferred.get("creditSpreads", "normal")))
    inflation = st.selectbox("Inflation pressure", ["cooling", "normal", "hot"], index=["cooling", "normal", "hot"].index(inferred.get("inflation", "normal")))
    recession = st.selectbox("Recession risk", ["low", "medium", "high"], index=1)

    st.header("Current Portfolio")
    for asset in ASSETS:
        st.session_state.current[asset["key"]] = st.number_input(
            asset["label"],
            min_value=0.0,
            max_value=100.0,
            value=float(st.session_state.current[asset["key"]]),
            step=0.5,
        )

mandate = {
    "portfolioSize": float(portfolio_size),
    "horizon": horizon,
    "riskTolerance": risk_tolerance,
    "maxHighYield": float(max_high_yield),
}
signals = {
    "yieldTrend": yield_trend,
    "creditSpreads": credit_spreads,
    "inflation": inflation,
    "recession": recession,
}
result = allocate(mandate, signals, st.session_state.current, market_data)

metric_cols = st.columns(4)
metric_cols[0].metric("Estimated duration", f"{result['duration']:.1f} yrs")
metric_cols[1].metric("Credit risk score", result["creditRisk"])
metric_cols[2].metric("Cash buffer", f"{result['cashBuffer']:.1f}%")
metric_cols[3].metric("Turnover", money(result["turnover"]))

left, right = st.columns([1.25, 1])
with left:
    st.subheader("Target Allocation")
    allocation_rows = [{"Segment": asset["label"], "Target %": result["target"][asset["key"]]} for asset in ASSETS]
    st.bar_chart({row["Segment"]: row["Target %"] for row in allocation_rows})
    st.dataframe(allocation_rows, use_container_width=True, hide_index=True)

with right:
    st.subheader("Market Data")
    st.caption(f"{market_data.get('provider')} / {market_data.get('authStatus')} / as of {market_data.get('asOf')}")
    market_cols = st.columns(2)
    market_cols[0].metric("2Y Treasury", percent_or_na((market_data.get("yields") or {}).get("us2y")))
    market_cols[1].metric("10Y Treasury", percent_or_na((market_data.get("yields") or {}).get("us10y")))
    market_cols[0].metric("HY Spread", percent_or_na((market_data.get("spreads") or {}).get("highYield")))
    market_cols[1].metric("10Y Breakeven", percent_or_na((market_data.get("inflationExpectations") or {}).get("us10yBreakeven")))

st.subheader("Rebalance Orders")
trade_rows = [
    {
        **trade,
        "Trade $": money(abs(trade["Trade $"])),
    }
    for trade in sorted(result["trades"], key=lambda item: abs(item["Trade $"]), reverse=True)
]
st.dataframe(trade_rows, use_container_width=True, hide_index=True)

st.subheader("Assistant Brief")
duration_posture = "long duration" if result["duration"] > 6.5 else "short duration" if result["duration"] < 4 else "neutral duration"
credit_posture = "higher credit beta" if result["creditRisk"] > 42 else "defensive credit" if result["creditRisk"] < 27 else "selective credit"
st.write(
    f"The allocation engine favors {duration_posture} and {credit_posture}. "
    "It combines mandate inputs, market signals, and policy bands, then calculates rebalance trades from the current portfolio."
)
for note in result["rationale"] + result["policyNotes"]:
    st.write(f"- {note}")

if st.button("Save scenario"):
    st.session_state.scenarios.insert(
        0,
        {
            "createdAt": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "mandate": mandate,
            "signals": signals,
            "target": result["target"],
            "turnover": result["turnover"],
        },
    )
    st.success("Scenario saved for this browser session.")

with st.expander("Scenario history"):
    if not st.session_state.scenarios:
        st.write("No saved scenarios yet.")
    else:
        st.dataframe(st.session_state.scenarios, use_container_width=True)

with st.expander("Publishing notes"):
    st.write(
        "For Streamlit Community Cloud, set `streamlit_app.py` as the app file. "
        "Add `FRED_API_KEY` and `ALPHA_VANTAGE_API_KEY` in Streamlit secrets for authenticated data. "
        "Without secrets, the app uses the demo fallback snapshot."
    )

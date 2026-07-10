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
    "recessionIndicators": {"smoothedProbability": 4.1, "unemploymentRate": 4.2},
    "etfs": {
        "SGOV": {"price": 100.42, "changePct": 0.01},
        "SHY": {"price": 82.18, "changePct": -0.04},
        "IEF": {"price": 92.35, "changePct": -0.18},
        "TLT": {"price": 87.62, "changePct": -0.42},
    },
    "sources": ["Demo snapshot used until FRED_API_KEY and ALPHA_VANTAGE_API_KEY are configured."],
    "errors": [],
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
        "recessionIndicators": {},
        "etfs": {},
        "sources": [],
        "errors": [],
        "retrievedAt": datetime.now(timezone.utc).isoformat(),
    }

    if fred_key:
        fred_series = {
            "us3m": ("DGS3MO", "yields"),
            "us2y": ("DGS2", "yields"),
            "us5y": ("DGS5", "yields"),
            "us10y": ("DGS10", "yields"),
            "us30y": ("DGS30", "yields"),
            "highYield": ("BAMLH0A0HYM2", "spreads"),
            "investmentGrade": ("BAMLC0A0CM", "spreads"),
            "us5yBreakeven": ("T5YIE", "inflationExpectations"),
            "us10yBreakeven": ("T10YIE", "inflationExpectations"),
            "smoothedProbability": ("RECPROUSM156N", "recessionIndicators"),
            "unemploymentRate": ("UNRATE", "recessionIndicators"),
        }
        for key, (series_id, bucket) in fred_series.items():
            try:
                value, date = fetch_fred_latest(series_id, fred_key)
                data[bucket][key] = value
                data["asOf"] = data["asOf"] or date
            except Exception as error:
                data["errors"].append(f"FRED {series_id}: {error}")
        data["sources"].append(
            "FRED API: Treasury yields, credit spreads, breakeven inflation, recession probability, and unemployment."
        )

    if alpha_key:
        for symbol in ("SGOV", "SHY", "IEF", "TLT"):
            try:
                data["etfs"][symbol] = fetch_alpha_vantage_quote(symbol, alpha_key)
            except Exception as error:
                data["errors"].append(f"Alpha Vantage {symbol}: {error}")
        data["sources"].append("Alpha Vantage API: ETF quote snapshots for SGOV, SHY, IEF, and TLT.")

    if not data["asOf"]:
        data["asOf"] = "n/a"
    return data


def weighted_metric(weights: dict[str, float], field: str) -> float:
    return sum((weights.get(asset["key"], 0) / 100) * asset[field] for asset in ASSETS)


def infer_market_signals(market_data: dict) -> dict:
    signals = {"yieldTrend": "stable", "creditSpreads": "normal", "inflation": "normal", "recession": "medium"}
    yields = market_data.get("yields") or {}
    spreads = market_data.get("spreads") or {}
    inflation = market_data.get("inflationExpectations") or {}
    recession = market_data.get("recessionIndicators") or {}

    if isinstance(yields.get("us10y"), (int, float)) and isinstance(yields.get("us2y"), (int, float)):
        slope = yields["us10y"] - yields["us2y"]
        signals["yieldTrend"] = "rising" if slope > 0.5 else "falling" if slope < -0.25 else "stable"

    if isinstance(spreads.get("highYield"), (int, float)):
        high_yield = spreads["highYield"]
        signals["creditSpreads"] = "wide" if high_yield > 5 else "tight" if high_yield < 3.2 else "normal"

    if isinstance(inflation.get("us10yBreakeven"), (int, float)):
        breakeven = inflation["us10yBreakeven"]
        signals["inflation"] = "hot" if breakeven > 2.6 else "cooling" if breakeven < 2 else "normal"

    probability = recession.get("smoothedProbability")
    if isinstance(probability, (int, float)):
        signals["recession"] = "high" if probability > 25 else "medium" if probability > 10 else "low"

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
    if signals.get("yieldTrend") == "rising":
        target["short"] += 8
        target["cash"] += 3
        target["long"] -= 7
        target["core"] -= 4
        rationale.append("A steep or rising yield-curve signal favors shorter duration and extra liquidity.")
    elif signals.get("yieldTrend") == "falling":
        target["long"] += 7
        target["core"] += 4
        target["short"] -= 6
        target["cash"] -= 2
        rationale.append("An inverted or falling yield-curve signal adds high-quality duration.")

    if signals.get("creditSpreads") == "wide":
        target["credit"] += 3
        target["yield"] += 0 if risk_tolerance == "defensive" else 2
        target["cash"] += 2
        target["core"] -= 4
        target["short"] -= 3
        rationale.append("Wide credit spreads allow selective credit exposure while preserving a cash buffer.")
    elif signals.get("creditSpreads") == "tight":
        target["credit"] -= 4
        target["yield"] -= 3
        target["core"] += 4
        target["cash"] += 3
        rationale.append("Tight credit spreads reduce compensation for lower-quality credit risk.")

    if signals.get("inflation") == "hot":
        target["tips"] += 7
        target["long"] -= 4
        target["core"] -= 3
        rationale.append("Elevated inflation expectations increase inflation-linked exposure and reduce nominal duration.")
    elif signals.get("inflation") == "cooling":
        target["tips"] -= 4
        target["core"] += 2
        target["long"] += 2
        rationale.append("Cooling inflation expectations shift some allocation back into nominal bonds.")

    if signals.get("recession") == "high":
        target["cash"] += 5
        target["long"] += 4
        target["yield"] -= 5
        target["credit"] -= 3
        target["core"] -= 1
        rationale.append("High recession risk increases liquidity and high-quality duration while reducing credit beta.")
    elif signals.get("recession") == "low" and risk_tolerance != "defensive":
        target["cash"] -= 2
        target["credit"] += 3
        target["yield"] += 2
        target["short"] -= 3
        rationale.append("Low recession risk supports more income exposure through credit.")


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


def allocate(mandate: dict, user_signals: dict, market_data: dict) -> dict:
    market_signals = infer_market_signals(market_data)
    signals = {**market_signals, **user_signals}
    rationale = [f"Base allocation selected for {mandate['riskTolerance']} risk and {mandate['horizon']} horizon."]
    target = base_weights(mandate["riskTolerance"], mandate["horizon"])
    apply_tilts(target, mandate["riskTolerance"], signals, rationale)
    target, policy_notes = enforce_policy(target, mandate["maxHighYield"])
    return {
        "target": target,
        "duration": weighted_metric(target, "duration"),
        "creditRisk": round(weighted_metric(target, "credit")),
        "cashBuffer": target["cash"],
        "signals": signals,
        "rationale": rationale,
        "policyNotes": policy_notes,
    }


def percent_or_na(value: float | None) -> str:
    return "n/a" if value is None or (isinstance(value, float) and math.isnan(value)) else f"{value:.2f}%"


def signed_percent_or_na(value: float | None) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "n/a"
    return f"{value:+.2f}%"


def describe_macro_rationale(result: dict, market_data: dict) -> list[tuple[str, str]]:
    yields = market_data.get("yields") or {}
    spreads = market_data.get("spreads") or {}
    inflation = market_data.get("inflationExpectations") or {}
    recession = market_data.get("recessionIndicators") or {}
    signals = result["signals"]
    slope = None
    if isinstance(yields.get("us10y"), (int, float)) and isinstance(yields.get("us2y"), (int, float)):
        slope = yields["us10y"] - yields["us2y"]

    return [
        (
            "Yield curve",
            (
                f"2Y Treasury is {percent_or_na(yields.get('us2y'))}, 10Y is {percent_or_na(yields.get('us10y'))}, "
                f"and the 10Y-2Y slope is {signed_percent_or_na(slope)}. "
                f"The model reads this as a {signals['yieldTrend']} duration signal, which "
                f"{'keeps more weight in short bonds and cash' if signals['yieldTrend'] == 'rising' else 'adds long and core duration' if signals['yieldTrend'] == 'falling' else 'keeps duration near the mandate baseline'}."
            ),
        ),
        (
            "Credit spreads",
            (
                f"High-yield spreads are {percent_or_na(spreads.get('highYield'))} and investment-grade spreads are "
                f"{percent_or_na(spreads.get('investmentGrade'))}. The model classifies spreads as "
                f"{signals['creditSpreads']}, so it "
                f"{'limits lower-quality credit because spread compensation is thin' if signals['creditSpreads'] == 'tight' else 'allows selective credit exposure while keeping liquidity' if signals['creditSpreads'] == 'wide' else 'keeps credit exposure close to the base allocation'}."
            ),
        ),
        (
            "Inflation expectations",
            (
                f"5Y breakeven inflation is {percent_or_na(inflation.get('us5yBreakeven'))} and 10Y breakeven inflation is "
                f"{percent_or_na(inflation.get('us10yBreakeven'))}. The inflation signal is {signals['inflation']}, "
                f"which {'raises TIPS exposure and trims nominal duration' if signals['inflation'] == 'hot' else 'reduces the TIPS tilt and supports nominal bonds' if signals['inflation'] == 'cooling' else 'keeps TIPS near the strategic weight'}."
            ),
        ),
        (
            "Recession risk",
            (
                f"FRED recession probability is {percent_or_na(recession.get('smoothedProbability'))} and unemployment is "
                f"{percent_or_na(recession.get('unemploymentRate'))}. The recession setting is {signals['recession']}, "
                f"so the recommendation {'adds liquidity and long Treasuries while cutting credit beta' if signals['recession'] == 'high' else 'allows more income-oriented credit exposure' if signals['recession'] == 'low' else 'keeps a balanced mix of carry, duration, and credit risk'}."
            ),
        ),
    ]


LLM_INSTRUCTIONS = """
You are an analyst inside a bond allocation dashboard. Use only the provided data snapshot and prior chat
messages to explain the current bond market environment, yield curve dynamics, credit spreads, inflation
expectations, recession risk, and allocation logic. Be concise, data-driven, and natural. Do not present the
output as personalized financial advice, and do not invent unavailable data.
""".strip()


def build_llm_snapshot(mandate: dict, result: dict, market_data: dict) -> dict:
    yields = market_data.get("yields") or {}
    slope_10y_2y = None
    if isinstance(yields.get("us10y"), (int, float)) and isinstance(yields.get("us2y"), (int, float)):
        slope_10y_2y = round(yields["us10y"] - yields["us2y"], 3)

    return {
        "asOf": market_data.get("asOf"),
        "provider": market_data.get("provider"),
        "authStatus": market_data.get("authStatus"),
        "mandate": mandate,
        "recommendedAllocation": result["target"],
        "portfolioMetrics": {
            "estimatedDurationYears": round(result["duration"], 2),
            "creditRiskScore": result["creditRisk"],
            "cashOrTBillsWeight": result["cashBuffer"],
        },
        "signals": result["signals"],
        "derivedMetrics": {"tenYearMinusTwoYearYieldSlope": slope_10y_2y},
        "marketData": {
            "treasuryYields": market_data.get("yields") or {},
            "creditSpreads": market_data.get("spreads") or {},
            "inflationExpectations": market_data.get("inflationExpectations") or {},
            "recessionIndicators": market_data.get("recessionIndicators") or {},
            "etfQuotes": market_data.get("etfs") or {},
        },
        "ruleBasedRationale": result["rationale"],
        "policyNotes": result["policyNotes"],
        "sources": market_data.get("sources") or [],
        "dataErrors": market_data.get("errors") or [],
    }


def init_chat_state() -> None:
    if "llm_messages" not in st.session_state:
        st.session_state.llm_messages = []


def call_llm(api_key: str, model: str, snapshot: dict, messages: list[dict[str, str]]) -> str:
    from openai import OpenAI

    input_messages = [
        {
            "role": "user",
            "content": (
                "Current dashboard data snapshot. Treat this as the authoritative dataset for the answer:\n"
                f"{json.dumps(snapshot, indent=2, sort_keys=True)}"
            ),
        },
        *messages[-10:],
    ]
    client = OpenAI(api_key=api_key)
    response = client.responses.create(
        model=model,
        instructions=LLM_INSTRUCTIONS,
        input=input_messages,
        max_output_tokens=650,
        temperature=0.3,
        truncation="auto",
    )
    return response.output_text.strip()


st.set_page_config(page_title="Dynamic Bond Allocation Assistant", layout="wide")
init_chat_state()

st.title("Dynamic Bond Allocation Assistant")
st.caption("General fixed-income allocation decision support. This is not personalized financial advice.")

fred_key = get_secret("FRED_API_KEY")
alpha_key = get_secret("ALPHA_VANTAGE_API_KEY")
openai_key = get_secret("OPENAI_API_KEY")
openai_model = get_secret("OPENAI_MODEL") or "gpt-5.6"
market_data = fetch_market_data(fred_key, alpha_key)

with st.sidebar:
    st.header("Mandate")
    horizon = st.selectbox(
        "Investment horizon",
        ["short", "medium", "long"],
        index=1,
        format_func=lambda value: {"short": "0-2 years", "medium": "3-7 years", "long": "8+ years"}[value],
    )
    risk_tolerance = st.selectbox(
        "Risk tolerance",
        ["defensive", "balanced", "growth"],
        index=1,
        format_func=lambda value: {"defensive": "Defensive", "balanced": "Balanced", "growth": "Income seeking"}[value],
    )
    max_high_yield = st.slider("Max high yield allocation", min_value=0, max_value=20, value=8)

    st.header("Market Signals")
    inferred = infer_market_signals(market_data)
    yield_trend = st.selectbox(
        "Yield trend",
        ["falling", "stable", "rising"],
        index=["falling", "stable", "rising"].index(inferred["yieldTrend"]),
        help="Prefilled from the 10Y-2Y Treasury curve slope when FRED data is available.",
    )
    credit_spreads = st.selectbox(
        "Credit spreads",
        ["tight", "normal", "wide"],
        index=["tight", "normal", "wide"].index(inferred["creditSpreads"]),
        help="Prefilled from high-yield spread data when FRED data is available.",
    )
    inflation = st.selectbox(
        "Inflation pressure",
        ["cooling", "normal", "hot"],
        index=["cooling", "normal", "hot"].index(inferred["inflation"]),
        help="Prefilled from 10Y breakeven inflation when FRED data is available.",
    )
    recession = st.selectbox(
        "Recession risk",
        ["low", "medium", "high"],
        index=["low", "medium", "high"].index(inferred["recession"]),
        help="Prefilled from FRED recession probability when available; otherwise defaults to medium.",
    )

mandate = {
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
result = allocate(mandate, signals, market_data)

metric_cols = st.columns(4)
metric_cols[0].metric("Estimated duration", f"{result['duration']:.1f} yrs")
metric_cols[1].metric("Credit risk score", result["creditRisk"])
metric_cols[2].metric("Cash / T-bills", f"{result['cashBuffer']:.1f}%")
metric_cols[3].metric("High yield cap", f"{max_high_yield:.0f}%")

left, right = st.columns([1.25, 1])
with left:
    st.subheader("Recommended Allocation")
    allocation_rows = [{"Segment": asset["label"], "Target %": result["target"][asset["key"]]} for asset in ASSETS]
    st.bar_chart({row["Segment"]: row["Target %"] for row in allocation_rows})
    st.dataframe(allocation_rows, use_container_width=True, hide_index=True)

with right:
    st.subheader("Market Data")
    st.caption(f"{market_data.get('provider')} / {market_data.get('authStatus')} / as of {market_data.get('asOf')}")
    market_cols = st.columns(2)
    yields = market_data.get("yields") or {}
    spreads = market_data.get("spreads") or {}
    breakevens = market_data.get("inflationExpectations") or {}
    recession_data = market_data.get("recessionIndicators") or {}
    market_cols[0].metric("2Y Treasury", percent_or_na(yields.get("us2y")))
    market_cols[1].metric("10Y Treasury", percent_or_na(yields.get("us10y")))
    market_cols[0].metric("30Y Treasury", percent_or_na(yields.get("us30y")))
    market_cols[1].metric("HY Spread", percent_or_na(spreads.get("highYield")))
    market_cols[0].metric("10Y Breakeven", percent_or_na(breakevens.get("us10yBreakeven")))
    market_cols[1].metric("Recession Probability", percent_or_na(recession_data.get("smoothedProbability")))

st.subheader("Macro Rationale")
for title, explanation in describe_macro_rationale(result, market_data):
    st.markdown(f"**{title}.** {explanation}")

st.subheader("AI Market Chat")
st.caption("Session-only conversation over the current dashboard dataset. This is narrative synthesis, not financial advice.")
llm_snapshot = build_llm_snapshot(mandate, result, market_data)

if not openai_key:
    st.info("Set `OPENAI_API_KEY` in Streamlit secrets or the environment to enable the chat assistant.")

summarize_clicked = st.button("Summarize dataset", disabled=not openai_key)
if summarize_clicked:
    summary_prompt = (
        "Summarize the full current data snapshot in analyst commentary. Cover the bond market environment, "
        "yield curve dynamics, credit spreads, inflation expectations, recession risk, and how these inputs affect "
        "the recommended allocation."
    )
    st.session_state.llm_messages.append({"role": "user", "content": summary_prompt})
    try:
        with st.spinner("Generating market commentary..."):
            answer = call_llm(openai_key, openai_model, llm_snapshot, st.session_state.llm_messages)
        st.session_state.llm_messages.append({"role": "assistant", "content": answer})
    except Exception as error:
        st.session_state.llm_messages.append(
            {"role": "assistant", "content": f"LLM request failed: {error}"}
        )

for message in st.session_state.llm_messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

chat_prompt = st.chat_input(
    "Ask about the dataset, allocation logic, or macro trends",
    disabled=not openai_key,
)
if chat_prompt:
    st.session_state.llm_messages.append({"role": "user", "content": chat_prompt})
    with st.chat_message("user"):
        st.markdown(chat_prompt)
    try:
        with st.spinner("Analyzing current data snapshot..."):
            answer = call_llm(openai_key, openai_model, llm_snapshot, st.session_state.llm_messages)
        st.session_state.llm_messages.append({"role": "assistant", "content": answer})
        with st.chat_message("assistant"):
            st.markdown(answer)
    except Exception as error:
        error_text = f"LLM request failed: {error}"
        st.session_state.llm_messages.append({"role": "assistant", "content": error_text})
        with st.chat_message("assistant"):
            st.error(error_text)

st.subheader("Advisor Brief")
duration_posture = "long duration" if result["duration"] > 6.5 else "short duration" if result["duration"] < 4 else "neutral duration"
credit_posture = "higher credit beta" if result["creditRisk"] > 42 else "defensive credit" if result["creditRisk"] < 27 else "selective credit"
st.write(
    f"The recommendation favors **{duration_posture}** and **{credit_posture}** positioning. "
    "It combines mandate inputs, current macro signals, and policy bands to produce a general target allocation."
)
for note in result["rationale"] + result["policyNotes"]:
    st.write(f"- {note}")

with st.expander("Data sources and publishing notes"):
    if market_data.get("sources"):
        for source in market_data["sources"]:
            st.write(f"- {source}")
    if market_data.get("errors"):
        st.warning("Some market data could not be refreshed.")
        for error in market_data["errors"]:
            st.write(f"- {error}")
    st.write(
        "For Streamlit Community Cloud, set `streamlit_app.py` as the app file. "
        "Add `FRED_API_KEY` and `ALPHA_VANTAGE_API_KEY` in Streamlit secrets for authenticated data. "
        "Without secrets, the app uses the demo fallback snapshot."
    )

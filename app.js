const assets = [
  { key: "cash", label: "Cash / T-Bills", color: "var(--cash)", duration: 0.2, credit: 0 },
  { key: "short", label: "Short Duration", color: "var(--short)", duration: 1.8, credit: 10 },
  { key: "core", label: "Core Bonds", color: "var(--core)", duration: 5.6, credit: 25 },
  { key: "long", label: "Long Treasuries", color: "var(--long)", duration: 15.5, credit: 0 },
  { key: "tips", label: "Inflation Linked", color: "var(--tips)", duration: 6.7, credit: 5 },
  { key: "credit", label: "Investment Grade Credit", color: "var(--credit)", duration: 6.8, credit: 55 },
  { key: "yield", label: "High Yield", color: "var(--yield)", duration: 3.7, credit: 95 },
];

const defaults = {
  cash: 8,
  short: 18,
  core: 34,
  long: 10,
  tips: 10,
  credit: 16,
  yield: 4,
};

const state = {
  current: { ...defaults },
};

const controls = {
  portfolioSize: document.querySelector("#portfolioSize"),
  horizon: document.querySelector("#horizon"),
  riskTolerance: document.querySelector("#riskTolerance"),
  maxHighYield: document.querySelector("#maxHighYield"),
  yieldTrend: document.querySelector("#yieldTrend"),
  creditSpreads: document.querySelector("#creditSpreads"),
  inflation: document.querySelector("#inflation"),
  recession: document.querySelector("#recession"),
};

function clamp(value, min, max) {
  return Math.min(Math.max(value, min), max);
}

function normalize(weights) {
  const total = Object.values(weights).reduce((sum, value) => sum + value, 0);
  if (!total) return { ...defaults };
  return Object.fromEntries(Object.entries(weights).map(([key, value]) => [key, (value / total) * 100]));
}

function rebalanceToHundred(weights) {
  const normalized = normalize(weights);
  return Object.fromEntries(Object.entries(normalized).map(([key, value]) => [key, Number(value.toFixed(1))]));
}

function computeTarget() {
  const risk = controls.riskTolerance.value;
  const horizon = controls.horizon.value;
  const target = {
    cash: risk === "defensive" ? 12 : risk === "growth" ? 5 : 8,
    short: 18,
    core: 34,
    long: horizon === "long" ? 13 : horizon === "short" ? 5 : 10,
    tips: 10,
    credit: risk === "growth" ? 19 : risk === "defensive" ? 12 : 16,
    yield: risk === "growth" ? 7 : risk === "defensive" ? 2 : 4,
  };

  if (controls.yieldTrend.value === "rising") {
    target.short += 8;
    target.cash += 3;
    target.long -= 7;
    target.core -= 4;
  }

  if (controls.yieldTrend.value === "falling") {
    target.long += 7;
    target.core += 4;
    target.short -= 6;
    target.cash -= 2;
  }

  if (controls.creditSpreads.value === "wide") {
    target.credit += 3;
    target.yield += risk === "defensive" ? 0 : 2;
    target.cash += 2;
    target.core -= 4;
    target.short -= 3;
  }

  if (controls.creditSpreads.value === "tight") {
    target.credit -= 4;
    target.yield -= 3;
    target.core += 4;
    target.cash += 3;
  }

  if (controls.inflation.value === "hot") {
    target.tips += 7;
    target.long -= 4;
    target.core -= 3;
  }

  if (controls.inflation.value === "cooling") {
    target.tips -= 4;
    target.core += 2;
    target.long += 2;
  }

  if (controls.recession.value === "high") {
    target.cash += 5;
    target.long += 4;
    target.yield -= 5;
    target.credit -= 3;
    target.core -= 1;
  }

  if (controls.recession.value === "low" && risk !== "defensive") {
    target.cash -= 2;
    target.credit += 3;
    target.yield += 2;
    target.short -= 3;
  }

  target.yield = clamp(target.yield, 0, Number(controls.maxHighYield.value));
  assets.forEach((asset) => {
    target[asset.key] = clamp(target[asset.key], 0, 65);
  });

  return rebalanceToHundred(target);
}

function weightedMetric(weights, field) {
  return assets.reduce((sum, asset) => sum + ((weights[asset.key] || 0) / 100) * asset[field], 0);
}

function formatCurrency(value) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(value);
}

function renderCurrentInputs() {
  const container = document.querySelector("#currentInputs");
  container.innerHTML = "";
  assets.forEach((asset) => {
    const row = document.createElement("label");
    row.className = "current-row";
    row.innerHTML = `
      <span>${asset.label}</span>
      <input type="number" min="0" max="100" step="0.5" value="${state.current[asset.key]}" aria-label="${asset.label} current weight" />
    `;
    row.querySelector("input").addEventListener("input", (event) => {
      state.current[asset.key] = Number(event.target.value || 0);
      render();
    });
    container.appendChild(row);
  });
}

function renderAllocationBars(target) {
  const container = document.querySelector("#allocationBars");
  container.innerHTML = "";
  assets.forEach((asset) => {
    const row = document.createElement("div");
    row.className = "bar-row";
    row.innerHTML = `
      <span class="bar-label">${asset.label}</span>
      <span class="bar-track"><span class="bar-fill" style="width: ${target[asset.key]}%; background: ${asset.color}"></span></span>
      <span class="bar-value">${target[asset.key].toFixed(1)}%</span>
    `;
    container.appendChild(row);
  });
}

function renderRebalance(target) {
  const portfolioSize = Number(controls.portfolioSize.value || 0);
  const current = normalize(state.current);
  const rows = assets.map((asset) => {
    const diff = target[asset.key] - current[asset.key];
    return { asset, diff, dollars: (diff / 100) * portfolioSize };
  });
  const turnover = rows.reduce((sum, row) => sum + Math.abs(row.dollars), 0) / 2;

  document.querySelector("#turnoverMetric").textContent = formatCurrency(turnover);

  const table = document.querySelector("#rebalanceTable");
  table.innerHTML = `
    <div class="table-row header">
      <span>Segment</span><span>Action</span><span>Amount</span>
    </div>
  `;

  rows
    .sort((a, b) => Math.abs(b.dollars) - Math.abs(a.dollars))
    .forEach((row) => {
      const action = Math.abs(row.dollars) < portfolioSize * 0.0025 ? "Hold" : row.dollars > 0 ? "Buy" : "Sell";
      const className = action === "Buy" ? "trade-buy" : action === "Sell" ? "trade-sell" : "";
      const element = document.createElement("div");
      element.className = "table-row";
      element.innerHTML = `
        <span>${row.asset.label}</span>
        <span class="${className}">${action}</span>
        <span>${formatCurrency(Math.abs(row.dollars))}</span>
      `;
      table.appendChild(element);
    });
}

function renderBrief(target) {
  const duration = weightedMetric(target, "duration");
  const credit = weightedMetric(target, "credit");
  const cash = target.cash;

  document.querySelector("#durationMetric").textContent = `${duration.toFixed(1)} yrs`;
  document.querySelector("#creditMetric").textContent = Math.round(credit);
  document.querySelector("#cashMetric").textContent = `${cash.toFixed(1)}%`;

  const durationPosture = duration > 6.5 ? "Long duration" : duration < 4 ? "Short duration" : "Neutral duration";
  const creditPosture = credit > 42 ? "Higher credit beta" : credit < 27 ? "Defensive credit" : "Selective credit";
  const riskPosture = controls.recession.value === "high" || controls.yieldTrend.value === "rising" ? "Defensive" : controls.riskTolerance.value === "growth" ? "Income seeking" : "Balanced";

  document.querySelector("#riskBadge").textContent = riskPosture;
  document.querySelector("#durationBadge").textContent = durationPosture;
  document.querySelector("#creditBadge").textContent = creditPosture;

  const brief = `The model favors ${durationPosture.toLowerCase()} and ${creditPosture.toLowerCase()} positioning. It adjusts duration around the yield trend, keeps liquidity near ${cash.toFixed(1)}%, and respects the high-yield cap of ${controls.maxHighYield.value}%. Treat this as an allocation proposal to review against taxes, mandates, holdings quality, and transaction costs.`;
  document.querySelector("#assistantBrief").textContent = brief;

  const risks = [];
  if (controls.yieldTrend.value === "rising") risks.push("Rising yields can pressure longer-duration holdings.");
  if (controls.creditSpreads.value === "tight") risks.push("Tight credit spreads reduce compensation for downgrade and default risk.");
  if (controls.creditSpreads.value === "wide") risks.push("Wide spreads may offer entry points, but liquidity and default risk can rise together.");
  if (controls.inflation.value === "hot") risks.push("Hot inflation increases the value of inflation protection but can keep policy rates restrictive.");
  if (controls.recession.value === "high") risks.push("High recession risk argues for liquidity, quality, and stress-tested cash flows.");
  if (!risks.length) risks.push("Base-case signals are balanced; monitor yield volatility, inflation surprises, and spread changes.");

  const list = document.querySelector("#riskList");
  list.innerHTML = "";
  risks.forEach((risk) => {
    const item = document.createElement("li");
    item.textContent = risk;
    list.appendChild(item);
  });
}

function render() {
  document.querySelector("#maxHighYieldValue").textContent = `${controls.maxHighYield.value}%`;
  const target = computeTarget();
  renderAllocationBars(target);
  renderRebalance(target);
  renderBrief(target);
}

Object.values(controls).forEach((control) => control.addEventListener("input", render));

document.querySelector("#resetButton").addEventListener("click", () => {
  state.current = { ...defaults };
  controls.portfolioSize.value = 1000000;
  controls.horizon.value = "medium";
  controls.riskTolerance.value = "balanced";
  controls.maxHighYield.value = 8;
  controls.yieldTrend.value = "stable";
  controls.creditSpreads.value = "normal";
  controls.inflation.value = "normal";
  controls.recession.value = "medium";
  renderCurrentInputs();
  render();
});

renderCurrentInputs();
render();

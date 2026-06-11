const engine = window.AllocationEngine;

const assetColors = {
  cash: "var(--cash)",
  short: "var(--short)",
  core: "var(--core)",
  long: "var(--long)",
  tips: "var(--tips)",
  credit: "var(--credit)",
  yield: "var(--yield)",
};

const state = {
  current: { ...engine.DEFAULT_WEIGHTS },
  marketData: null,
  latestResult: null,
  backendAvailable: true,
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

function formatCurrency(value) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(value);
}

function formatPct(value) {
  return Number.isFinite(Number(value)) ? `${Number(value).toFixed(2)}%` : "n/a";
}

async function api(path, options) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!response.ok) throw new Error(`API ${path} failed with ${response.status}`);
  return response.json();
}

function getInput() {
  return {
    mandate: {
      portfolioSize: Number(controls.portfolioSize.value || 0),
      horizon: controls.horizon.value,
      riskTolerance: controls.riskTolerance.value,
      maxHighYield: Number(controls.maxHighYield.value || 0),
    },
    signals: {
      yieldTrend: controls.yieldTrend.value,
      creditSpreads: controls.creditSpreads.value,
      inflation: controls.inflation.value,
      recession: controls.recession.value,
    },
    current: state.current,
    marketData: state.marketData,
  };
}

function renderCurrentInputs() {
  const container = document.querySelector("#currentInputs");
  container.innerHTML = "";
  engine.ASSETS.forEach((asset) => {
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
  engine.ASSETS.forEach((asset) => {
    const row = document.createElement("div");
    row.className = "bar-row";
    row.innerHTML = `
      <span class="bar-label">${asset.label}</span>
      <span class="bar-track"><span class="bar-fill" style="width: ${target[asset.key]}%; background: ${assetColors[asset.key]}"></span></span>
      <span class="bar-value">${target[asset.key].toFixed(1)}%</span>
    `;
    container.appendChild(row);
  });
}

function renderRebalance(result) {
  document.querySelector("#turnoverMetric").textContent = formatCurrency(result.rebalance.turnover);

  const table = document.querySelector("#rebalanceTable");
  table.innerHTML = `
    <div class="table-row header">
      <span>Segment</span><span>Action</span><span>Amount</span>
    </div>
  `;

  result.rebalance.trades
    .slice()
    .sort((a, b) => Math.abs(b.dollars) - Math.abs(a.dollars))
    .forEach((trade) => {
      const className = trade.action === "Buy" ? "trade-buy" : trade.action === "Sell" ? "trade-sell" : "";
      const element = document.createElement("div");
      element.className = "table-row";
      element.innerHTML = `
        <span>${trade.label}</span>
        <span class="${className}">${trade.action}</span>
        <span>${formatCurrency(Math.abs(trade.dollars))}</span>
      `;
      table.appendChild(element);
    });
}

function renderBrief(result) {
  const duration = result.metrics.duration;
  const credit = result.metrics.creditRisk;
  const cash = result.metrics.cashBuffer;

  document.querySelector("#durationMetric").textContent = `${duration.toFixed(1)} yrs`;
  document.querySelector("#creditMetric").textContent = credit;
  document.querySelector("#cashMetric").textContent = `${cash.toFixed(1)}%`;

  const durationPosture = duration > 6.5 ? "Long duration" : duration < 4 ? "Short duration" : "Neutral duration";
  const creditPosture = credit > 42 ? "Higher credit beta" : credit < 27 ? "Defensive credit" : "Selective credit";
  const riskPosture = controls.recession.value === "high" || controls.yieldTrend.value === "rising" ? "Defensive" : controls.riskTolerance.value === "growth" ? "Income seeking" : "Balanced";

  document.querySelector("#riskBadge").textContent = riskPosture;
  document.querySelector("#durationBadge").textContent = durationPosture;
  document.querySelector("#creditBadge").textContent = creditPosture;

  const policyText = result.policyAdjustments.length ? ` Policy constraints applied: ${result.policyAdjustments.join(" ")}` : "";
  document.querySelector("#assistantBrief").textContent = `The allocation engine favors ${durationPosture.toLowerCase()} and ${creditPosture.toLowerCase()} positioning. It combines mandate inputs, market signals, and policy bands, then calculates rebalance trades from the current portfolio.${policyText} Treat this as decision support to review against taxes, mandates, holdings quality, and transaction costs.`;

  const list = document.querySelector("#riskList");
  list.innerHTML = "";
  [...result.rationale, ...result.policyAdjustments].forEach((risk) => {
    const item = document.createElement("li");
    item.textContent = risk;
    list.appendChild(item);
  });
}

function renderMarketData() {
  const status = document.querySelector("#marketStatus");
  const grid = document.querySelector("#marketDataGrid");
  const marketData = state.marketData;
  if (!marketData) {
    status.textContent = "Unavailable";
    grid.innerHTML = `<div class="market-item"><span>Status</span><strong>Static mode</strong></div>`;
    return;
  }

  status.textContent = `${marketData.provider} / ${marketData.authStatus}`;
  const items = [
    ["As of", marketData.asOf || "n/a"],
    ["2Y Treasury", formatPct(marketData.yields && marketData.yields.us2y)],
    ["10Y Treasury", formatPct(marketData.yields && marketData.yields.us10y)],
    ["30Y Treasury", formatPct(marketData.yields && marketData.yields.us30y)],
    ["HY Spread", formatPct(marketData.spreads && marketData.spreads.highYield)],
    ["10Y Breakeven", formatPct(marketData.inflationExpectations && marketData.inflationExpectations.us10yBreakeven)],
    ["SHY", marketData.etfs && marketData.etfs.SHY ? formatCurrency(marketData.etfs.SHY.price) : "n/a"],
    ["TLT", marketData.etfs && marketData.etfs.TLT ? formatCurrency(marketData.etfs.TLT.price) : "n/a"],
  ];

  grid.innerHTML = items
    .map(([label, value]) => `<div class="market-item"><span>${label}</span><strong>${value}</strong></div>`)
    .join("");
}

async function renderHistory() {
  const container = document.querySelector("#historyList");
  if (!state.backendAvailable) {
    container.innerHTML = `<div class="history-item"><span>Backend</span><strong>Not running</strong><p>Start the server to save scenarios and audit history.</p></div>`;
    return;
  }

  try {
    const [scenarios, audit] = await Promise.all([api("/api/scenarios"), api("/api/audit")]);
    const scenarioItems = scenarios.slice(0, 3).map((scenario) => ({
      label: "Scenario",
      title: scenario.name || "Saved allocation",
      detail: new Date(scenario.createdAt).toLocaleString(),
    }));
    const auditItems = audit.slice(0, 3).map((entry) => ({
      label: "Audit",
      title: entry.action,
      detail: new Date(entry.timestamp).toLocaleString(),
    }));
    const items = [...scenarioItems, ...auditItems];
    container.innerHTML = items.length
      ? items
          .map((item) => `<div class="history-item"><span>${item.label}</span><strong>${item.title}</strong><p>${item.detail}</p></div>`)
          .join("")
      : `<div class="history-item"><span>History</span><strong>No saved scenarios yet</strong><p>Save a scenario to create an audit entry.</p></div>`;
  } catch (error) {
    state.backendAvailable = false;
    renderHistory();
  }
}

function render() {
  document.querySelector("#maxHighYieldValue").textContent = `${controls.maxHighYield.value}%`;
  const result = engine.allocate(getInput());
  state.latestResult = result;
  renderAllocationBars(result.target);
  renderRebalance(result);
  renderBrief(result);
  renderMarketData();
}

async function refreshFromBackend() {
  try {
    state.marketData = await api("/api/market-data");
    state.backendAvailable = true;
  } catch (error) {
    state.backendAvailable = false;
  }
  render();
  await renderHistory();
}

async function saveScenario() {
  if (!state.latestResult) return;
  const payload = {
    name: `Scenario ${new Date().toLocaleString()}`,
    input: getInput(),
    result: state.latestResult,
  };
  if (!state.backendAvailable) {
    alert("Start the backend server to save scenarios.");
    return;
  }
  await api("/api/scenarios", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  await renderHistory();
}

Object.values(controls).forEach((control) => control.addEventListener("input", render));

document.querySelector("#resetButton").addEventListener("click", () => {
  state.current = { ...engine.DEFAULT_WEIGHTS };
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

document.querySelector("#saveScenarioButton").addEventListener("click", saveScenario);

renderCurrentInputs();
render();
refreshFromBackend();

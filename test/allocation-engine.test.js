const test = require("node:test");
const assert = require("node:assert/strict");
const {
  allocate,
  calculateRebalance,
  DEFAULT_WEIGHTS,
  normalize,
} = require("../src/allocation-engine");

function sumWeights(weights) {
  return Object.values(weights).reduce((sum, value) => sum + value, 0);
}

test("normalize converts arbitrary weights to 100 percent", () => {
  const normalized = normalize({ cash: 1, short: 1, core: 2 });
  assert.equal(Number(sumWeights(normalized).toFixed(6)), 100);
  assert.equal(normalized.core, 50);
});

test("allocation respects max high-yield policy after normalization and rounding", () => {
  const result = allocate({
    mandate: {
      riskTolerance: "growth",
      horizon: "medium",
      maxHighYield: 3,
      portfolioSize: 100000,
    },
    signals: {
      creditSpreads: "wide",
      recession: "low",
      yieldTrend: "stable",
      inflation: "normal",
    },
    current: DEFAULT_WEIGHTS,
  });

  assert.equal(Number(sumWeights(result.target).toFixed(1)), 100);
  assert.ok(result.target.yield <= 3);
  assert.ok(result.policyAdjustments.some((adjustment) => adjustment.includes("High Yield")));
});

test("rising-yield signal lowers duration versus falling-yield signal", () => {
  const common = {
    mandate: {
      riskTolerance: "balanced",
      horizon: "medium",
      maxHighYield: 8,
      portfolioSize: 100000,
    },
    current: DEFAULT_WEIGHTS,
  };

  const rising = allocate({
    ...common,
    signals: { yieldTrend: "rising", creditSpreads: "normal", inflation: "normal", recession: "medium" },
  });
  const falling = allocate({
    ...common,
    signals: { yieldTrend: "falling", creditSpreads: "normal", inflation: "normal", recession: "medium" },
  });

  assert.ok(rising.metrics.duration < falling.metrics.duration);
  assert.ok(rising.target.long < falling.target.long);
});

test("hot inflation tilts toward TIPS and away from long nominal duration", () => {
  const normal = allocate({
    mandate: { riskTolerance: "balanced", horizon: "medium", maxHighYield: 8, portfolioSize: 100000 },
    signals: { yieldTrend: "stable", creditSpreads: "normal", inflation: "normal", recession: "medium" },
    current: DEFAULT_WEIGHTS,
  });
  const hot = allocate({
    mandate: { riskTolerance: "balanced", horizon: "medium", maxHighYield: 8, portfolioSize: 100000 },
    signals: { yieldTrend: "stable", creditSpreads: "normal", inflation: "hot", recession: "medium" },
    current: DEFAULT_WEIGHTS,
  });

  assert.ok(hot.target.tips > normal.target.tips);
  assert.ok(hot.target.long < normal.target.long);
});

test("rebalance calculates buy and sell dollar amounts from target differences", () => {
  const rebalance = calculateRebalance(
    { cash: 50, short: 50, core: 0, long: 0, tips: 0, credit: 0, yield: 0 },
    { cash: 25, short: 50, core: 25, long: 0, tips: 0, credit: 0, yield: 0 },
    100000,
    0.1
  );

  const cashTrade = rebalance.trades.find((trade) => trade.key === "cash");
  const coreTrade = rebalance.trades.find((trade) => trade.key === "core");
  assert.equal(cashTrade.action, "Sell");
  assert.equal(coreTrade.action, "Buy");
  assert.equal(Math.abs(cashTrade.dollars), 25000);
  assert.equal(coreTrade.dollars, 25000);
  assert.equal(rebalance.turnover, 25000);
});

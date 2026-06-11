(function initAllocationEngine(root, factory) {
  if (typeof module === "object" && module.exports) {
    module.exports = factory();
  } else {
    root.AllocationEngine = factory();
  }
})(typeof globalThis !== "undefined" ? globalThis : this, function createAllocationEngine() {
  const ASSETS = [
    { key: "cash", label: "Cash / T-Bills", duration: 0.2, credit: 0 },
    { key: "short", label: "Short Duration", duration: 1.8, credit: 10 },
    { key: "core", label: "Core Bonds", duration: 5.6, credit: 25 },
    { key: "long", label: "Long Treasuries", duration: 15.5, credit: 0 },
    { key: "tips", label: "Inflation Linked", duration: 6.7, credit: 5 },
    { key: "credit", label: "Investment Grade Credit", duration: 6.8, credit: 55 },
    { key: "yield", label: "High Yield", duration: 3.7, credit: 95 },
  ];

  const DEFAULT_WEIGHTS = {
    cash: 8,
    short: 18,
    core: 34,
    long: 10,
    tips: 10,
    credit: 16,
    yield: 4,
  };

  const DEFAULT_POLICY = {
    cash: { min: 2, max: 30 },
    short: { min: 5, max: 45 },
    core: { min: 15, max: 55 },
    long: { min: 0, max: 30 },
    tips: { min: 0, max: 25 },
    credit: { min: 0, max: 30 },
    yield: { min: 0, max: 10 },
  };

  function clamp(value, min, max) {
    return Math.min(Math.max(value, min), max);
  }

  function normalize(weights) {
    const total = Object.values(weights).reduce((sum, value) => sum + Number(value || 0), 0);
    if (!total) return { ...DEFAULT_WEIGHTS };
    return Object.fromEntries(Object.entries(weights).map(([key, value]) => [key, (Number(value || 0) / total) * 100]));
  }

  function roundWeights(weights, policy) {
    const rounded = Object.fromEntries(ASSETS.map((asset) => [asset.key, Number((weights[asset.key] || 0).toFixed(1))]));
    let diff = Number((100 - Object.values(rounded).reduce((sum, value) => sum + value, 0)).toFixed(1));
    const direction = diff > 0 ? "add" : "remove";
    while (Math.abs(diff) >= 0.1) {
      const candidate = ASSETS.find((asset) => {
        const bounds = policy && policy[asset.key] ? policy[asset.key] : { min: 0, max: 100 };
        return direction === "add" ? rounded[asset.key] + 0.1 <= bounds.max : rounded[asset.key] - 0.1 >= bounds.min;
      });
      if (!candidate) break;
      rounded[candidate.key] = Number((rounded[candidate.key] + (direction === "add" ? 0.1 : -0.1)).toFixed(1));
      diff = Number((100 - Object.values(rounded).reduce((sum, value) => sum + value, 0)).toFixed(1));
    }
    return rounded;
  }

  function weightedMetric(weights, field) {
    return ASSETS.reduce((sum, asset) => sum + ((weights[asset.key] || 0) / 100) * asset[field], 0);
  }

  function inferSignalsFromMarketData(marketData) {
    const signals = {};
    const yields = marketData && marketData.yields ? marketData.yields : {};
    const spreads = marketData && marketData.spreads ? marketData.spreads : {};
    const inflation = marketData && marketData.inflationExpectations ? marketData.inflationExpectations : {};

    if (Number.isFinite(yields.us10y) && Number.isFinite(yields.us2y)) {
      const slope = yields.us10y - yields.us2y;
      signals.yieldTrend = slope > 0.5 ? "rising" : slope < -0.25 ? "falling" : "stable";
    }

    if (Number.isFinite(spreads.highYield)) {
      signals.creditSpreads = spreads.highYield > 5 ? "wide" : spreads.highYield < 3.2 ? "tight" : "normal";
    }

    if (Number.isFinite(inflation.us10yBreakeven)) {
      signals.inflation = inflation.us10yBreakeven > 2.6 ? "hot" : inflation.us10yBreakeven < 2 ? "cooling" : "normal";
    }

    return signals;
  }

  function baseWeights(mandate) {
    const risk = mandate.riskTolerance || "balanced";
    const horizon = mandate.horizon || "medium";
    return {
      cash: risk === "defensive" ? 12 : risk === "growth" ? 5 : 8,
      short: 18,
      core: 34,
      long: horizon === "long" ? 13 : horizon === "short" ? 5 : 10,
      tips: 10,
      credit: risk === "growth" ? 19 : risk === "defensive" ? 12 : 16,
      yield: risk === "growth" ? 7 : risk === "defensive" ? 2 : 4,
    };
  }

  function applySignalTilts(target, mandate, signals, rationale) {
    const risk = mandate.riskTolerance || "balanced";

    if (signals.yieldTrend === "rising") {
      target.short += 8;
      target.cash += 3;
      target.long -= 7;
      target.core -= 4;
      rationale.push("Rising-yield signal reduced long-duration exposure and increased short-duration liquidity.");
    }

    if (signals.yieldTrend === "falling") {
      target.long += 7;
      target.core += 4;
      target.short -= 6;
      target.cash -= 2;
      rationale.push("Falling-yield signal increased duration through long Treasuries and core bonds.");
    }

    if (signals.creditSpreads === "wide") {
      target.credit += 3;
      target.yield += risk === "defensive" ? 0 : 2;
      target.cash += 2;
      target.core -= 4;
      target.short -= 3;
      rationale.push("Wide credit-spread signal added selective credit exposure while preserving extra cash.");
    }

    if (signals.creditSpreads === "tight") {
      target.credit -= 4;
      target.yield -= 3;
      target.core += 4;
      target.cash += 3;
      rationale.push("Tight credit-spread signal reduced lower-quality credit because compensation is thinner.");
    }

    if (signals.inflation === "hot") {
      target.tips += 7;
      target.long -= 4;
      target.core -= 3;
      rationale.push("Hot-inflation signal increased inflation-linked exposure and reduced nominal duration.");
    }

    if (signals.inflation === "cooling") {
      target.tips -= 4;
      target.core += 2;
      target.long += 2;
      rationale.push("Cooling-inflation signal shifted some TIPS weight into nominal core and long bonds.");
    }

    if (signals.recession === "high") {
      target.cash += 5;
      target.long += 4;
      target.yield -= 5;
      target.credit -= 3;
      target.core -= 1;
      rationale.push("High-recession signal increased liquidity and high-quality duration while reducing credit beta.");
    }

    if (signals.recession === "low" && risk !== "defensive") {
      target.cash -= 2;
      target.credit += 3;
      target.yield += 2;
      target.short -= 3;
      rationale.push("Low-recession signal allowed more credit exposure for income.");
    }
  }

  function enforcePolicy(weights, policy, mandate) {
    const maxHighYield = Number.isFinite(Number(mandate.maxHighYield)) ? Number(mandate.maxHighYield) : policy.yield.max;
    const effectivePolicy = {
      ...policy,
      yield: {
        ...policy.yield,
        max: Math.min(policy.yield.max, maxHighYield),
      },
    };
    const constrained = { ...weights };
    const adjustments = [];

    ASSETS.forEach((asset) => {
      const bounds = effectivePolicy[asset.key] || { min: 0, max: 100 };
      const before = constrained[asset.key] || 0;
      const after = clamp(before, bounds.min, bounds.max);
      constrained[asset.key] = after;
      if (after !== before) {
        adjustments.push(`${asset.label} constrained from ${before.toFixed(1)}% to ${after.toFixed(1)}%.`);
      }
    });

    rebalanceWithinPolicy(constrained, effectivePolicy);

    return { weights: roundWeights(constrained, effectivePolicy), adjustments };
  }

  function rebalanceWithinPolicy(weights, policy) {
    for (let iteration = 0; iteration < 12; iteration += 1) {
      const total = Object.values(weights).reduce((sum, value) => sum + value, 0);
      const diff = 100 - total;
      if (Math.abs(diff) < 0.0001) break;

      const direction = diff > 0 ? "add" : "remove";
      const candidates = ASSETS.filter((asset) => {
        const bounds = policy[asset.key] || { min: 0, max: 100 };
        return direction === "add" ? weights[asset.key] < bounds.max : weights[asset.key] > bounds.min;
      });
      if (!candidates.length) break;

      const available = candidates.reduce((sum, asset) => {
        const bounds = policy[asset.key] || { min: 0, max: 100 };
        return sum + (direction === "add" ? bounds.max - weights[asset.key] : weights[asset.key] - bounds.min);
      }, 0);
      if (available <= 0) break;

      candidates.forEach((asset) => {
        const bounds = policy[asset.key] || { min: 0, max: 100 };
        const capacity = direction === "add" ? bounds.max - weights[asset.key] : weights[asset.key] - bounds.min;
        const adjustment = Math.min(Math.abs(diff) * (capacity / available), capacity);
        weights[asset.key] += direction === "add" ? adjustment : -adjustment;
        weights[asset.key] = clamp(weights[asset.key], bounds.min, bounds.max);
      });
    }
  }

  function calculateRebalance(current, target, portfolioSize, thresholdPct) {
    const currentNormalized = normalize(current || DEFAULT_WEIGHTS);
    const threshold = Number.isFinite(Number(thresholdPct)) ? Number(thresholdPct) : 0.25;
    const size = Number(portfolioSize || 0);
    const trades = ASSETS.map((asset) => {
      const currentWeight = currentNormalized[asset.key] || 0;
      const targetWeight = target[asset.key] || 0;
      const diff = targetWeight - currentWeight;
      const dollars = (diff / 100) * size;
      const action = Math.abs(diff) < threshold ? "Hold" : diff > 0 ? "Buy" : "Sell";
      return {
        key: asset.key,
        label: asset.label,
        currentWeight: Number(currentWeight.toFixed(1)),
        targetWeight: Number(targetWeight.toFixed(1)),
        diff: Number(diff.toFixed(1)),
        dollars,
        action,
      };
    });
    const turnover = trades.reduce((sum, trade) => sum + Math.abs(trade.dollars), 0) / 2;
    return { trades, turnover };
  }

  function allocate(input) {
    const mandate = input && input.mandate ? input.mandate : {};
    const userSignals = input && input.signals ? input.signals : {};
    const marketSignals = inferSignalsFromMarketData(input && input.marketData);
    const signals = { ...marketSignals, ...userSignals };
    const policy = { ...DEFAULT_POLICY, ...(input && input.policy ? input.policy : {}) };
    const rationale = [];
    const target = baseWeights(mandate);

    rationale.push(`Base allocation selected for ${mandate.riskTolerance || "balanced"} risk and ${mandate.horizon || "medium"} horizon.`);
    applySignalTilts(target, mandate, signals, rationale);

    const policyResult = enforcePolicy(target, policy, mandate);
    const weights = policyResult.weights;
    const metrics = {
      duration: Number(weightedMetric(weights, "duration").toFixed(2)),
      creditRisk: Math.round(weightedMetric(weights, "credit")),
      cashBuffer: Number((weights.cash || 0).toFixed(1)),
    };
    const rebalance = calculateRebalance(input && input.current, weights, mandate.portfolioSize, mandate.rebalanceThresholdPct);

    return {
      target: weights,
      metrics,
      rebalance,
      rationale,
      policyAdjustments: policyResult.adjustments,
      signals,
      assets: ASSETS,
    };
  }

  return {
    ASSETS,
    DEFAULT_WEIGHTS,
    DEFAULT_POLICY,
    allocate,
    calculateRebalance,
    inferSignalsFromMarketData,
    normalize,
    weightedMetric,
  };
});

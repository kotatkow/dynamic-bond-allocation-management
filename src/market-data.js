const https = require("node:https");

const DEMO_MARKET_DATA = {
  asOf: "2026-06-10",
  provider: "demo-fallback",
  authStatus: "missing-api-keys",
  yields: {
    us3m: 3.82,
    us2y: 4.13,
    us5y: 4.26,
    us10y: 4.53,
    us30y: 5.01,
  },
  spreads: {
    investmentGrade: 1.05,
    highYield: 3.75,
  },
  inflationExpectations: {
    us5yBreakeven: 2.38,
    us10yBreakeven: 2.31,
  },
  etfs: {
    SGOV: { price: 100.42, changePct: 0.01 },
    SHY: { price: 82.18, changePct: -0.04 },
    IEF: { price: 92.35, changePct: -0.18 },
    TLT: { price: 87.62, changePct: -0.42 },
  },
  sources: [
    "Demo data is used until FRED_API_KEY and ALPHA_VANTAGE_API_KEY are configured.",
  ],
};

function requestJson(url) {
  return new Promise((resolve, reject) => {
    https
      .get(url, (response) => {
        let body = "";
        response.on("data", (chunk) => {
          body += chunk;
        });
        response.on("end", () => {
          if (response.statusCode < 200 || response.statusCode >= 300) {
            reject(new Error(`HTTP ${response.statusCode} from ${url}`));
            return;
          }
          try {
            resolve(JSON.parse(body));
          } catch (error) {
            reject(error);
          }
        });
      })
      .on("error", reject);
  });
}

async function fetchFredLatest(seriesId, apiKey) {
  const url = new URL("https://api.stlouisfed.org/fred/series/observations");
  url.searchParams.set("series_id", seriesId);
  url.searchParams.set("api_key", apiKey);
  url.searchParams.set("file_type", "json");
  url.searchParams.set("sort_order", "desc");
  url.searchParams.set("limit", "1");
  const payload = await requestJson(url);
  const observation = payload.observations && payload.observations[0];
  const value = observation && observation.value !== "." ? Number(observation.value) : null;
  return { value, date: observation ? observation.date : null };
}

async function fetchAlphaVantageQuote(symbol, apiKey) {
  const url = new URL("https://www.alphavantage.co/query");
  url.searchParams.set("function", "GLOBAL_QUOTE");
  url.searchParams.set("symbol", symbol);
  url.searchParams.set("apikey", apiKey);
  const payload = await requestJson(url);
  const quote = payload["Global Quote"] || {};
  return {
    price: Number(quote["05. price"] || 0) || null,
    changePct: Number(String(quote["10. change percent"] || "").replace("%", "")) || null,
  };
}

async function fetchMarketData(env = process.env) {
  const fredKey = env.FRED_API_KEY;
  const alphaKey = env.ALPHA_VANTAGE_API_KEY;
  if (!fredKey && !alphaKey) {
    return { ...DEMO_MARKET_DATA, retrievedAt: new Date().toISOString() };
  }

  const data = {
    asOf: null,
    provider: "fred-alpha-vantage",
    authStatus: "authenticated",
    yields: {},
    spreads: {},
    inflationExpectations: {},
    etfs: {},
    sources: [],
    retrievedAt: new Date().toISOString(),
  };

  if (fredKey) {
    const fredSeries = {
      us3m: "DGS3MO",
      us2y: "DGS2",
      us5y: "DGS5",
      us10y: "DGS10",
      us30y: "DGS30",
      highYield: "BAMLH0A0HYM2",
      investmentGrade: "BAMLC0A0CM",
      us5yBreakeven: "T5YIE",
      us10yBreakeven: "T10YIE",
    };
    const entries = await Promise.all(
      Object.entries(fredSeries).map(async ([key, series]) => [key, await fetchFredLatest(series, fredKey)])
    );
    entries.forEach(([key, observation]) => {
      if (["highYield", "investmentGrade"].includes(key)) {
        data.spreads[key] = observation.value;
      } else if (["us5yBreakeven", "us10yBreakeven"].includes(key)) {
        data.inflationExpectations[key] = observation.value;
      } else {
        data.yields[key] = observation.value;
      }
      if (!data.asOf && observation.date) data.asOf = observation.date;
    });
    data.sources.push("FRED authenticated API: Treasury yields, spreads, and inflation expectation series.");
  }

  if (alphaKey) {
    const symbols = ["SGOV", "SHY", "IEF", "TLT"];
    const quotes = await Promise.all(symbols.map(async (symbol) => [symbol, await fetchAlphaVantageQuote(symbol, alphaKey)]));
    data.etfs = Object.fromEntries(quotes);
    data.sources.push("Alpha Vantage authenticated API: ETF/fund quote snapshots.");
  }

  return data;
}

module.exports = {
  DEMO_MARKET_DATA,
  fetchMarketData,
};

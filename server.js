const http = require("node:http");
const fs = require("node:fs");
const path = require("node:path");
const { allocate } = require("./src/allocation-engine");
const { fetchMarketData } = require("./src/market-data");
const { createStorage } = require("./src/storage");

const PORT = Number(process.env.PORT || 3000);
const PUBLIC_ROOT = __dirname;
const storage = createStorage();

const MIME_TYPES = {
  ".css": "text/css; charset=utf-8",
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".md": "text/markdown; charset=utf-8",
};

let marketDataCache = null;
let marketDataCachedAt = 0;
const MARKET_DATA_TTL_MS = 15 * 60 * 1000;

function sendJson(response, statusCode, payload) {
  response.writeHead(statusCode, { "Content-Type": "application/json; charset=utf-8" });
  response.end(JSON.stringify(payload, null, 2));
}

function readBody(request) {
  return new Promise((resolve, reject) => {
    let body = "";
    request.on("data", (chunk) => {
      body += chunk;
      if (body.length > 1_000_000) {
        request.destroy(new Error("Request body too large"));
      }
    });
    request.on("end", () => {
      if (!body) {
        resolve({});
        return;
      }
      try {
        resolve(JSON.parse(body));
      } catch (error) {
        reject(error);
      }
    });
    request.on("error", reject);
  });
}

async function getMarketData() {
  const now = Date.now();
  if (marketDataCache && now - marketDataCachedAt < MARKET_DATA_TTL_MS) {
    return marketDataCache;
  }
  marketDataCache = await fetchMarketData();
  marketDataCachedAt = now;
  storage.addAudit("market_data.refreshed", {
    provider: marketDataCache.provider,
    authStatus: marketDataCache.authStatus,
    asOf: marketDataCache.asOf,
  });
  return marketDataCache;
}

async function handleApi(request, response, pathname) {
  try {
    if (request.method === "GET" && pathname === "/api/market-data") {
      sendJson(response, 200, await getMarketData());
      return;
    }

    if (request.method === "POST" && pathname === "/api/allocate") {
      const body = await readBody(request);
      const marketData = body.marketData || (await getMarketData());
      const result = allocate({ ...body, marketData });
      storage.addAudit("allocation.calculated", {
        duration: result.metrics.duration,
        creditRisk: result.metrics.creditRisk,
        target: result.target,
      });
      sendJson(response, 200, { ...result, marketData });
      return;
    }

    if (request.method === "GET" && pathname === "/api/portfolios") {
      sendJson(response, 200, storage.listPortfolios());
      return;
    }

    if (request.method === "POST" && pathname === "/api/portfolios") {
      sendJson(response, 201, storage.addPortfolio(await readBody(request)));
      return;
    }

    if (request.method === "GET" && pathname === "/api/scenarios") {
      sendJson(response, 200, storage.listScenarios());
      return;
    }

    if (request.method === "POST" && pathname === "/api/scenarios") {
      sendJson(response, 201, storage.addScenario(await readBody(request)));
      return;
    }

    if (request.method === "GET" && pathname === "/api/audit") {
      sendJson(response, 200, storage.listAudit());
      return;
    }

    sendJson(response, 404, { error: "API route not found" });
  } catch (error) {
    sendJson(response, 500, { error: error.message });
  }
}

function serveStatic(request, response, pathname) {
  const relativePath = pathname === "/" ? "index.html" : pathname.slice(1);
  const resolved = path.normalize(path.join(PUBLIC_ROOT, relativePath));
  if (!resolved.startsWith(PUBLIC_ROOT)) {
    response.writeHead(403);
    response.end("Forbidden");
    return;
  }

  fs.readFile(resolved, (error, content) => {
    if (error) {
      response.writeHead(404);
      response.end("Not found");
      return;
    }
    response.writeHead(200, { "Content-Type": MIME_TYPES[path.extname(resolved)] || "application/octet-stream" });
    response.end(content);
  });
}

const server = http.createServer(async (request, response) => {
  const url = new URL(request.url, `http://${request.headers.host}`);
  if (url.pathname.startsWith("/api/")) {
    await handleApi(request, response, url.pathname);
    return;
  }
  serveStatic(request, response, url.pathname);
});

if (require.main === module) {
  server.listen(PORT, () => {
    console.log(`Dynamic Bond Allocation Assistant running at http://localhost:${PORT}`);
  });
}

module.exports = { server };

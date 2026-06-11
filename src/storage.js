const fs = require("node:fs");
const path = require("node:path");
const crypto = require("node:crypto");

const INITIAL_STORE = {
  portfolios: [],
  scenarios: [],
  auditTrail: [],
};

function createStorage(filePath) {
  const resolved = filePath || path.join(__dirname, "..", "data", "store.json");

  function ensureStore() {
    fs.mkdirSync(path.dirname(resolved), { recursive: true });
    if (!fs.existsSync(resolved)) {
      fs.writeFileSync(resolved, JSON.stringify(INITIAL_STORE, null, 2));
    }
  }

  function read() {
    ensureStore();
    return JSON.parse(fs.readFileSync(resolved, "utf8"));
  }

  function write(store) {
    ensureStore();
    fs.writeFileSync(resolved, JSON.stringify(store, null, 2));
  }

  function addAudit(action, details) {
    const store = read();
    const entry = {
      id: crypto.randomUUID(),
      timestamp: new Date().toISOString(),
      action,
      details: details || {},
    };
    store.auditTrail.unshift(entry);
    write(store);
    return entry;
  }

  function list(collection) {
    return read()[collection] || [];
  }

  function add(collection, value, auditAction) {
    const store = read();
    const item = {
      id: crypto.randomUUID(),
      createdAt: new Date().toISOString(),
      ...value,
    };
    store[collection].unshift(item);
    store.auditTrail.unshift({
      id: crypto.randomUUID(),
      timestamp: new Date().toISOString(),
      action: auditAction,
      details: { id: item.id, name: item.name || item.title || null },
    });
    write(store);
    return item;
  }

  return {
    addAudit,
    addPortfolio: (value) => add("portfolios", value, "portfolio.created"),
    addScenario: (value) => add("scenarios", value, "scenario.saved"),
    listAudit: () => list("auditTrail"),
    listPortfolios: () => list("portfolios"),
    listScenarios: () => list("scenarios"),
    read,
  };
}

module.exports = {
  createStorage,
};

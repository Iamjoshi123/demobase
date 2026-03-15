import http from "node:http";
import process from "node:process";

import { Stagehand } from "@browserbasehq/stagehand";

const HOST = process.env.STAGEHAND_BRIDGE_HOST || "127.0.0.1";
const PORT = Number.parseInt(process.env.STAGEHAND_BRIDGE_PORT || "4545", 10);
const SESSION_TTL_MS = Number.parseInt(process.env.STAGEHAND_BRIDGE_SESSION_TTL_MS || "300000", 10);
const ACT_MAX_OUTPUT_TOKENS = Number.parseInt(process.env.STAGEHAND_ACT_MAX_OUTPUT_TOKENS || "1200", 10);
const OBSERVE_MAX_OUTPUT_TOKENS = Number.parseInt(process.env.STAGEHAND_OBSERVE_MAX_OUTPUT_TOKENS || "900", 10);
const EXTRACT_MAX_OUTPUT_TOKENS = Number.parseInt(process.env.STAGEHAND_EXTRACT_MAX_OUTPUT_TOKENS || "700", 10);

const sessions = new Map();
const ANTHROPIC_MODEL_FALLBACKS = [
  "anthropic/claude-sonnet-4-5",
  "anthropic/claude-sonnet-4-20250514",
  "anthropic/claude-sonnet-4-0",
  "anthropic/claude-3-5-haiku-latest",
  "anthropic/claude-3-haiku-20240307",
];
const MODEL_ALIASES = new Map([
  ["anthropic/claude-3-5-sonnet-latest", "anthropic/claude-sonnet-4-5"],
  ["anthropic/claude-3-5-sonnet-20241022", "anthropic/claude-sonnet-4-5"],
  ["anthropic/claude-3-7-sonnet-latest", "anthropic/claude-sonnet-4-5"],
  ["anthropic/claude-3-7-sonnet-20250219", "anthropic/claude-sonnet-4-5"],
]);

function json(response, status, payload) {
  response.writeHead(status, { "Content-Type": "application/json; charset=utf-8" });
  response.end(JSON.stringify(payload));
}

async function readJson(request) {
  const chunks = [];
  for await (const chunk of request) {
    chunks.push(chunk);
  }

  if (!chunks.length) {
    return {};
  }

  return JSON.parse(Buffer.concat(chunks).toString("utf-8"));
}

function normalizeComparableUrl(value) {
  if (!value) {
    return "";
  }

  try {
    const parsed = new URL(value);
    return `${parsed.origin}${parsed.pathname}`;
  } catch {
    return value;
  }
}

function normalizeModelName(modelName) {
  if (!modelName) {
    return {
      provider: "",
      requestedModelName: "",
      resolvedModelName: "",
    };
  }

  const requestedModelName = modelName.trim();
  if (requestedModelName.startsWith("openrouter/")) {
    return {
      provider: "openrouter",
      requestedModelName,
      resolvedModelName: requestedModelName.slice("openrouter/".length),
    };
  }

  const resolvedModelName = MODEL_ALIASES.get(requestedModelName) || requestedModelName;
  const provider = resolvedModelName.includes("/") ? resolvedModelName.split("/", 1)[0] : "";

  return {
    provider,
    requestedModelName,
    resolvedModelName,
  };
}

function modelFallbacksFor(modelName) {
  const { provider, resolvedModelName } = normalizeModelName(modelName);
  if (provider !== "anthropic") {
    return [resolvedModelName].filter(Boolean);
  }

  return [...new Set([resolvedModelName, ...ANTHROPIC_MODEL_FALLBACKS].filter(Boolean))];
}

function isModelNotFoundError(error) {
  const statusCode = error?.statusCode;
  const responseType = error?.data?.error?.type;
  const message = error?.data?.error?.message || error?.message || "";
  return statusCode === 404 && responseType === "not_found_error" && message.startsWith("model:");
}

async function resolvePage(stagehand, expectedUrl = "") {
  const pages = stagehand.context.pages();
  if (!pages.length) {
    throw new Error("No pages found in attached browser");
  }

  if (!expectedUrl) {
    return pages[0];
  }

  const exact = pages.find((page) => page.url() === expectedUrl);
  if (exact) {
    return exact;
  }

  const comparable = normalizeComparableUrl(expectedUrl);
  const normalized = pages.find((page) => normalizeComparableUrl(page.url()) === comparable);
  if (normalized) {
    return normalized;
  }

  const nonBlank = pages.find((page) => page.url() && page.url() !== "about:blank");
  return nonBlank || pages[0];
}

async function closeSession(entry) {
  if (!entry) {
    return;
  }

  try {
    await entry.stagehand.close({ force: true });
  } catch (error) {
    console.warn("[stagehand-bridge] close failed:", error);
  }
}

async function ensureSession(payload) {
  const sessionKey = payload.session_key;
  const cdpUrl = payload.cdp_url;
  const { provider, requestedModelName, resolvedModelName } = normalizeModelName(payload.model_name);
  const apiKey = payload.api_key;
  const baseURL = payload.base_url;

  if (!sessionKey) {
    throw new Error("session_key is required");
  }
  if (!cdpUrl) {
    throw new Error("cdp_url is required");
  }
  if (!resolvedModelName) {
    throw new Error("model_name is required");
  }

  const existing = sessions.get(sessionKey);
  if (
    existing &&
    existing.cdpUrl === cdpUrl &&
    existing.modelName === resolvedModelName &&
    existing.apiKey === apiKey &&
    existing.baseURL === baseURL
  ) {
    existing.lastUsedAt = Date.now();
    return existing.stagehand;
  }

  if (existing) {
    await closeSession(existing);
    sessions.delete(sessionKey);
  }

  const modelConfig =
    apiKey
      ? provider === "openrouter"
        ? {
            modelName: resolvedModelName.startsWith("openai/") ? resolvedModelName : `openai/${resolvedModelName}`,
            apiKey,
            baseURL: baseURL || "https://openrouter.ai/api/v1",
          }
        : baseURL
          ? { modelName: resolvedModelName, apiKey, baseURL }
          : { modelName: resolvedModelName, apiKey }
      : resolvedModelName;

  const stagehand = new Stagehand({
    env: "LOCAL",
    disableAPI: true,
    disablePino: true,
    keepAlive: true,
    selfHeal: true,
    verbose: 0,
    model: modelConfig,
    localBrowserLaunchOptions: {
      cdpUrl,
      headless: true,
      viewport: { width: 1280, height: 720 },
    },
  });

  await stagehand.init();
  sessions.set(sessionKey, {
    apiKey,
    baseURL,
    cdpUrl,
    lastUsedAt: Date.now(),
    modelName: resolvedModelName,
    requestedModelName,
    stagehand,
  });
  return stagehand;
}

async function recreateSession(payload, modelName) {
  const entry = sessions.get(payload.session_key);
  if (entry) {
    await closeSession(entry);
    sessions.delete(payload.session_key);
  }

  return await ensureSession({
    ...payload,
    model_name: modelName,
  });
}

async function withStagehandFallback(payload, operation) {
  const attemptedModels = new Set();
  let lastError;

  for (const modelName of modelFallbacksFor(payload.model_name)) {
    if (attemptedModels.has(modelName)) {
      continue;
    }
    attemptedModels.add(modelName);

    try {
      const stagehand = await recreateSession(payload, modelName);
      return await operation(stagehand, modelName);
    } catch (error) {
      lastError = error;
      if (!isModelNotFoundError(error)) {
        throw error;
      }
    }
  }

  throw lastError || new Error("No compatible Stagehand model could be resolved");
}

async function selectActivePage(stagehand, pageUrl) {
  const page = await resolvePage(stagehand, pageUrl);
  stagehand.context.setActivePage(page);
  return page;
}

async function handleAct(payload) {
  return await withStagehandFallback(payload, async (stagehand) => {
    await selectActivePage(stagehand, payload.page_url);
    const result = await stagehand.act(payload.instruction, {
      maxOutputTokens: ACT_MAX_OUTPUT_TOKENS,
      timeout: payload.timeout_ms,
    });

    return {
      action_description: result.actionDescription,
      actions: result.actions || [],
      message: result.message || "",
      success: Boolean(result.success),
    };
  });
}

async function handleObserve(payload) {
  return await withStagehandFallback(payload, async (stagehand) => {
    await selectActivePage(stagehand, payload.page_url);
    const result = await stagehand.observe(payload.instruction, {
      maxOutputTokens: OBSERVE_MAX_OUTPUT_TOKENS,
      timeout: payload.timeout_ms,
    });
    return { actions: Array.from(result || []) };
  });
}

async function handleExtract(payload) {
  return await withStagehandFallback(payload, async (stagehand) => {
    await selectActivePage(stagehand, payload.page_url);
    const result = await stagehand.extract(payload.instruction, payload.schema, {
      maxOutputTokens: EXTRACT_MAX_OUTPUT_TOKENS,
      timeout: payload.timeout_ms,
    });
    return { result };
  });
}

async function handleRelease(payload) {
  const entry = sessions.get(payload.session_key);
  if (entry) {
    await closeSession(entry);
    sessions.delete(payload.session_key);
  }
  return { released: true };
}

async function pruneSessions() {
  const cutoff = Date.now() - SESSION_TTL_MS;
  for (const [sessionKey, entry] of sessions.entries()) {
    if (entry.lastUsedAt >= cutoff) {
      continue;
    }
    await closeSession(entry);
    sessions.delete(sessionKey);
  }
}

const server = http.createServer(async (request, response) => {
  try {
    if (request.method === "GET" && request.url === "/health") {
      return json(response, 200, { active_sessions: sessions.size, status: "ok" });
    }

    if (request.method !== "POST") {
      return json(response, 405, { error: "Method not allowed" });
    }

    const payload = await readJson(request);

    if (request.url === "/v1/act") {
      return json(response, 200, await handleAct(payload));
    }
    if (request.url === "/v1/observe") {
      return json(response, 200, await handleObserve(payload));
    }
    if (request.url === "/v1/extract") {
      return json(response, 200, await handleExtract(payload));
    }
    if (request.url === "/v1/release") {
      return json(response, 200, await handleRelease(payload));
    }

    return json(response, 404, { error: "Not found" });
  } catch (error) {
    console.error("[stagehand-bridge] request failed:", error);
    return json(response, 500, {
      error: error instanceof Error ? error.message : String(error),
      success: false,
    });
  }
});

const interval = setInterval(() => {
  void pruneSessions();
}, 60_000);
interval.unref?.();

async function shutdown() {
  clearInterval(interval);
  for (const entry of sessions.values()) {
    await closeSession(entry);
  }
  sessions.clear();
  server.close();
}

for (const signal of ["SIGINT", "SIGTERM"]) {
  process.on(signal, () => {
    void shutdown().finally(() => process.exit(0));
  });
}

server.listen(PORT, HOST, () => {
  console.log(`[stagehand-bridge] listening on http://${HOST}:${PORT}`);
});

// 三格同步 Pages Function 模板。
// 复制为 Pages 输出目录中的 _worker.js，并配置 DB 与 SYNC_TOKEN。

const MAX_ITEMS = 5000;
const MAX_PAYLOAD = 64 * 1024;
const CORS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
  "Access-Control-Allow-Headers": "authorization, content-type",
  "Access-Control-Max-Age": "86400",
};

function json(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "content-type": "application/json; charset=utf-8", ...CORS },
  });
}

function safeEqual(a, b) {
  if (typeof a !== "string" || typeof b !== "string" || a.length !== b.length) return false;
  let diff = 0;
  for (let i = 0; i < a.length; i++) diff |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return diff === 0;
}

function validKind(kind) {
  return typeof kind === "string" && /^[a-z][a-z0-9_]{0,15}$/.test(kind);
}

async function handleSync(request, env) {
  const auth = request.headers.get("authorization") || "";
  const token = auth.startsWith("Bearer ") ? auth.slice(7).trim() : "";
  if (!env.SYNC_TOKEN || !safeEqual(token, env.SYNC_TOKEN)) {
    return json({ error: "unauthorized" }, 401);
  }

  let body;
  try { body = await request.json(); }
  catch { return json({ error: "invalid json" }, 400); }

  const incoming = Array.isArray(body?.items) ? body.items : [];
  if (incoming.length > MAX_ITEMS) return json({ error: "too many items" }, 413);

  const owner = String(env.SYNC_OWNER || "default");
  const rows = [];
  for (const item of incoming) {
    if (!item || !validKind(item.kind)) continue;
    if (typeof item.id !== "string" || !item.id || item.id.length > 128) continue;
    const updatedAt = Number(item.updatedAt);
    if (!Number.isFinite(updatedAt) || updatedAt <= 0) continue;
    const payload = JSON.stringify(item.payload ?? null);
    if (payload.length > MAX_PAYLOAD) continue;
    rows.push({
      kind: item.kind,
      id: item.id,
      payload,
      updatedAt: Math.floor(updatedAt),
      deleted: item.deleted ? 1 : 0,
    });
  }

  if (rows.length) {
    const stmt = env.DB.prepare(
      `INSERT INTO items (owner, kind, id, payload, updated_at, deleted)
       VALUES (?, ?, ?, ?, ?, ?)
       ON CONFLICT(owner, kind, id) DO UPDATE SET
         payload = excluded.payload,
         updated_at = excluded.updated_at,
         deleted = excluded.deleted
       WHERE excluded.updated_at > items.updated_at`
    );
    await env.DB.batch(
      rows.map(row => stmt.bind(owner, row.kind, row.id, row.payload, row.updatedAt, row.deleted))
    );
  }

  const { results } = await env.DB.prepare(
    "SELECT kind, id, payload, updated_at, deleted FROM items WHERE owner = ?"
  ).bind(owner).all();

  return json({
    ok: true,
    serverTime: Date.now(),
    items: (results || []).map(row => ({
      kind: row.kind,
      id: row.id,
      payload: JSON.parse(row.payload),
      updatedAt: row.updated_at,
      deleted: !!row.deleted,
    })),
  });
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (url.pathname === "/api/health") return json({ ok: true, service: "sange-sync" });
    if (url.pathname !== "/api/sync") return env.ASSETS.fetch(request);
    if (request.method === "OPTIONS") return new Response(null, { headers: CORS });
    if (request.method !== "POST") return json({ error: "method not allowed" }, 405);
    return handleSync(request, env);
  },
};

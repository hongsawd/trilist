// 三格同步：单用户 token + 按条 LWW。
// POST /sync  body: { items: [{ kind, id, updatedAt, deleted, payload }] }
// 返回合并后的全量：{ ok, serverTime, items: [...] }

const OWNER = "default";
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

// 常数时间比较，避免按字符提前返回
function safeEqual(a, b) {
  if (typeof a !== "string" || typeof b !== "string") return false;
  if (a.length !== b.length) return false;
  let diff = 0;
  for (let i = 0; i < a.length; i++) diff |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return diff === 0;
}

function validKind(kind) {
  return typeof kind === "string" && /^[a-z][a-z0-9_]{0,15}$/.test(kind);
}

export default {
  async fetch(req, env) {
    const url = new URL(req.url);

    if (req.method === "OPTIONS") return new Response(null, { headers: CORS });
    if (url.pathname === "/health") return json({ ok: true, service: "sange-sync" });
    if (url.pathname !== "/sync") return json({ error: "not found" }, 404);
    if (req.method !== "POST") return json({ error: "method not allowed" }, 405);

    if (!env.SYNC_TOKEN) return json({ error: "server not configured" }, 500);

    const auth = req.headers.get("authorization") || "";
    const token = auth.startsWith("Bearer ") ? auth.slice(7).trim() : "";
    if (!safeEqual(token, env.SYNC_TOKEN)) return json({ error: "unauthorized" }, 401);

    let body;
    try {
      body = await req.json();
    } catch {
      return json({ error: "invalid json" }, 400);
    }

    const incoming = Array.isArray(body?.items) ? body.items : [];
    if (incoming.length > MAX_ITEMS) return json({ error: "too many items" }, 413);

    const rows = [];
    for (const it of incoming) {
      if (!it || !validKind(it.kind)) continue;
      if (typeof it.id !== "string" || !it.id || it.id.length > 128) continue;
      const updatedAt = Number(it.updatedAt);
      if (!Number.isFinite(updatedAt) || updatedAt <= 0) continue;
      const payload = JSON.stringify(it.payload ?? null);
      if (payload.length > MAX_PAYLOAD) continue;
      rows.push({
        kind: it.kind,
        id: it.id,
        payload,
        updatedAt: Math.floor(updatedAt),
        deleted: it.deleted ? 1 : 0,
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
        rows.map((r) =>
          stmt.bind(OWNER, r.kind, r.id, r.payload, r.updatedAt, r.deleted)
        )
      );
    }

    const { results } = await env.DB.prepare(
      `SELECT kind, id, payload, updated_at, deleted FROM items WHERE owner = ?`
    )
      .bind(OWNER)
      .all();

    const items = (results || []).map((r) => ({
      kind: r.kind,
      id: r.id,
      payload: JSON.parse(r.payload),
      updatedAt: r.updated_at,
      deleted: !!r.deleted,
    }));

    return json({ ok: true, serverTime: Date.now(), items });
  },
};

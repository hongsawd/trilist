CREATE TABLE IF NOT EXISTS items (
  owner      TEXT NOT NULL,
  kind       TEXT NOT NULL,
  id         TEXT NOT NULL,
  payload    TEXT NOT NULL,
  updated_at INTEGER NOT NULL,
  deleted    INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY (owner, kind, id)
);

CREATE INDEX IF NOT EXISTS idx_items_owner_updated
  ON items (owner, updated_at);

CREATE TABLE IF NOT EXISTS meta (
  key   TEXT PRIMARY KEY,
  value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sync_users (
  token_sha256 TEXT PRIMARY KEY,
  owner TEXT NOT NULL UNIQUE,
  enabled INTEGER NOT NULL DEFAULT 1,
  created_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS signup_limits (
  fingerprint TEXT PRIMARY KEY,
  created_at INTEGER NOT NULL,
  attempts INTEGER NOT NULL DEFAULT 1
);

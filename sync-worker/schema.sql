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

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS push_wake_outbox (
  scope_key TEXT PRIMARY KEY,
  namespace TEXT NOT NULL,
  revision INTEGER,
  business_date TEXT,
  authority_epoch INTEGER NOT NULL,
  authority_seq INTEGER NOT NULL,
  payload_json TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'PENDING' CHECK(status IN ('PENDING','RETRY','SENT','FAILED')),
  attempt_count INTEGER NOT NULL DEFAULT 0,
  next_attempt_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  last_error_class TEXT,
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
CREATE INDEX IF NOT EXISTS idx_push_wake_due ON push_wake_outbox(status,next_attempt_at,updated_at);

CREATE TABLE IF NOT EXISTS session_special_projection_outbox (
  event_id TEXT PRIMARY KEY REFERENCES events(event_id) ON DELETE CASCADE,
  status TEXT NOT NULL DEFAULT 'PENDING' CHECK(status IN ('PENDING','INFLIGHT','RETRY','SYNCED','FAILED')),
  attempt_count INTEGER NOT NULL DEFAULT 0,
  next_attempt_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  claim_token TEXT,
  claimed_at TEXT,
  last_error TEXT,
  projected_at TEXT,
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
CREATE INDEX IF NOT EXISTS idx_session_special_due ON session_special_projection_outbox(status,next_attempt_at,created_at);

INSERT OR IGNORE INTO schema_migrations(version,checksum)
VALUES('0016_r5_background_terminal','R5_BACKGROUND_TERMINAL_V1');

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS quota_policy (
  metric TEXT PRIMARY KEY,
  hard_limit INTEGER NOT NULL CHECK(hard_limit > 0),
  unit TEXT NOT NULL,
  source_requirement TEXT NOT NULL,
  updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);

INSERT INTO quota_policy(metric,hard_limit,unit,source_requirement) VALUES
  ('GOOGLE_SHEETS_DAILY',250,'requests/day','R5-15'),
  ('GOOGLE_SHEETS_PROJECT_MINUTE',100,'requests/minute/project','R5-15'),
  ('GOOGLE_SHEETS_READ_MINUTE',30,'read requests/minute/user','R5-15'),
  ('GOOGLE_SHEETS_WRITE_MINUTE',30,'write requests/minute/user','R5-15')
ON CONFLICT(metric) DO UPDATE SET hard_limit=excluded.hard_limit,unit=excluded.unit,source_requirement=excluded.source_requirement,updated_at=strftime('%Y-%m-%dT%H:%M:%fZ','now');

CREATE TABLE IF NOT EXISTS quota_usage (
  window_key TEXT NOT NULL,
  metric TEXT NOT NULL REFERENCES quota_policy(metric),
  used INTEGER NOT NULL DEFAULT 0 CHECK(used >= 0),
  hard_limit INTEGER NOT NULL CHECK(hard_limit > 0),
  updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  PRIMARY KEY(window_key,metric),
  CONSTRAINT quota_hard_limit CHECK(used <= hard_limit)
);
CREATE INDEX IF NOT EXISTS idx_quota_usage_metric_window ON quota_usage(metric,window_key);

INSERT INTO system_meta(key,value,updated_at) VALUES('r5_operational_repair_dirty','1',strftime('%Y-%m-%dT%H:%M:%fZ','now')) ON CONFLICT(key) DO NOTHING;
INSERT INTO system_meta(key,value,updated_at) VALUES('r5_document_audit_dirty','1',strftime('%Y-%m-%dT%H:%M:%fZ','now')) ON CONFLICT(key) DO NOTHING;

INSERT OR IGNORE INTO schema_migrations(version,checksum) VALUES('0017_r5_quota_budget','R5_QUOTA_BUDGET_V2_NO_TRIGGER');

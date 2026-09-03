-- Beta116 owner scope: per-image document note + global LAN test control.
ALTER TABLE document_records ADD COLUMN note TEXT NOT NULL DEFAULT '';

CREATE TABLE IF NOT EXISTS lan_test_mode (
  singleton_id INTEGER PRIMARY KEY CHECK(singleton_id=1),
  enabled INTEGER NOT NULL DEFAULT 0,
  epoch INTEGER NOT NULL DEFAULT 0,
  enabled_by TEXT NOT NULL DEFAULT '',
  updated_at TEXT NOT NULL
);
INSERT OR IGNORE INTO lan_test_mode(singleton_id,enabled,epoch,enabled_by,updated_at)
VALUES(1,0,0,'','1970-01-01T00:00:00.000Z');

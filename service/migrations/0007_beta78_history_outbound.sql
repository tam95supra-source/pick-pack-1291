PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS historical_session_snapshots (
  session_id TEXT PRIMARY KEY,
  mnv TEXT NOT NULL,
  business_date TEXT NOT NULL,
  snapshot_json TEXT NOT NULL,
  source_version INTEGER NOT NULL DEFAULT 0,
  hydrated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_historical_session_date ON historical_session_snapshots(business_date,mnv);

INSERT OR IGNORE INTO historical_session_snapshots(session_id,mnv,business_date,snapshot_json,source_version,hydrated_at)
SELECT session_id,mnv,business_date,
  json_object(
    'session_id',session_id,'mnv',mnv,'business_date',business_date,'shift',shift,
    'work_choice',work_choice,'state',state,'pda_serial',pda_serial,'user_pick',user_pick,
    'pack_table',pack_table,'user_pack',user_pack,'pda_enter_status',pda_enter_status,
    'pda_exit_status',pda_exit_status,'resource_note',resource_note,'enter_at',enter_at,
    'exit_at',exit_at,'entered_by',entered_by,'exited_by',exited_by,'version',version
  ),version,strftime('%Y-%m-%dT%H:%M:%fZ','now')
FROM attendance_sessions
WHERE business_date >= date('now','+7 hours','-44 days');

CREATE TABLE IF NOT EXISTS outbound_locations (
  location_key TEXT PRIMARY KEY,
  location TEXT NOT NULL,
  version INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS outbound_drop_records (
  record_id TEXT PRIMARY KEY,
  location TEXT NOT NULL,
  business_date TEXT NOT NULL,
  scan_qr TEXT NOT NULL DEFAULT '',
  do_number TEXT NOT NULL,
  package_count INTEGER NOT NULL CHECK(package_count>0),
  actor_id TEXT NOT NULL,
  actor_display_name TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_outbound_drop_date ON outbound_drop_records(business_date,created_at);

CREATE TABLE IF NOT EXISTS outbound_replication_outbox (
  outbox_id INTEGER PRIMARY KEY AUTOINCREMENT,
  event_id TEXT NOT NULL UNIQUE REFERENCES events(event_id) ON DELETE CASCADE,
  status TEXT NOT NULL DEFAULT 'PENDING' CHECK(status IN ('PENDING','INFLIGHT','RETRY','SYNCED')),
  attempt_count INTEGER NOT NULL DEFAULT 0,
  next_attempt_at TEXT NOT NULL,
  claimed_at TEXT,
  replicated_at TEXT,
  last_error TEXT
);
CREATE INDEX IF NOT EXISTS idx_outbound_outbox_due ON outbound_replication_outbox(status,next_attempt_at,outbox_id);

CREATE TABLE IF NOT EXISTS outbound_meta (
  singleton_id INTEGER PRIMARY KEY CHECK(singleton_id=1),
  locations_hydrated INTEGER NOT NULL DEFAULT 0 CHECK(locations_hydrated IN (0,1)),
  hydrated_at TEXT
);
INSERT OR IGNORE INTO outbound_meta(singleton_id,locations_hydrated,hydrated_at) VALUES(1,0,NULL);

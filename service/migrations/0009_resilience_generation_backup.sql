-- RESILIENCE_V1: provider-neutral capacity/generation/backup/DR metadata. No authority change.
CREATE TABLE IF NOT EXISTS runtime_config(
  config_key TEXT PRIMARY KEY NOT NULL,
  config_value TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
INSERT OR IGNORE INTO runtime_config(config_key,config_value,updated_at) VALUES
 ('WARN_DB_PERCENT','70',datetime('now')),
 ('PREPARE_NEXT_DB_PERCENT','80',datetime('now')),
 ('CUTOVER_DB_PERCENT','85',datetime('now')),
 ('OWNER_TOTAL_QUOTA_WARN_PERCENT','80',datetime('now')),
 ('RETENTION_DAYS','45',datetime('now')),
 ('D1_DB_QUOTA_BYTES','0',datetime('now')),
 ('D1_ACCOUNT_QUOTA_BYTES','0',datetime('now'));

CREATE TABLE IF NOT EXISTS d1_generation_registry(
  generation_id TEXT PRIMARY KEY NOT NULL,
  db_binding TEXT NOT NULL,
  db_name TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL,
  active_from_event TEXT,
  active_to_event TEXT,
  business_date_from TEXT,
  business_date_to TEXT,
  schema_version INTEGER NOT NULL,
  status TEXT NOT NULL CHECK(status IN ('PREPARED','ACTIVE_WRITE','READ_ONLY_HISTORY','RETIRED')),
  checksum_checkpoint TEXT NOT NULL DEFAULT '',
  authority_epoch INTEGER NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_d1_generation_active_write ON d1_generation_registry(status) WHERE status='ACTIVE_WRITE';
INSERT OR IGNORE INTO d1_generation_registry(generation_id,db_binding,created_at,schema_version,status,authority_epoch)
 SELECT service_generation,'DB',datetime('now'),9,'ACTIVE_WRITE',authority_epoch FROM authority_state WHERE singleton_id=1;

CREATE TABLE IF NOT EXISTS backup_manifests(
  backup_id TEXT PRIMARY KEY NOT NULL,
  created_at TEXT NOT NULL,
  source TEXT NOT NULL,
  first_event TEXT NOT NULL DEFAULT '',
  last_event TEXT NOT NULL DEFAULT '',
  first_business_date TEXT NOT NULL,
  last_business_date TEXT NOT NULL,
  row_counts_json TEXT NOT NULL,
  table_counts_json TEXT NOT NULL,
  checksum TEXT NOT NULL,
  schema_version INTEGER NOT NULL,
  checkpoint TEXT NOT NULL,
  status TEXT NOT NULL CHECK(status IN ('CREATED','RESTORED','VERIFIED','FAILED')),
  verified_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_backup_verified_dates ON backup_manifests(status,first_business_date,last_business_date);

CREATE TABLE IF NOT EXISTS dr_replay_checkpoints(
  target_id TEXT PRIMARY KEY NOT NULL,
  provider TEXT NOT NULL,
  status TEXT NOT NULL CHECK(status IN ('PASSIVE','PREPARING','READY','ACTIVE_WRITE','FAILED','FENCED')),
  last_event_id TEXT NOT NULL DEFAULT '',
  last_authority_epoch INTEGER NOT NULL DEFAULT 0,
  last_authority_seq INTEGER NOT NULL DEFAULT 0,
  service_generation TEXT NOT NULL DEFAULT '',
  checksum TEXT NOT NULL DEFAULT '',
  updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS lan_authority_leases(
  singleton_id INTEGER PRIMARY KEY CHECK(singleton_id=1),
  lan_epoch INTEGER NOT NULL,
  master_device_id TEXT NOT NULL,
  backup_device_id TEXT NOT NULL DEFAULT '',
  lease_until TEXT NOT NULL,
  generation INTEGER NOT NULL,
  checksum TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

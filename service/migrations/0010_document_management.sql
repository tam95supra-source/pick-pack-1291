-- Document management metadata only. Image bytes remain in Google Drive.
CREATE TABLE IF NOT EXISTS document_categories (
  category_id TEXT PRIMARY KEY,
  display_name TEXT NOT NULL,
  normalized_name TEXT NOT NULL UNIQUE,
  status TEXT NOT NULL DEFAULT 'ACTIVE' CHECK(status IN ('ACTIVE','ARCHIVED')),
  created_at TEXT NOT NULL,
  created_by TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  updated_by TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS document_records (
  document_id TEXT PRIMARY KEY,
  idempotency_key TEXT NOT NULL UNIQUE,
  category_id TEXT NOT NULL,
  category_name_snapshot TEXT NOT NULL,
  uploader_id TEXT NOT NULL,
  uploader_name_snapshot TEXT NOT NULL,
  captured_at TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  completed_at TEXT,
  status TEXT NOT NULL CHECK(status IN ('PENDING','COMPLETE','FAILED')),
  file_name TEXT NOT NULL,
  mime_type TEXT NOT NULL,
  byte_size INTEGER NOT NULL,
  sha256 TEXT NOT NULL,
  md5 TEXT NOT NULL,
  dhash64 TEXT,
  width INTEGER,
  height INTEGER,
  source_kind TEXT NOT NULL CHECK(source_kind IN ('CAMERA','GALLERY')),
  drive_file_id TEXT,
  duplicate_of_document_id TEXT,
  last_error TEXT
);

CREATE INDEX IF NOT EXISTS idx_document_records_created
  ON document_records(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_document_records_category
  ON document_records(category_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_document_records_sha256
  ON document_records(sha256, status);
CREATE INDEX IF NOT EXISTS idx_document_records_status
  ON document_records(status, created_at DESC);

CREATE TABLE IF NOT EXISTS document_drive_folders (
  path_key TEXT PRIMARY KEY,
  drive_folder_id TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS document_audit (
  audit_id TEXT PRIMARY KEY,
  action TEXT NOT NULL,
  target_type TEXT NOT NULL,
  target_id TEXT NOT NULL,
  actor_id TEXT NOT NULL,
  actor_role TEXT NOT NULL,
  detail_json TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_document_audit_target
  ON document_audit(target_type, target_id, created_at DESC);

-- Beta110: multi-image document groups + durable selected-document hard delete.
ALTER TABLE document_records ADD COLUMN group_id TEXT;
ALTER TABLE document_records ADD COLUMN group_mode TEXT NOT NULL DEFAULT 'SINGLE';
ALTER TABLE document_records ADD COLUMN page_index INTEGER NOT NULL DEFAULT 1;
ALTER TABLE document_records ADD COLUMN page_count INTEGER NOT NULL DEFAULT 1;

CREATE INDEX IF NOT EXISTS idx_document_records_group
  ON document_records(group_id, page_index, completed_at DESC);

CREATE TABLE IF NOT EXISTS document_delete_mutations (
  mutation_id TEXT PRIMARY KEY,
  idempotency_key TEXT NOT NULL UNIQUE,
  state TEXT NOT NULL CHECK(state IN ('RUNNING','DONE','FAILED')),
  total_items INTEGER NOT NULL DEFAULT 0,
  processed_items INTEGER NOT NULL DEFAULT 0,
  actor_id TEXT NOT NULL,
  actor_role TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  completed_at TEXT,
  last_error TEXT
);

CREATE TABLE IF NOT EXISTS document_delete_items (
  mutation_id TEXT NOT NULL,
  document_id TEXT NOT NULL,
  drive_file_id TEXT,
  category_id TEXT,
  category_name_snapshot TEXT,
  file_name TEXT,
  state TEXT NOT NULL CHECK(state IN ('PENDING','DONE','FAILED')),
  last_error TEXT,
  updated_at TEXT NOT NULL,
  PRIMARY KEY(mutation_id, document_id)
);

CREATE INDEX IF NOT EXISTS idx_document_delete_items_state
  ON document_delete_items(mutation_id, state, updated_at);

-- OWNER 2026-09-01: document category UPDATE renames all historical metadata + Drive filenames.
-- DELETE hard-purges Drive files + business records; only a minimal technical mutation receipt remains.
ALTER TABLE document_categories ADD COLUMN mutation_state TEXT NOT NULL DEFAULT 'NONE'
  CHECK(mutation_state IN ('NONE','RENAMING','DELETING'));
ALTER TABLE document_categories ADD COLUMN mutation_id TEXT;

CREATE TABLE IF NOT EXISTS document_category_mutations (
  mutation_id TEXT PRIMARY KEY,
  idempotency_key TEXT NOT NULL UNIQUE,
  category_id TEXT NOT NULL,
  operation TEXT NOT NULL CHECK(operation IN ('UPDATE','DELETE')),
  old_display_name TEXT NOT NULL,
  new_display_name TEXT,
  new_normalized_name TEXT,
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

CREATE INDEX IF NOT EXISTS idx_document_category_mutations_active
  ON document_category_mutations(state, updated_at);

CREATE TABLE IF NOT EXISTS document_category_mutation_items (
  mutation_id TEXT NOT NULL,
  document_id TEXT NOT NULL,
  drive_file_id TEXT,
  old_file_name TEXT NOT NULL,
  new_file_name TEXT,
  state TEXT NOT NULL CHECK(state IN ('DONE','FAILED')),
  last_error TEXT,
  updated_at TEXT NOT NULL,
  PRIMARY KEY(mutation_id, document_id)
);

CREATE INDEX IF NOT EXISTS idx_document_category_mutation_items_state
  ON document_category_mutation_items(mutation_id, state, updated_at);

PRAGMA foreign_keys = ON;

-- S64_SESSION_RESOURCE_MODEL
-- Append-only assignment history for one attendance session owning N users/positions
-- while resource_leases remains the exclusive ACTIVE ownership fence.
CREATE TABLE IF NOT EXISTS session_positions (
  position_assignment_id TEXT PRIMARY KEY,
  session_id TEXT NOT NULL REFERENCES attendance_sessions(session_id) ON DELETE CASCADE,
  mnv TEXT NOT NULL,
  business_date TEXT NOT NULL,
  position_key TEXT NOT NULL,
  position_label TEXT NOT NULL,
  state TEXT NOT NULL CHECK(state IN ('ACTIVE','USED','VOID')),
  started_at TEXT NOT NULL,
  ended_at TEXT,
  start_event_id TEXT NOT NULL,
  end_event_id TEXT,
  reason TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_session_positions_session_state ON session_positions(session_id,state,position_key);
CREATE UNIQUE INDEX IF NOT EXISTS uq_session_position_active ON session_positions(session_id,position_key) WHERE state='ACTIVE';

CREATE TABLE IF NOT EXISTS session_resource_assignments (
  assignment_id TEXT PRIMARY KEY,
  session_id TEXT NOT NULL REFERENCES attendance_sessions(session_id) ON DELETE CASCADE,
  mnv TEXT NOT NULL,
  business_date TEXT NOT NULL,
  resource_type TEXT NOT NULL CHECK(resource_type IN ('PDA','USER_PICK','PACK_TABLE','USER_PACK')),
  resource_id TEXT NOT NULL,
  position_key TEXT NOT NULL DEFAULT '',
  state TEXT NOT NULL CHECK(state IN ('ACTIVE','USED','VOID')),
  acquired_at TEXT NOT NULL,
  released_at TEXT,
  acquire_event_id TEXT NOT NULL,
  release_event_id TEXT,
  release_reason TEXT NOT NULL DEFAULT '',
  release_disposition TEXT NOT NULL DEFAULT '',
  context_json TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_session_resource_assignments_session ON session_resource_assignments(session_id,state,resource_type,acquired_at);
CREATE INDEX IF NOT EXISTS idx_session_resource_assignments_resource ON session_resource_assignments(business_date,resource_type,resource_id,state);
CREATE UNIQUE INDEX IF NOT EXISTS uq_session_active_pda ON session_resource_assignments(session_id) WHERE resource_type='PDA' AND state='ACTIVE';
CREATE UNIQUE INDEX IF NOT EXISTS uq_session_active_pack_table ON session_resource_assignments(session_id) WHERE resource_type='PACK_TABLE' AND state='ACTIVE';
CREATE UNIQUE INDEX IF NOT EXISTS uq_session_resource_active_same_id ON session_resource_assignments(session_id,resource_type,resource_id) WHERE state='ACTIVE';

-- Claims make expected session version a true cross-device CAS fence for S64 mutations.
CREATE TABLE IF NOT EXISTS session_version_claims (
  session_id TEXT NOT NULL,
  base_version INTEGER NOT NULL,
  event_id TEXT NOT NULL UNIQUE,
  claimed_at TEXT NOT NULL,
  PRIMARY KEY(session_id,base_version)
);

-- Backfill current/legacy single-value session projections so S64 can adopt live sessions
-- without deleting or rewriting any existing attendance/event data.
INSERT OR IGNORE INTO session_resource_assignments(assignment_id,session_id,mnv,business_date,resource_type,resource_id,position_key,state,acquired_at,released_at,acquire_event_id,release_event_id,release_reason,release_disposition,context_json)
SELECT 'legacy-pda-'||session_id,session_id,mnv,business_date,'PDA',pda_serial,'PICK',CASE WHEN state='ACTIVE' THEN 'ACTIVE' ELSE 'USED' END,COALESCE(enter_at,updated_at),CASE WHEN state='ACTIVE' THEN NULL ELSE exit_at END,'LEGACY_BACKFILL',CASE WHEN state='ACTIVE' THEN NULL ELSE 'LEGACY_BACKFILL' END,'','', '{}'
FROM attendance_sessions WHERE COALESCE(pda_serial,'')<>'';
INSERT OR IGNORE INTO session_resource_assignments(assignment_id,session_id,mnv,business_date,resource_type,resource_id,position_key,state,acquired_at,released_at,acquire_event_id,release_event_id,release_reason,release_disposition,context_json)
SELECT 'legacy-pick-'||session_id,session_id,mnv,business_date,'USER_PICK',user_pick,'PICK',CASE WHEN state='ACTIVE' THEN 'ACTIVE' ELSE 'USED' END,COALESCE(enter_at,updated_at),CASE WHEN state='ACTIVE' THEN NULL ELSE exit_at END,'LEGACY_BACKFILL',CASE WHEN state='ACTIVE' THEN NULL ELSE 'LEGACY_BACKFILL' END,'','', '{}'
FROM attendance_sessions WHERE COALESCE(user_pick,'')<>'';
INSERT OR IGNORE INTO session_resource_assignments(assignment_id,session_id,mnv,business_date,resource_type,resource_id,position_key,state,acquired_at,released_at,acquire_event_id,release_event_id,release_reason,release_disposition,context_json)
SELECT 'legacy-table-'||session_id,session_id,mnv,business_date,'PACK_TABLE',pack_table,'PACK',CASE WHEN state='ACTIVE' THEN 'ACTIVE' ELSE 'USED' END,COALESCE(enter_at,updated_at),CASE WHEN state='ACTIVE' THEN NULL ELSE exit_at END,'LEGACY_BACKFILL',CASE WHEN state='ACTIVE' THEN NULL ELSE 'LEGACY_BACKFILL' END,'','', '{}'
FROM attendance_sessions WHERE COALESCE(pack_table,'')<>'';
INSERT OR IGNORE INTO session_resource_assignments(assignment_id,session_id,mnv,business_date,resource_type,resource_id,position_key,state,acquired_at,released_at,acquire_event_id,release_event_id,release_reason,release_disposition,context_json)
SELECT 'legacy-pack-'||session_id,session_id,mnv,business_date,'USER_PACK',user_pack,'PACK',CASE WHEN state='ACTIVE' THEN 'ACTIVE' ELSE 'USED' END,COALESCE(enter_at,updated_at),CASE WHEN state='ACTIVE' THEN NULL ELSE exit_at END,'LEGACY_BACKFILL',CASE WHEN state='ACTIVE' THEN NULL ELSE 'LEGACY_BACKFILL' END,'','', '{}'
FROM attendance_sessions WHERE COALESCE(user_pack,'')<>'';

INSERT OR IGNORE INTO session_positions(position_assignment_id,session_id,mnv,business_date,position_key,position_label,state,started_at,ended_at,start_event_id,end_event_id,reason)
SELECT 'legacy-pos-'||session_id,session_id,mnv,business_date,work_choice,CASE work_choice WHEN 'PICK' THEN 'Pick' WHEN 'PACK' THEN 'Pack' ELSE 'Không' END,CASE WHEN state='ACTIVE' THEN 'ACTIVE' ELSE 'USED' END,COALESCE(enter_at,updated_at),CASE WHEN state='ACTIVE' THEN NULL ELSE exit_at END,'LEGACY_BACKFILL',CASE WHEN state='ACTIVE' THEN NULL ELSE 'LEGACY_BACKFILL' END,''
FROM attendance_sessions WHERE work_choice IN ('PICK','PACK');

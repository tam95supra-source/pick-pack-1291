PRAGMA foreign_keys = ON;

-- Application guard for SpreadsheetApp operations executed behind the Stable GAS bridge.
-- These are NOT Sheets API requests and must never be reported as provider Sheets API quota.
INSERT INTO quota_policy(metric,hard_limit,unit,source_requirement) VALUES
  ('GOOGLE_GAS_SHEET_OP_DAILY',250,'application sheet-operation units/day','R5-15'),
  ('GOOGLE_GAS_SHEET_READ_MINUTE',30,'application read-operation units/minute','R5-15'),
  ('GOOGLE_GAS_SHEET_WRITE_MINUTE',30,'application write-operation units/minute','R5-15')
ON CONFLICT(metric) DO UPDATE SET hard_limit=excluded.hard_limit,unit=excluded.unit,source_requirement=excluded.source_requirement,updated_at=strftime('%Y-%m-%dT%H:%M:%fZ','now');

INSERT OR IGNORE INTO schema_migrations(version,checksum) VALUES('0018_r5_gas_operation_budget','R5_GAS_OPERATION_BUDGET_V1');

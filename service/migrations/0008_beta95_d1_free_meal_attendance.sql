-- Beta95: bounded D1 Free storage + isolated post-meal attendance.
CREATE TABLE IF NOT EXISTS service_maintenance (
  task_key TEXT PRIMARY KEY,
  last_run_at TEXT,
  checkpoint TEXT,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS post_meal_attendance (
  business_date TEXT NOT NULL,
  mnv TEXT NOT NULL,
  shift TEXT NOT NULL,
  full_name_snapshot TEXT NOT NULL DEFAULT '',
  supplier_snapshot TEXT NOT NULL DEFAULT '',
  status TEXT NOT NULL DEFAULT 'PENDING' CHECK(status IN ('PENDING','CHECKED_IN','NO_RETURN','LATE_EXPECTED')),
  checked_at TEXT,
  reason_code TEXT,
  reason_note TEXT,
  expected_return_at TEXT,
  actual_return_at TEXT,
  actor_id TEXT,
  device_id TEXT,
  version INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  PRIMARY KEY(business_date,mnv)
);
CREATE INDEX IF NOT EXISTS idx_post_meal_date_status ON post_meal_attendance(business_date,status,mnv);
CREATE INDEX IF NOT EXISTS idx_post_meal_updated ON post_meal_attendance(updated_at);

CREATE TABLE IF NOT EXISTS post_meal_attendance_audit (
  event_id TEXT PRIMARY KEY REFERENCES events(event_id) ON DELETE CASCADE,
  business_date TEXT NOT NULL,
  mnv TEXT NOT NULL,
  before_json TEXT NOT NULL,
  after_json TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_post_meal_audit_date_mnv ON post_meal_attendance_audit(business_date,mnv,created_at);

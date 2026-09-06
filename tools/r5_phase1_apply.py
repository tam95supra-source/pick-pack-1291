#!/usr/bin/env python3
from pathlib import Path

migration = Path('service/migrations/0015_r5_quota_realtime_revision.sql')
migration.write_text("""-- R5 QUOTA-REALTIME-DELTA-001
-- Small canonical revision projection. The one-time backfill may scan events;
-- normal sync-status must never scan/group events again.
CREATE TABLE IF NOT EXISTS day_revision_state (
  business_date TEXT NOT NULL,
  authority_epoch INTEGER NOT NULL,
  service_generation TEXT NOT NULL,
  revision INTEGER NOT NULL,
  updated_at TEXT NOT NULL,
  PRIMARY KEY (business_date, authority_epoch, service_generation)
);
CREATE INDEX IF NOT EXISTS idx_day_revision_authority
  ON day_revision_state(authority_epoch, service_generation, business_date);

INSERT INTO day_revision_state(business_date,authority_epoch,service_generation,revision,updated_at)
SELECT business_date,authority_epoch,service_generation,MAX(authority_seq),MAX(committed_at)
FROM events
GROUP BY business_date,authority_epoch,service_generation
ON CONFLICT(business_date,authority_epoch,service_generation) DO UPDATE SET
  revision=CASE WHEN excluded.revision>day_revision_state.revision THEN excluded.revision ELSE day_revision_state.revision END,
  updated_at=CASE WHEN excluded.revision>=day_revision_state.revision THEN excluded.updated_at ELSE day_revision_state.updated_at END;

CREATE TRIGGER IF NOT EXISTS trg_events_day_revision
AFTER INSERT ON events
BEGIN
  INSERT INTO day_revision_state(business_date,authority_epoch,service_generation,revision,updated_at)
  VALUES(NEW.business_date,NEW.authority_epoch,NEW.service_generation,NEW.authority_seq,NEW.committed_at)
  ON CONFLICT(business_date,authority_epoch,service_generation) DO UPDATE SET
    revision=CASE WHEN excluded.revision>day_revision_state.revision THEN excluded.revision ELSE day_revision_state.revision END,
    updated_at=CASE WHEN excluded.revision>=day_revision_state.revision THEN excluded.updated_at ELSE day_revision_state.updated_at END;
END;
""", encoding='utf-8')

p = Path('service/src/sync_contract.ts')
t = p.read_text(encoding='utf-8')
old = 'const auth=await authenticate(env.DB,env,request);if(!auth)return apiError("UNAUTHORIZED","AUTH",401);const now=nowIso(),cutoff=new Date(Date.now()-60_000).toISOString();'
new = 'const auth=await authenticate(env.DB,env,request);if(!auth)return apiError("UNAUTHORIZED","AUTH",401);const now=nowIso(),cutoff=new Date(Date.now()-15*60_000).toISOString();'
if old not in t:
    raise SystemExit('sync_contract heartbeat anchor missing')
t = t.replace(old, new, 1)
oldq = '''env.DB.prepare(`WITH recent AS (SELECT business_date,sequence_no FROM business_dates ORDER BY sequence_no DESC LIMIT 7)
      SELECT r.business_date,r.sequence_no,COALESCE(MAX(e.authority_seq),0) revision FROM recent r LEFT JOIN events e ON e.business_date=r.business_date GROUP BY r.business_date,r.sequence_no ORDER BY r.sequence_no DESC`),'''
newq = '''env.DB.prepare(`WITH recent AS (SELECT business_date,sequence_no FROM business_dates ORDER BY sequence_no DESC LIMIT 7),
      current_authority AS (SELECT authority_epoch,service_generation FROM authority_state WHERE singleton_id=1)
      SELECT r.business_date,r.sequence_no,COALESCE(d.revision,0) revision
      FROM recent r CROSS JOIN current_authority a
      LEFT JOIN day_revision_state d ON d.business_date=r.business_date AND d.authority_epoch=a.authority_epoch AND d.service_generation=a.service_generation
      ORDER BY r.sequence_no DESC`),'''
if oldq not in t:
    raise SystemExit('sync_contract status anchor missing')
p.write_text(t.replace(oldq, newq, 1), encoding='utf-8')

p = Path('service/src/legacy_sync_portable.ts')
t = p.read_text(encoding='utf-8')
start = t.index('  const q=`WITH recent AS (')
end = t.index('`;\n  const result=', start) + 2
nq = '''  const q=`WITH recent AS (
      SELECT business_date,sequence_no FROM business_dates ORDER BY sequence_no DESC LIMIT 7
    ), current_authority AS (
      SELECT authority_epoch,authority_seq,mode,scope,service_generation,updated_at FROM authority_state WHERE singleton_id=1
    ), rev AS (
      SELECT recent.business_date,recent.sequence_no,COALESCE(day_revision_state.revision,0) AS max_seq
      FROM recent CROSS JOIN current_authority a
      LEFT JOIN day_revision_state ON day_revision_state.business_date=recent.business_date
        AND day_revision_state.authority_epoch=a.authority_epoch
        AND day_revision_state.service_generation=a.service_generation
    ), meta AS (
      SELECT
        (SELECT business_date FROM business_dates ORDER BY sequence_no ASC LIMIT 1) AS server_retention_floor,
        COALESCE((SELECT pending_count FROM replication_status WHERE singleton_id=1),0) AS projection_pending,
        COALESCE((SELECT revision FROM revision_state WHERE namespace='employees'),0) AS master_revision
    )
    SELECT rev.business_date,rev.sequence_no,rev.max_seq,
      a.authority_epoch,a.authority_seq,a.mode,a.scope,a.service_generation,a.updated_at,
      meta.server_retention_floor,meta.projection_pending,meta.master_revision
    FROM rev CROSS JOIN current_authority a CROSS JOIN meta
    ORDER BY rev.sequence_no DESC`;'''
p.write_text(t[:start] + nq + t[end:], encoding='utf-8')

Path('tools/r5_quota_realtime_guard.py').write_text("""#!/usr/bin/env python3
import sqlite3
import re
from pathlib import Path

sc = Path('service/src/sync_contract.ts').read_text(encoding='utf-8')
lg = Path('service/src/legacy_sync_portable.ts').read_text(encoding='utf-8')
for name, text in [('sync_contract', sc), ('legacy_sync_portable', lg)]:
    if re.search(r'LEFT\\s+JOIN\\s+events|MAX\\s*\\(\\s*(?:e|events)\\.authority_seq', text, re.I | re.S):
        raise SystemExit(f'R5_STATUS_EVENTS_SCAN_FORBIDDEN:{name}')
if '15*60_000' not in sc:
    raise SystemExit('R5_CLIENT_HEARTBEAT_NOT_COALESCED')

mig = Path('service/migrations/0015_r5_quota_realtime_revision.sql').read_text(encoding='utf-8')
status_sql = """WITH recent AS (SELECT business_date,sequence_no FROM business_dates ORDER BY sequence_no DESC LIMIT 7),
current_authority AS (SELECT authority_epoch,service_generation FROM authority_state WHERE singleton_id=1)
SELECT r.business_date,r.sequence_no,COALESCE(d.revision,0) revision
FROM recent r CROSS JOIN current_authority a
LEFT JOIN day_revision_state d ON d.business_date=r.business_date AND d.authority_epoch=a.authority_epoch AND d.service_generation=a.service_generation
ORDER BY r.sequence_no DESC"""

def build(n):
    db = sqlite3.connect(':memory:')
    db.executescript("""
    CREATE TABLE authority_state(singleton_id INTEGER PRIMARY KEY,authority_epoch INTEGER,authority_seq INTEGER,mode TEXT,scope TEXT,service_generation TEXT,updated_at TEXT);
    INSERT INTO authority_state VALUES(1,9,0,'SERVICE_PRIMARY','PRODUCTION','g1','x');
    CREATE TABLE business_dates(business_date TEXT PRIMARY KEY,sequence_no INTEGER UNIQUE,source TEXT);
    CREATE INDEX idx_business_dates_sequence ON business_dates(sequence_no DESC);
    CREATE TABLE events(event_id TEXT PRIMARY KEY,event_type TEXT,entity_type TEXT,entity_id TEXT,business_date TEXT,authority_epoch INTEGER,authority_seq INTEGER,service_generation TEXT,base_version INTEGER,new_version INTEGER,actor_id TEXT,actor_role TEXT,device_id TEXT,occurred_at TEXT,committed_at TEXT,payload_json TEXT,idempotency_key TEXT UNIQUE,origin TEXT,schema_version INTEGER,checksum TEXT);
    CREATE INDEX idx_events_business_seq ON events(business_date,authority_epoch,authority_seq);
    """)
    for d in range(1, 8):
        db.execute('INSERT INTO business_dates VALUES(?,?,?)', (f'2026-09-{d:02d}', d, 'T'))
    rows = []
    for i in range(1, n + 1):
        date = f'2026-09-{(i % 7) + 1:02d}'
        rows.append((f'e{i}','X','X',str(i),date,9,i,'g1',0,1,'a','USER','d','x','x','{}',f'k{i}','T',1,'c'))
    if rows:
        db.executemany('INSERT INTO events VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)', rows)
    db.executescript(mig)
    db.execute('UPDATE authority_state SET authority_seq=? WHERE singleton_id=1', (n,))
    return db

for n in (0, 1540, 10000):
    db = build(n)
    rows = db.execute(status_sql).fetchall()
    if len(rows) != 7:
        raise SystemExit(f'R5_STATUS_WINDOW_BAD:{n}:{len(rows)}')
    plan = ' '.join(str(x) for row in db.execute('EXPLAIN QUERY PLAN ' + status_sql) for x in row).lower()
    if 'events' in plan:
        raise SystemExit(f'R5_STATUS_QUERY_PLAN_SCANS_EVENTS:{n}:{plan}')
    db.execute('INSERT INTO events VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)', (f'new{n}','X','X','n','2026-09-07',9,n+1,'g1',0,1,'a','USER','d','x','z','{}',f'kn{n}','T',1,'c'))
    rev = db.execute("SELECT revision FROM day_revision_state WHERE business_date='2026-09-07' AND authority_epoch=9 AND service_generation='g1'").fetchone()[0]
    if rev != n + 1:
        raise SystemExit(f'R5_REVISION_TRIGGER_BAD:{n}:{rev}')
print('R5_QUOTA_REALTIME_GUARD_PASS')
""", encoding='utf-8')

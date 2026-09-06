#!/usr/bin/env python3
import json
import re
import sqlite3
from pathlib import Path

sc = Path('service/src/sync_contract.ts').read_text(encoding='utf-8')
lg = Path('service/src/legacy_sync_portable.ts').read_text(encoding='utf-8')
core = Path('service/src/core.ts').read_text(encoding='utf-8')
for name, text in [('sync_contract', sc), ('legacy_sync_portable', lg)]:
    if re.search(r'LEFT\s+JOIN\s+events|MAX\s*\(\s*(?:e|events)\.authority_seq', text, re.I | re.S):
        raise SystemExit(f'R5_STATUS_EVENTS_SCAN_FORBIDDEN:{name}')
if '15*60_000' not in sc:
    raise SystemExit('R5_CLIENT_HEARTBEAT_NOT_COALESCED')

mig = Path('service/migrations/0015_r5_quota_realtime_revision.sql').read_text(encoding='utf-8')
if re.search(r'CREATE\s+TRIGGER', mig, re.I):
    raise SystemExit('R5_REVISION_TRIGGER_DEPENDENCY_FORBIDDEN')

# Revision projection must be part of the canonical event writer batch, not an implicit DB trigger.
writer_needles = [
    'INSERT INTO events(event_id,event_type,entity_type,entity_id,business_date,authority_epoch,authority_seq,service_generation',
    'INSERT INTO day_revision_state(business_date,authority_epoch,service_generation,revision,updated_at)',
    'ON CONFLICT(business_date,authority_epoch,service_generation) DO UPDATE SET',
    'revision=CASE WHEN excluded.revision>day_revision_state.revision THEN excluded.revision ELSE day_revision_state.revision END',
    '.bind(event.business_date,event.authority_epoch,event.service_generation,event.authority_seq,event.committed_at)',
]
for needle in writer_needles:
    if needle not in core:
        raise SystemExit('R5_CANONICAL_WRITER_REVISION_PROJECTION_MISSING:' + needle[:40])
if core.index(writer_needles[0]) > core.index(writer_needles[1]):
    raise SystemExit('R5_CANONICAL_WRITER_REVISION_ORDER_BAD')

status_sql = """WITH recent AS (SELECT business_date,sequence_no FROM business_dates ORDER BY sequence_no DESC LIMIT 7),
current_authority AS (SELECT authority_epoch,service_generation FROM authority_state WHERE singleton_id=1)
SELECT r.business_date,r.sequence_no,COALESCE(d.revision,0) revision
FROM recent r CROSS JOIN current_authority a
LEFT JOIN day_revision_state d ON d.business_date=r.business_date AND d.authority_epoch=a.authority_epoch AND d.service_generation=a.service_generation
ORDER BY r.sequence_no DESC"""


def canonical_event_commit(db: sqlite3.Connection, row):
    """Model the two statements that core.ts sends in the same D1 batch."""
    with db:
        db.execute('INSERT INTO events VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)', row)
        db.execute(
            """INSERT INTO day_revision_state(business_date,authority_epoch,service_generation,revision,updated_at)
               VALUES(?,?,?,?,?)
               ON CONFLICT(business_date,authority_epoch,service_generation) DO UPDATE SET
                 revision=CASE WHEN excluded.revision>day_revision_state.revision THEN excluded.revision ELSE day_revision_state.revision END,
                 updated_at=CASE WHEN excluded.revision>=day_revision_state.revision THEN excluded.updated_at ELSE day_revision_state.updated_at END""",
            (row[4], row[5], row[7], row[6], row[14]),
        )


def build(n: int):
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
    # Migration owns only initial backfill. Future changes are projected by canonical_event_commit/core.ts.
    db.executescript(mig)
    db.execute('UPDATE authority_state SET authority_seq=? WHERE singleton_id=1', (n,))
    return db


evidence = []
for n in (0, 1540, 10000):
    db = build(n)
    rows = db.execute(status_sql).fetchall()
    if len(rows) != 7:
        raise SystemExit(f'R5_STATUS_WINDOW_BAD:{n}:{len(rows)}')
    plan = ' '.join(str(x) for row in db.execute('EXPLAIN QUERY PLAN ' + status_sql) for x in row).lower()
    if 'events' in plan:
        raise SystemExit(f'R5_STATUS_QUERY_PLAN_SCANS_EVENTS:{n}:{plan}')

    # Backfill correctness for existing data: per-day revision is the max authority_seq already present.
    if n:
        expected = db.execute("SELECT COALESCE(MAX(authority_seq),0) FROM events WHERE business_date='2026-09-07' AND authority_epoch=9 AND service_generation='g1'").fetchone()[0]
        got = db.execute("SELECT COALESCE(revision,0) FROM day_revision_state WHERE business_date='2026-09-07' AND authority_epoch=9 AND service_generation='g1'").fetchone()
        got = 0 if got is None else got[0]
        if got != expected:
            raise SystemExit(f'R5_REVISION_BACKFILL_BAD:{n}:{got}:{expected}')

    # New event uses canonical writer projection and must advance revision without any trigger.
    new_row = (f'new{n}','X','X','n','2026-09-07',9,n+1,'g1',0,1,'a','USER','d','x','z','{}',f'kn{n}','T',1,'c')
    canonical_event_commit(db, new_row)
    rev = db.execute("SELECT revision FROM day_revision_state WHERE business_date='2026-09-07' AND authority_epoch=9 AND service_generation='g1'").fetchone()[0]
    if rev != n + 1:
        raise SystemExit(f'R5_REVISION_WRITER_BAD:{n}:{rev}')

    # An older/out-of-order projection must never lower the day revision.
    older_seq = max(0, n)
    old_row = (f'old{n}','X','X','old','2026-09-07',9,older_seq,'g1',0,1,'a','USER','d','x','zz','{}',f'ko{n}','T',1,'c')
    canonical_event_commit(db, old_row)
    rev2 = db.execute("SELECT revision FROM day_revision_state WHERE business_date='2026-09-07' AND authority_epoch=9 AND service_generation='g1'").fetchone()[0]
    if rev2 != n + 1:
        raise SystemExit(f'R5_REVISION_MONOTONIC_BAD:{n}:{rev2}')
    evidence.append({'events': n, 'status_rows': len(rows), 'revision': rev2, 'status_plan_scans_events': False})

out = Path('/tmp/r5-full-dod')
out.mkdir(parents=True, exist_ok=True)
(out / 'o1_revision_guard.json').write_text(json.dumps({'status':'PASS','mechanism':'CANONICAL_WRITER_BATCH_NO_TRIGGER','cases':evidence}, indent=2) + '\n')
print('R5_QUOTA_REALTIME_GUARD_PASS CANONICAL_WRITER_BATCH_NO_TRIGGER')

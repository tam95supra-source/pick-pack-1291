#!/usr/bin/env python3
import re
import sqlite3
from pathlib import Path

sc = Path('service/src/sync_contract.ts').read_text(encoding='utf-8')
lg = Path('service/src/legacy_sync_portable.ts').read_text(encoding='utf-8')
for name, text in [('sync_contract', sc), ('legacy_sync_portable', lg)]:
    if re.search(r'LEFT\s+JOIN\s+events|MAX\s*\(\s*(?:e|events)\.authority_seq', text, re.I | re.S):
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
    db.execute(
        'INSERT INTO events VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
        (f'new{n}','X','X','n','2026-09-07',9,n+1,'g1',0,1,'a','USER','d','x','z','{}',f'kn{n}','T',1,'c'),
    )
    rev = db.execute("SELECT revision FROM day_revision_state WHERE business_date='2026-09-07' AND authority_epoch=9 AND service_generation='g1'").fetchone()[0]
    if rev != n + 1:
        raise SystemExit(f'R5_REVISION_TRIGGER_BAD:{n}:{rev}')
print('R5_QUOTA_REALTIME_GUARD_PASS')

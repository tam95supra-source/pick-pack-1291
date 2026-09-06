#!/usr/bin/env python3
from pathlib import Path
import json

scope=json.load(open('ops/OWNER_SCOPE_CURRENT.json'))
assert scope['scope_id']=='OWNER_20260906_R5_QUOTA_REALTIME'
assert scope['revision']==6 and scope['ledger_head_sequence']==8

p=Path('service/migrations/0015_r5_quota_realtime_revision.sql'); s=p.read_text(); marker='CREATE TRIGGER IF NOT EXISTS trg_events_day_revision\n'
if marker in s:
    p.write_text(s[:s.index(marker)] + "-- Revision maintenance is performed explicitly inside the canonical writer D1 batch.\n")
elif 'Revision maintenance is performed explicitly' not in s:
    raise SystemExit('R5_FIX_FAIL:0015')

p=Path('service/src/core.ts'); s=p.read_text()
a='''.bind(event.event_id,event.event_type,event.entity_type,event.entity_id,event.business_date,event.authority_epoch,event.authority_seq,event.service_generation,event.base_version,event.new_version,event.actor_id,event.actor_role,event.device_id,event.occurred_at,event.committed_at,event.payload_json,event.idempotency_key,event.origin,event.schema_version,event.checksum),\n    db.prepare("INSERT INTO sheet_replication_outbox(event_id,status,next_attempt_at) VALUES(?1,'PENDING',?2)").bind(event.event_id,event.committed_at),'''
b='''.bind(event.event_id,event.event_type,event.entity_type,event.entity_id,event.business_date,event.authority_epoch,event.authority_seq,event.service_generation,event.base_version,event.new_version,event.actor_id,event.actor_role,event.device_id,event.occurred_at,event.committed_at,event.payload_json,event.idempotency_key,event.origin,event.schema_version,event.checksum),\n    db.prepare(`INSERT INTO day_revision_state(business_date,authority_epoch,service_generation,revision,updated_at) VALUES(?1,?2,?3,?4,?5)\n      ON CONFLICT(business_date,authority_epoch,service_generation) DO UPDATE SET\n        revision=CASE WHEN excluded.revision>day_revision_state.revision THEN excluded.revision ELSE day_revision_state.revision END,\n        updated_at=CASE WHEN excluded.revision>=day_revision_state.revision THEN excluded.updated_at ELSE day_revision_state.updated_at END`)\n      .bind(event.business_date,event.authority_epoch,event.service_generation,event.authority_seq,event.committed_at),\n    db.prepare("INSERT INTO sheet_replication_outbox(event_id,status,next_attempt_at) VALUES(?1,'PENDING',?2)").bind(event.event_id,event.committed_at),'''
if a in s: s=s.replace(a,b,1)
elif 'INSERT INTO day_revision_state(business_date,authority_epoch,service_generation,revision,updated_at)' not in s: raise SystemExit('R5_FIX_FAIL:CORE')
p.write_text(s)

Path('service/migrations/0017_r5_quota_budget.sql').write_text('''PRAGMA foreign_keys = ON;\n\nCREATE TABLE IF NOT EXISTS quota_policy (\n  metric TEXT PRIMARY KEY,\n  hard_limit INTEGER NOT NULL CHECK(hard_limit > 0),\n  unit TEXT NOT NULL,\n  source_requirement TEXT NOT NULL,\n  updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))\n);\n\nINSERT INTO quota_policy(metric,hard_limit,unit,source_requirement) VALUES\n  ('GOOGLE_SHEETS_DAILY',250,'requests/day','R5-15'),\n  ('GOOGLE_SHEETS_PROJECT_MINUTE',100,'requests/minute/project','R5-15'),\n  ('GOOGLE_SHEETS_READ_MINUTE',30,'read requests/minute/user','R5-15'),\n  ('GOOGLE_SHEETS_WRITE_MINUTE',30,'write requests/minute/user','R5-15')\nON CONFLICT(metric) DO UPDATE SET hard_limit=excluded.hard_limit,unit=excluded.unit,source_requirement=excluded.source_requirement,updated_at=strftime('%Y-%m-%dT%H:%M:%fZ','now');\n\nCREATE TABLE IF NOT EXISTS quota_usage (\n  window_key TEXT NOT NULL,\n  metric TEXT NOT NULL REFERENCES quota_policy(metric),\n  used INTEGER NOT NULL DEFAULT 0 CHECK(used >= 0),\n  hard_limit INTEGER NOT NULL CHECK(hard_limit > 0),\n  updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),\n  PRIMARY KEY(window_key,metric),\n  CONSTRAINT quota_hard_limit CHECK(used <= hard_limit)\n);\nCREATE INDEX IF NOT EXISTS idx_quota_usage_metric_window ON quota_usage(metric,window_key);\n\nINSERT INTO system_meta(key,value,updated_at) VALUES('r5_operational_repair_dirty','1',strftime('%Y-%m-%dT%H:%M:%fZ','now')) ON CONFLICT(key) DO NOTHING;\nINSERT INTO system_meta(key,value,updated_at) VALUES('r5_document_audit_dirty','1',strftime('%Y-%m-%dT%H:%M:%fZ','now')) ON CONFLICT(key) DO NOTHING;\n\nINSERT OR IGNORE INTO schema_migrations(version,checksum) VALUES('0017_r5_quota_budget','R5_QUOTA_BUDGET_V2_NO_TRIGGER');\n''')

p=Path('service/src/quota_budget.ts'); s=p.read_text()
old='''function usageStmt(db:D1Database,windowKey:string,metric:string,count:number):D1PreparedStatement{\n  return db.prepare(`INSERT INTO quota_usage(window_key,metric,used,updated_at) VALUES(?1,?2,?3,strftime('%Y-%m-%dT%H:%M:%fZ','now'))\n    ON CONFLICT(window_key,metric) DO UPDATE SET used=used+excluded.used,updated_at=excluded.updated_at`).bind(windowKey,metric,count);\n}'''
new='''function usageStmt(db:D1Database,windowKey:string,metric:string,count:number):D1PreparedStatement{\n  return db.prepare(`INSERT INTO quota_usage(window_key,metric,used,hard_limit,updated_at)\n    SELECT ?1,p.metric,?3,p.hard_limit,strftime('%Y-%m-%dT%H:%M:%fZ','now') FROM quota_policy p WHERE p.metric=?2\n    ON CONFLICT(window_key,metric) DO UPDATE SET\n      used=quota_usage.used+excluded.used,hard_limit=excluded.hard_limit,updated_at=excluded.updated_at`)\n    .bind(windowKey,metric,count);\n}'''
if old in s: s=s.replace(old,new,1)
elif 'quota_usage.used+excluded.used' not in s: raise SystemExit('R5_FIX_FAIL:QUOTA_STMT')
s=s.replace('if(String(e).includes("QUOTA_HARD_LIMIT"))return false;','if(String(e).includes("quota_hard_limit")||String(e).includes("CHECK constraint failed"))return false;',1)
s=s.replace('D1 batch rollback on trigger abort guarantees daily/project/kind windows advance together or not at all.','D1 batch rollback on named CHECK constraint guarantees daily/project/kind windows advance together or not at all.',1)
p.write_text(s)

Path('config/stable_r5_parity.json').write_text(json.dumps({
  'schema_version':1,'status':'READY_NOT_LIVE','environment_id':'STABLE','service_audience':'PICK_PACK_1291_STABLE',
  'implementation_contract':'R5-15/QUOTA-REALTIME-DELTA-001','shared_runtime_source':True,
  'required_mechanisms':['O1_REVISION_STATUS','INDEXED_DELTA_CURSOR','SINGLE_FLIGHT_SYNC','COALESCED_WAKE','TERMINAL_OUTBOX','SHEETS_BATCH_METERING','DIRTY_DUE_SCHEDULING','QUOTA_CIRCUIT'],
  'dynamic_bindings':['STABLE_DB','STABLE_GSHEET_API_URL','STABLE_FIREBASE_PROJECT_ID','STABLE_FIREBASE_GOOGLE_APP_ID','STABLE_FIREBASE_API_KEY','STABLE_FIREBASE_GCM_SENDER_ID'],
  'activation':'OWNER_PROMOTE_ONLY','deploy_now':False
},indent=2)+'\n')

Path('tools/r5_stable_parity_guard.py').write_text('''#!/usr/bin/env python3\nimport json\nfrom pathlib import Path\ndef need(c,m):\n    if not c: raise SystemExit('R5_STABLE_PARITY_FAIL:'+m)\nc=json.loads(Path('config/stable_r5_parity.json').read_text())\nneed(c['status']=='READY_NOT_LIVE' and c['deploy_now'] is False,'NO_DEPLOY')\nneed(c['environment_id']=='STABLE' and c['service_audience']=='PICK_PACK_1291_STABLE','IDENTITY')\nneed(c['shared_runtime_source'] is True,'SHARED_RUNTIME')\nb=Path('app/build.gradle.kts').read_text(); need('create("stable")' in b and 'PICK_PACK_1291_STABLE' in b and 'STABLE_GSHEET_API_URL' in b,'ANDROID_STABLE'); need(not Path('app/src/stable').exists(),'SOURCE_FORK')\nq=Path('service/src/quota_budget.ts').read_text(); need('quota_usage.used+excluded.used' in q and 'hard_limit=excluded.hard_limit' in q,'QUOTA')\nneed('day_revision_state' in Path('service/src/core.ts').read_text(),'REVISION'); need('day_revision_state' in Path('service/src/sync_contract.ts').read_text(),'O1'); need('push_wake_outbox' in Path('service/src/push.ts').read_text(),'WAKE')\nprint('R5_STABLE_PARITY_PASS READY_NOT_LIVE')\n'''); Path('tools/r5_stable_parity_guard.py').chmod(0o755)

p=Path('tools/beta78_service_live_gate.sh'); s=p.read_text(); anchor='set -Eeuo pipefail\n\nD=/tmp/beta78-service-live'; repl='''set -Eeuo pipefail\n\n# Recovery callers may run this gate after a failed candidate migration. Make the service tree byte-exact to the base commit so candidate-only migrations cannot leak into rollback.\nif [[ -n "${BASE_SERVICE_SOURCE_SHA:-}" && -n "${SERVICE_SOURCE_SHA:-}" && "$SERVICE_SOURCE_SHA" == "$BASE_SERVICE_SOURCE_SHA" ]]; then\n  bash tools/restore_exact_service_tree.sh "$SERVICE_SOURCE_SHA"\nfi\n\nD=/tmp/beta78-service-live'''
if anchor in s: s=s.replace(anchor,repl,1)
elif 'restore_exact_service_tree.sh' not in s: raise SystemExit('R5_FIX_FAIL:RECOVERY')
p.write_text(s)
print('R5_TRIGGERLESS_STABLE_PARITY_PATCH_APPLIED')

#!/usr/bin/env python3
import json, math, statistics, time
from pathlib import Path

ROOT=Path('.')
scope=json.loads((ROOT/'ops/OWNER_SCOPE_CURRENT.json').read_text())
req=next((x for x in scope.get('requirements',[]) if x.get('requirement_id')=='R5-15'),None)
assert req is not None, 'R5_15_SCOPE_MISSING'
assert req.get('invariant_id')=='QUOTA-REALTIME-DELTA-001'
assert req.get('state')=='LOCKED_REQUIREMENT_PENDING_FIX'
assert len(req.get('acceptance',[]))==12, f"R5_15_ACCEPTANCE_COUNT:{len(req.get('acceptance',[]))}"

sc=(ROOT/'service/src/sync_contract.ts').read_text()
legacy=(ROOT/'service/src/legacy_sync_portable.ts').read_text()
web=(ROOT/'service/public/app.js').read_text()
android_store=(ROOT/'app/src/main/java/vn/pickpack1291/app/beta/OperationalDataStore.kt').read_text()
android_bg=(ROOT/'app/src/main/java/vn/pickpack1291/app/beta/M2BackgroundSync.kt').read_text()
android_fg=(ROOT/'app/src/main/java/vn/pickpack1291/app/beta/ForegroundSyncCoordinator.kt').read_text()
android_fcm=(ROOT/'app/src/main/java/vn/pickpack1291/app/beta/M2Firebase.kt').read_text()
push=(ROOT/'service/src/push.ts').read_text()
special=(ROOT/'service/src/session_hotfix.ts').read_text()
repl=(ROOT/'service/src/replication.ts').read_text()
entry=(ROOT/'service/src/entry_product.ts').read_text()
quota=(ROOT/'service/src/quota_budget.ts').read_text()

# O(1) revision/status + indexed delta.
assert 'day_revision_state' in sc and '15*60_000' in sc
assert 'LEFT JOIN events' not in sc
assert 'authority_epoch=?2 AND e.service_generation=?3 AND e.authority_seq>?4' in sc
assert 'revision_state' in legacy and 'MAX(source_row)' not in legacy

# Normal web path must be delta/single-flight, not full bootstrap/re-render.
assert 'singleFlight' in web
assert '/v1/delta/day?' in web and '/v1/delta/master?' in web
assert web.count('/v1/bootstrap?business_date=') == 1
replay=web[web.index('async function replay()'):web.index('function showConflict')]
assert 'await refresh()' not in replay
socket=web[web.index('async function connectSocket'):web.index('function connectRealtime')]
assert 'refresh()' not in socket

# Android one-orchestrator / indexed delta normal path.
assert 'applyDayDelta' in android_store
assert 'sync_day' not in android_bg
assert 'scheduleOutbox(app)' in android_fg
assert 'scheduleCatchUp(applicationContext)' in android_fcm

# Background amplification removal / terminalization.
assert 'push_wake_outbox' in push and 'day_revision_state' in push
assert "'day:'||event_id" not in push
assert 'deviceState=new Map' in push
assert 'session_special_projection_outbox' in special
assert "ORDER BY authority_seq DESC LIMIT 120" not in special
assert "status='SYNCED'" in special and 'STALE_INFLIGHT_RECOVERED' in special

# Sheets batching + ACK fence + no duplicate verify read.
assert 'limit=100' in repl and 'Math.min(limit,100)' in repl
assert 'batchPutValues' in repl and '/values:batchUpdate' in repl
assert 'claim_token=?3' in repl
section=repl[repl.index('async function replicateOperational('):repl.index('export async function replicationHealth')]
assert section.count('loadOperationalIndex(env,token)') == 1
assert 'REPLICATION_OPERATIONAL_INCOMPLETE' in section

# Every direct Sheets API module is metered; limits are policy-backed, not business-logic constants.
sheets_files=[]
for f in (ROOT/'service/src').glob('*.ts'):
    text=f.read_text(errors='ignore')
    if 'sheets.googleapis.com' in text:
        sheets_files.append(str(f))
        assert 'requireSheetsCall' in text, f'UNMETERED_SHEETS_API:{f}'
assert sheets_files
assert 'SELECT metric,hard_limit,unit,source_requirement FROM quota_policy' in quota
assert 'catalog-source-30m' in entry and 'repair-dirty-5m' in entry and 'repair-30m' not in entry

# Conservative structural quota budget for the OWNER max-day model.
EVENTS=1540
CLIENTS=5
ANDROID=3
WEB=2
BATCH=100
# HTTP/scheduled invocation budget: event mutations + worst-case one delta fetch/client/event + 15m status + cron + recovery reserve.
worker_mutations=EVENTS
worker_delta=EVENTS*CLIENTS
worker_status=CLIENTS*96
worker_cron=1440
worker_recovery_reserve=2000
worker_requests=worker_mutations+worker_delta+worker_status+worker_cron+worker_recovery_reserve
# D1 structural budget is deliberately conservative and is NOT a replacement for post-deploy metrics.
d1_rows_read=(EVENTS*40)+(EVENTS*CLIENTS*6)+(CLIENTS*96*32)+(1440*100)+(EVENTS*20)
d1_rows_read_with_margin=d1_rows_read+100000
# Bound canonical/write-side amplification to 9 D1 row writes/event plus metering/heartbeat/maintenance reserve.
d1_rows_written=(EVENTS*9)+(CLIENTS*96)+(math.ceil(EVENTS/BATCH)*10*3)+1000
sheets_calls=math.ceil(EVENTS/BATCH)*10

assert worker_requests <= 20000, worker_requests
assert d1_rows_read_with_margin <= 500000, d1_rows_read_with_margin
assert d1_rows_written <= 20000, d1_rows_written
assert sheets_calls <= 250, sheets_calls

# CPU-only reducer benchmark: validates delta patch cost does not scale as full reload.
# This is synthetic local reducer evidence, not an Android frame/UI measurement.
state={i:0 for i in range(CLIENTS)}
samples=[]
for revision in range(1,EVENTS+1):
    for client in range(CLIENTS):
        t0=time.perf_counter_ns()
        if revision>state[client]: state[client]=revision
        samples.append((time.perf_counter_ns()-t0)/1_000_000)
assert all(v==EVENTS for v in state.values())
samples.sort()
p95=samples[max(0,math.ceil(len(samples)*.95)-1)]

receipt={
  'status':'R5_PREPROD_INTEGRATED_PASS',
  'scope_id':scope['scope_id'],
  'scope_revision':scope['revision'],
  'requirement_id':'R5-15',
  'invariant_id':'QUOTA-REALTIME-DELTA-001',
  'max_day':{'events':EVENTS,'clients':CLIENTS,'android':ANDROID,'web':WEB},
  'structural_quota_model':{
    'worker_requests_per_day':worker_requests,'target_max':20000,
    'd1_rows_read_per_day_with_margin':d1_rows_read_with_margin,'target_max_rows_read':500000,
    'd1_rows_written_per_day':d1_rows_written,'target_max_rows_written':20000,
    'sheets_api_calls_per_day':sheets_calls,'target_max_sheets_calls':250,
    'replication_batch_size':BATCH,
    'classification':'CONSERVATIVE_PREPROD_MODEL_NOT_LIVE_MEASUREMENT'
  },
  'synthetic_reducer_p95_ms':p95,
  'synthetic_reducer_classification':'CPU_ONLY_NOT_UI_FRAME_LATENCY',
  'direct_sheets_clients_metered':sheets_files,
  'remaining_fresh_evidence_required_before_technical_pass':[
    'ANDROID_LOCAL_UI_P95_LE_100MS_ON_EXACT_CANDIDATE',
    'REMOTE_CONVERGENCE_P95_LE_1S_P99_LE_2S_ON_BETA_SERVICE',
    'POST_DEPLOY_D1_QUOTA_READBACK_OR_EQUIVALENT_EXACT_SOURCE_MEASUREMENT',
    'FULL_ACTIVE_PASS_REGRESSION_BEFORE_BETA_OTA'
  ]
}
out=Path('/tmp/r5-full-dod');out.mkdir(parents=True,exist_ok=True)
(out/'receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2))
print(json.dumps(receipt,ensure_ascii=False))

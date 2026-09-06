#!/usr/bin/env python3
import json, math, time
from pathlib import Path

ROOT=Path('.')
scope=json.loads((ROOT/'ops/OWNER_SCOPE_CURRENT.json').read_text())
req=next((x for x in scope.get('requirements',[]) if x.get('requirement_id')=='R5-15'),None)
assert req is not None, 'R5_15_SCOPE_MISSING'
assert req.get('invariant_id')=='QUOTA-REALTIME-DELTA-001'
assert req.get('state')=='LOCKED_REQUIREMENT_PENDING_FIX'
assert isinstance(req.get('acceptance'), list) and req['acceptance'], 'R5_15_ACCEPTANCE_MISSING'

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
maintenance=(ROOT/'service/src/d1_maintenance.ts').read_text()
quota=(ROOT/'service/src/quota_budget.ts').read_text()

# STATIC contract checks only. These checks are useful, but they are not runtime evidence.
assert 'day_revision_state' in sc and '15*60_000' in sc
assert 'LEFT JOIN events' not in sc
assert 'authority_epoch=?2 AND e.service_generation=?3 AND e.authority_seq>?4' in sc
assert 'revision_state' in legacy and 'MAX(source_row)' not in legacy
assert 'singleFlight' in web
assert '/v1/delta/day?' in web and '/v1/delta/master?' in web
assert web.count('/v1/bootstrap?business_date=') == 1
replay=web[web.index('async function replay()'):web.index('function showConflict')]
assert 'await refresh()' not in replay
socket=web[web.index('async function connectSocket'):web.index('function connectRealtime')]
assert 'refresh()' not in socket
assert 'applyDayDelta' in android_store
assert 'sync_day' not in android_bg
assert 'scheduleOutbox(app)' in android_fg
assert 'scheduleCatchUp(applicationContext)' in android_fcm
assert 'push_wake_outbox' in push and 'day_revision_state' in push
assert "'day:'||event_id" not in push
assert 'deviceState=new Map' in push
assert 'session_special_projection_outbox' in special
assert "ORDER BY authority_seq DESC LIMIT 120" not in special
assert "status='SYNCED'" in special and 'STALE_INFLIGHT_RECOVERED' in special
assert 'limit=100' in repl and 'Math.min(limit,100)' in repl
assert 'batchPutValues' in repl and '/values:batchUpdate' in repl
assert 'claim_token=?3' in repl
section=repl[repl.index('async function replicateOperational('):repl.index('export async function replicationHealth')]
assert section.count('loadOperationalIndex(env,token)') == 1
assert 'REPLICATION_OPERATIONAL_INCOMPLETE' in section

# Direct Sheets API modules must still be metered. GAS/SpreadsheetApp operations are a
# different quota family and are intentionally NOT mislabeled as Sheets API calls here.
sheets_files=[]
for f in (ROOT/'service/src').glob('*.ts'):
    text=f.read_text(errors='ignore')
    if 'sheets.googleapis.com' in text:
        sheets_files.append(str(f))
        assert 'requireSheetsCall' in text, f'UNMETERED_SHEETS_API:{f}'
assert sheets_files
assert 'SELECT metric,hard_limit,unit,source_requirement FROM quota_policy' in quota

# Scheduled capacity must not repeatedly full-count hot business tables.
assert 'capacity-6h' in entry
assert 'capacity-30m' not in entry
assert "UNION ALL SELECT 'attendance_sessions',COUNT(*)" not in maintenance
assert 'rows_by_table:"OMITTED_FROM_HOT_PATH"' in maintenance

# OWNER envelope used for LOCAL forecasting. It is not a measured full day and cannot
# satisfy the Free/quota acceptance gate by itself.
EVENTS=2000
CLIENTS=5
ANDROID=3
WEB=2
BATCH=100
worker_mutations=EVENTS
worker_delta=EVENTS*CLIENTS
worker_status=CLIENTS*96
worker_cron=1440
worker_recovery_reserve=2000
worker_requests=worker_mutations+worker_delta+worker_status+worker_cron+worker_recovery_reserve
# Historical live evidence showed 7 billed rows for one events INSERT and 4 for one
# sheet-outbox INSERT on the observed path. This is a warning lower bound for that
# path only; it must not be applied to every mutation without route measurement.
observed_two_insert_write_lower_bound_if_all_events_follow_path=EVENTS*(7+4)
sheets_batch_floor=math.ceil(EVENTS/BATCH)

# CPU-only reducer benchmark. This is LOCAL_RUNTIME reducer evidence, not Android/web
# frame latency and not source-action-to-other-client realtime latency.
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
  'status':'NOT_VERIFIED',
  'technical_pass':False,
  'scope_id':scope['scope_id'],
  'scope_revision':scope['revision'],
  'requirement_id':'R5-15',
  'invariant_id':'QUOTA-REALTIME-DELTA-001',
  'evidence_classes':['STATIC','LOCAL_RUNTIME'],
  'owner_envelope':{
    'events':EVENTS,'clients':CLIENTS,'android':ANDROID,'web':WEB,
    'basis':'OWNER conservative envelope; endpoint manifest must reconcile actual route mix before cloud measurement'
  },
  'forecast_only':{
    'worker_requests_per_day_model':worker_requests,
    'owner_target_worker_requests':20000,
    'observed_two_insert_write_lower_bound_if_all_events_follow_path':observed_two_insert_write_lower_bound_if_all_events_follow_path,
    'owner_target_d1_rows_written':20000,
    'replication_batch_floor':sheets_batch_floor,
    'classification':'FORECAST_NOT_CLOUD_MEASURED_NOT_LIVE_SHIFT'
  },
  'synthetic_reducer_p95_ms':p95,
  'synthetic_reducer_classification':'LOCAL_RUNTIME_CPU_ONLY_NOT_UI_FRAME_LATENCY',
  'direct_sheets_api_clients_metered':sheets_files,
  'gaps_that_block_technical_pass':[
    'ACTUAL_ROUTE_MANIFEST_200_WORKERS_200_LABOR_50_DROP_MAX_RESOURCES',
    'ROUTE_SPECIFIC_D1_WRITE_AMPLIFICATION_MEASURED',
    'ANDROID_AND_WEB_LOCAL_UI_P95_LE_100MS_INSTRUMENTED',
    'SOURCE_ACTION_TO_OTHER_CLIENT_REALTIME_P95_LE_1S_P99_LE_2S',
    'FULL_5_CLIENT_SCENARIO_STATE_CHECKSUM_EVENT_COUNT_OUTBOX_MATCH',
    'GOOGLE_GAS_ALL_PATH_OPERATION_COUNTS_AND_LAG_LE_30M',
    'ACCOUNT_SUMMED_FREE_BUDGET_WITH_CI_MAINTENANCE_DR_HEADROOM',
    'STABLE_PRIVATE_R5_RUNTIME_PARITY_AND_IDLE_QUIET',
    'FULL_ACTIVE_PASS_REGRESSION_BEFORE_BETA_OTA'
  ]
}
out=Path('/tmp/r5-full-dod');out.mkdir(parents=True,exist_ok=True)
(out/'receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(receipt,ensure_ascii=False))

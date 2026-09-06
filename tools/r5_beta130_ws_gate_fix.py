#!/usr/bin/env python3
from pathlib import Path
p=Path('tools/r5_beta130_convergence_only_gate.sh')
s=p.read_text(encoding='utf-8')
old='''# Disposable employee is the only business projection required by ENTER/RESOURCE_CHANGE.
sql "INSERT INTO employees(mnv,full_name,main_position,supplier,department,site,warehouse,start_date,note,source_row,source_checksum) VALUES('$B80_MNV','R5 convergence fixture','Pick','TEST','','1291','','2026-01-01','technical-only',-515,'r5-$SUFFIX');" >/dev/null

mutation_api(){ local name=$1 body=$2; curl -fsS --connect-timeout 10 --max-time 20 -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' --data-binary "$body" "$SERVICE_URL/v1/legacy-mutations/batch" > "$D/$name.json"; }

# Apply the previously validated runner-only corrections, then enforce five isolated sessions.
python3 tools/r5_beta130_convergence_timing_fix.py
python3 tools/r5_beta130_prearm_observers_fix.py
python3 tools/r5_beta130_day_delta_probe_fix.py
python3 tools/r5_beta130_five_session_fix.py
git diff --check
git diff --quiet HEAD -- app service google-apps-script

# The function uses only Service/D1 endpoints. No replication/Drive/Sheets path is called.
source tools/r5_service_convergence_gate.sh
r5_service_convergence_gate

SHEETS_AFTER=$(sql "SELECT used,hard_limit FROM quota_usage WHERE window_key='$QKEY' AND metric='GOOGLE_SHEETS_DAILY';")
'''
new='''# Disposable employee/session are the only business projections required by RESOURCE_CHANGE.
sql "INSERT INTO employees(mnv,full_name,main_position,supplier,department,site,warehouse,start_date,note,source_row,source_checksum) VALUES('$B80_MNV','R5 convergence fixture','Pick','TEST','','1291','','2026-01-01','technical-only',-515,'r5-$SUFFIX');" >/dev/null
mutation_api(){ local name=$1 body=$2; curl -fsS --connect-timeout 10 --max-time 20 -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' --data-binary "$body" "$SERVICE_URL/v1/legacy-mutations/batch" > "$D/$name.json"; }
R5_ENTER="__R5_WS_ENTER_${SUFFIX}"
mutation_api r5-ws-fixture-enter "$(jq -nc --arg e "$R5_ENTER" --arg dev "$DEVICE" --arg date "$B80_DATE" --arg mnv "$B80_MNV" '{events:[{action:"enter",event_id:$e,device_id:$dev,business_date:$date,payload:{mnv:$mnv,shift:"Ca 2",work_choice:"KHONG",pda_serial:"",user_pick:"",pack_table:"",user_pack:"",resource_note:"R5 WS convergence fixture",duplicate_user:false,note:""}}]}')"
if ! jq -e --arg e "$R5_ENTER" '.ok==true and .results[0].local_event_id==$e and .results[0].status=="CONFIRMED" and .results[0].canonical_event_id==$e' "$D/r5-ws-fixture-enter.json" >/dev/null; then
  echo R5_WS_FIXTURE_ENTER_FAILED >&2
  exit 65
fi

# Real foreground path: INVALIDATION_V1 WebSocket wake then the exact PDA/Web delta transport.
# This replaces artificial pre-commit REST polling, which measured poll phase rather than runtime convergence.
export SERVICE_URL B80_DATE B80_MNV SUFFIX DEVICE
if ! R5_WS_OUT="$D/r5-live-measurement" node tools/r5_beta130_ws_convergence.mjs; then
  rc=$?
  echo "R5_WS_CONVERGENCE_FAILED" >&2
  exit $(( rc == 0 ? 67 : rc ))
fi

git diff --check || exit 68
git diff --quiet HEAD -- app service google-apps-script || exit 69

SHEETS_AFTER=$(sql "SELECT used,hard_limit FROM quota_usage WHERE window_key='$QKEY' AND metric='GOOGLE_SHEETS_DAILY';")
'''
if s.count(old)!=1: raise SystemExit(f'R5_WS_GATE_BLOCK_ANCHOR:{s.count(old)}')
s=s.replace(old,new,1)
old2='''jq --argjson before "$SHEETS_USED_BEFORE" --argjson after "$SHEETS_USED_AFTER" --arg source_sha "${SERVICE_SOURCE_SHA:-}" --arg run_id "${GITHUB_RUN_ID:-}" '. + {sheets_quota:{daily_before:$before,daily_after:$after,delta:($after-$before),google_api_calls_from_gate:0},exact_service_source_sha:$source_sha,github_run_id:$run_id}' "$D/r5-live-measurement/receipt.json" > "$D/receipt.json"
jq -e '.status=="PASS" and .auth_sessions.isolated==true and .clients.total==5 and .clients.android_pda==3 and .clients.web==2 and .sheets_quota.delta==0 and .remote_convergence_ms.p95<=1000 and .remote_convergence_ms.p99<=2000' "$D/receipt.json" >/dev/null
'''
new2='''if ! jq --argjson before "$SHEETS_USED_BEFORE" --argjson after "$SHEETS_USED_AFTER" --arg source_sha "${SERVICE_SOURCE_SHA:-}" --arg run_id "${GITHUB_RUN_ID:-}" '. + {sheets_quota:{daily_before:$before,daily_after:$after,delta:($after-$before),google_api_calls_from_gate:0},exact_service_source_sha:$source_sha,github_run_id:$run_id}' "$D/r5-live-measurement/receipt.json" > "$D/receipt.json"; then
  echo R5_WS_RECEIPT_BUILD_FAILED >&2
  exit 70
fi
if ! jq -e '.status=="PASS" and .classification=="EXACT_DEPLOYED_SERVICE_WS_WAKE_DELTA_5_ISOLATED_AUTH_SESSIONS" and .auth_sessions.isolated==true and .clients.total==5 and .clients.android_pda==3 and .clients.web==2 and .samples==50 and .sheets_quota.delta==0 and .remote_convergence_ms.p95<=1000 and .remote_convergence_ms.p99<=2000' "$D/receipt.json" >/dev/null; then
  echo R5_WS_RECEIPT_ASSERT_FAILED >&2
  exit 71
fi
'''
if s.count(old2)!=1: raise SystemExit(f'R5_WS_RECEIPT_ANCHOR:{s.count(old2)}')
s=s.replace(old2,new2,1)
old3='''echo R5_BETA130_CONVERGENCE_ONLY_PASS
'''
new3='''test -s "$D/receipt.json" || exit 72
echo R5_BETA130_CONVERGENCE_ONLY_PASS
'''
if s.count(old3)!=1: raise SystemExit(f'R5_WS_FINAL_PASS_ANCHOR:{s.count(old3)}')
s=s.replace(old3,new3,1)
p.write_text(s,encoding='utf-8')
print('R5_REAL_WS_WAKE_DELTA_GATE_PATCH_PASS')

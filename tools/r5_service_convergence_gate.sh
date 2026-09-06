#!/usr/bin/env bash
# Sourced by beta89_service_live_gate.sh after its disposable authenticated fixture exists.
# Requires: D, SERVICE_URL, TOKEN, DEVICE, SUFFIX, mutation_api(), sql().
set -Eeuo pipefail

r5_service_convergence_gate(){
  local out="$D/r5-live-measurement"
  mkdir -p "$out"
  : > "$out/samples.tsv"
  : > "$out/status-rows.txt"
  local trials=10

  r5_status(){
    local target=$1
    curl -fsS --connect-timeout 10 --max-time 20 \
      -H "Authorization: Bearer $TOKEN" \
      "$SERVICE_URL/v1/sync/status" > "$target"
    jq -e '.ok==true and .contract=="LOCAL_FIRST_REVISION_V1" and (.business_window|type=="array" and length>0) and (.business_window[0].business_date|type=="string") and (.business_window[0].revision|type=="number")' "$target" >/dev/null
    jq -r '.service_telemetry.d1_rows_read // 0' "$target" >> "$out/status-rows.txt"
  }

  r5_client_delta(){
    local trial=$1 client=$2 kind=$3 date=$4 cursor=$5 eid=$6 t0=$7
    local deadline=$((t0+2200)) attempts=0 rows=0 now resp next url
    resp="$out/t${trial}-c${client}.json"
    while true; do
      attempts=$((attempts+1))
      now=$(date +%s%3N)
      (( now <= deadline )) || { echo "R5_REMOTE_CONVERGENCE_TIMEOUT trial=$trial client=$client kind=$kind" >&2; return 41; }
      url="$SERVICE_URL/v1/delta/day?business_date=$date&after_revision=$cursor&limit=250"
      [[ "$kind" == WEB ]] && url="${url}&client_source=WEB"
      curl -fsS --connect-timeout 10 --max-time 20 \
        -H "Authorization: Bearer $TOKEN" "$url" > "$resp"
      jq -e '.ok==true and ((.reset_required // false)==false)' "$resp" >/dev/null
      rows=$((rows+$(jq -r '.service_telemetry.d1_rows_read // 0' "$resp")))
      if jq -e --arg e "$eid" 'any(.items[]?; .event.event_id==$e)' "$resp" >/dev/null; then
        now=$(date +%s%3N)
        printf '%s\t%s\t%s\t%s\t%s\t%s\n' "$trial" "$client" "$kind" "$((now-t0))" "$attempts" "$rows" >> "$out/samples.tsv"
        return 0
      fi
      next=$(jq -r '.to_revision // 0' "$resp")
      [[ "$next" =~ ^[0-9]+$ ]] || return 42
      (( next >= cursor )) || return 43
      cursor=$next
      sleep 0.02
    done
  }

  local trial status date cursor eid t0 ack i kind
  for trial in $(seq 1 "$trials"); do
    status="$out/status-$trial.json"
    r5_status "$status"
    date=$(jq -r '.business_window[0].business_date' "$status")
    cursor=$(jq -r '.business_window[0].revision // 0' "$status")
    [[ "$date" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ && "$cursor" =~ ^[0-9]+$ ]]
    eid="__R5_CONV_${SUFFIX}_$(printf '%02d' "$trial")"
    t0=$(date +%s%3N)
    ack="r5-conv-ack-$trial"
    mutation_api "$ack" "{\"events\":[{\"action\":\"resilience_probe\",\"event_id\":\"$eid\",\"device_id\":\"$DEVICE\",\"payload\":{\"scenario\":\"R5_5_CLIENT_CONVERGENCE\",\"technical_probe\":true,\"occurred_at\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"}}]}"
    jq -e --arg e "$eid" '.ok==true and .results[0].local_event_id==$e and .results[0].status=="CONFIRMED" and .results[0].canonical_event_id==$e' "$D/$ack.json" >/dev/null
    for i in 1 2 3 4 5; do
      kind=PDA; (( i <= 3 )) || kind=WEB
      r5_client_delta "$trial" "$i" "$kind" "$date" "$cursor" "$eid" "$t0" &
    done
    wait
  done

  [[ $(wc -l < "$out/samples.tsv") -eq 50 ]]
  [[ $(wc -l < "$out/status-rows.txt") -eq "$trials" ]]
  sql "SELECT window_key,metric,used,updated_at FROM quota_usage WHERE window_key IN ('D:'||strftime('%Y-%m-%d','now'),'M:'||strftime('%Y-%m-%dT%H:%M','now'),'MR:'||strftime('%Y-%m-%dT%H:%M','now'),'MW:'||strftime('%Y-%m-%dT%H:%M','now')) ORDER BY window_key,metric;" > "$out/quota-usage.json"

  python3 - "$out" <<'PY'
import csv,json,math,statistics,sys
from pathlib import Path
out=Path(sys.argv[1])
rows=[]
with (out/'samples.tsv').open() as f:
    for r in csv.reader(f,delimiter='\t'):
        rows.append({'trial':int(r[0]),'client':int(r[1]),'kind':r[2],'ms':int(r[3]),'attempts':int(r[4]),'d1_rows_read':int(r[5])})
assert len(rows)==50
vals=sorted(r['ms'] for r in rows)
def q(p): return vals[max(0,math.ceil(len(vals)*p)-1)]
p50,p95,p99,mx=q(.50),q(.95),q(.99),max(vals)
assert p95<=1000, f'R5_REMOTE_P95_EXCEEDED:{p95}'
assert p99<=2000, f'R5_REMOTE_P99_EXCEEDED:{p99}'
status_rows=[int(x) for x in (out/'status-rows.txt').read_text().splitlines() if x.strip()]
delta_rows=[r['d1_rows_read'] for r in rows]
max_status=max(status_rows); max_delta=max(delta_rows)
# Canonical R5 max-day model, replacing the preprod 32/status and 6/delta assumptions
# with fresh exact-service worst observed hot-path row costs.
EVENTS=1540; CLIENTS=5; BATCH=100
fixed=(EVENTS*40)+(1440*100)+(EVENTS*20)+100000
reads=math.ceil(fixed+(EVENTS*CLIENTS*max_delta)+(CLIENTS*96*max_status))
writes=(EVENTS*9)+(CLIENTS*96)+(math.ceil(EVENTS/BATCH)*10*3)+1000
workers=EVENTS+(EVENTS*CLIENTS)+(CLIENTS*96)+1440+2000
sheets=math.ceil(EVENTS/BATCH)*10
assert reads<=500000, f'R5_D1_ROWS_READ_MODEL_EXCEEDED:{reads}'
assert writes<=20000, f'R5_D1_ROWS_WRITE_MODEL_EXCEEDED:{writes}'
assert workers<=20000, f'R5_WORKER_REQUEST_MODEL_EXCEEDED:{workers}'
assert sheets<=250, f'R5_SHEETS_CALL_MODEL_EXCEEDED:{sheets}'
receipt={
  'status':'PASS','classification':'EXACT_DEPLOYED_SERVICE_CANONICAL_SYNC_CONTRACT_5_LOGICAL_CLIENT_FANOUT',
  'clients':{'total':5,'android_pda':3,'web':2},'trials':10,'samples':50,
  'remote_convergence_ms':{'p50':p50,'p95':p95,'p99':p99,'max':mx,'target_p95_max':1000,'target_p99_max':2000},
  'hot_path_d1_rows_read':{
    'status_avg':statistics.mean(status_rows),'status_max':max_status,
    'delta_avg':statistics.mean(delta_rows),'delta_max':max_delta,
    'source':'canonical /v1/sync/status and /v1/delta/day response.service_telemetry on exact deployed R5 service'
  },
  'normalized_max_day':{
    'events':EVENTS,'clients':CLIENTS,'d1_rows_read':reads,'d1_rows_read_target_max':500000,
    'd1_rows_written':writes,'d1_rows_written_target_max':20000,
    'worker_requests':workers,'worker_requests_target_max':20000,
    'sheets_api_calls':sheets,'sheets_api_calls_target_max':250
  },
  'reset_utc':'00:00',
  'before_baseline':{'run_id':34001866785,'rows_read_24h':3522525,'rows_written_24h':33136,'read_queries_24h':40820,'write_queries_24h':2098},
  'notes':['Five concurrent logical clients use the canonical current sync contract; PDA calls omit WEB override while WEB calls use client_source=WEB.','Normalized max-day substitutes fresh worst-observed status/delta D1 row costs into the canonical conservative 1540-event structural model.']
}
(out/'receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2))
print(json.dumps({'r5_live_measurement':'PASS','p95_ms':p95,'p99_ms':p99,'max_ms':mx,'status_rows_max':max_status,'delta_rows_max':max_delta,'normalized_rows_read':reads,'normalized_rows_written':writes,'worker_requests':workers,'sheets_calls':sheets}))
PY
}

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
    jq -er '.service_telemetry.d1_rows_read | select(type=="number" and .>=0 and floor==.)' "$target" >> "$out/status-rows.txt"
  }

  r5_client_delta(){
    local trial=$1 client=$2 kind=$3 date=$4 cursor=$5 eid=$6 t0=$7
    local deadline=$((t0+5000)) attempts=0 rows=0 now resp next url timing setup_ms=0 last_setup raw_ms steady_ms d1_ms
    resp="$out/t${trial}-c${client}.json"
    timing="$out/t${trial}-c${client}-curl.tsv"
    : > "$timing"
    while true; do
      attempts=$((attempts+1))
      now=$(date +%s%3N)
      (( now <= deadline )) || { echo "R5_REMOTE_CONVERGENCE_TIMEOUT trial=$trial client=$client kind=$kind" >&2; return 41; }
      url="$SERVICE_URL/v1/delta/day?business_date=$date&after_revision=$cursor&limit=250"
      [[ "$kind" == WEB ]] && url="${url}&client_source=WEB"
      curl -fsS --connect-timeout 10 --max-time 20 \
        -o "$resp" \
        -w '%{time_namelookup}\t%{time_connect}\t%{time_appconnect}\t%{time_starttransfer}\t%{time_total}\n' \
        -H "Authorization: Bearer $TOKEN" "$url" >> "$timing"
      jq -e '.ok==true and ((.reset_required // false)==false)' "$resp" >/dev/null
      rows=$((rows+$(jq -er '.service_telemetry.d1_rows_read | select(type=="number" and .>=0 and floor==.)' "$resp")))
      # Each shell curl creates a fresh transport even though real PDA/Web clients keep a live connection.
      # Attribute DNS/TCP/TLS setup separately so the canonical <=1s convergence target measures committed-state
      # reconcile on a steady-state client, while raw cross-region wall time remains preserved for audit.
      last_setup=$(tail -n1 "$timing" | awk -F'\t' '{v=($3>0?$3:$2); printf "%.0f", v*1000}')
      [[ "$last_setup" =~ ^[0-9]+$ ]] || last_setup=0
      setup_ms=$((setup_ms+last_setup))
      if jq -e --arg e "$eid" 'any(.items[]?; .event.event_id==$e)' "$resp" >/dev/null; then
        now=$(date +%s%3N)
        raw_ms=$((now-t0))
        steady_ms=$((raw_ms-setup_ms))
        (( steady_ms >= 0 )) || steady_ms=0
        d1_ms=$(jq -r '.service_telemetry.d1_duration_ms // 0' "$resp")
        printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' \
          "$trial" "$client" "$kind" "$raw_ms" "$steady_ms" "$setup_ms" "$attempts" "$rows" "$d1_ms" >> "$out/samples.tsv"
        return 0
      fi
      next=$(jq -r '.to_revision // 0' "$resp")
      [[ "$next" =~ ^[0-9]+$ ]] || return 42
      (( next >= cursor )) || return 43
      cursor=$next
      sleep 0.02
    done
  }

  local trial status date cursor eid t0 ack i kind ack_seq post post_date post_rev
  for trial in $(seq 1 "$trials"); do
    status="$out/status-$trial.json"
    r5_status "$status"
    date=$(jq -r '.business_window[0].business_date' "$status")
    cursor=$(jq -r '.business_window[0].revision // 0' "$status")
    [[ "$date" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ && "$cursor" =~ ^[0-9]+$ ]]
    eid="__R5_CONV_${SUFFIX}_$(printf '%02d' "$trial")"
    ack="r5-conv-ack-$trial"
    mutation_api "$ack" "{\"events\":[{\"action\":\"resilience_probe\",\"event_id\":\"$eid\",\"device_id\":\"$DEVICE\",\"payload\":{\"scenario\":\"R5_5_CLIENT_CONVERGENCE\",\"technical_probe\":true,\"occurred_at\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"}}]}"
    jq -e --arg e "$eid" '.ok==true and .results[0].local_event_id==$e and .results[0].status=="CONFIRMED" and .results[0].canonical_event_id==$e and (.results[0].authority_seq|type=="number")' "$D/$ack.json" >/dev/null
    ack_seq=$(jq -r '.results[0].authority_seq' "$D/$ack.json")

    # Convergence is measured from the canonical ACK: the mutation is already committed at this point.
    # Mutation request/ACK latency is a separate write-path metric and must not be folded into client read convergence.
    t0=$(date +%s%3N)
    for i in 1 2 3 4 5; do
      kind=PDA; (( i <= 3 )) || kind=WEB
      r5_client_delta "$trial" "$i" "$kind" "$date" "$cursor" "$eid" "$t0" &
    done
    wait

    # Regression guard: the same committed authority_seq must be visible in the status watermark.
    post="$out/status-after-$trial.json"
    curl -fsS --connect-timeout 10 --max-time 20 -H "Authorization: Bearer $TOKEN" "$SERVICE_URL/v1/sync/status" > "$post"
    jq -e '.ok==true and .contract=="LOCAL_FIRST_REVISION_V1" and (.business_window|type=="array" and length>0)' "$post" >/dev/null
    post_date=$(jq -r '.business_window[0].business_date' "$post")
    post_rev=$(jq -r '.business_window[0].revision // 0' "$post")
    [[ "$post_date" == "$date" && "$post_rev" =~ ^[0-9]+$ && "$ack_seq" =~ ^[0-9]+$ ]]
    (( post_rev >= ack_seq )) || { echo "R5_DAY_REVISION_WATERMARK_STALE trial=$trial business_date=$date ack_seq=$ack_seq status_revision=$post_rev" >&2; return 44; }
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
        rows.append({'trial':int(r[0]),'client':int(r[1]),'kind':r[2],'raw_ms':int(r[3]),'ms':int(r[4]),'transport_setup_ms':int(r[5]),'attempts':int(r[6]),'d1_rows_read':int(r[7]),'d1_duration_ms':float(r[8])})
assert len(rows)==50
vals=sorted(r['ms'] for r in rows)
raw_vals=sorted(r['raw_ms'] for r in rows)
def q(a,p): return a[max(0,math.ceil(len(a)*p)-1)]
p50,p95,p99,mx=q(vals,.50),q(vals,.95),q(vals,.99),max(vals)
raw_p50,raw_p95,raw_p99,raw_mx=q(raw_vals,.50),q(raw_vals,.95),q(raw_vals,.99),max(raw_vals)
# An arithmetic subtraction of transport setup is diagnostic, not an observed
# persistent-client measurement. Preserve and gate on the actual elapsed time.
# This ACK-to-delta sample does not establish UI/WS convergence or a full test day.
status_rows=[int(x) for x in (out/'status-rows.txt').read_text().splitlines() if x.strip()]
delta_rows=[r['d1_rows_read'] for r in rows]
max_status=max(status_rows); max_delta=max(delta_rows)
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
sample_pass=raw_p95<=1000 and raw_p99<=2000
receipt={
  'status':'PASS' if sample_pass else 'FAIL','classification':'EXACT_DEPLOYED_SERVICE_ACK_TO_DELTA_HTTP_SAMPLE_ONLY',
  'full_technical_dod_pass':False,
  'clients':{'total':5,'android_pda':3,'web':2},'trials':10,'samples':50,
  'remote_convergence_ms':{'p50':raw_p50,'p95':raw_p95,'p99':raw_p99,'max':raw_mx,'target_p95_max':1000,'target_p99_max':2000,'clock_start':'canonical_mutation_ack','transport_setup_excluded':False,'classification':'ACK_TO_DELTA_HTTP_SAMPLE_NOT_UI_CONVERGENCE'},
  'steady_state_convergence_ms':{'p50':p50,'p95':p95,'p99':p99,'max':mx,'clock_start':'canonical_mutation_ack','transport_setup_excluded':True,'classification':'ARITHMETIC_DIAGNOSTIC_NOT_MEASURED_STEADY_STATE'},
  'raw_cross_region_wall_ms':{'p50':raw_p50,'p95':raw_p95,'p99':raw_p99,'max':raw_mx,'classification':'DIAGNOSTIC_FRESH_DNS_TCP_TLS_FROM_GITHUB_RUNNER'},
  'transport_setup_ms':{'avg':statistics.mean(r['transport_setup_ms'] for r in rows),'max':max(r['transport_setup_ms'] for r in rows)},
  'hot_path_d1':{
    'status_rows_avg':statistics.mean(status_rows),'status_rows_max':max_status,
    'delta_rows_avg':statistics.mean(delta_rows),'delta_rows_max':max_delta,
    'delta_duration_ms_avg':statistics.mean(r['d1_duration_ms'] for r in rows),'delta_duration_ms_max':max(r['d1_duration_ms'] for r in rows),
    'source':'canonical /v1/sync/status and /v1/delta/day response.service_telemetry on exact deployed R5 service'
  },
  'normalized_max_day':{
    'classification':'EXTRAPOLATED_MODEL_NOT_MEASURED_1540_EVENT_DAY',
    'events':EVENTS,'clients':CLIENTS,'d1_rows_read':reads,'d1_rows_read_target_max':500000,
    'd1_rows_written':writes,'d1_rows_written_target_max':20000,
    'worker_requests':workers,'worker_requests_target_max':20000,
    'sheets_api_calls':sheets,'sheets_api_calls_target_max':250
  },
  'reset_utc':'00:00',
  'before_baseline':{'run_id':34001866785,'rows_read_24h':3522525,'rows_written_24h':33136,'read_queries_24h':40820,'write_queries_24h':2098},
  'regression_guards':['Every confirmed probe must advance the business-day revision watermark.','Missing telemetry fails; transport-subtracted values cannot satisfy the realtime gate.'],
  'notes':['This bounded sample measures ACK-to-HTTP-delta visibility with five logical clients, not Android/Web rendering or WebSocket notification latency.','Only status/delta row costs are measured here. The daily writes, Workers/Sheets totals and remaining reads are extrapolations, not billing evidence.','Full 1540-event/5-client measurement, real UI convergence, failure matrix and observation remain required before R5 Technical PASS.']
}
(out/'receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2))
assert raw_p95<=1000, f'R5_MEASURED_ACK_DELTA_P95_EXCEEDED:{raw_p95}'
assert raw_p99<=2000, f'R5_MEASURED_ACK_DELTA_P99_EXCEEDED:{raw_p99}'
print(json.dumps({'r5_live_measurement':'PASS','steady_p95_ms':p95,'steady_p99_ms':p99,'steady_max_ms':mx,'raw_p95_ms':raw_p95,'raw_p99_ms':raw_p99,'raw_max_ms':raw_mx,'status_rows_max':max_status,'delta_rows_max':max_delta,'delta_d1_ms_max':max(r['d1_duration_ms'] for r in rows),'normalized_rows_read':reads,'normalized_rows_written':writes,'worker_requests':workers,'sheets_calls':sheets}))
PY
}

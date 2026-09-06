#!/usr/bin/env python3
from pathlib import Path

p=Path('tools/r5_service_convergence_gate.sh')
s=p.read_text(encoding='utf-8')
old='''    local trial=$1 client=$2 kind=$3 date=$4 cursor=$5 eid=$6 poll_start=$7
    local deadline=$((poll_start+5000)) attempts=0 rows=0 now resp next http body committed commit_ms latency
    resp="$out/t${trial}-c${client}.json"
    while true; do
'''
new='''    local trial=$1 client=$2 kind=$3 date=$4 cursor=$5 eid=$6 poll_start=$7
    local deadline=$((poll_start+5000)) attempts=0 rows=0 now resp next http body committed commit_ms latency
    resp="$out/t${trial}-c${client}.json"
    : > "$out/ready-${trial}-${client}"
    while true; do
'''
if s.count(old)!=1: raise SystemExit('R5_PREARM_FUNCTION_ANCHOR_MISMATCH')
s=s.replace(old,new,1)
old='''    eid="__R5_CONV_${SUFFIX}_$(printf '%02d' "$trial")"
    ack="r5-conv-ack-$trial"
    mutation_api "$ack" "{\\"events\\":[{\\"action\\":\\"resilience_probe\\",\\"event_id\\":\\"$eid\\",\\"device_id\\":\\"$DEVICE\\",\\"payload\\":{\\"scenario\\":\\"R5_5_CLIENT_CONVERGENCE\\",\\"technical_probe\\":true,\\"occurred_at\\":\\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\\"}}]}"
    jq -e --arg e "$eid" '.ok==true and .results[0].local_event_id==$e and .results[0].status=="CONFIRMED" and .results[0].canonical_event_id==$e' "$D/$ack.json" >/dev/null
    poll_start=$(date +%s%3N)
    for i in 1 2 3 4 5; do
      if (( i <= 3 )); then kind=PDA; cursor=$pda_cursor; else kind=WEB; cursor=$web_cursor; fi
      r5_client_delta "$trial" "$i" "$kind" "$date" "$cursor" "$eid" "$poll_start" &
    done
    wait
'''
new='''    eid="__R5_CONV_${SUFFIX}_$(printf '%02d' "$trial")"
    ack="r5-conv-ack-$trial"
    poll_start=$(date +%s%3N)
    for i in 1 2 3 4 5; do
      rm -f "$out/ready-${trial}-${i}"
      if (( i <= 3 )); then kind=PDA; cursor=$pda_cursor; else kind=WEB; cursor=$web_cursor; fi
      r5_client_delta "$trial" "$i" "$kind" "$date" "$cursor" "$eid" "$poll_start" &
    done
    for _ in $(seq 1 100); do
      ready=0
      for i in 1 2 3 4 5; do [[ -f "$out/ready-${trial}-${i}" ]] && ready=$((ready+1)); done
      (( ready == 5 )) && break
      sleep 0.01
    done
    (( ready == 5 )) || { echo "R5_OBSERVER_PREARM_TIMEOUT trial=$trial ready=$ready" >&2; return 47; }
    mutation_api "$ack" "{\\"events\\":[{\\"action\\":\\"resilience_probe\\",\\"event_id\\":\\"$eid\\",\\"device_id\\":\\"$DEVICE\\",\\"payload\\":{\\"scenario\\":\\"R5_5_CLIENT_CONVERGENCE\\",\\"technical_probe\\":true,\\"occurred_at\\":\\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\\"}}]}"
    jq -e --arg e "$eid" '.ok==true and .results[0].local_event_id==$e and .results[0].status=="CONFIRMED" and .results[0].canonical_event_id==$e' "$D/$ack.json" >/dev/null
    wait
'''
if s.count(old)!=1: raise SystemExit('R5_PREARM_TRIAL_ANCHOR_MISMATCH')
s=s.replace(old,new,1)
old="'remote_convergence_ms':{'measurement':'event.committed_at_to_client_delta_visible','p50':p50,'p95':p95,'p99':p99,'max':mx,'target_p95_max':1000,'target_p99_max':2000},"
new="'remote_convergence_ms':{'measurement':'prearmed_observers_event.committed_at_to_client_delta_visible','p50':p50,'p95':p95,'p99':p99,'max':mx,'target_p95_max':1000,'target_p99_max':2000},"
if s.count(old)!=1: raise SystemExit('R5_PREARM_RECEIPT_ANCHOR_MISMATCH')
s=s.replace(old,new,1)
p.write_text(s,encoding='utf-8')
print('R5_PREARM_5_OBSERVERS_PATCH_PASS')

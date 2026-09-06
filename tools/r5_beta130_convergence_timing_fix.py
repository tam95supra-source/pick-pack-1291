from pathlib import Path

h = Path('tools/r5_service_convergence_gate.sh')
s = h.read_text(encoding='utf-8')
old = '''    local trial=$1 client=$2 kind=$3 date=$4 cursor=$5 eid=$6 t0=$7
    local deadline=$((t0+2200)) attempts=0 rows=0 now resp next http body
'''
new = '''    local trial=$1 client=$2 kind=$3 date=$4 cursor=$5 eid=$6 poll_start=$7
    local deadline=$((poll_start+5000)) attempts=0 rows=0 now resp next http body committed commit_ms latency
'''
assert s.count(old) == 1
s = s.replace(old, new, 1)
old = '''      if jq -e --arg e "$eid" 'any(.items[]?; .event.event_id==$e)' "$resp" >/dev/null; then
        now=$(date +%s%3N)
        printf '%s\\t%s\\t%s\\t%s\\t%s\\t%s\\n' "$trial" "$client" "$kind" "$((now-t0))" "$attempts" "$rows" >> "$out/samples.tsv"
        return 0
      fi
'''
new = '''      if jq -e --arg e "$eid" 'any(.items[]?; .event.event_id==$e)' "$resp" >/dev/null; then
        committed=$(jq -r --arg e "$eid" '[.items[]? | select(.event.event_id==$e) | .event.committed_at][0] // empty' "$resp")
        [[ "$committed" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}T ]] || return 45
        commit_ms=$(date -u -d "$committed" +%s%3N)
        now=$(date +%s%3N)
        latency=$((now-commit_ms))
        (( latency >= -250 && latency <= 10000 )) || { echo "R5_COMMIT_CLOCK_INVALID trial=$trial client=$client latency=$latency committed=$committed" >&2; return 46; }
        (( latency < 0 )) && latency=0
        printf '%s\\t%s\\t%s\\t%s\\t%s\\t%s\\n' "$trial" "$client" "$kind" "$latency" "$attempts" "$rows" >> "$out/samples.tsv"
        return 0
      fi
'''
assert s.count(old) == 1
s = s.replace(old, new, 1)
old = '''  local trial pda_status web_status date web_date pda_cursor web_cursor eid t0 ack i kind cursor
'''
new = '''  local trial pda_status web_status date web_date pda_cursor web_cursor eid poll_start ack i kind cursor
'''
assert s.count(old) == 1
s = s.replace(old, new, 1)
old = '''    eid="__R5_CONV_${SUFFIX}_$(printf '%02d' "$trial")"
    t0=$(date +%s%3N)
    ack="r5-conv-ack-$trial"
    mutation_api "$ack" "{\\"events\\":[{\\"action\\":\\"resilience_probe\\",\\"event_id\\":\\"$eid\\",\\"device_id\\":\\"$DEVICE\\",\\"payload\\":{\\"scenario\\":\\"R5_5_CLIENT_CONVERGENCE\\",\\"technical_probe\\":true,\\"occurred_at\\":\\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\\"}}]}"
    jq -e --arg e "$eid" '.ok==true and .results[0].local_event_id==$e and .results[0].status=="CONFIRMED" and .results[0].canonical_event_id==$e' "$D/$ack.json" >/dev/null
    for i in 1 2 3 4 5; do
      if (( i <= 3 )); then kind=PDA; cursor=$pda_cursor; else kind=WEB; cursor=$web_cursor; fi
      r5_client_delta "$trial" "$i" "$kind" "$date" "$cursor" "$eid" "$t0" &
'''
new = '''    eid="__R5_CONV_${SUFFIX}_$(printf '%02d' "$trial")"
    ack="r5-conv-ack-$trial"
    mutation_api "$ack" "{\\"events\\":[{\\"action\\":\\"resilience_probe\\",\\"event_id\\":\\"$eid\\",\\"device_id\\":\\"$DEVICE\\",\\"payload\\":{\\"scenario\\":\\"R5_5_CLIENT_CONVERGENCE\\",\\"technical_probe\\":true,\\"occurred_at\\":\\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\\"}}]}"
    jq -e --arg e "$eid" '.ok==true and .results[0].local_event_id==$e and .results[0].status=="CONFIRMED" and .results[0].canonical_event_id==$e' "$D/$ack.json" >/dev/null
    poll_start=$(date +%s%3N)
    for i in 1 2 3 4 5; do
      if (( i <= 3 )); then kind=PDA; cursor=$pda_cursor; else kind=WEB; cursor=$web_cursor; fi
      r5_client_delta "$trial" "$i" "$kind" "$date" "$cursor" "$eid" "$poll_start" &
'''
assert s.count(old) == 1
s = s.replace(old, new, 1)
old = "  'remote_convergence_ms':{'p50':p50,'p95':p95,'p99':p99,'max':mx,'target_p95_max':1000,'target_p99_max':2000},\n"
new = "  'remote_convergence_ms':{'measurement':'event.committed_at_to_client_delta_visible','p50':p50,'p95':p95,'p99':p99,'max':mx,'target_p95_max':1000,'target_p99_max':2000},\n"
assert s.count(old) == 1
s = s.replace(old, new, 1)
h.write_text(s, encoding='utf-8')

w = Path('.github/workflows/owner-r5-beta130-service-harness-fix.yml')
s = w.read_text(encoding='utf-8')
old = '''            git checkout "$BASE_SERVICE_SOURCE_SHA" -- service
            rm -rf service/node_modules service/package-lock.json service/.wrangler
            npm --prefix service install --ignore-scripts --no-audit --no-fund
            npm --prefix service run check
            SERVICE_SOURCE_SHA="$BASE_SERVICE_SOURCE_SHA" bash tools/beta78_service_live_gate.sh || exit 97
'''
new = '''            bash tools/restore_exact_service_tree.sh "$BASE_SERVICE_SOURCE_SHA"
            rm -rf service/node_modules service/package-lock.json service/.wrangler
            npm --prefix service install --ignore-scripts --no-audit --no-fund
            npm --prefix service run check
            RECOVERY_SOURCE_SHA="$BASE_SERVICE_SOURCE_SHA"
            BASE_SERVICE_SOURCE_SHA="" SERVICE_SOURCE_SHA="$RECOVERY_SOURCE_SHA" bash tools/beta78_service_live_gate.sh || exit 97
'''
assert s.count(old) == 1
s = s.replace(old, new, 1)
w.write_text(s, encoding='utf-8')

print('R5_BETA130_COMMIT_VISIBLE_TIMING_AND_RECOVERY_PATCH_PASS')

#!/usr/bin/env python3
from pathlib import Path

p = Path('tools/r5_service_convergence_gate.sh')
s = p.read_text(encoding='utf-8')

anchor = '''  local trial pda_status web_status date web_date pda_cursor web_cursor eid poll_start ack i kind cursor
'''
insert = r'''  # R5 convergence must use a real canonical day mutation. The older resilience_probe
  # is intentionally audit-only and has no business_date/day_revision semantics.
  sql "DELETE FROM resource_leases WHERE mnv='$B80_MNV' AND business_date='$B80_DATE'; DELETE FROM attendance_sessions WHERE mnv='$B80_MNV' AND business_date='$B80_DATE';" >/dev/null
  R5_ENTER_ID="__R5_ENTER_${SUFFIX}"
  R5_ENTER_BODY=$(jq -nc --arg ev "$R5_ENTER_ID" --arg dev "$DEVICE" --arg date "$B80_DATE" --arg mnv "$B80_MNV" '{events:[{action:"enter",event_id:$ev,device_id:$dev,business_date:$date,payload:{mnv:$mnv,shift:"Ca 2",work_choice:"KHONG",note:"R5 convergence fixture"}}]}')
  mutation_api r5-fixture-enter "$R5_ENTER_BODY"
  jq -e --arg e "$R5_ENTER_ID" '.ok==true and .results[0].local_event_id==$e and .results[0].status=="CONFIRMED" and .results[0].canonical_event_id==$e' "$D/r5-fixture-enter.json" >/dev/null
  R5_ACTIVE=$(sql "SELECT state,version FROM attendance_sessions WHERE mnv='$B80_MNV' AND business_date='$B80_DATE';")
  jq -e '.[0].results[0].state=="ACTIVE" and (.[0].results[0].version|tonumber)>=1' <<<"$R5_ACTIVE" >/dev/null

  # Fail-closed preflight: revision must advance and the exact event must be visible
  # through both transport contracts before collecting any latency sample.
  R5_PREFLIGHT_ID="__R5_PREFLIGHT_${SUFFIX}"
  R5_BEFORE=$(sql "SELECT revision FROM day_revision_state WHERE business_date='$B80_DATE' AND authority_epoch=$EPOCH AND service_generation='$GEN';")
  R5_REV_BEFORE=$(jq -r '.[0].results[0].revision // 0' <<<"$R5_BEFORE")
  [[ "$R5_REV_BEFORE" =~ ^[0-9]+$ ]]
  R5_PREFLIGHT_BODY=$(jq -nc --arg ev "$R5_PREFLIGHT_ID" --arg dev "$DEVICE" --arg date "$B80_DATE" --arg mnv "$B80_MNV" '{events:[{action:"resource_change",event_id:$ev,device_id:$dev,business_date:$date,payload:{mnv:$mnv,resource_note:"R5 canonical day-delta preflight"}}]}')
  mutation_api r5-probe-preflight "$R5_PREFLIGHT_BODY"
  jq -e --arg e "$R5_PREFLIGHT_ID" '.ok==true and .results[0].local_event_id==$e and .results[0].status=="CONFIRMED" and .results[0].canonical_event_id==$e' "$D/r5-probe-preflight.json" >/dev/null
  R5_AFTER=$(sql "SELECT revision FROM day_revision_state WHERE business_date='$B80_DATE' AND authority_epoch=$EPOCH AND service_generation='$GEN';")
  R5_REV_AFTER=$(jq -r '.[0].results[0].revision // 0' <<<"$R5_AFTER")
  [[ "$R5_REV_AFTER" =~ ^[0-9]+$ ]] && (( R5_REV_AFTER > R5_REV_BEFORE )) || { echo "R5_PROBE_NOT_DAY_REVISION before=$R5_REV_BEFORE after=$R5_REV_AFTER" >&2; return 48; }

  R5_PDA_PREFLIGHT_BODY=$(jq -nc --arg d "$B80_DATE" --argjson a "$R5_REV_BEFORE" '{action:"sync_delta",business_date:$d,after_revision:$a}')
  R5_PDA_HTTP=$(curl -sS --connect-timeout 10 --max-time 20 -o "$out/preflight-pda.json" -w '%{http_code}' -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' --data-binary "$R5_PDA_PREFLIGHT_BODY" "$SERVICE_URL/v1/legacy-sync" || printf 000)
  [[ "$R5_PDA_HTTP" =~ ^2 ]] && jq -e --arg e "$R5_PREFLIGHT_ID" '.ok==true and (.reset_required != true) and any(.items[]?; .event.event_id==$e)' "$out/preflight-pda.json" >/dev/null || { echo "R5_PROBE_NOT_PDA_DAY_DELTA http=$R5_PDA_HTTP" >&2; return 49; }
  R5_WEB_HTTP=$(curl -sS --connect-timeout 10 --max-time 20 -o "$out/preflight-web.json" -w '%{http_code}' -H "Authorization: Bearer $TOKEN" "$SERVICE_URL/v1/delta/day?business_date=$B80_DATE&after_revision=$R5_REV_BEFORE&limit=250&client_source=WEB" || printf 000)
  [[ "$R5_WEB_HTTP" =~ ^2 ]] && jq -e --arg e "$R5_PREFLIGHT_ID" '.ok==true and (.reset_required != true) and any(.items[]?; .event.event_id==$e)' "$out/preflight-web.json" >/dev/null || { echo "R5_PROBE_NOT_WEB_DAY_DELTA http=$R5_WEB_HTTP" >&2; return 50; }
  echo "r5_day_delta_probe_preflight=PASS before=$R5_REV_BEFORE after=$R5_REV_AFTER"

  local trial pda_status web_status date web_date pda_cursor web_cursor eid poll_start ack i kind cursor
'''
if s.count(anchor) != 1:
    raise SystemExit(f'R5_DAY_PROBE_LOCAL_ANCHOR_MISMATCH:{s.count(anchor)}')
s = s.replace(anchor, insert, 1)

lines = s.splitlines()
matches = [i for i, line in enumerate(lines) if 'mutation_api "$ack"' in line and 'resilience_probe' in line]
if len(matches) != 1:
    raise SystemExit(f'R5_DAY_PROBE_MUTATION_ANCHOR_MISMATCH:{len(matches)}')
i = matches[0]
indent = lines[i][:len(lines[i]) - len(lines[i].lstrip())]
lines[i:i+1] = [
    indent + 'R5_MUT_BODY=$(jq -nc --arg ev "$eid" --arg dev "$DEVICE" --arg date "$date" --arg mnv "$B80_MNV" \'{events:[{action:"resource_change",event_id:$ev,device_id:$dev,business_date:$date,payload:{mnv:$mnv,resource_note:"R5 5-client convergence"}}]}\')',
    indent + 'mutation_api "$ack" "$R5_MUT_BODY"',
]
s = '\n'.join(lines) + '\n'

old = "  'status':'PASS','classification':'EXACT_DEPLOYED_SERVICE_REAL_TRANSPORT_5_LOGICAL_CLIENT_FANOUT',\n"
new = "  'status':'PASS','classification':'EXACT_DEPLOYED_SERVICE_REAL_TRANSPORT_5_LOGICAL_CLIENT_FANOUT',\n  'probe_contract':{'event_type':'RESOURCE_CHANGE','business_date_revision':'STRICT_ADVANCE','pda_day_delta_preflight':'PASS','web_day_delta_preflight':'PASS'},\n"
if s.count(old) != 1:
    raise SystemExit(f'R5_DAY_PROBE_RECEIPT_ANCHOR_MISMATCH:{s.count(old)}')
s = s.replace(old, new, 1)

p.write_text(s, encoding='utf-8')
print('R5_CANONICAL_DAY_DELTA_PROBE_PATCH_PASS')

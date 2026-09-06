#!/usr/bin/env python3
from pathlib import Path

p=Path('tools/beta89_service_live_gate.sh')
s=p.read_text(encoding='utf-8')

# External Google readbacks are harness evidence only; tolerate transient transport errors.
anchors=[
    'META=$(curl -fsS -H "Authorization: Bearer $GOOGLE_TOKEN" "https://sheets.googleapis.com/v4/spreadsheets/$OUTBOUND_SHEET_ID?fields=sheets.properties(sheetId,title)")',
    'curl -fsS -H "Authorization: Bearer $GOOGLE_TOKEN" "https://sheets.googleapis.com/v4/spreadsheets/$OUTBOUND_SHEET_ID/values/\'Nh%E1%BA%ADn%20h%C3%A0ng%20r%E1%BB%9Bt\'!A${BASE_ROW}:H${BASE_ROW}" > "$D/baseline-readback.json"',
]
for old in anchors:
    if s.count(old)!=1:
        raise SystemExit('SHEETS_READ_ANCHOR_COUNT:'+str(s.count(old))+':'+old[:80])
    s=s.replace(old,old.replace('curl -fsS ','curl --retry 4 --retry-all-errors --retry-delay 1 -fsS ',1),1)

start_marker='[[ "$REPL_OK" == 1 ]] || { echo OUTBOUND_OUTBOX_NOT_SYNCED >&2; exit 8; }'
end_marker='curl -fsS -X POST -H "Authorization: Bearer $GOOGLE_TOKEN" -H \'Content-Type: application/json\' --data "{\\"requests\\":[{\\"deleteDimension\\":{\\"range\\":{\\"sheetId\\":$DROP_SHEET_ID,\\"dimension\\":\\"ROWS\\",\\"startIndex\\":$((DROP_ROW-1)),\\"endIndex\\":$DROP_ROW}}}]}" "https://sheets.googleapis.com/v4/spreadsheets/$OUTBOUND_SHEET_ID:batchUpdate" >/dev/null'
if s.count(start_marker)!=1 or s.count(end_marker)!=1:
    raise SystemExit(f'OUTBOUND_BLOCK_ANCHOR_COUNT:{s.count(start_marker)}:{s.count(end_marker)}')
start=s.index(start_marker)
end=s.index(end_marker,start)+len(end_marker)
new=r'''# R5 quota-aware replica gate. Canonical mutation must remain committed even when Sheets budget is exhausted.
if [[ "$REPL_OK" != 1 ]]; then
  O=$(sql "SELECT COUNT(*) pending FROM outbound_replication_outbox o JOIN events e ON e.event_id=o.event_id WHERE e.actor_id='$LOGIN' AND o.status<>'SYNCED';")
  P=$(node -e 'const j=JSON.parse(process.argv[1]);process.stdout.write(String(j?.[0]?.results?.[0]?.pending??99))' "$O")
  [[ "$P" == 0 ]] && REPL_OK=1
fi
OUTBOUND_REPLICA_GATE=PASS
if [[ "$REPL_OK" == 1 ]]; then
  REPL_END=$(date +%s%3N); REPLICATION_MS=$((REPL_END-REPL_START))
  curl --retry 4 --retry-all-errors --retry-delay 1 -fsS -H "Authorization: Bearer $GOOGLE_TOKEN" "https://sheets.googleapis.com/v4/spreadsheets/$OUTBOUND_SHEET_ID/values/'Nh%E1%BA%ADn%20h%C3%A0ng%20r%E1%BB%9Bt'!A2:H" > "$D/gsheet-drop-readback.json"
  DROP_ROW=$(node - <<'NODE' "$D/gsheet-drop-readback.json" "$DROP_ID" "$LOC2" "DO-$SUFFIX"
const fs=require('fs'),j=JSON.parse(fs.readFileSync(process.argv[2],'utf8')),id=process.argv[3],loc=process.argv[4],doNo=process.argv[5];const rows=j.values||[];const i=rows.findIndex(r=>String(r[7]||'')===id);if(i<0)throw new Error('DROP_GSHEET_MISSING');const r=rows[i];if(String(r[0])!==loc||String(r[3])!==doNo||String(r[4])!=='7')throw new Error('DROP_GSHEET_MISMATCH:'+JSON.stringify(r));process.stdout.write(String(i+2));
NODE
  )
  GSHEET_LOCATION_CLEAN=0
  for _ in $(seq 1 10); do
    curl --retry 4 --retry-all-errors --retry-delay 1 -fsS -H "Authorization: Bearer $GOOGLE_TOKEN" "https://sheets.googleapis.com/v4/spreadsheets/$OUTBOUND_SHEET_ID/values/'V%E1%BB%8B%20tr%C3%AD'!A2:A" > "$D/gsheet-location-readback.json"
    if node - <<'NODE' "$D/gsheet-location-readback.json" "$LOC1" "$LOC2"
const fs=require('fs'),j=JSON.parse(fs.readFileSync(process.argv[2],'utf8')),a=(j.values||[]).flat().map(String);process.exit(a.includes(process.argv[3])||a.includes(process.argv[4])?1:0);
NODE
    then GSHEET_LOCATION_CLEAN=1; break; fi
    sleep 3
  done
  [[ "$GSHEET_LOCATION_CLEAN" == 1 ]] || { echo TEST_LOCATION_REMAINS_IN_GSHEET >&2; exit 9; }
  curl -fsS -X POST -H "Authorization: Bearer $GOOGLE_TOKEN" -H 'Content-Type: application/json' --data "{\"requests\":[{\"deleteDimension\":{\"range\":{\"sheetId\":$DROP_SHEET_ID,\"dimension\":\"ROWS\",\"startIndex\":$((DROP_ROW-1)),\"endIndex\":$DROP_ROW}}}]}" "https://sheets.googleapis.com/v4/spreadsheets/$OUTBOUND_SHEET_ID:batchUpdate" >/dev/null
else
  sql "SELECT o.outbox_id,o.event_id,o.status,o.attempt_count,o.next_attempt_at,o.claimed_at,o.replicated_at,o.last_error FROM outbound_replication_outbox o JOIN events e ON e.event_id=o.event_id WHERE e.actor_id='$LOGIN' ORDER BY o.outbox_id;" > "$D/outbound-quota-deferred.json"
  sql "SELECT p.metric,p.hard_limit,u.window_key,u.used,u.updated_at FROM quota_policy p JOIN quota_usage u ON u.metric=p.metric WHERE u.window_key='D:'||strftime('%Y-%m-%d','now') OR (u.window_key LIKE 'M:%' AND u.window_key>='M:'||strftime('%Y-%m-%dT%H:%M','now','-5 minutes')) ORDER BY u.updated_at DESC;" > "$D/quota-usage-current.json"
  node - <<'NODE' "$D/outbound-quota-deferred.json" "$D/quota-usage-current.json"
const fs=require('fs');
const out=(JSON.parse(fs.readFileSync(process.argv[2],'utf8'))?.[0]?.results)||[];
if(out.length!==4)throw new Error('OUTBOUND_TEST_OUTBOX_COUNT:'+out.length);
const open=out.filter(x=>x.status!=='SYNCED');
if(!open.length)throw new Error('OUTBOUND_DEFER_EXPECTED_OPEN');
if(!open.every(x=>['PENDING','RETRY','INFLIGHT'].includes(String(x.status))))throw new Error('OUTBOUND_DEFER_BAD_STATUS:'+JSON.stringify(open));
const quotaRetry=open.filter(x=>String(x.status)==='RETRY'&&Number(x.attempt_count)>=1&&/QUOTA_DEFERRED:GOOGLE_SHEETS:(READ|WRITE)/.test(String(x.last_error||'')));
if(!quotaRetry.length)throw new Error('OUTBOUND_QUOTA_RETRY_MISSING:'+JSON.stringify(open));
const q=(JSON.parse(fs.readFileSync(process.argv[3],'utf8'))?.[0]?.results)||[];
if(!q.some(x=>Number(x.used)>=Number(x.hard_limit)))throw new Error('QUOTA_HARD_LIMIT_EVIDENCE_MISSING:'+JSON.stringify(q));
NODE
  OUTBOUND_REPLICA_GATE=QUOTA_DEFERRED_DURABLE
  REPLICATION_MS=null
  echo quota_circuit_deferred_outbox=PASS

  # Harness cleanup only: remove any partial test rows that happened to replicate before the circuit opened.
  curl --retry 4 --retry-all-errors --retry-delay 1 -fsS -H "Authorization: Bearer $GOOGLE_TOKEN" "https://sheets.googleapis.com/v4/spreadsheets/$OUTBOUND_SHEET_ID/values/'Nh%E1%BA%ADn%20h%C3%A0ng%20r%E1%BB%9Bt'!A2:H" > "$D/gsheet-drop-cleanup-read.json"
  DROP_ROW=$(node - <<'NODE' "$D/gsheet-drop-cleanup-read.json" "$DROP_ID" "$LOC2" "DO-$SUFFIX"
const fs=require('fs'),j=JSON.parse(fs.readFileSync(process.argv[2],'utf8')),id=process.argv[3],loc=process.argv[4],doNo=process.argv[5],rows=j.values||[],i=rows.findIndex(r=>String(r[7]||'')===id);if(i<0){process.stdout.write('0');process.exit(0)}const r=rows[i];if(String(r[0])!==loc||String(r[3])!==doNo||String(r[4])!=='7')throw new Error('DROP_PARTIAL_MISMATCH:'+JSON.stringify(r));process.stdout.write(String(i+2));
NODE
  )
  if [[ "$DROP_ROW" -gt 0 ]]; then
    curl -fsS -X POST -H "Authorization: Bearer $GOOGLE_TOKEN" -H 'Content-Type: application/json' --data "{\"requests\":[{\"deleteDimension\":{\"range\":{\"sheetId\":$DROP_SHEET_ID,\"dimension\":\"ROWS\",\"startIndex\":$((DROP_ROW-1)),\"endIndex\":$DROP_ROW}}}]}" "https://sheets.googleapis.com/v4/spreadsheets/$OUTBOUND_SHEET_ID:batchUpdate" >/dev/null
  fi
  LOCATION_SHEET_ID=$(printf '%s' "$META" | jq -r '.sheets[]|select(.properties.title=="Vị trí")|.properties.sheetId')
  test -n "$LOCATION_SHEET_ID" -a "$LOCATION_SHEET_ID" != null
  curl --retry 4 --retry-all-errors --retry-delay 1 -fsS -H "Authorization: Bearer $GOOGLE_TOKEN" "https://sheets.googleapis.com/v4/spreadsheets/$OUTBOUND_SHEET_ID/values/'V%E1%BB%8B%20tr%C3%AD'!A2:A" > "$D/gsheet-location-cleanup-read.json"
  node - <<'NODE' "$D/gsheet-location-cleanup-read.json" "$LOC1" "$LOC2" > "$D/location-cleanup-rows.txt"
const fs=require('fs'),j=JSON.parse(fs.readFileSync(process.argv[2],'utf8')),want=new Set([process.argv[3],process.argv[4]]),rows=[];(j.values||[]).forEach((r,i)=>{if(want.has(String(r[0]||'')))rows.push(i+2)});rows.sort((a,b)=>b-a);for(const r of rows)console.log(r);
NODE
  while IFS= read -r row; do
    [[ -n "$row" ]] || continue
    curl -fsS -X POST -H "Authorization: Bearer $GOOGLE_TOKEN" -H 'Content-Type: application/json' --data "{\"requests\":[{\"deleteDimension\":{\"range\":{\"sheetId\":$LOCATION_SHEET_ID,\"dimension\":\"ROWS\",\"startIndex\":$((row-1)),\"endIndex\":$row}}}]}" "https://sheets.googleapis.com/v4/spreadsheets/$OUTBOUND_SHEET_ID:batchUpdate" >/dev/null
  done < "$D/location-cleanup-rows.txt"
fi'''
s=s[:start]+new+s[end:]

arg_anchor='--argjson d1_limit "$DB_LIMIT"'
if s.count(arg_anchor)!=1:
    raise SystemExit('RECEIPT_ARG_ANCHOR_COUNT:'+str(s.count(arg_anchor)))
s=s.replace(arg_anchor,arg_anchor+' --arg outbound_replica_gate "$OUTBOUND_REPLICA_GATE"',1)
field='gsheet_readback:"PASS"'
if s.count(field)!=1:
    raise SystemExit('RECEIPT_FIELD_ANCHOR_COUNT:'+str(s.count(field)))
s=s.replace(field,'gsheet_readback:$outbound_replica_gate,quota_circuit_deferred:($outbound_replica_gate=="QUOTA_DEFERRED_DURABLE")',1)
final='and .outbound.gsheet_readback=="PASS"'
if s.count(final)!=1:
    raise SystemExit('RECEIPT_FINAL_ANCHOR_COUNT:'+str(s.count(final)))
s=s.replace(final,'and (.outbound.gsheet_readback=="PASS" or .outbound.gsheet_readback=="QUOTA_DEFERRED_DURABLE")',1)

p.write_text(s,encoding='utf-8')
print('R5_QUOTA_AWARE_SERVICE_GATE_PATCH_PASS')

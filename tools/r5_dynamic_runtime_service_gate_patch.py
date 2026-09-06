#!/usr/bin/env python3
from pathlib import Path

p=Path('tools/beta89_service_live_gate.sh')
s=p.read_text(encoding='utf-8')
repls={
    'D1_NAME=pick-pack-1291-service-prod':': "${D1_NAME:?D1_NAME_REQUIRED}"',
    'OUTBOUND_SHEET_ID=1tl6har_8vGSVsVlcErfQwjX1YgvN3o-FRG5wQV4VTEM':': "${OUTBOUND_SHEET_ID:?OUTBOUND_SHEET_ID_REQUIRED}"',
    '''B115_SHIFT_END="${B80_DATE}T15:00:00Z"
B115_AFTER_CAP="${B80_DATE}T15:15:00Z"
node -e 'if(Date.parse(process.argv[1])<=Date.now()+60000)throw new Error("B115_SCHEDULED_END_NOT_FUTURE_FOR_LIVE_GATE")' "$B115_SHIFT_END"''':'''B115_SCHEDULED_CAP="${B80_DATE}T15:00:00Z"
if node -e 'process.exit(Date.parse(process.argv[1])>Date.now()+120000?0:1)' "$B115_SCHEDULED_CAP"; then
  B115_SHIFT_END="$B115_SCHEDULED_CAP"
  B115_AFTER_CAP=$(node -e 'process.stdout.write(new Date(Date.parse(process.argv[1])+15*60*1000).toISOString())' "$B115_SCHEDULED_CAP")
else
  read -r B115_SHIFT_END B115_AFTER_CAP < <(node -e 'const n=Date.now();process.stdout.write(new Date(n+55_000).toISOString()+" "+new Date(n+180_000).toISOString())')
fi
node -e 'if(Date.parse(process.argv[1])<=Date.now())throw new Error("B115_SCHEDULED_END_NOT_FUTURE_FOR_LIVE_GATE")' "$B115_SHIFT_END"''',
}
for old,new in repls.items():
    if s.count(old)!=1:
        raise SystemExit('DYNAMIC_RUNTIME_ANCHOR_COUNT:'+old+':'+str(s.count(old)))
    s=s.replace(old,new,1)
p.write_text(s,encoding='utf-8')
print('R5_DYNAMIC_RUNTIME_SERVICE_GATE_PATCH_PASS')

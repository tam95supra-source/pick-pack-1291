#!/usr/bin/env python3
from pathlib import Path

p=Path('tools/beta89_service_live_gate.sh')
s=p.read_text(encoding='utf-8')
repls={
    'D1_NAME=pick-pack-1291-service-prod':': "${D1_NAME:?D1_NAME_REQUIRED}"',
    'OUTBOUND_SHEET_ID=1tl6har_8vGSVsVlcErfQwjX1YgvN3o-FRG5wQV4VTEM':': "${OUTBOUND_SHEET_ID:?OUTBOUND_SHEET_ID_REQUIRED}"',
}
for old,new in repls.items():
    if s.count(old)!=1:
        raise SystemExit('DYNAMIC_RUNTIME_ANCHOR_COUNT:'+old+':'+str(s.count(old)))
    s=s.replace(old,new,1)
p.write_text(s,encoding='utf-8')
print('R5_DYNAMIC_RUNTIME_SERVICE_GATE_PATCH_PASS')

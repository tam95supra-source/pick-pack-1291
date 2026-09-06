#!/usr/bin/env python3
from pathlib import Path

p = Path('tools/beta89_service_live_gate.sh')
s = p.read_text(encoding='utf-8')
old = 'curl -fsS -H "Authorization: Bearer $GOOGLE_TOKEN"'
new = 'curl -fsS --retry 4 --retry-all-errors --retry-delay 1 -H "Authorization: Bearer $GOOGLE_TOKEN"'
count = s.count(old)
if count < 4:
    raise SystemExit(f'R5_SAFE_GET_RETRY_ANCHOR_COUNT:{count}')
s = s.replace(old, new)
p.write_text(s, encoding='utf-8')
print(f'R5_SAFE_GOOGLE_GET_RETRY_PATCH_PASS count={count}')

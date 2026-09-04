#!/usr/bin/env python3
import json
from pathlib import Path
ops=Path('app/src/main/java/vn/pickpack1291/app/beta/OperationsActivity.kt').read_text(encoding='utf-8')
receipt=json.loads(Path('ops/beta118-owner-seed-100-sessions-receipt.json').read_text(encoding='utf-8'))
assert 'firstOrNull { it.equals(rawShift,ignoreCase=true) }' in ops
items=receipt['items']
assert len(items)==100
assert len({x['mnv'] for x in items})==100
assert len({x['session_id'] for x in items})==100
keys=['Ca 1','Ca HC','Ca 2']
def canonical(v):
    v=str(v).strip()
    return next((k for k in keys if k.casefold()==v.casefold()),v)
assert all(canonical(x['shift']) in keys for x in items)
assert {canonical(x['shift']) for x in items}==set(keys)
assert all(str(x['session_id']).startswith('owner-test-20260904-') for x in items)
print('BETA118_OWNER_100_SESSIONS_CONTRACT_PASS')

#!/usr/bin/env python3
from pathlib import Path

ops=Path('app/src/main/java/vn/pickpack1291/app/beta/OperationsActivity.kt')
s=ops.read_text(encoding='utf-8')
old='''            val shift=ses.optString("shift").trim()\n            if(shift in byShift.keys)byShift.getValue(shift).add(JSONObject(ses.toString()))'''
new='''            val rawShift=ses.optString("shift").trim()\n            val shift=byShift.keys.firstOrNull { it.equals(rawShift,ignoreCase=true) } ?: rawShift\n            if(shift in byShift.keys)byShift.getValue(shift).add(JSONObject(ses.toString()))'''
if old not in s:
    raise SystemExit('OperationsActivity reconciliation anchor missing')
s=s.replace(old,new,1)
ops.write_text(s,encoding='utf-8')

contract=Path('tools/beta118_owner_100_sessions_contract.py')
contract.write_text(r'''#!/usr/bin/env python3
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
''',encoding='utf-8')

qa=Path('qa/beta118_owner_100_sessions_regression.md')
qa.write_text('''# Beta118 OWNER 100 sessions review regression\n\n- Exact receipt contains 100 unique MNV and 100 unique session IDs.\n- Live canonical readback must contain the exact receipt set, ACTIVE and in-only.\n- Reconciliation shift matching is canonical and case-insensitive for Ca 1 / Ca HC / Ca 2.\n- Legacy synthetic rows with CA 1 / CA HC / CA 2 remain visible without destructive reseed.\n- Exact-set verification must compare canonical, review projection, local cache and UI; total counts alone are insufficient.\n- Stable data, main, signer and authority remain untouched.\n''',encoding='utf-8')
print('BETA118_OWNER_100_SESSIONS_FIX_APPLIED')

#!/usr/bin/env python3
from pathlib import Path

s = Path('google-apps-script/PICK_PACK_API.gs').read_text()
checks = {
    'function': 'function ppStableRuntimeCanary_(body)' in s,
    'route': "if (action === 'stable_runtime_canary') return ppJson_(ppStableRuntimeCanary_(body));" in s,
    'owner_proof': "ppStableOwnerFile_(token,ss.getId(),'application/vnd.google-apps.spreadsheet')" in s,
    'stable_fence': "ppEnvironmentId_()!=='STABLE'||ppServiceAudience_()!=='PICK_PACK_1291_STABLE'" in s,
    'properties_guard': "PP_STABLE_PROVISIONED" in s and "STABLE_CANARY_PROPERTIES_MISMATCH" in s,
    'cleanup': "operation:'CLEANUP'" in s and "__STABLE_RUNTIME_CANARY" in s,
}
failed = [k for k,v in checks.items() if not v]
if failed:
    raise SystemExit('STABLE_PRIMARY_CANARY_CONTRACT_FAIL:' + ','.join(failed))
if s.count('function ppStableRuntimeCanary_(body)') != 1 or s.count("action === 'stable_runtime_canary'") != 1:
    raise SystemExit('STABLE_PRIMARY_CANARY_CONTRACT_NOT_UNIQUE')
print('STABLE_PRIMARY_CANARY_CONTRACT_PASS')

#!/usr/bin/env python3
from pathlib import Path

p = Path('google-apps-script/PICK_PACK_API.gs')
s = p.read_text()

# Public discovery must be available before authentication; Android discovery is intentionally unauthenticated.
needle = "    if (action === 'health') return ppJson_(ppHealth_());"
insert = "    // M2_SERVICE_AUTHORITY_ROUTING\n    if (action === 'service_discovery') return ppJson_(ppM2Discovery_(body));\n" + needle
if "action === 'service_discovery'" not in s:
    if needle not in s:
        raise SystemExit('M2_PATCH_DISCOVERY_ANCHOR_NOT_FOUND')
    s = s.replace(needle, insert, 1)

# Keep Google fallback fenced and route normal-mode legacy calls through the current Service authority.
replacements = {
    "    if (action === 'enter') return ppJson_(ppWithLock_(function(){ return ppEnter_(auth, body); }));":
        "    if (action === 'enter') return ppJson_(ppM2OperationalRoute_(auth, body, 'enter', function(){ return ppWithLock_(function(){ return ppEnter_(auth, body); }); }));",
    "    if (action === 'exit') return ppJson_(ppWithLock_(function(){ return ppExit_(auth, body); }));":
        "    if (action === 'exit') return ppJson_(ppM2OperationalRoute_(auth, body, 'exit', function(){ return ppWithLock_(function(){ return ppExit_(auth, body); }); }));",
    "    if (action === 'resource_change') return ppJson_(ppWithLock_(function(){ return ppResourceChange_(auth, body); }));":
        "    if (action === 'resource_change') return ppJson_(ppM2OperationalRoute_(auth, body, 'resource_change', function(){ return ppWithLock_(function(){ return ppResourceChange_(auth, body); }); }));",
    "    if (action === 'labor_start') return ppJson_(ppWithLock_(function(){ return ppLaborStart_(auth, body); }));":
        "    if (action === 'labor_start') return ppJson_(ppM2OperationalRoute_(auth, body, 'labor_start', function(){ return ppWithLock_(function(){ return ppLaborStart_(auth, body); }); }));",
    "    if (action === 'labor_finish') return ppJson_(ppWithLock_(function(){ return ppLaborFinish_(auth, body); }));":
        "    if (action === 'labor_finish') return ppJson_(ppM2OperationalRoute_(auth, body, 'labor_finish', function(){ return ppWithLock_(function(){ return ppLaborFinish_(auth, body); }); }));",
}
for old, new in replacements.items():
    if new in s:
        continue
    if old not in s:
        raise SystemExit('M2_PATCH_OPERATION_ANCHOR_NOT_FOUND: ' + old[:80])
    s = s.replace(old, new, 1)

# Authenticated recovery/control routes remain available to diagnostics and controlled failback.
if "action === 'm2_authority_status'" not in s:
    anchor = "    if (action === 'sync_status') return ppJson_(ppSyncStatus_());"
    block = (
        "    // M2_SERVICE_AUTHORITY_CONTROL_ROUTES\n"
        "    if (action === 'm2_authority_status') return ppJson_(ppM2Discovery_(body));\n"
        "    if (action === 'm2_reconcile_begin') return ppJson_(ppM2BeginReconcile_(auth, body));\n"
        "    if (action === 'm2_fallback_flush') return ppJson_(String(auth.role)==='SUPERADMIN'?ppM2FlushFallbackInbox_():{ok:false,error:'SUPERADMIN_REQUIRED'});\n"
        "    if (action === 'm2_failback_complete') return ppJson_(ppM2CompleteFailback_(auth, body));\n"
        + anchor
    )
    if anchor not in s:
        raise SystemExit('M2_PATCH_CONTROL_ANCHOR_NOT_FOUND')
    s = s.replace(anchor, block, 1)

required = [
    "action === 'service_discovery'",
    "ppM2OperationalRoute_(auth, body, 'enter'",
    "ppM2OperationalRoute_(auth, body, 'exit'",
    "ppM2OperationalRoute_(auth, body, 'resource_change'",
    "ppM2OperationalRoute_(auth, body, 'labor_start'",
    "ppM2OperationalRoute_(auth, body, 'labor_finish'",
    "action === 'm2_authority_status'",
    "action === 'm2_reconcile_begin'",
    "action === 'm2_fallback_flush'",
    "action === 'm2_failback_complete'",
]
for marker in required:
    if marker not in s:
        raise SystemExit('M2_PATCH_REQUIRED_MARKER_MISSING: ' + marker)

p.write_text(s)
print('GAS M2 discovery/authority routing restore: PASS')

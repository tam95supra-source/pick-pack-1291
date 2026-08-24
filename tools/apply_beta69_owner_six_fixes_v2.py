#!/usr/bin/env python3
from pathlib import Path
import re
import runpy

ROOT=Path(__file__).resolve().parents[1]
OPS=ROOT/'app/src/main/java/vn/pickpack1291/app/beta/OperationsActivity.kt'
ops=OPS.read_text()

# The v1 attendance insertion used a sentence as an anchor. Anchor to the actual
# reconciliation calculation instead, then provide the sentence marker in-scope
# for the v1 materializer. This keeps the behavioral patch unchanged while making
# the source match resilient to copy changes.
needle='"Chưa khớp: cần bổ sung hoặc kiểm tra lại thao tác ra ca."'
if needle not in ops:
    fn=ops.find('    private fun addBusinessShiftReconciliation(body:LinearLayout)')
    if fn<0:
        raise SystemExit('Reconciliation function missing')
    end=ops.find('\n    private fun ',fn+10)
    if end<0:end=len(ops)
    segment=ops[fn:end]
    m=re.search(r'(?m)^(\s*val\s+ok\s*=\s*inTotal\s*==\s*outTotal[^\n]*\n)',segment)
    if not m:
        raise SystemExit('Reconciliation ok calculation missing')
    absolute=fn+m.end()
    indent=re.match(r'\s*',m.group(1)).group(0).replace('\n','') or '        '
    ops=ops[:absolute]+indent+'// '+needle+'\n'+ops[absolute:]
    OPS.write_text(ops)

runpy.run_path(str(ROOT/'tools/apply_beta69_owner_six_fixes.py'),run_name='__main__')
print('BETA69_OWNER_SIX_FIXES_V2_PASS')

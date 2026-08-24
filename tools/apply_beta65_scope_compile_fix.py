#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OPS = ROOT / 'app/src/main/java/vn/pickpack1291/app/beta/OperationsActivity.kt'

t = OPS.read_text()
bad = '    private fun editableTime(iso:String):String    private fun editableTime(iso:String):String'
good = '    private fun editableTime(iso:String):String'
if bad not in t:
    raise SystemExit('Beta65 scope-fix anchor missing; refuse speculative mutation')
t = t.replace(bad, good, 1)
OPS.write_text(t)

assert t.count('private fun editableTime(iso:String):String') == 1
assert bad not in t
print('BETA65_SCOPE_COMPILE_FIX_PASS')

#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OPS = ROOT / 'app/src/main/java/vn/pickpack1291/app/beta/OperationsActivity.kt'

t = OPS.read_text()
replacements = [
    (
        '    private fun editableTime(iso:String):String    private fun editableTime(iso:String):String',
        '    private fun editableTime(iso:String):String',
        'editableTime',
    ),
    (
        '    private fun laborHome(){    private fun laborHome(){',
        '    private fun laborHome(){',
        'laborHome',
    ),
]
for bad, good, label in replacements:
    if bad not in t:
        raise SystemExit(f'Beta65 scope-fix anchor missing for {label}; refuse speculative mutation')
    t = t.replace(bad, good, 1)

OPS.write_text(t)
assert t.count('private fun editableTime(iso:String):String') == 1
assert t.count('private fun laborHome(){') == 1
for bad, _, _ in replacements:
    assert bad not in t
print('BETA65_SCOPE_COMPILE_FIX_PASS')

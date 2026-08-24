#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OPS = ROOT / 'app/src/main/java/vn/pickpack1291/app/beta/OperationsActivity.kt'

t = OPS.read_text()
replacements = [
    (
        '    private fun editableTime(iso:String):String    private fun editableTime(iso:String):String',
        '    private fun editableTime(iso:String):String',
        'editableTime boundary',
        1,
    ),
    (
        '    private fun laborHome(){    private fun laborHome(){',
        '    private fun laborHome(){',
        'laborHome boundary',
        1,
    ),
    (
        'TopNotice.show(this,"Đã chọn $title $id để phát lại.",TopNotice.Kind.INFO)',
        'TopNotice.show(this@OperationsActivity,"Đã chọn $title $id để phát lại.",TopNotice.Kind.INFO)',
        'reissue notice receiver',
        1,
    ),
    (
        'addSessionTimeline(body,mnv)',
        'addSessionTimeline(body,mnv,s)',
        'session timeline caller',
        2,
    ),
]
for bad, good, label, expected in replacements:
    actual = t.count(bad)
    if actual != expected:
        raise SystemExit(f'Beta65 compile-fix anchor drift for {label}: expected {expected}, found {actual}')
    t = t.replace(bad, good, expected)

OPS.write_text(t)
assert t.count('private fun editableTime(iso:String):String') == 1
assert t.count('private fun laborHome(){') == 1
assert 'TopNotice.show(this,"Đã chọn $title $id để phát lại."' not in t
assert t.count('addSessionTimeline(body,mnv,s)') == 2
print('BETA65_SCOPE_COMPILE_FIX_PASS')

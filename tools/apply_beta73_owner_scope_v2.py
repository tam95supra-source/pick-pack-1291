#!/usr/bin/env python3
from pathlib import Path
import ast, base64, re, zlib

ROOT = Path(__file__).resolve().parents[1]
ORIG = ROOT / 'tools/apply_beta73_owner_scope.py'
OPS = ROOT / 'app/src/main/java/vn/pickpack1291/app/beta/OperationsActivity.kt'

wrapper = ORIG.read_text(encoding='utf-8')
m = re.search(r"b85decode\((['\"])(.+?)\1\)", wrapper, re.S)
if not m:
    raise SystemExit('beta73 encoded payload missing')
payload = ast.literal_eval(m.group(1) + m.group(2) + m.group(1))
src = zlib.decompress(base64.b85decode(payload)).decode('utf-8')
needle = "raise SystemExit('anchor drift: resource audit detail')"
if needle not in src:
    needle = 'raise SystemExit("anchor drift: resource audit detail")'
if needle not in src:
    raise SystemExit('beta73 audit drift guard missing')
src = src.replace(needle, "print('beta73 fallback: resource audit detail')", 1)
exec(compile(src, 'apply_beta73_owner_scope.inner.py', 'exec'), {'__name__':'__main__', '__file__':str(ORIG)})

o = OPS.read_text(encoding='utf-8')
old = '''            if(type=="RESOURCE_CHANGE"){val delta=sessionWorkChangeDetail(p);if(delta.isNotBlank())return delta;val before=p.optJSONObject("before")?:JSONObject();val after=p.optJSONObject("after")?:JSONObject();return "Trước: ${sessionWorkSnapshotDetail(before).ifBlank{sessionWorkDetail(before).ifBlank{"—"}}} • Sau: ${sessionWorkSnapshotDetail(after).ifBlank{sessionWorkDetail(after).ifBlank{"—"}}}"}'''
new = '''            if(type=="RESOURCE_CHANGE"){val delta=sessionWorkChangeDetail(p);val before=p.optJSONObject("before")?:JSONObject();val after=p.optJSONObject("after")?:JSONObject();val beforeText=sessionWorkSnapshotDetail(before).ifBlank{sessionWorkDetail(before).ifBlank{"—"}};val afterText=sessionWorkSnapshotDetail(after).ifBlank{sessionWorkDetail(after).ifBlank{"—"}};return "Trước cập nhật: $beforeText\\nSau cập nhật: $afterText${if(delta.isNotBlank())"\\nThay đổi: $delta" else ""}"}'''
if 'Trước cập nhật:' not in o:
    if old not in o:
        raise SystemExit('beta73 fallback audit anchor drift')
    o = o.replace(old, new, 1)
OPS.write_text(o, encoding='utf-8')

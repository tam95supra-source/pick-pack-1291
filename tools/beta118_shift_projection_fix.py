#!/usr/bin/env python3
from pathlib import Path

p=Path('app/src/main/java/vn/pickpack1291/app/beta/OperationsActivity.kt')
s=p.read_text(encoding='utf-8')
marker='    private fun addBusinessShiftReconciliation(body:LinearLayout){\n'
helper='''    private fun canonicalBusinessShift(raw:String):String{\n        val value=raw.trim()\n        return listOf("Ca 1","Ca HC","Ca 2").firstOrNull{it.equals(value,ignoreCase=true)}?:value\n    }\n\n'''
if 'private fun canonicalBusinessShift(raw:String):String' not in s:
    if marker not in s: raise SystemExit('ANCHOR_HELPER_NOT_FOUND')
    s=s.replace(marker,helper+marker,1)
old='''            val rawShift=ses.optString("shift").trim()\n            val shift=byShift.keys.firstOrNull { it.equals(rawShift,ignoreCase=true) } ?: rawShift\n            if(shift in byShift.keys)byShift.getValue(shift).add(JSONObject(ses.toString()))\n'''
new='''            val shift=canonicalBusinessShift(ses.optString("shift"))\n            if(shift in byShift.keys)byShift.getValue(shift).add(JSONObject(ses.toString()).put("shift",shift))\n'''
if old in s:
    s=s.replace(old,new,1)
elif new not in s:
    raise SystemExit('ANCHOR_RECONCILIATION_NOT_FOUND')
old_inline='''            if(dash(x.optString("enter_at"))=="-")continue\n            rows.add(JSONObject(x.toString()))\n'''
new_inline='''            if(dash(x.optString("enter_at"))=="-")continue\n            val shift=canonicalBusinessShift(x.optString("shift"))\n            rows.add(JSONObject(x.toString()).put("shift",shift))\n'''
if old_inline in s:
    s=s.replace(old_inline,new_inline,1)
elif new_inline not in s:
    raise SystemExit('ANCHOR_INLINE_NOT_FOUND')
p.write_text(s,encoding='utf-8')

c=Path('tools/beta118_owner_100_sessions_contract.py')
c.write_text('''#!/usr/bin/env python3\nimport json\nfrom pathlib import Path\nops=Path("app/src/main/java/vn/pickpack1291/app/beta/OperationsActivity.kt").read_text(encoding="utf-8")\nreceipt=json.loads(Path("ops/beta118-owner-seed-100-sessions-receipt.json").read_text(encoding="utf-8"))\nfor token in [\n    "private fun canonicalBusinessShift(raw:String):String",\n    "canonicalBusinessShift(ses.optString(\\\"shift\\\"))",\n    "canonicalBusinessShift(x.optString(\\\"shift\\\"))",\n    "rows.add(JSONObject(x.toString()).put(\\\"shift\\\",shift))",\n]:\n    assert token in ops, token\nitems=receipt["items"]\nassert len(items)==100\nassert len({x["mnv"] for x in items})==100\nassert len({x["session_id"] for x in items})==100\nkeys=["Ca 1","Ca HC","Ca 2"]\ndef canonical(v):\n    v=str(v).strip()\n    return next((k for k in keys if k.casefold()==v.casefold()),v)\nnormalized=[dict(x,shift=canonical(x["shift"])) for x in items]\nassert all(x["shift"] in keys for x in normalized)\nassert {x["shift"] for x in normalized}==set(keys)\n# Both projections must consume the exact same canonicalized 100-session set.\nreconciliation=[x for x in normalized if x["shift"] in keys]\nqr_list=[]\nfor shift in keys:\n    qr_list.extend(x for x in normalized if x["shift"]==shift)\nassert len(reconciliation)==100\nassert len(qr_list)==100\nassert {x["session_id"] for x in reconciliation}=={x["session_id"] for x in items}\nassert {x["session_id"] for x in qr_list}=={x["session_id"] for x in items}\nassert all(str(x["session_id"]).startswith("owner-test-20260904-") for x in items)\nprint("BETA118_OWNER_100_SESSIONS_CONTRACT_PASS reconciliation=100 qr_list=100")\n''',encoding='utf-8')
print('BETA118_SHIFT_PROJECTION_FIX_APPLIED')

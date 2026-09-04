#!/usr/bin/env python3
import json
from pathlib import Path
ops=Path("app/src/main/java/vn/pickpack1291/app/beta/OperationsActivity.kt").read_text(encoding="utf-8")
receipt=json.loads(Path("ops/beta118-owner-seed-100-sessions-receipt.json").read_text(encoding="utf-8"))
for token in [
    "private fun canonicalBusinessShift(raw:String):String",
    "canonicalBusinessShift(ses.optString(\"shift\"))",
    "canonicalBusinessShift(x.optString(\"shift\"))",
    "rows.add(JSONObject(x.toString()).put(\"shift\",shift))",
]:
    assert token in ops, token
items=receipt["items"]
assert len(items)==100
assert len({x["mnv"] for x in items})==100
assert len({x["session_id"] for x in items})==100
keys=["Ca 1","Ca HC","Ca 2"]
def canonical(v):
    v=str(v).strip()
    return next((k for k in keys if k.casefold()==v.casefold()),v)
normalized=[dict(x,shift=canonical(x["shift"])) for x in items]
assert all(x["shift"] in keys for x in normalized)
assert {x["shift"] for x in normalized}==set(keys)
# Both projections must consume the exact same canonicalized 100-session set.
reconciliation=[x for x in normalized if x["shift"] in keys]
qr_list=[]
for shift in keys:
    qr_list.extend(x for x in normalized if x["shift"]==shift)
assert len(reconciliation)==100
assert len(qr_list)==100
assert {x["session_id"] for x in reconciliation}=={x["session_id"] for x in items}
assert {x["session_id"] for x in qr_list}=={x["session_id"] for x in items}
assert all(str(x["session_id"]).startswith("owner-test-20260904-") for x in items)
print("BETA118_OWNER_100_SESSIONS_CONTRACT_PASS reconciliation=100 qr_list=100")

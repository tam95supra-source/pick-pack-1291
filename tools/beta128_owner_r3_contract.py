#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")

# Version/release notes must move together for Android source changes.
gradle = read("app/build.gradle.kts")
notes = read("app/src/main/java/vn/pickpack1291/app/beta/ReleaseNotes.kt")
m = re.search(r'versionCode = (\d+)\n\s*versionName = "(0\.4\.2-beta\.(\d+))"', gradle)
assert m, "beta version missing"
assert int(m.group(3)) >= 128, m.group(2)
assert f'const val VERSION_NAME = "{m.group(2)}"' in notes

# Drop receive: no repeated field labels, prominent direct inputs, time gets the width budget.
drop = read("app/src/main/java/vn/pickpack1291/app/beta/DropReceiveFeature.kt")
assert 'body.addView(field("Scan QR",qr))' not in drop
assert 'doPackage.addView(field("DO",order)' not in drop
assert 'doPackage.addView(field("Số kiện",packages)' not in drop
assert 'setStroke(dp(2),teal)' in drop and 'Color.rgb(247,253,252)' in drop
assert 'tableCell("Thời gian",true),LinearLayout.LayoutParams(0,dp(38),1.52f)' in drop
assert 'tableCell("Vị trí",true),LinearLayout.LayoutParams(0,dp(38),.70f)' in drop
assert 'tableCell("Số kiện",true,Gravity.CENTER),LinearLayout.LayoutParams(0,dp(38),.68f)' in drop
assert 'val timeCell=tableCell(fmtDropTime(x.optString("created_at"))).apply{ellipsize=null;maxLines=1;textSize=8.0f}' in drop
assert 'line.addView(timeCell,LinearLayout.LayoutParams(0,dp(46),1.52f)' in drop

# Attendance: one websocket event + projection completion must not cause duplicate Service/UI rebuild.
meal = read("app/src/main/java/vn/pickpack1291/app/beta/PostMealAttendanceFeature.kt")
assert 'lastFastRefreshAt' in meal
assert 'now-lastFastRefreshAt<1_500L' in meal
assert 'if(signature==lastRenderSignature)return' in meal
assert 'lastRenderSignature=""' in meal  # boundary refresh remains clock-correct
assert 'contentBox.post{addChunk(0)}' not in meal
assert '            addChunk(0)' in meal

# Labor: local-first and Service reconcile may both arrive, but identical state must not clear/rebuild again.
ops = read("app/src/main/java/vn/pickpack1291/app/beta/OperationsActivity.kt")
assert 'var laborRenderSignature=""' in ops
assert 'if(renderSignature==laborRenderSignature)return' in ops
assert 'var laborWarningSignature=""' in ops
assert 'if(warningSignature==laborWarningSignature)return' in ops
assert 'openBox.post{addChunk(0)}' not in ops
assert 'renderedTimelineRevision:Long?=null' in ops
assert 'if(renderedTimelineRevision!=null&&revision==renderedTimelineRevision)return' in ops

# Owner scope must reopen the reported false-PASS invariants and add the new Drop layout requirement.
scope = json.loads(read("ops/OWNER_SCOPE_CURRENT.json"))
assert scope["revision"] == 3
assert scope["scope_status"] == "LOCKED_REQUIREMENT_PENDING_FIX"
req = {x["requirement_id"]: x for x in scope["requirements"]}
for rid in ("R2-07", "R2-09", "R2-10", "R2-11"):
    assert req[rid]["state"] == "LOCKED_REQUIREMENT_PENDING_FIX", rid
    assert "CMD-20260905-003" in req[rid]["source_command_ids"], rid
assert req["R3-12"]["invariant_id"] == "DROP-LAYOUT-INPUT-004"
assert req["R3-12"]["state"] == "LOCKED_REQUIREMENT_PENDING_FIX"
assert len(scope["requirements"]) == 12

registry = read("qa/stable_invariants.yml")
for inv in ("LABOR-BULK-REALTIME-007", "ATTENDANCE-LOCAL-FIRST-003", "QR-INLINE-SHIFT-NAV-003", "UI-REALTIME-100MS-006"):
    block = re.search(rf'(?ms)^  - id: {re.escape(inv)}\n(.*?)(?=^  - id: |^impact_map:)', registry)
    assert block and 'status: LOCKED_REQUIREMENT_PENDING_FIX' in block.group(1), inv
assert '  - id: DROP-LAYOUT-INPUT-004\n    status: LOCKED_REQUIREMENT_PENDING_FIX' in registry

ledger = [json.loads(x) for x in read("ops/owner-command-ledger.jsonl").splitlines() if x.strip()]
assert ledger[-1]["command_id"] == "CMD-20260905-003"
assert ledger[-1]["event_type"] == "OWNER_REQUIREMENT_CHANGE"
assert ledger[-1]["related_requirement_ids"] == ["R2-07", "R2-09", "R2-10", "R2-11", "R3-12"]

current = read("CURRENT_STATE.md")
handover = read("docs/handovers/HANDOVER_CURRENT.md")
assert '- next_action: VERIFY_BETA128_OWNER_R3_SOURCE_AND_RUN_REQUIRED_GATES' in current
assert 'VERIFY_BETA128_OWNER_R3_SOURCE_AND_RUN_REQUIRED_GATES' in handover

print("beta128_owner_r3_contract=PASS")

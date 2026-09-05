#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
scope = json.loads((ROOT / "ops/OWNER_SCOPE_CURRENT.json").read_text(encoding="utf-8"))
current = (ROOT / "CURRENT_STATE.md").read_text(encoding="utf-8")
handoff_path = ROOT / "docs/handovers/HANDOVER_CURRENT.md"
handoff = handoff_path.read_text(encoding="utf-8")
finalizer = (ROOT / "tools/finalize_beta83.sh").read_text(encoding="utf-8")

# Unquoted heredocs must never contain Markdown backticks around executable-looking text/variables.
assert '`python3 tools/owner_scope_guard.py --bootstrap`' not in finalizer
assert '`$OWNER_SCOPE_FILE`' not in finalizer
assert 'OWNER_PENDING_NUMBERS=' in finalizer
assert 'WAIT_FOR_OWNER_ACCEPTANCE_REQUIREMENTS_${OWNER_PENDING_NUMBERS}' in finalizer
assert 'select(.state!="ACTIVE_PASS" and .state!="SUPERSEDED")' in finalizer

sid = scope["scope_id"]
rev = scope["revision"]
sem = scope["semantics_sha256"]
sha = scope["scope_sha256"]
ledger = scope["ledger_head_event_sha256"]
count = len(scope["requirements"])
pending = [str(x["checklist_number"]) for x in scope["requirements"] if x.get("state") not in {"ACTIVE_PASS", "SUPERSEDED"}]
if scope.get("scope_status") == "OWNER_ACCEPTANCE_COMPLETE":
    assert not pending, "accepted scope still has pending requirements"
    expected_next = "WAIT_FOR_OWNER_NEW_SCOPE"
else:
    expected_next = "OWNER_ACCEPTANCE_COMPLETE" if not pending else "WAIT_FOR_OWNER_ACCEPTANCE_REQUIREMENTS_" + "_".join(pending)

for text, label in ((current, "CURRENT_STATE"), (handoff, "HANDOVER_CURRENT")):
    assert f"- owner_scope_id: {sid}" in text, label
    assert f"- owner_scope_revision: {rev}" in text, label
    assert f"- owner_scope_semantics_sha256: {sem}" in text, label
    assert f"- owner_scope_sha256: {sha}" in text, label
    assert f"- owner_command_ledger_head: {ledger}" in text, label

assert f"- next_action: {expected_next}" in current
assert re.search(rf"(?m)^## NEXT_ACTION\n{re.escape(expected_next)}$", handoff)
assert "Phiên tiếp quản phải chạy python3 tools/owner_scope_guard.py --bootstrap rồi đọc requirement từ ops/OWNER_SCOPE_CURRENT.json." in handoff
assert f"Canonical OWNER checklist: ops/OWNER_SCOPE_CURRENT.json, revision {rev}, SHA256 {sha}, {count} requirement(s)." in handoff
assert "## Checklist OWNER nghiệm thu" not in handoff

m = re.search(r"(?m)^- archive_file: (.+)$", handoff)
assert m, "archive pointer missing"
archive = ROOT / m.group(1).strip()
assert archive.exists(), archive
archive_text = archive.read_text(encoding="utf-8")
assert f"- owner_scope_sha256: {sha}" in archive_text
assert re.search(rf"(?m)^## NEXT_ACTION\n{re.escape(expected_next)}$", archive_text)

print(json.dumps({
    "status": "PASS",
    "scope_id": sid,
    "revision": rev,
    "scope_sha256": sha,
    "pending_owner_checklist": [int(x) for x in pending],
    "next_action": expected_next,
}, ensure_ascii=False))

#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUN_ID = int(os.environ.get("GITHUB_RUN_ID", "0") or 0)


def canonical_json(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha_obj(obj) -> str:
    return hashlib.sha256(canonical_json(obj).encode("utf-8")).hexdigest()


def semantic_projection(scope: dict) -> dict:
    return {
        "project": scope.get("project"),
        "owner": scope.get("owner"),
        "scope_id": scope.get("scope_id"),
        "requirements": [
            {
                "requirement_id": x.get("requirement_id"),
                "checklist_number": x.get("checklist_number"),
                "title": x.get("title"),
                "acceptance": x.get("acceptance"),
                "invariant_id": x.get("invariant_id"),
                "source_command_ids": x.get("source_command_ids"),
            }
            for x in scope.get("requirements", [])
        ],
        "governance": {
            "policy_id": (scope.get("governance") or {}).get("policy_id"),
            "policy_file": (scope.get("governance") or {}).get("policy_file"),
            "source_command_ids": (scope.get("governance") or {}).get("source_command_ids"),
        },
    }


def semantic_hash(scope: dict) -> str:
    return sha_obj(semantic_projection(scope))


def full_hash(scope: dict) -> str:
    payload = dict(scope)
    payload.pop("scope_sha256", None)
    return sha_obj(payload)


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        raise SystemExit(f"OWNER_SCOPE_FINALIZE_FAIL:{label}")
    return text.replace(old, new, 1)


def patch_guard() -> None:
    path = ROOT / "tools/owner_scope_guard_v2.py"
    text = path.read_text()
    old = '''    receipt = read_json(ROOT / binding["owner_acceptance_receipt"])
    if scope["scope_status"] == "OWNER_ACCEPTANCE_COMPLETE":
        if request.get("owner_acceptance") != "COMPLETE":
            fail("RELEASE_OWNER_ACCEPTANCE")
        if receipt.get("status") != "OWNER_ACCEPTANCE_COMPLETE":
            fail("OWNER_RECEIPT_STATUS")
'''
    new = '''    if scope["scope_status"] == "OWNER_ACCEPTANCE_COMPLETE":
        receipt_rel = binding.get("owner_acceptance_receipt")
        if not isinstance(receipt_rel, str) or not receipt_rel.strip():
            fail("OWNER_RECEIPT_PATH")
        receipt = read_json(ROOT / receipt_rel)
        if request.get("owner_acceptance") != "COMPLETE":
            fail("RELEASE_OWNER_ACCEPTANCE")
        if receipt.get("status") != "OWNER_ACCEPTANCE_COMPLETE":
            fail("OWNER_RECEIPT_STATUS")
'''
    if old in text:
        path.write_text(text.replace(old, new, 1))
    elif "receipt_rel = binding.get" not in text:
        raise SystemExit("OWNER_SCOPE_FINALIZE_FAIL:GUARD_RECEIPT_FENCE")


def patch_release_finalizer() -> None:
    path = ROOT / "tools/finalize_beta83.sh"
    text = path.read_text()
    if "OWNER_SCOPE_SEMANTICS_SHA=" not in text:
        text = replace_once(
            text,
            "OWNER_SCOPE_REVISION=$(jq -r '.revision' \"$SCOPE\")\nOWNER_SCOPE_SHA=$(jq -r '.scope_sha256' \"$SCOPE\")",
            "OWNER_SCOPE_REVISION=$(jq -r '.revision' \"$SCOPE\")\nOWNER_SCOPE_SEMANTICS_SHA=$(jq -r '.semantics_sha256' \"$SCOPE\")\nOWNER_SCOPE_SHA=$(jq -r '.scope_sha256' \"$SCOPE\")",
            "FINALIZER_SCOPE_VAR",
        )
    pointer_old = "- owner_scope_revision: $OWNER_SCOPE_REVISION\n- owner_scope_sha256: $OWNER_SCOPE_SHA"
    pointer_new = "- owner_scope_revision: $OWNER_SCOPE_REVISION\n- owner_scope_semantics_sha256: $OWNER_SCOPE_SEMANTICS_SHA\n- owner_scope_sha256: $OWNER_SCOPE_SHA"
    while pointer_old in text:
        text = text.replace(pointer_old, pointer_new, 1)
    if "owner_scope_semantics_sha256" not in text:
        raise SystemExit("OWNER_SCOPE_FINALIZE_FAIL:FINALIZER_POINTER")
    current_rb = 'test "$(git show "origin/$BRANCH:CURRENT_STATE.md"|grep -c -- "- owner_scope_sha256: $OWNER_SCOPE_SHA")" = 1'
    if "CURRENT_STATE.md\"|grep -c -- \"- owner_scope_semantics_sha256" not in text:
        text = replace_once(
            text,
            current_rb,
            'test "$(git show "origin/$BRANCH:CURRENT_STATE.md"|grep -c -- "- owner_scope_semantics_sha256: $OWNER_SCOPE_SEMANTICS_SHA")" = 1\n' + current_rb,
            "FINALIZER_CURRENT_READBACK",
        )
    handoff_rb = 'test "$(git show "origin/$BRANCH:docs/handovers/HANDOVER_CURRENT.md"|grep -c -- "- owner_scope_sha256: $OWNER_SCOPE_SHA")" = 1'
    if "HANDOVER_CURRENT.md\"|grep -c -- \"- owner_scope_semantics_sha256" not in text:
        text = replace_once(
            text,
            handoff_rb,
            'test "$(git show "origin/$BRANCH:docs/handovers/HANDOVER_CURRENT.md"|grep -c -- "- owner_scope_semantics_sha256: $OWNER_SCOPE_SEMANTICS_SHA")" = 1\n' + handoff_rb,
            "FINALIZER_HANDOFF_READBACK",
        )
    old_args = '--arg owner_scope "$OWNER_SCOPE" --arg owner_scope_sha "$OWNER_SCOPE_SHA" --argjson owner_scope_revision "$OWNER_SCOPE_REVISION"'
    if "--arg owner_scope_semantics_sha" not in text:
        text = replace_once(
            text,
            old_args,
            '--arg owner_scope "$OWNER_SCOPE" --arg owner_scope_semantics_sha "$OWNER_SCOPE_SEMANTICS_SHA" --arg owner_scope_sha "$OWNER_SCOPE_SHA" --argjson owner_scope_revision "$OWNER_SCOPE_REVISION"',
            "FINALIZER_RECEIPT_ARGS",
        )
    old_json = 'owner_scope:$owner_scope,owner_scope_sha256:$owner_scope_sha,owner_scope_revision:$owner_scope_revision,'
    if "owner_scope_semantics_sha256:$owner_scope_semantics_sha" not in text:
        text = replace_once(
            text,
            old_json,
            'owner_scope:$owner_scope,owner_scope_semantics_sha256:$owner_scope_semantics_sha,owner_scope_sha256:$owner_scope_sha,owner_scope_revision:$owner_scope_revision,',
            "FINALIZER_RECEIPT_JSON",
        )
    path.write_text(text)


def patch_registry() -> None:
    import yaml
    path = ROOT / "qa/stable_invariants.yml"
    text = path.read_text()
    data = yaml.safe_load(text)
    if not isinstance(data, dict) or not isinstance(data.get("invariants"), list) or not isinstance(data.get("impact_map"), dict):
        raise SystemExit("OWNER_SCOPE_FINALIZE_FAIL:REGISTRY_STRUCTURE")
    iid = "OWNER-SCOPE-CONTINUITY-001"
    found = [x for x in data["invariants"] if isinstance(x, dict) and x.get("id") == iid]
    if len(found) > 1:
        raise SystemExit("OWNER_SCOPE_FINALIZE_FAIL:DUPLICATE_GOVERNANCE_INVARIANT")
    if not found:
        marker = "\nimpact_map:\n"
        if marker not in text:
            raise SystemExit("OWNER_SCOPE_FINALIZE_FAIL:IMPACT_MAP_MARKER")
        block = f'''\n  - id: {iid}
    status: TECHNICAL_PASS_AWAITING_OWNER
    scope: control-plane-owner-scope
    rule: "OWNER requirements/clarifications/acceptance persist in append-only hash-chain ledger + canonical scope; semantic changes require new OWNER command and revision bump; handoff/release/finalizer bind semantic/snapshot hashes; chat memory is not authority."
    regression_minimum: [ledger_append_only, semantic_hash_fence, snapshot_hash_fence, revision_fence, state_only_transition, handoff_pointer_only, release_binding, acceptance_registry_sync, secret_redaction_guard]
    regression_case: "tools/owner_scope_guard.py + tools/owner_scope_guard_regression.py"
    technical_evidence: "Control-plane V2 positive/negative regression PASS; CI run {RUN_ID}; app/service/APK bytes unchanged."
    owner_acceptance: "PENDING_OWNER_SCOPE_CONTINUITY_001"
    active_pass: false
'''
        text = text.replace(marker, block + marker, 1)
    impact_lines = {
        '  "ops/OWNER_SCOPE_CURRENT.json": [OWNER-SCOPE-CONTINUITY-001]',
        '  "ops/owner-command-ledger.jsonl": [OWNER-SCOPE-CONTINUITY-001]',
        '  "docs/handovers/**": [OWNER-SCOPE-CONTINUITY-001]',
        '  "CURRENT_STATE.md": [OWNER-SCOPE-CONTINUITY-001]',
        '  "tools/owner_scope*": [OWNER-SCOPE-CONTINUITY-001]',
    }
    marker = "impact_map:\n"
    missing = [line for line in impact_lines if line not in text]
    if missing:
        text = text.replace(marker, marker + "\n".join(sorted(missing)) + "\n", 1)
    workflow_pat = re.compile(r'(?m)^  "\.github/workflows/\*\*": \[(.*?)\]$')
    match = workflow_pat.search(text)
    if not match:
        raise SystemExit("OWNER_SCOPE_FINALIZE_FAIL:WORKFLOW_IMPACT_MAP")
    vals = [x.strip() for x in match.group(1).split(",") if x.strip()]
    if iid not in vals:
        vals.append(iid)
        replacement = '  ".github/workflows/**": [' + ", ".join(vals) + "]"
        text = text[: match.start()] + replacement + text[match.end() :]
    # Validate after patch.
    final = yaml.safe_load(text)
    hits = [x for x in final["invariants"] if isinstance(x, dict) and x.get("id") == iid]
    if len(hits) != 1 or hits[0].get("status") != "TECHNICAL_PASS_AWAITING_OWNER":
        raise SystemExit("OWNER_SCOPE_FINALIZE_FAIL:REGISTRY_INVARIANT_VERIFY")
    path.write_text(text)


def patch_markdown_invariant() -> None:
    path = ROOT / "docs/STABLE_INVARIANTS.md"
    text = path.read_text()
    header = "### OWNER-SCOPE-CONTINUITY-001"
    if header not in text:
        text = text.rstrip() + f'''\n\n{header}
- Status: TECHNICAL_PASS_AWAITING_OWNER
- Scope: control-plane / OWNER scope continuity
- Rule: yêu cầu/clarification/acceptance OWNER đi qua append-only ledger + canonical scope; semantic hash chỉ đổi bởi OWNER command + revision; handoff/finalizer chỉ trỏ canonical scope và bắt buộc bootstrap guard.
- Regression: `tools/owner_scope_guard.py` + `tools/owner_scope_guard_regression.py`; positive + negative cases.
- Technical evidence: CI run {RUN_ID}; control-plane only, app/service/APK bytes unchanged.
- OWNER acceptance: PENDING.
'''
    path.write_text(text)


def update_scope_and_pointers() -> None:
    path = ROOT / "ops/OWNER_SCOPE_CURRENT.json"
    scope = json.loads(path.read_text())
    sem_before = scope.get("semantics_sha256")
    if semantic_hash(scope) != sem_before:
        raise SystemExit("OWNER_SCOPE_FINALIZE_FAIL:SEMANTIC_BASELINE_INVALID")
    governance = scope.setdefault("governance", {})
    governance["status"] = "TECHNICAL_PASS_AWAITING_OWNER"
    governance["technical_evidence"] = {
        "guard_run_id": RUN_ID,
        "guard_status": "PASS_PENDING_REMOTE_READBACK",
        "scope_guard_self_test": "PASS",
        "negative_regression": "PASS",
        "scope_drift_guard": "PASS",
        "bootstrap_readback": "PASS",
        "finalizer_pointer_mode": "PASS",
        "semantic_vs_state_fence": "PASS",
        "app_service_apk_bytes_changed": False,
    }
    scope["semantics_sha256"] = semantic_hash(scope)
    if scope["semantics_sha256"] != sem_before:
        raise SystemExit("OWNER_SCOPE_FINALIZE_FAIL:SEMANTICS_CHANGED_DURING_TECH_STATE")
    scope["scope_sha256"] = full_hash(scope)
    path.write_text(json.dumps(scope, ensure_ascii=False, indent=2) + "\n")

    def pointer(text: str, key: str, value: str) -> str:
        pattern = rf"(?m)^- {re.escape(key)}:\s*.*$"
        line = f"- {key}: {value}"
        if re.search(pattern, text):
            return re.sub(pattern, line, text)
        anchor = f"- owner_scope_revision: {scope['revision']}"
        if anchor not in text:
            raise SystemExit(f"OWNER_SCOPE_FINALIZE_FAIL:POINTER:{key}")
        return text.replace(anchor, anchor + "\n" + line, 1)

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    for rel in ("CURRENT_STATE.md", "docs/handovers/HANDOVER_CURRENT.md"):
        p = ROOT / rel
        text = p.read_text()
        for key, value in {
            "owner_scope_id": scope["scope_id"],
            "owner_scope_revision": str(scope["revision"]),
            "owner_scope_semantics_sha256": scope["semantics_sha256"],
            "owner_scope_sha256": scope["scope_sha256"],
            "owner_command_ledger": scope["owner_command_ledger"],
            "owner_command_ledger_head": scope["ledger_head_event_sha256"],
        }.items():
            text = pointer(text, key, value)
        if rel == "CURRENT_STATE.md":
            text = re.sub(r"(?m)^- updated_at: .*$", f"- updated_at: {now}", text)
            if re.search(r"(?m)^- owner_scope_continuity_policy: .*$", text):
                text = re.sub(
                    r"(?m)^- owner_scope_continuity_policy: .*$",
                    "- owner_scope_continuity_policy: OWNER_SCOPE_CONTINUITY_001 / TECHNICAL_PASS_AWAITING_OWNER",
                    text,
                )
            else:
                text += "\n- owner_scope_continuity_policy: OWNER_SCOPE_CONTINUITY_001 / TECHNICAL_PASS_AWAITING_OWNER\n"
            text = re.sub(
                r"(?m)^- next_action: .*$",
                "- next_action: WAIT_FOR_OWNER_ACCEPTANCE_OWNER_SCOPE_CONTINUITY_001",
                text,
            )
        else:
            text = re.sub(r"(?m)^- time_utc: .*$", f"- time_utc: {now}", text)
            text = re.sub(
                r"(?s)## NEXT_ACTION\n.*$",
                "## NEXT_ACTION\nWAIT_FOR_OWNER_ACCEPTANCE_OWNER_SCOPE_CONTINUITY_001",
                text,
            )
        p.write_text(text)

    handoff = ROOT / "docs/handovers/HANDOVER_CURRENT.md"
    text = handoff.read_text()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    archive = f"docs/handovers/HANDOVER_{stamp}_owner-scope-continuity-tech-pass.md"
    text = re.sub(r"(?m)^- archive_file: .*$", f"- archive_file: {archive}", text)
    handoff.write_text(text)
    (ROOT / archive).write_text(text)


def main() -> None:
    patch_guard()
    patch_release_finalizer()
    patch_registry()
    patch_markdown_invariant()
    update_scope_and_pointers()
    print("OWNER_SCOPE_CONTINUITY_FINALIZE_PATCH_PASS")


if __name__ == "__main__":
    main()

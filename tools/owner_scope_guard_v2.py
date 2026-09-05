#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCOPE_PATH = ROOT / "ops/OWNER_SCOPE_CURRENT.json"
LEDGER_PATH = ROOT / "ops/owner-command-ledger.jsonl"
HANDOVER_PATH = ROOT / "docs/handovers/HANDOVER_CURRENT.md"
CURRENT_STATE_PATH = ROOT / "CURRENT_STATE.md"
RELEASE_REQUEST_PATH = ROOT / "ops/beta-release-request.json"
OWNER_ACCEPTANCE_PATH = ROOT / "ops/owner-acceptance-current.json"
REGISTRY_PATH = ROOT / "qa/stable_invariants.yml"

ALLOWED_REQUIREMENT_STATES = {
    "LOCKED_REQUIREMENT_PENDING_FIX",
    "TECHNICAL_PASS_AWAITING_OWNER",
    "ACTIVE_PASS",
    "SUPERSEDED",
}
ALLOWED_SCOPE_STATUS = {
    "LOCKED_REQUIREMENT_PENDING_FIX",
    "TECHNICAL_PASS_AWAITING_OWNER",
    "OWNER_ACCEPTANCE_COMPLETE",
    "SUPERSEDED",
}
ALLOWED_GOVERNANCE_STATES = {
    "LOCKED_REQUIREMENT_PENDING_FIX",
    "TECHNICAL_PASS_AWAITING_OWNER",
    "ACTIVE_PASS",
    "SUPERSEDED",
}


def fail(msg: str) -> None:
    raise SystemExit(f"OWNER_SCOPE_GUARD_FAIL:{msg}")


def canonical_json(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha_obj(obj) -> str:
    return hashlib.sha256(canonical_json(obj).encode("utf-8")).hexdigest()


def read_json(path: Path):
    try:
        return json.loads(path.read_text())
    except Exception as exc:
        fail(f"JSON:{path}:{exc}")


def semantic_projection(scope: dict) -> dict:
    reqs = []
    for item in scope.get("requirements") or []:
        reqs.append({
            "requirement_id": item.get("requirement_id"),
            "checklist_number": item.get("checklist_number"),
            "title": item.get("title"),
            "acceptance": item.get("acceptance"),
            "invariant_id": item.get("invariant_id"),
            "source_command_ids": item.get("source_command_ids"),
        })
    governance = scope.get("governance") or {}
    return {
        "project": scope.get("project"),
        "owner": scope.get("owner"),
        "scope_id": scope.get("scope_id"),
        "requirements": reqs,
        "governance": {
            "policy_id": governance.get("policy_id"),
            "policy_file": governance.get("policy_file"),
            "source_command_ids": governance.get("source_command_ids"),
        },
    }


def full_scope_hash(scope: dict) -> str:
    payload = dict(scope)
    payload.pop("scope_sha256", None)
    return sha_obj(payload)


def semantic_hash(scope: dict) -> str:
    return sha_obj(semantic_projection(scope))


def load_ledger(path: Path = LEDGER_PATH):
    if not path.exists():
        fail(f"LEDGER_MISSING:{path}")
    events = []
    for line_no, line in enumerate(path.read_text().splitlines(), 1):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except Exception as exc:
            fail(f"LEDGER_JSON_LINE_{line_no}:{exc}")
        events.append(event)
    if not events:
        fail("LEDGER_EMPTY")
    prev = None
    seen_ids = set()
    for idx, event in enumerate(events, 1):
        if event.get("sequence") != idx:
            fail(f"LEDGER_SEQUENCE:{idx}:{event.get('sequence')}")
        cid = event.get("command_id")
        if not isinstance(cid, str) or not cid.strip() or cid in seen_ids:
            fail(f"LEDGER_COMMAND_ID:{idx}")
        seen_ids.add(cid)
        raw = event.get("raw_text")
        if not isinstance(raw, str) or not raw.strip():
            fail(f"LEDGER_RAW_TEXT:{cid}")
        if event.get("source") != "OWNER_CHAT":
            fail(f"LEDGER_NON_OWNER_SOURCE:{cid}")
        if event.get("previous_event_sha256") != prev:
            fail(f"LEDGER_PREV_HASH:{cid}")
        stored = event.get("event_sha256")
        payload = dict(event)
        payload.pop("event_sha256", None)
        expected = sha_obj(payload)
        if stored != expected:
            fail(f"LEDGER_EVENT_HASH:{cid}")
        prev = stored
    return events


def load_scope(path: Path = SCOPE_PATH):
    scope = read_json(path)
    if scope.get("schema_version") != 1:
        fail("SCOPE_SCHEMA")
    if scope.get("project") != "APK PICK PACK 1291":
        fail("SCOPE_PROJECT")
    if scope.get("owner") != "Nguyễn Văn Tâm":
        fail("SCOPE_OWNER")
    sid = scope.get("scope_id")
    if not isinstance(sid, str) or not sid.strip() or sid.lower() in {"null", "none", "unspecified"}:
        fail("SCOPE_ID")
    rev = scope.get("revision")
    if not isinstance(rev, int) or rev < 1:
        fail("SCOPE_REVISION")
    if scope.get("scope_status") not in ALLOWED_SCOPE_STATUS:
        fail("SCOPE_STATUS")
    reqs = scope.get("requirements")
    if not isinstance(reqs, list) or not reqs:
        fail("SCOPE_REQUIREMENTS")
    ids, nums = set(), set()
    for item in reqs:
        rid = item.get("requirement_id")
        num = item.get("checklist_number")
        title = item.get("title")
        acceptance = item.get("acceptance")
        state = item.get("state")
        if not isinstance(rid, str) or not rid or rid in ids:
            fail(f"REQUIREMENT_ID:{rid}")
        ids.add(rid)
        if not isinstance(num, int) or num < 1 or num in nums:
            fail(f"REQUIREMENT_NUMBER:{rid}")
        nums.add(num)
        if not isinstance(title, str) or not title.strip():
            fail(f"REQUIREMENT_TITLE:{rid}")
        if not isinstance(acceptance, list) or not acceptance or any(not isinstance(x, str) or not x.strip() for x in acceptance):
            fail(f"REQUIREMENT_ACCEPTANCE:{rid}")
        if state not in ALLOWED_REQUIREMENT_STATES:
            fail(f"REQUIREMENT_STATE:{rid}:{state}")
        src = item.get("source_command_ids")
        if not isinstance(src, list) or not src:
            fail(f"REQUIREMENT_SOURCE_COMMANDS:{rid}")
    if sorted(nums) != list(range(1, len(nums) + 1)):
        fail("REQUIREMENT_NUMBERS_NOT_CONTIGUOUS")
    governance = scope.get("governance") or {}
    if governance:
        if governance.get("status") not in ALLOWED_GOVERNANCE_STATES:
            fail("GOVERNANCE_STATUS")
        if not governance.get("policy_id") or not governance.get("policy_file"):
            fail("GOVERNANCE_ID_OR_FILE")
        if not isinstance(governance.get("source_command_ids"), list) or not governance.get("source_command_ids"):
            fail("GOVERNANCE_SOURCE_COMMANDS")
    sem_stored = scope.get("semantics_sha256")
    sem_expected = semantic_hash(scope)
    if sem_stored != sem_expected:
        fail("SEMANTICS_HASH")
    full_stored = scope.get("scope_sha256")
    full_expected = full_scope_hash(scope)
    if full_stored != full_expected:
        fail("SCOPE_HASH")
    return scope


def require_pointer(text: str, key: str, expected: str) -> None:
    pattern = rf"(?m)^- {re.escape(key)}:\s*(.+?)\s*$"
    match = re.search(pattern, text)
    if not match or match.group(1).strip() != expected:
        fail(f"POINTER:{key}")


def invariant_status_blocks(text: str):
    out = {}
    matches = list(re.finditer(r"(?m)^  - id:\s*([A-Za-z0-9_.-]+)\s*$", text))
    for idx, match in enumerate(matches):
        start = match.start()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        block = text[start:end]
        status = re.search(r"(?m)^\s{4}status:\s*([A-Z_]+)\s*$", block)
        out[match.group(1)] = status.group(1) if status else None
    return out


def check_release_binding(scope: dict) -> None:
    binding = scope.get("release_binding") or {}
    if binding.get("mode") != "CURRENT_RELEASE":
        return
    request = read_json(RELEASE_REQUEST_PATH)
    if request.get("owner_scope") != scope["scope_id"]:
        fail("RELEASE_SCOPE_ID")
    if request.get("owner_checklist_revision") != scope["revision"]:
        fail("RELEASE_SCOPE_REVISION")
    checklist = request.get("owner_checklist")
    if not isinstance(checklist, list) or len(checklist) != len(scope["requirements"]):
        fail("RELEASE_CHECKLIST_COUNT")
    by_number = {x["checklist_number"]: x for x in scope["requirements"]}
    for item in checklist:
        num = item.get("id")
        scoped = by_number.get(num)
        if not scoped:
            fail(f"RELEASE_CHECKLIST_NUMBER:{num}")
        if item.get("title") != scoped["title"] or item.get("acceptance") != scoped["acceptance"]:
            fail(f"RELEASE_CHECKLIST_CONTENT:{num}")
    receipt = read_json(ROOT / binding["owner_acceptance_receipt"])
    if scope["scope_status"] == "OWNER_ACCEPTANCE_COMPLETE":
        if request.get("owner_acceptance") != "COMPLETE":
            fail("RELEASE_OWNER_ACCEPTANCE")
        if receipt.get("status") != "OWNER_ACCEPTANCE_COMPLETE":
            fail("OWNER_RECEIPT_STATUS")


def check_acceptance_registry(scope: dict) -> None:
    if scope["scope_status"] != "OWNER_ACCEPTANCE_COMPLETE":
        return
    acceptance = read_json(OWNER_ACCEPTANCE_PATH)
    if (acceptance.get("owner_scope") or {}).get("scope_id") != scope["scope_id"]:
        fail("ACCEPTANCE_LEDGER_SCOPE")
    if (acceptance.get("owner_scope") or {}).get("status") != "OWNER_ACCEPTANCE_COMPLETE":
        fail("ACCEPTANCE_LEDGER_STATUS")
    current = {
        item.get("id"): item.get("status")
        for item in (acceptance.get("owner_scope") or {}).get("requirements", [])
        if isinstance(item, dict)
    }
    registry = invariant_status_blocks(REGISTRY_PATH.read_text())
    for item in scope["requirements"]:
        if item["state"] != "ACTIVE_PASS":
            fail(f"ACCEPTED_SCOPE_NON_ACTIVE:{item['requirement_id']}")
        invariant_id = item.get("invariant_id")
        if not invariant_id or current.get(invariant_id) != "ACTIVE_PASS":
            fail(f"ACCEPTANCE_LEDGER_INVARIANT:{invariant_id}")
        if registry.get(invariant_id) != "ACTIVE_PASS":
            fail(f"REGISTRY_INVARIANT:{invariant_id}:{registry.get(invariant_id)}")


def git_show(ref: str, path: str):
    proc = subprocess.run(["git", "show", f"{ref}:{path}"], cwd=ROOT, text=True, capture_output=True)
    return proc.stdout if proc.returncode == 0 else None


def check_append_only(base_ref: str, scope: dict, events: list[dict]) -> None:
    old_ledger = git_show(base_ref, "ops/owner-command-ledger.jsonl")
    old_scope_raw = git_show(base_ref, "ops/OWNER_SCOPE_CURRENT.json")
    if old_ledger is not None:
        new_text = LEDGER_PATH.read_text()
        if not new_text.startswith(old_ledger):
            fail("LEDGER_NOT_APPEND_ONLY")
        old_event_count = len([x for x in old_ledger.splitlines() if x.strip()])
        if len(events) < old_event_count:
            fail("LEDGER_SHRANK")
    else:
        old_event_count = 0
    if old_scope_raw is None:
        return
    try:
        old_scope = json.loads(old_scope_raw)
    except Exception:
        fail("BASE_SCOPE_JSON")
    old_revision = old_scope.get("revision", 0)
    if scope["revision"] < old_revision:
        fail("SCOPE_REVISION_ROLLBACK")
    old_sem = old_scope.get("semantics_sha256") or semantic_hash(old_scope)
    new_sem = scope["semantics_sha256"]
    semantic_changed = new_sem != old_sem
    ledger_grew = len(events) > old_event_count
    if semantic_changed:
        if not ledger_grew:
            fail("SEMANTICS_CHANGED_WITHOUT_NEW_OWNER_COMMAND")
        if scope["revision"] <= old_revision:
            fail("SEMANTICS_CHANGED_WITHOUT_REVISION_BUMP")
    else:
        if scope["revision"] != old_revision:
            fail("REVISION_CHANGED_WITHOUT_SEMANTIC_CHANGE")
    # State/evidence-only transitions are allowed without a new OWNER command,
    # but requirement text and governance semantics are protected by semantic hash.


def validate(base_ref: str | None = None, bootstrap: bool = False) -> None:
    events = load_ledger()
    scope = load_scope()
    if scope.get("owner_command_ledger") != "ops/owner-command-ledger.jsonl":
        fail("SCOPE_LEDGER_PATH")
    if scope.get("ledger_head_sequence") != events[-1]["sequence"]:
        fail("SCOPE_LEDGER_SEQUENCE")
    if scope.get("ledger_head_event_sha256") != events[-1]["event_sha256"]:
        fail("SCOPE_LEDGER_HEAD_HASH")
    event_ids = {event["command_id"] for event in events}
    for item in scope["requirements"]:
        if any(command_id not in event_ids for command_id in item["source_command_ids"]):
            fail(f"REQUIREMENT_UNKNOWN_COMMAND:{item['requirement_id']}")
    governance = scope.get("governance") or {}
    if any(command_id not in event_ids for command_id in governance.get("source_command_ids", [])):
        fail("GOVERNANCE_UNKNOWN_COMMAND")

    handover = HANDOVER_PATH.read_text()
    current = CURRENT_STATE_PATH.read_text()
    for text, where in ((handover, "HANDOVER"), (current, "CURRENT_STATE")):
        require_pointer(text, "owner_scope_file", "ops/OWNER_SCOPE_CURRENT.json")
        require_pointer(text, "owner_scope_revision", str(scope["revision"]))
        require_pointer(text, "owner_scope_semantics_sha256", scope["semantics_sha256"])
        require_pointer(text, "owner_scope_sha256", scope["scope_sha256"])
        require_pointer(text, "owner_command_ledger", "ops/owner-command-ledger.jsonl")
    if "## Checklist OWNER nghiệm thu" in handover:
        fail("HANDOVER_DUPLICATES_CHECKLIST")
    if re.search(r"(?i)\bowner_scope(?:_id)?:\s*(null|none|unspecified)\b", handover + "\n" + current):
        fail("NULL_SCOPE_POINTER")

    check_release_binding(scope)
    check_acceptance_registry(scope)
    if base_ref:
        check_append_only(base_ref, scope, events)

    if bootstrap:
        match = re.search(r"(?m)^- next_action:\s*(.+)$", current)
        next_action = match.group(1).strip() if match else None
        print(json.dumps({
            "status": "BOOTSTRAP_PASS",
            "scope_id": scope["scope_id"],
            "revision": scope["revision"],
            "semantics_sha256": scope["semantics_sha256"],
            "scope_sha256": scope["scope_sha256"],
            "scope_status": scope["scope_status"],
            "requirements": len(scope["requirements"]),
            "governance_status": (scope.get("governance") or {}).get("status"),
            "ledger_head_sequence": scope["ledger_head_sequence"],
            "ledger_head_event_sha256": scope["ledger_head_event_sha256"],
            "next_action": next_action,
        }, ensure_ascii=False))
    else:
        print(
            f"owner_scope_guard=PASS scope={scope['scope_id']} revision={scope['revision']} "
            f"requirements={len(scope['requirements'])} semantics={scope['semantics_sha256']}"
        )


def self_test() -> None:
    sample_event = {
        "sequence": 1,
        "command_id": "CMD-1",
        "recorded_at": "2026-01-01T00:00:00Z",
        "source": "OWNER_CHAT",
        "event_type": "REQUIREMENT",
        "raw_text": "x",
        "related_requirement_ids": ["R1"],
        "previous_event_sha256": None,
    }
    digest = sha_obj(sample_event)
    sample_event["event_sha256"] = digest
    payload = dict(sample_event)
    payload.pop("event_sha256")
    assert sha_obj(payload) == digest

    base = {
        "project": "APK PICK PACK 1291",
        "owner": "Nguyễn Văn Tâm",
        "scope_id": "S1",
        "revision": 1,
        "requirements": [{
            "requirement_id": "R1",
            "checklist_number": 1,
            "title": "A",
            "acceptance": ["B"],
            "invariant_id": "I1",
            "state": "LOCKED_REQUIREMENT_PENDING_FIX",
            "source_command_ids": ["CMD-1"],
        }],
        "governance": {
            "policy_id": "P1",
            "policy_file": "p.md",
            "source_command_ids": ["CMD-1"],
            "status": "LOCKED_REQUIREMENT_PENDING_FIX",
        },
    }
    sem1 = semantic_hash(base)
    state_only = json.loads(json.dumps(base))
    state_only["requirements"][0]["state"] = "TECHNICAL_PASS_AWAITING_OWNER"
    state_only["governance"]["status"] = "TECHNICAL_PASS_AWAITING_OWNER"
    assert semantic_hash(state_only) == sem1
    changed = json.loads(json.dumps(base))
    changed["requirements"][0]["acceptance"] = ["C"]
    assert semantic_hash(changed) != sem1
    print("owner_scope_guard_v2_self_test=PASS")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-ref")
    parser.add_argument("--bootstrap", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return
    validate(args.base_ref, args.bootstrap)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SRC = Path(__file__).resolve().parents[1]
FILES = [
    "tools/owner_scope_guard.py",
    "tools/owner_scope_guard_v2.py",
    "ops/OWNER_SCOPE_CURRENT.json",
    "ops/owner-command-ledger.jsonl",
    "ops/beta-release-request.json",
    "ops/owner-acceptance-current.json",
    "docs/handovers/HANDOVER_CURRENT.md",
    "CURRENT_STATE.md",
    "qa/stable_invariants.yml",
]


def canonical_json(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha_obj(obj) -> str:
    return hashlib.sha256(canonical_json(obj).encode("utf-8")).hexdigest()


def semantic_projection(scope: dict) -> dict:
    return {
        "project": scope["project"],
        "owner": scope["owner"],
        "scope_id": scope["scope_id"],
        "requirements": [{
            "requirement_id": x["requirement_id"],
            "checklist_number": x["checklist_number"],
            "title": x["title"],
            "acceptance": x["acceptance"],
            "invariant_id": x.get("invariant_id"),
            "source_command_ids": x["source_command_ids"],
        } for x in scope["requirements"]],
        "governance": {
            "policy_id": scope["governance"]["policy_id"],
            "policy_file": scope["governance"]["policy_file"],
            "source_command_ids": scope["governance"]["source_command_ids"],
        },
    }


def rehash(scope: dict) -> None:
    scope["semantics_sha256"] = sha_obj(semantic_projection(scope))
    payload = dict(scope)
    payload.pop("scope_sha256", None)
    scope["scope_sha256"] = sha_obj(payload)


def update_pointer(path: Path, key: str, value: str) -> None:
    import re
    text = path.read_text()
    pattern = rf"(?m)^- {re.escape(key)}:\s*.*$"
    if not re.search(pattern, text):
        raise RuntimeError(f"missing pointer {key}")
    path.write_text(re.sub(pattern, f"- {key}: {value}", text))


def sync(root: Path, scope: dict) -> None:
    for rel in ("docs/handovers/HANDOVER_CURRENT.md", "CURRENT_STATE.md"):
        path = root / rel
        update_pointer(path, "owner_scope_revision", str(scope["revision"]))
        update_pointer(path, "owner_scope_semantics_sha256", scope["semantics_sha256"])
        update_pointer(path, "owner_scope_sha256", scope["scope_sha256"])
        update_pointer(path, "owner_command_ledger_head", scope["ledger_head_event_sha256"])


def sync_release_request(root: Path, scope: dict) -> None:
    path = root / "ops/beta-release-request.json"
    req = json.loads(path.read_text())
    req["owner_scope"] = scope["scope_id"]
    req["owner_checklist_revision"] = scope["revision"]
    req["owner_scope_semantics_sha256"] = scope["semantics_sha256"]
    req["owner_scope_sha256"] = scope["scope_sha256"]
    req["owner_command_ledger_head"] = scope["ledger_head_event_sha256"]
    by_number = {x["checklist_number"]: x for x in scope["requirements"]}
    for item in req.get("owner_checklist", []):
        scoped = by_number[item["id"]]
        item["title"] = scoped["title"]
        item["acceptance"] = scoped["acceptance"]
    path.write_text(json.dumps(req, ensure_ascii=False, indent=2) + "\n")


def run(root: Path, *args: str, expect: int = 0, needle: str | None = None) -> str:
    proc = subprocess.run(
        [sys.executable, "tools/owner_scope_guard.py", *args],
        cwd=root, text=True, capture_output=True,
    )
    output = (proc.stdout or "") + (proc.stderr or "")
    if (proc.returncode == 0) != (expect == 0):
        raise SystemExit(f"REGRESSION_FAIL command={args} rc={proc.returncode} output={output}")
    if needle and needle not in output:
        raise SystemExit(f"REGRESSION_FAIL missing={needle} output={output}")
    return output


def prepare() -> tuple[tempfile.TemporaryDirectory, Path]:
    td = tempfile.TemporaryDirectory()
    root = Path(td.name)
    files = list(FILES)
    live_scope = json.loads((SRC / "ops/OWNER_SCOPE_CURRENT.json").read_text())
    receipt = (live_scope.get("release_binding") or {}).get("owner_acceptance_receipt")
    if receipt:
        receipt_path = SRC / receipt
        if not receipt_path.is_file():
            raise SystemExit(f"REGRESSION_FAIL missing_dynamic_owner_receipt={receipt}")
        files.append(receipt)
    for rel in files:
        dst = root / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(SRC / rel, dst)
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.name", "scope-regression"], cwd=root, check=True)
    subprocess.run(["git", "add", "."], cwd=root, check=True)
    subprocess.run(["git", "commit", "-qm", "baseline"], cwd=root, check=True)
    return td, root


def main() -> None:
    td, root = prepare()
    try:
        run(root, "--bootstrap", needle="BOOTSTRAP_PASS")
    finally:
        td.cleanup()

    # State/evidence-only transitions are valid without a new OWNER command or revision.
    td, root = prepare()
    try:
        scope_path = root / "ops/OWNER_SCOPE_CURRENT.json"
        scope = json.loads(scope_path.read_text())
        scope["governance"]["status"] = (
            "ACTIVE_PASS" if scope["governance"]["status"] != "ACTIVE_PASS"
            else "TECHNICAL_PASS_AWAITING_OWNER"
        )
        rehash(scope)
        scope_path.write_text(json.dumps(scope, ensure_ascii=False, indent=2) + "\n")
        sync(root, scope)
        run(root, "--base-ref", "HEAD", needle="owner_scope_guard=PASS")
    finally:
        td.cleanup()

    # Semantic drift with no OWNER command must fail at semantic authority fence.
    td, root = prepare()
    try:
        scope_path = root / "ops/OWNER_SCOPE_CURRENT.json"
        scope = json.loads(scope_path.read_text())
        scope["requirements"][0]["acceptance"][0] += " DRIFT"
        rehash(scope)
        scope_path.write_text(json.dumps(scope, ensure_ascii=False, indent=2) + "\n")
        sync(root, scope)
        sync_release_request(root, scope)
        run(root, "--base-ref", "HEAD", expect=1, needle="SEMANTICS_CHANGED_WITHOUT_NEW_OWNER_COMMAND")
    finally:
        td.cleanup()

    # New OWNER event without revision bump must still fail.
    td, root = prepare()
    try:
        ledger_path = root / "ops/owner-command-ledger.jsonl"
        events = [json.loads(x) for x in ledger_path.read_text().splitlines() if x.strip()]
        event = {
            "sequence": len(events) + 1,
            "command_id": "CMD-REGRESSION-NEW",
            "recorded_at": "2026-09-05T22:00:00+07:00",
            "source": "OWNER_CHAT",
            "event_type": "CLARIFICATION",
            "raw_text": "regression semantic change",
            "related_requirement_ids": ["R2-01"],
            "previous_event_sha256": events[-1]["event_sha256"],
        }
        event["event_sha256"] = sha_obj(event)
        events.append(event)
        ledger_path.write_text("\n".join(json.dumps(x, ensure_ascii=False, separators=(",", ":")) for x in events) + "\n")
        scope_path = root / "ops/OWNER_SCOPE_CURRENT.json"
        scope = json.loads(scope_path.read_text())
        scope["requirements"][0]["acceptance"][0] += " OWNER-CHANGED"
        scope["requirements"][0]["source_command_ids"].append(event["command_id"])
        scope["ledger_head_sequence"] = event["sequence"]
        scope["ledger_head_event_sha256"] = event["event_sha256"]
        rehash(scope)
        scope_path.write_text(json.dumps(scope, ensure_ascii=False, indent=2) + "\n")
        sync(root, scope)
        sync_release_request(root, scope)
        run(root, "--base-ref", "HEAD", expect=1, needle="SEMANTICS_CHANGED_WITHOUT_REVISION_BUMP")
    finally:
        td.cleanup()

    # Rewriting an old ledger event must fail hash-chain validation.
    td, root = prepare()
    try:
        ledger_path = root / "ops/owner-command-ledger.jsonl"
        lines = ledger_path.read_text().splitlines()
        first = json.loads(lines[0])
        first["raw_text"] += " TAMPER"
        lines[0] = json.dumps(first, ensure_ascii=False, separators=(",", ":"))
        ledger_path.write_text("\n".join(lines) + "\n")
        run(root, expect=1, needle="LEDGER_EVENT_HASH")
    finally:
        td.cleanup()

    # Handoff must never duplicate the OWNER checklist.
    td, root = prepare()
    try:
        handoff = root / "docs/handovers/HANDOVER_CURRENT.md"
        handoff.write_text(handoff.read_text() + "\n## Checklist OWNER nghiệm thu\n1. bad copy\n")
        run(root, expect=1, needle="HANDOVER_DUPLICATES_CHECKLIST")
    finally:
        td.cleanup()

    print("OWNER_SCOPE_CONTINUITY_NEGATIVE_REGRESSION_PASS")


if __name__ == "__main__":
    main()

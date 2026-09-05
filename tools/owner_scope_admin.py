#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from owner_scope_guard_v2 import semantic_hash, full_scope_hash

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "ops/owner-command-ledger.jsonl"
SCOPE = ROOT / "ops/OWNER_SCOPE_CURRENT.json"
HANDOVER = ROOT / "docs/handovers/HANDOVER_CURRENT.md"
CURRENT = ROOT / "CURRENT_STATE.md"


def canonical_json(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha_obj(obj) -> str:
    return hashlib.sha256(canonical_json(obj).encode("utf-8")).hexdigest()


def read_ledger() -> list[dict]:
    return [json.loads(line) for line in LEDGER.read_text().splitlines() if line.strip()]


def write_ledger(events: list[dict]) -> None:
    LEDGER.write_text("\n".join(json.dumps(x, ensure_ascii=False, separators=(",", ":")) for x in events) + "\n")


def read_scope() -> dict:
    return json.loads(SCOPE.read_text())


def write_scope(scope: dict) -> None:
    scope["semantics_sha256"] = semantic_hash(scope)
    scope["scope_sha256"] = full_scope_hash(scope)
    SCOPE.write_text(json.dumps(scope, ensure_ascii=False, indent=2) + "\n")


def replace_pointer(text: str, key: str, value: str) -> str:
    pattern = rf"(?m)^- {re.escape(key)}:\s*.*$"
    line = f"- {key}: {value}"
    if re.search(pattern, text):
        return re.sub(pattern, line, text)
    anchor = "- owner_scope_file: ops/OWNER_SCOPE_CURRENT.json"
    if anchor in text:
        return text.replace(anchor, anchor + "\n" + line)
    raise SystemExit(f"OWNER_SCOPE_ADMIN_FAIL:POINTER_ANCHOR:{key}")


def sync_pointers(scope: dict) -> None:
    values = {
        "owner_scope_id": scope["scope_id"],
        "owner_scope_revision": str(scope["revision"]),
        "owner_scope_semantics_sha256": scope["semantics_sha256"],
        "owner_scope_sha256": scope["scope_sha256"],
        "owner_command_ledger": scope["owner_command_ledger"],
        "owner_command_ledger_head": scope["ledger_head_event_sha256"],
    }
    for path in (HANDOVER, CURRENT):
        text = path.read_text()
        for key, value in values.items():
            text = replace_pointer(text, key, value)
        path.write_text(text)


def refresh() -> None:
    events = read_ledger()
    if not events:
        raise SystemExit("OWNER_SCOPE_ADMIN_FAIL:EMPTY_LEDGER")
    scope = read_scope()
    scope["ledger_head_sequence"] = events[-1]["sequence"]
    scope["ledger_head_event_sha256"] = events[-1]["event_sha256"]
    write_scope(scope)
    scope = read_scope()
    sync_pointers(scope)
    print(json.dumps({
        "status": "REFRESHED",
        "scope_id": scope["scope_id"],
        "revision": scope["revision"],
        "semantics_sha256": scope["semantics_sha256"],
        "scope_sha256": scope["scope_sha256"],
        "ledger_head_sequence": scope["ledger_head_sequence"],
    }, ensure_ascii=False))


def append_command(args) -> None:
    raw = args.raw_text.strip()
    if not raw:
        raise SystemExit("OWNER_SCOPE_ADMIN_FAIL:EMPTY_OWNER_TEXT")
    if args.secret_redacted and "[REDACTED_SECRET" not in raw:
        raise SystemExit("OWNER_SCOPE_ADMIN_FAIL:SECRET_REDACTION_MARKER_REQUIRED")
    events = read_ledger()
    seq = len(events) + 1
    prev = events[-1]["event_sha256"] if events else None
    recorded = args.recorded_at or datetime.now(timezone.utc).isoformat()
    event = {
        "sequence": seq,
        "command_id": args.command_id or f"CMD-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{seq:03d}",
        "recorded_at": recorded,
        "source": "OWNER_CHAT",
        "event_type": args.event_type,
        "raw_text": raw,
        "related_requirement_ids": [x for x in args.related.split(",") if x] if args.related else [],
        "previous_event_sha256": prev,
    }
    if args.secret_redacted:
        event["redaction_applied"] = True
        if args.original_sha256:
            event["original_text_sha256"] = args.original_sha256
    event["event_sha256"] = sha_obj(event)
    events.append(event)
    write_ledger(events)
    refresh()


def governance_status(args) -> None:
    scope = read_scope()
    governance = scope.setdefault("governance", {})
    governance["status"] = args.status
    if args.evidence:
        evidence = json.loads(args.evidence)
        if not isinstance(evidence, dict):
            raise SystemExit("OWNER_SCOPE_ADMIN_FAIL:EVIDENCE_NOT_OBJECT")
        governance["technical_evidence"] = evidence
    write_scope(scope)
    scope = read_scope()
    sync_pointers(scope)
    print(json.dumps({
        "status": "GOVERNANCE_STATE_UPDATED",
        "governance_status": governance["status"],
        "semantics_sha256": scope["semantics_sha256"],
        "scope_sha256": scope["scope_sha256"],
    }, ensure_ascii=False))


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("append-command")
    p.add_argument("--raw-text", required=True)
    p.add_argument("--event-type", required=True)
    p.add_argument("--related", default="")
    p.add_argument("--recorded-at")
    p.add_argument("--command-id")
    p.add_argument("--secret-redacted", action="store_true")
    p.add_argument("--original-sha256")
    p.set_defaults(func=append_command)

    p = sub.add_parser("refresh")
    p.set_defaults(func=lambda _args: refresh())

    p = sub.add_parser("governance-status")
    p.add_argument("--status", required=True, choices=[
        "LOCKED_REQUIREMENT_PENDING_FIX",
        "TECHNICAL_PASS_AWAITING_OWNER",
        "ACTIVE_PASS",
        "SUPERSEDED",
    ])
    p.add_argument("--evidence")
    p.set_defaults(func=governance_status)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()

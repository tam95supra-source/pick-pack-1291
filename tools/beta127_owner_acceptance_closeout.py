#!/usr/bin/env python3
import json
import os
import re
from pathlib import Path

try:
    import yaml
except ImportError as exc:
    raise SystemExit(f"OWNER_CLOSEOUT_FAIL:PY_YAML_REQUIRED:{exc}")

ROOT = Path(__file__).resolve().parents[1]
OWNER_RESPONSE = "1 ok 2 ok 3 ok 4 ok 5 ok 6 ok 7 ok 8 ok 9 ok 10 ok 11 ok"
ACCEPTED_AT = "2026-09-05T21:14:36+07:00"
ACCEPTED_AT_UTC = "2026-09-05T14:14:36Z"
STATE_EPOCH = 20260905211436
INVARIANT_IDS = [
    "SETTINGS-RESET-LAYOUT-002",
    "HISTORY-DATE-BULK-DETAIL-003",
    "STATUS-QUEUE-RECOVERY-004",
    "STAFF-SEARCH-DEBOUNCE-001",
    "DROP-PAGINATION-003",
    "REPORT-MANPOWER-LABOR-003",
    "LABOR-BULK-REALTIME-007",
    "PDA-EXCHANGE-SOURCE-002",
    "ATTENDANCE-LOCAL-FIRST-003",
    "QR-INLINE-SHIFT-NAV-003",
    "UI-REALTIME-100MS-006",
]
SCOPES = [
    "settings", "history", "status-sync-service", "staff-search", "drop-receive",
    "manpower-report", "labor", "pda-exchange", "attendance", "qr-navigation", "ui-realtime",
]
EVIDENCE = (
    "Beta127 LIVE exact bytes; source 014ea67eb05773d0d61593f705c2171b5ec574ee; "
    "candidate 33967758178/9970037896; Fast Check 33968559771 PASS; "
    "visual+PDA+API36 33967758178/9970125449 + human PASS 44 screenshots 320x568/360x640/480x800; "
    "runtime DoD 33968559764/9970218116 PASS; terminal publish+OTA+install/readback+finalize 33969468377 PASS; "
    "APK SHA256 922dd571c8e8d6cb5e6d8dbe7fd4f3d73433e14a9f35a50a78d97bf64fa9fbf7; size 14461941; "
    "signer d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e; Stable/main/authority unchanged."
)


def fail(msg: str) -> None:
    raise SystemExit("OWNER_CLOSEOUT_FAIL:" + msg)


def q(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def load_request() -> tuple[Path, dict, list]:
    path = ROOT / "ops/beta-release-request.json"
    req = json.loads(path.read_text())
    checklist = req.get("owner_checklist")
    checks = [
        req.get("stage") == "pass_live",
        req.get("live") is True,
        req.get("version_name") == "0.4.2-beta.127",
        req.get("version_code") == 133,
        req.get("source_sha") == "014ea67eb05773d0d61593f705c2171b5ec574ee",
        req.get("apk_sha256") == "922dd571c8e8d6cb5e6d8dbe7fd4f3d73433e14a9f35a50a78d97bf64fa9fbf7",
        req.get("candidate_locked") is True,
        req.get("technical_pass_status") == "PASS",
        req.get("ota_readback_status") == "PASS",
        req.get("owner_acceptance") == "PENDING",
        isinstance(checklist, list) and len(checklist) == 11,
        isinstance(checklist, list) and [x.get("id") for x in checklist] == list(range(1, 12)),
        req.get("stable_publish") == "FORBIDDEN",
        req.get("authority_change") == "NONE",
    ]
    if not all(checks):
        fail("EXACT_BETA127_FENCE")
    return path, req, checklist


def repair_and_lock_registry(checklist: list) -> None:
    path = ROOT / "qa/stable_invariants.yml"
    text = path.read_text()
    marker = "\nimpact_map:\n"
    if marker not in text:
        fail("IMPACT_MAP_MISSING")
    before, after = text.split(marker, 1)
    misplaced_idx = after.find("\n  - id:")
    if misplaced_idx >= 0:
        impact_body = after[:misplaced_idx].rstrip()
        misplaced = after[misplaced_idx + 1 :].rstrip()
        text = before.rstrip() + "\n\n" + misplaced + "\n\nimpact_map:\n" + impact_body + "\n"

    try:
        parsed = yaml.safe_load(text)
    except Exception as exc:
        fail(f"YAML_REPAIR_PARSE:{exc}")
    if not isinstance(parsed, dict) or not isinstance(parsed.get("invariants"), list) or not isinstance(parsed.get("impact_map"), dict):
        fail("YAML_STRUCTURE")
    existing = {str(x.get("id")) for x in parsed["invariants"] if isinstance(x, dict)}
    present = [x for x in INVARIANT_IDS if x in existing]
    if present and len(present) != len(INVARIANT_IDS):
        fail("PARTIAL_BETA127_INVARIANTS")

    if not present:
        entries: list[str] = []
        for idx, (iid, scope, item) in enumerate(zip(INVARIANT_IDS, SCOPES, checklist), 1):
            rule = " ".join(item["acceptance"])
            entries += [
                f"  - id: {iid}",
                "    status: ACTIVE_PASS",
                f"    scope: {scope}",
                f"    rule: {q(rule)}",
                '    technical_candidate: "0.4.2-beta.127"',
                f"    technical_evidence: {q(EVIDENCE)}",
                f"    owner_acceptance: {q(f'PASS — OWNER item {idx} OK, {ACCEPTED_AT}.')}",
                '    owner_receipt: "ops/beta127-owner-acceptance.json"',
                "    active_pass: true",
                f"    last_verified: {q('0.4.2-beta.127 LIVE / OWNER acceptance complete 11/11 / ' + ACCEPTED_AT)}",
                "",
            ]
        block = "\n".join(entries).rstrip()
        before2, after2 = text.split(marker, 1)
        text = before2.rstrip() + "\n\n" + block + "\n\nimpact_map:\n" + after2
        match = re.search(r'(?m)^  "app/\*\*": \[(.*?)\]$', text)
        if not match:
            fail("APP_IMPACT_MAP_LINE")
        old = [x.strip() for x in match.group(1).split(",") if x.strip()]
        for iid in INVARIANT_IDS:
            if iid not in old:
                old.append(iid)
        replacement = '  "app/**": [' + ", ".join(old) + "]"
        text = text[: match.start()] + replacement + text[match.end() :]

    final = yaml.safe_load(text)
    final_ids = [str(x.get("id")) for x in final["invariants"] if isinstance(x, dict)]
    if any(final_ids.count(i) != 1 for i in INVARIANT_IDS):
        fail("BETA127_ID_CARDINALITY")
    app_impact = final["impact_map"].get("app/**") or []
    if any(i not in app_impact for i in INVARIANT_IDS):
        fail("IMPACT_MAP_MISSING_BETA127")
    path.write_text(text)


def write_stable_markdown(checklist: list) -> None:
    path = ROOT / "docs/STABLE_INVARIANTS.md"
    text = path.read_text()
    header = "## Beta127 — OWNER acceptance R2 11/11 (2026-09-05)"
    if header in text:
        return
    lines = [
        "", header, "",
        f"- OWNER response: `{OWNER_RESPONSE}`",
        f"- Accepted at: `{ACCEPTED_AT}`",
        "- State: all items below are `ACTIVE_PASS`.",
        "- Evidence: exact Beta127 candidate 33967758178/9970037896; Fast Check 33968559771; visual/PDA/API36 33967758178/9970125449 + 44-screen human PASS; runtime 33968559764/9970218116; publish/OTA/install/readback/finalize 33969468377; Stable/main/signer/authority unchanged.",
        "",
    ]
    for idx, (iid, item) in enumerate(zip(INVARIANT_IDS, checklist), 1):
        lines += [
            f"### {iid} — ACTIVE_PASS",
            f"- OWNER item: {idx} — **OK**",
            f"- Rule: {' '.join(item['acceptance'])}",
            "- Owner receipt: `ops/beta127-owner-acceptance.json`",
            "",
        ]
    path.write_text(text.rstrip() + "\n" + "\n".join(lines) + "\n")


def close_release_request(path: Path, req: dict, checklist: list) -> None:
    for item in checklist:
        item["owner_result"] = "OK"
        item["owner_status"] = "ACTIVE_PASS"
        item["owner_accepted_at"] = ACCEPTED_AT
    req["owner_acceptance"] = "COMPLETE"
    req["owner_acceptance_at"] = ACCEPTED_AT
    req["owner_acceptance_response"] = OWNER_RESPONSE
    req["owner_acceptance_receipt"] = "ops/beta127-owner-acceptance.json"
    req["next_action"] = "WAIT_FOR_OWNER_NEW_SCOPE"
    path.write_text(json.dumps(req, ensure_ascii=False, indent=2) + "\n")


def write_receipt(req: dict) -> dict:
    receipt = {
        "schema_version": 1,
        "project": "APK PICK PACK 1291",
        "channel": "BETA",
        "version_name": req["version_name"],
        "version_code": req["version_code"],
        "owner_scope": req["owner_scope"],
        "checklist_id": req["owner_checklist_id"],
        "checklist_revision": req["owner_checklist_revision"],
        "accepted_at": ACCEPTED_AT,
        "owner_response": OWNER_RESPONSE,
        "status": "OWNER_ACCEPTANCE_COMPLETE",
        "items": [
            {"number": n, "invariant_id": iid, "status": "OWNER_OK", "invariant_state": "ACTIVE_PASS"}
            for n, iid in enumerate(INVARIANT_IDS, 1)
        ],
        "technical_evidence": {
            "candidate_run_id": 33967758178,
            "candidate_artifact_id": 9970037896,
            "verify_run_id": 33967758178,
            "verify_artifact_id": 9970125449,
            "fast_check_run_id": 33968559771,
            "runtime_dod_run_id": 33968559764,
            "runtime_dod_artifact_id": 9970218116,
            "terminal_run_id": 33969468377,
            "apk_sha256": req["apk_sha256"],
            "apk_size": req["apk_size"],
            "signer_sha256": req["signer_sha256"],
            "ota_readback": "PASS",
            "human_visual": "PASS",
            "stable_unchanged": True,
            "main_unchanged": True,
            "authority_change": "NONE",
        },
        "next_action": "WAIT_FOR_OWNER_NEW_SCOPE",
    }
    (ROOT / "ops/beta127-owner-acceptance.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n")
    return receipt


def write_ledger(req: dict, checklist: list, receipt: dict) -> None:
    path = ROOT / "ops/owner-acceptance-current.json"
    old = json.loads(path.read_text())
    ledger = {
        "schema_version": 1,
        "state_epoch": STATE_EPOCH,
        "channel": "BETA",
        "public_beta": {
            "version_name": req["version_name"],
            "version_code": req["version_code"],
            "source_sha": req["source_sha"],
            "apk_sha256": req["apk_sha256"],
            "technical_status": "PASS_LIVE",
        },
        "owner_scope": {
            "scope_id": req["owner_scope"],
            "status": "OWNER_ACCEPTANCE_COMPLETE",
            "requirements": [
                {"id": iid, "status": "ACTIVE_PASS", "rule": " ".join(item["acceptance"])}
                for iid, item in zip(INVARIANT_IDS, checklist)
            ],
        },
        "technical_evidence": receipt["technical_evidence"] | {"owner_receipt": "ops/beta127-owner-acceptance.json"},
        "checklist": {
            "checklist_id": req["owner_checklist_id"],
            "revision": req["owner_checklist_revision"],
            "status": "OWNER_ACCEPTANCE_COMPLETE",
            "items": [
                {"number": n, "id": iid, "status": "OWNER_OK", "test": "OWNER explicitly confirmed item OK on Beta127."}
                for n, iid in enumerate(INVARIANT_IDS, 1)
            ],
            "owner_responses": [
                {"recorded_at": ACCEPTED_AT, "response": OWNER_RESPONSE, "items": {str(n): "OK" for n in range(1, 12)}}
            ],
        },
        "previous_acceptance": old,
        "fencing": {
            "reject_lower_state_epoch": True,
            "reject_older_beta_version": True,
            "reject_lower_checklist_revision": True,
            "owner_silence_is_acceptance": False,
        },
        "security": old.get("security", {}),
        "next_action": "WAIT_FOR_OWNER_NEW_SCOPE",
    }
    path.write_text(json.dumps(ledger, ensure_ascii=False, indent=2) + "\n")


def update_current_state() -> None:
    path = ROOT / "CURRENT_STATE.md"
    text = path.read_text()
    text = re.sub(r"^- updated_at: .*$", f"- updated_at: {ACCEPTED_AT_UTC}", text, flags=re.M)
    text = re.sub(r"^- next_action: .*$", "- next_action: WAIT_FOR_OWNER_NEW_SCOPE", text, flags=re.M)
    additions = [
        "- owner_acceptance: COMPLETE (11/11 OWNER OK)",
        f"- owner_acceptance_at: {ACCEPTED_AT}",
        "- owner_acceptance_receipt: ops/beta127-owner-acceptance.json",
    ]
    anchor = "- owner_checklist_revision: 2\n"
    for line in additions:
        if line not in text:
            text = text.replace(anchor, anchor + line + "\n")
    path.write_text(text)


def update_handoff(checklist: list) -> None:
    path = ROOT / "docs/handovers/HANDOVER_CURRENT.md"
    text = path.read_text()
    archive = "docs/handovers/HANDOVER_20260905-211436_beta127-owner-accepted.md"
    text = re.sub(r"^- time_utc: .*$", f"- time_utc: {ACCEPTED_AT_UTC}", text, flags=re.M)
    text = re.sub(r"^- archive_file: .*$", f"- archive_file: {archive}", text, flags=re.M)
    text = text.replace(
        "OWNER acceptance còn PENDING.",
        "OWNER acceptance COMPLETE 11/11; toàn bộ checklist R2 đã được OWNER xác nhận OK và khóa ACTIVE_PASS.",
    )
    text = text.replace(
        "- TARGET: PASS/LIVE, chờ OWNER nghiệm thu đúng checklist của release request.",
        "- TARGET: PASS/LIVE; OWNER acceptance COMPLETE 11/11; chờ scope mới.",
    )
    text = text.replace(
        "Không có blocker kỹ thuật. Technical DoD PASS; đang chờ OWNER nghiệm thu đúng checklist phía trên.",
        "Không có blocker. Technical DoD PASS và OWNER acceptance COMPLETE 11/11.",
    )
    for n, item in enumerate(checklist, 1):
        text = text.replace(
            f"{n}. **{item['title']}**",
            f"{n}. **{item['title']} — ACTIVE_PASS (OWNER OK)**",
        )
    text = re.sub(
        r"## NEXT_ACTION\n.*$",
        "## OWNER ACCEPTANCE\n"
        f"- Response: `{OWNER_RESPONSE}`\n"
        "- Result: **11/11 OWNER OK — ACTIVE_PASS**\n"
        "- Receipt: `ops/beta127-owner-acceptance.json`\n\n"
        "## NEXT_ACTION\nWAIT_FOR_OWNER_NEW_SCOPE",
        text,
        flags=re.S,
    )
    path.write_text(text)
    (ROOT / archive).write_text(text)


def verify_worktree() -> None:
    req = json.loads((ROOT / "ops/beta-release-request.json").read_text())
    if req.get("owner_acceptance") != "COMPLETE" or req.get("next_action") != "WAIT_FOR_OWNER_NEW_SCOPE":
        fail("REQUEST_CLOSEOUT")
    if len(req.get("owner_checklist", [])) != 11 or any(x.get("owner_result") != "OK" or x.get("owner_status") != "ACTIVE_PASS" for x in req["owner_checklist"]):
        fail("REQUEST_ITEMS")
    data = yaml.safe_load((ROOT / "qa/stable_invariants.yml").read_text())
    inv = {x["id"]: x for x in data["invariants"]}
    if any(inv.get(i, {}).get("status") != "ACTIVE_PASS" for i in INVARIANT_IDS):
        fail("REGISTRY_ACTIVE_PASS")
    if any(i not in data["impact_map"]["app/**"] for i in INVARIANT_IDS):
        fail("REGISTRY_IMPACT_MAP")
    ledger = json.loads((ROOT / "ops/owner-acceptance-current.json").read_text())
    if ledger["public_beta"]["version_name"] != "0.4.2-beta.127" or ledger["checklist"]["status"] != "OWNER_ACCEPTANCE_COMPLETE" or len(ledger["checklist"]["items"]) != 11:
        fail("LEDGER")
    print("BETA127_OWNER_ACCEPTANCE_11_OF_11_WORKTREE_PASS")


def main() -> None:
    req_path, req, checklist = load_request()
    repair_and_lock_registry(checklist)
    write_stable_markdown(checklist)
    close_release_request(req_path, req, checklist)
    receipt = write_receipt(req)
    write_ledger(req, checklist, receipt)
    update_current_state()
    update_handoff(checklist)
    verify_worktree()


if __name__ == "__main__":
    main()

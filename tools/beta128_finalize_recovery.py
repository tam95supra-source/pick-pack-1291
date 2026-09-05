#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from owner_scope_guard_v2 import semantic_hash, full_scope_hash  # noqa: E402
from owner_scope_admin import sync_pointers  # noqa: E402

SCOPE = ROOT / "ops/OWNER_SCOPE_CURRENT.json"
REQUEST = ROOT / "ops/beta-release-request.json"
REGISTRY = ROOT / "qa/stable_invariants.yml"
DOCS = ROOT / "docs/STABLE_INVARIANTS.md"
CURRENT = ROOT / "CURRENT_STATE.md"
HANDOVER = ROOT / "docs/handovers/HANDOVER_CURRENT.md"

TARGETS = {
    "R2-07": "LABOR-BULK-REALTIME-007",
    "R2-09": "ATTENDANCE-LOCAL-FIRST-003",
    "R2-10": "QR-INLINE-SHIFT-NAV-003",
    "R2-11": "UI-REALTIME-100MS-006",
    "R3-12": "DROP-LAYOUT-INPUT-004",
}


def dump_json(path: Path, obj: dict) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def update_yaml_invariant(text: str, invariant_id: str, candidate: str, evidence: str) -> str:
    pat = re.compile(rf"(?ms)(^  - id: {re.escape(invariant_id)}\n)(.*?)(?=^  - id: |^impact_map:|\Z)")
    m = pat.search(text)
    if not m:
        raise SystemExit(f"BETA128_RECOVERY_FAIL:REGISTRY_MISSING:{invariant_id}")
    body = m.group(2)
    if not re.search(r"(?m)^    status: [A-Z_]+$", body):
        raise SystemExit(f"BETA128_RECOVERY_FAIL:REGISTRY_STATUS_MISSING:{invariant_id}")
    body = re.sub(r"(?m)^    status: [A-Z_]+$", "    status: TECHNICAL_PASS_AWAITING_OWNER", body, count=1)
    cand_line = f"    technical_candidate: {json.dumps(candidate, ensure_ascii=False)}"
    if re.search(r"(?m)^    technical_candidate: .+$", body):
        body = re.sub(r"(?m)^    technical_candidate: .+$", cand_line, body, count=1)
    else:
        body = re.sub(r"(?m)^(    status: TECHNICAL_PASS_AWAITING_OWNER)$", rf"\1\n{cand_line}", body, count=1)
    ev_line = f"    technical_evidence: {json.dumps(evidence, ensure_ascii=False)}"
    if re.search(r"(?m)^    technical_evidence: .+$", body):
        body = re.sub(r"(?m)^    technical_evidence: .+$", ev_line, body, count=1)
    else:
        body = re.sub(r"(?m)^(    technical_candidate: .+)$", rf"\1\n{ev_line}", body, count=1)
    return text[:m.start()] + m.group(1) + body + text[m.end():]


def update_docs_invariant(text: str, invariant_id: str, candidate: str, evidence: str) -> str:
    # Canonical docs encode lifecycle in the heading itself, e.g.
    # "### ID — LOCKED_REQUIREMENT_PENDING_FIX", rather than a mandatory Status row.
    pat = re.compile(rf"(?ms)^### {re.escape(invariant_id)}(?: — [A-Z_]+)?\n(.*?)(?=^### |\Z)")
    m = pat.search(text)
    if not m:
        raise SystemExit(f"BETA128_RECOVERY_FAIL:DOCS_MISSING:{invariant_id}")
    body = m.group(1)
    if re.search(r"(?m)^- Status: [A-Z_]+$", body):
        body = re.sub(r"(?m)^- Status: [A-Z_]+$", "- Status: TECHNICAL_PASS_AWAITING_OWNER", body, count=1)
    cand_line = f"- Technical candidate: {candidate}"
    if re.search(r"(?m)^- Technical candidate: .+$", body):
        body = re.sub(r"(?m)^- Technical candidate: .+$", cand_line, body, count=1)
    else:
        body = body.rstrip() + "\n" + cand_line + "\n"
    ev_line = f"- Technical evidence Beta128: {evidence}"
    if re.search(r"(?m)^- Technical evidence Beta128: .+$", body):
        body = re.sub(r"(?m)^- Technical evidence Beta128: .+$", ev_line, body, count=1)
    else:
        body = body.rstrip() + "\n" + ev_line + "\n\n"
    replacement = f"### {invariant_id} — TECHNICAL_PASS_AWAITING_OWNER\n" + body
    return text[:m.start()] + replacement + text[m.end():]


def replace_current_next_action(text: str, next_action: str) -> str:
    if re.search(r"(?m)^- next_action: .+$", text):
        return re.sub(r"(?m)^- next_action: .+$", f"- next_action: {next_action}", text, count=1)
    return text.rstrip() + f"\n- next_action: {next_action}\n"


def replace_handover_next_action(text: str, next_action: str) -> str:
    marker = "## NEXT_ACTION"
    if marker not in text:
        raise SystemExit("BETA128_RECOVERY_FAIL:HANDOVER_NEXT_ACTION_MISSING")
    return re.sub(r"(?ms)(## NEXT_ACTION\n).*?(?=\n## |\Z)", rf"\1{next_action}\n", text, count=1)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--release-run", required=True, type=int)
    p.add_argument("--publish-artifact", required=True, type=int)
    p.add_argument("--pda-artifact", required=True, type=int)
    p.add_argument("--fast-check-run", required=True, type=int)
    p.add_argument("--control-plane-run", required=True, type=int)
    p.add_argument("--recovery-run", required=True, type=int)
    args = p.parse_args()

    scope = json.loads(SCOPE.read_text(encoding="utf-8"))
    request = json.loads(REQUEST.read_text(encoding="utf-8"))
    if scope.get("scope_id") != "OWNER_20260905_R3_DROP_REALTIME_BETA128" or scope.get("revision") != 3:
        raise SystemExit("BETA128_RECOVERY_FAIL:SCOPE_ID_OR_REVISION")
    if request.get("version_name") != "0.4.2-beta.128" or request.get("version_code") != 134:
        raise SystemExit("BETA128_RECOVERY_FAIL:VERSION")
    if request.get("stage") != "pass_live" or request.get("ota_readback_status") != "PASS":
        raise SystemExit(f"BETA128_RECOVERY_FAIL:FINALIZER_NOT_LIVE:{request.get('stage')}:{request.get('ota_readback_status')}")
    old_semantics = scope.get("semantics_sha256")
    old_revision = scope.get("revision")

    evidence_text = (
        f"Beta128 LIVE exact bytes; source {request['candidate_source_sha']}; "
        f"candidate {request['candidate_run_id']}/{request['candidate_artifact_id']}; "
        f"Fast Check {args.fast_check_run} PASS; control-plane {args.control_plane_run} PASS; "
        f"visual/PDA/API36 {request['verify_run_id']}/{request['verify_artifact_id']} + human PASS "
        f"{request['human_visual_screenshot_count']} screenshots 320x568/360x640/480x800; "
        f"runtime DoD {request['runtime_dod_run_id']}/{request['runtime_dod_artifact_id']} PASS; "
        f"publish/OTA/install/readback run {args.release_run} artifacts {args.publish_artifact}/{args.pda_artifact} PASS; "
        f"APK SHA256 {request['apk_sha256']}; size {request['apk_size']}; signer {request['signer_sha256']}; "
        "Stable/main/authority unchanged."
    )
    evidence_obj = {
        "version_name": request["version_name"],
        "source_sha": request["candidate_source_sha"],
        "candidate_run_id": request["candidate_run_id"],
        "candidate_artifact_id": request["candidate_artifact_id"],
        "verify_run_id": request["verify_run_id"],
        "verify_artifact_id": request["verify_artifact_id"],
        "fast_check_run_id": args.fast_check_run,
        "control_plane_run_id": args.control_plane_run,
        "runtime_dod_run_id": request["runtime_dod_run_id"],
        "runtime_dod_artifact_id": request["runtime_dod_artifact_id"],
        "release_run_id": args.release_run,
        "publish_artifact_id": args.publish_artifact,
        "pda_ota_artifact_id": args.pda_artifact,
        "apk_sha256": request["apk_sha256"],
        "apk_size": request["apk_size"],
        "signer_sha256": request["signer_sha256"],
        "status": "PASS",
    }

    req_by_id = {x["requirement_id"]: x for x in scope["requirements"]}
    for rid, invariant_id in TARGETS.items():
        item = req_by_id[rid]
        if item.get("invariant_id") != invariant_id:
            raise SystemExit(f"BETA128_RECOVERY_FAIL:INVARIANT_MAP:{rid}")
        if item.get("state") not in {"LOCKED_REQUIREMENT_PENDING_FIX", "TECHNICAL_PASS_AWAITING_OWNER"}:
            raise SystemExit(f"BETA128_RECOVERY_FAIL:UNEXPECTED_STATE:{rid}:{item.get('state')}")
        item["state"] = "TECHNICAL_PASS_AWAITING_OWNER"
        item["technical_evidence"] = evidence_obj

    for item in scope["requirements"]:
        if item["requirement_id"] not in TARGETS and item.get("state") != "ACTIVE_PASS":
            raise SystemExit(f"BETA128_RECOVERY_FAIL:PREVIOUS_ACCEPTANCE_DRIFT:{item['requirement_id']}:{item.get('state')}")

    scope["scope_status"] = "TECHNICAL_PASS_AWAITING_OWNER"
    governance = scope.setdefault("governance", {})
    governance["status"] = "TECHNICAL_PASS_AWAITING_OWNER"
    governance["technical_evidence"] = {
        "control_plane_run_id": args.control_plane_run,
        "recovery_run_id": args.recovery_run,
        "status": "PASS",
        "note": "Bootstrap/hash/ledger/finalizer recovery verified; app/service/APK bytes unchanged by recovery.",
    }
    scope["release_binding"] = {
        "mode": "CURRENT_RELEASE",
        "base_live_version_name": request.get("base_version"),
        "live_version_name": request["version_name"],
        "live_version_code": request["version_code"],
        "candidate_source_sha": request["candidate_source_sha"],
        "candidate_run_id": request["candidate_run_id"],
        "candidate_artifact_id": request["candidate_artifact_id"],
        "apk_sha256": request["apk_sha256"],
        "apk_size": request["apk_size"],
        "terminal_run_id": args.release_run,
        "ota_readback_status": "PASS",
        "owner_acceptance": "PENDING",
    }
    scope["semantics_sha256"] = semantic_hash(scope)
    if scope["semantics_sha256"] != old_semantics or scope["revision"] != old_revision:
        raise SystemExit("BETA128_RECOVERY_FAIL:SEMANTIC_OR_REVISION_DRIFT")
    scope["scope_sha256"] = full_scope_hash(scope)
    dump_json(SCOPE, scope)

    registry = REGISTRY.read_text(encoding="utf-8")
    docs = DOCS.read_text(encoding="utf-8")
    for invariant_id in TARGETS.values():
        registry = update_yaml_invariant(registry, invariant_id, request["version_name"], evidence_text)
        docs = update_docs_invariant(docs, invariant_id, request["version_name"], evidence_text)
    REGISTRY.write_text(registry, encoding="utf-8")
    DOCS.write_text(docs, encoding="utf-8")

    sync_pointers(scope)

    pending_numbers = [str(x["checklist_number"]) for x in scope["requirements"] if x["state"] == "TECHNICAL_PASS_AWAITING_OWNER"]
    if pending_numbers != ["7", "9", "10", "11", "12"]:
        raise SystemExit(f"BETA128_RECOVERY_FAIL:PENDING_CHECKLIST:{pending_numbers}")
    next_action = "WAIT_FOR_OWNER_ACCEPTANCE_REQUIREMENTS_" + "_".join(pending_numbers)

    request = json.loads(REQUEST.read_text(encoding="utf-8"))
    request["owner_scope_semantics_sha256"] = scope["semantics_sha256"]
    request["owner_scope_sha256"] = scope["scope_sha256"]
    request["technical_pass_status"] = "PASS"
    request["owner_acceptance"] = "PENDING"
    request["ota_readback_status"] = "PASS"
    request["next_action"] = next_action
    request["technical_pass_requirement_numbers"] = [int(x) for x in pending_numbers]
    request["technical_pass_recovery_run_id"] = args.recovery_run
    dump_json(REQUEST, request)

    CURRENT.write_text(replace_current_next_action(CURRENT.read_text(encoding="utf-8"), next_action), encoding="utf-8")
    HANDOVER.write_text(replace_handover_next_action(HANDOVER.read_text(encoding="utf-8"), next_action), encoding="utf-8")

    print(json.dumps({
        "status": "TECHNICAL_PASS_AWAITING_OWNER",
        "scope_id": scope["scope_id"],
        "revision": scope["revision"],
        "semantics_sha256": scope["semantics_sha256"],
        "scope_sha256": scope["scope_sha256"],
        "pending_owner_checklist_numbers": [int(x) for x in pending_numbers],
        "next_action": next_action,
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()

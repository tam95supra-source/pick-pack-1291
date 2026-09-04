#!/usr/bin/env python3
import json
import re
from pathlib import Path

LEDGER = Path("ops/owner-acceptance-current.json")
DOC = Path("docs/STABLE_INVARIANTS.md")
REG = Path("qa/stable_invariants.yml")
TARGETS = ("CURRENT_PUBLIC_BETA_001", "SUPERADMIN_AUTH_002", "OWNER_ACCEPTANCE_LEDGER_001")


def replace_one(text: str, pattern: str, repl: str, label: str) -> str:
    out, n = re.subn(pattern, repl, text, count=1, flags=re.M)
    if n != 1:
        raise SystemExit(f"OWNER_ACCEPTANCE_APPLY_FAIL:{label}:count={n}")
    return out


def update_doc_section(text: str, invariant_id: str, status: str, owner_line: str, evidence_line: str | None = None) -> str:
    marker = f"### {invariant_id}\n"
    start = text.find(marker)
    if start < 0:
        raise SystemExit("OWNER_ACCEPTANCE_APPLY_FAIL:DOC_MISSING:" + invariant_id)
    end = text.find("\n### ", start + len(marker))
    if end < 0:
        end = len(text)
    section = text[start:end]
    section = replace_one(section, r"^- Status: [^\n]+$", f"- Status: {status}", "DOC_STATUS_" + invariant_id)
    section = replace_one(section, r"^- OWNER acceptance: [^\n]+$", f"- OWNER acceptance: {owner_line}", "DOC_OWNER_" + invariant_id)
    if evidence_line is not None:
        section = replace_one(section, r"^- Technical evidence: [^\n]+$", f"- Technical evidence: {evidence_line}", "DOC_EVIDENCE_" + invariant_id)
    return text[:start] + section + text[end:]


def main() -> None:
    ledger = json.loads(LEDGER.read_text())
    if ledger.get("schema_version") != 1 or ledger.get("channel") != "BETA":
        raise SystemExit("OWNER_ACCEPTANCE_APPLY_FAIL:LEDGER_SCHEMA")
    public = ledger.get("public_beta") or {}
    if public.get("version_name") != "0.4.2-beta.119" or public.get("technical_status") != "PASS_LIVE":
        raise SystemExit("OWNER_ACCEPTANCE_APPLY_FAIL:NOT_BETA119_PASS_LIVE")
    checklist = ledger.get("checklist") or {}
    revision = int(checklist.get("revision", 0))
    if checklist.get("checklist_id") != "BETA119_OWNER_ACCEPTANCE_20260904_R1" or revision < 2:
        raise SystemExit("OWNER_ACCEPTANCE_APPLY_FAIL:CHECKLIST_NOT_ADVANCED")

    reqs = {x.get("id"): x.get("status") for x in (ledger.get("owner_scope") or {}).get("requirements", []) if isinstance(x, dict)}
    for target in TARGETS:
        if target not in reqs:
            raise SystemExit("OWNER_ACCEPTANCE_APPLY_FAIL:MISSING_REQUIREMENT:" + target)

    doc = DOC.read_text()
    doc = update_doc_section(
        doc,
        "CURRENT_PUBLIC_BETA_001",
        reqs["CURRENT_PUBLIC_BETA_001"],
        "PASS — OWNER checklist item 1 OK, 2026-09-04 19:11 +07:00.",
    )
    doc = update_doc_section(
        doc,
        "SUPERADMIN_AUTH_002",
        reqs["SUPERADMIN_AUTH_002"],
        "PASS — OWNER checklist items 2, 3, 4 OK, 2026-09-04 19:11 +07:00.",
    )
    ledger_owner = "PASS — OWNER confirmed." if reqs["OWNER_ACCEPTANCE_LEDGER_001"] == "ACTIVE_PASS" else "PENDING — technical self-check PASS; waiting explicit OWNER item 5 OK."
    doc = update_doc_section(
        doc,
        "OWNER_ACCEPTANCE_LEDGER_001",
        reqs["OWNER_ACCEPTANCE_LEDGER_001"],
        ledger_owner,
        f"Beta119 ledger state epoch `202609041911`, checklist `BETA119_OWNER_ACCEPTANCE_20260904_R1`, revision {revision}; fresh-read `beta/current` preserved Beta119/revision; monotonic control-plane guard run `33871649452` PASS including stale acceptance rejection.",
    )
    DOC.write_text(doc)

    reg = REG.read_text()
    for target in TARGETS:
        reg = replace_one(reg, rf"^(  - id: {re.escape(target)}\n    status: )[^\n]+$", rf"\1{reqs[target]}", "REG_STATUS_" + target)
    reg = replace_one(reg, r'^(  - id: CURRENT_PUBLIC_BETA_001(?:\n(?!  - id:).*)*\n    owner_acceptance: )[^\n]+$', r'\1"OWNER_ITEM_1_OK_2026-09-04T19:11+07:00"', "REG_CURRENT_OWNER")
    reg = replace_one(reg, r'^(  - id: SUPERADMIN_AUTH_002(?:\n(?!  - id:).*)*\n    owner_acceptance: )[^\n]+$', r'\1"OWNER_ITEMS_2_3_4_OK_2026-09-04T19:11+07:00"', "REG_AUTH_OWNER")
    ledger_owner_reg = '"OWNER_OK"' if reqs["OWNER_ACCEPTANCE_LEDGER_001"] == "ACTIVE_PASS" else '"PENDING_TECHNICAL_SELF_CHECK_PASS_RUN_33871649452"'
    reg = replace_one(reg, r'^(  - id: OWNER_ACCEPTANCE_LEDGER_001(?:\n(?!  - id:).*)*\n    technical_evidence: )[^\n]+$', rf'\1"ops/owner-acceptance-current.json epoch 202609041911 / BETA119_OWNER_ACCEPTANCE_20260904_R1 rev{revision}; fresh-read beta/current PASS; monotonic guard 33871649452 PASS"', "REG_LEDGER_EVIDENCE")
    reg = replace_one(reg, r'^(  - id: OWNER_ACCEPTANCE_LEDGER_001(?:\n(?!  - id:).*)*\n    owner_acceptance: )[^\n]+$', rf'\1{ledger_owner_reg}', "REG_LEDGER_OWNER")
    REG.write_text(reg)
    print("beta119_owner_acceptance_apply=PASS revision=" + str(revision))


if __name__ == "__main__":
    main()

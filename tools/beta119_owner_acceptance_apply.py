#!/usr/bin/env python3
import json
import re
from pathlib import Path

LEDGER = Path("ops/owner-acceptance-current.json")
DOC = Path("docs/STABLE_INVARIANTS.md")
REG = Path("qa/stable_invariants.yml")
B119_TARGETS = ("CURRENT_PUBLIC_BETA_001", "SUPERADMIN_AUTH_002", "OWNER_ACCEPTANCE_LEDGER_001")
B120_ID = "OLD-SESSION-BULK-EXIT-001"


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


def apply_beta119(ledger: dict) -> None:
    checklist = ledger.get("checklist") or {}
    revision = int(checklist.get("revision", 0))
    if checklist.get("checklist_id") != "BETA119_OWNER_ACCEPTANCE_20260904_R1" or revision < 2:
        raise SystemExit("OWNER_ACCEPTANCE_APPLY_FAIL:CHECKLIST_NOT_ADVANCED")
    reqs = {x.get("id"): x.get("status") for x in (ledger.get("owner_scope") or {}).get("requirements", []) if isinstance(x, dict)}
    for target in B119_TARGETS:
        if target not in reqs:
            raise SystemExit("OWNER_ACCEPTANCE_APPLY_FAIL:MISSING_REQUIREMENT:" + target)

    doc = DOC.read_text()
    doc = update_doc_section(doc, "CURRENT_PUBLIC_BETA_001", reqs["CURRENT_PUBLIC_BETA_001"], "PASS — OWNER checklist item 1 OK, 2026-09-04 19:11 +07:00.")
    doc = update_doc_section(doc, "SUPERADMIN_AUTH_002", reqs["SUPERADMIN_AUTH_002"], "PASS — OWNER checklist items 2, 3, 4 OK, 2026-09-04 19:11 +07:00.")
    ledger_owner = "PASS — OWNER confirmed." if reqs["OWNER_ACCEPTANCE_LEDGER_001"] == "ACTIVE_PASS" else "PENDING — technical self-check PASS; waiting explicit OWNER item 5 OK."
    doc = update_doc_section(doc, "OWNER_ACCEPTANCE_LEDGER_001", reqs["OWNER_ACCEPTANCE_LEDGER_001"], ledger_owner, f"Beta119 ledger state epoch `202609041911`, checklist `BETA119_OWNER_ACCEPTANCE_20260904_R1`, revision {revision}; fresh-read `beta/current` preserved Beta119/revision; monotonic control-plane guard run `33871649452` PASS including stale acceptance rejection.")
    DOC.write_text(doc)

    reg = REG.read_text()
    for target in B119_TARGETS:
        reg = replace_one(reg, rf"^(  - id: {re.escape(target)}\n    status: )[^\n]+$", rf"\1{reqs[target]}", "REG_STATUS_" + target)
    reg = replace_one(reg, r'^(  - id: CURRENT_PUBLIC_BETA_001(?:\n(?!  - id:).*)*\n    owner_acceptance: )[^\n]+$', r'\1"OWNER_ITEM_1_OK_2026-09-04T19:11+07:00"', "REG_CURRENT_OWNER")
    reg = replace_one(reg, r'^(  - id: SUPERADMIN_AUTH_002(?:\n(?!  - id:).*)*\n    owner_acceptance: )[^\n]+$', r'\1"OWNER_ITEMS_2_3_4_OK_2026-09-04T19:11+07:00"', "REG_AUTH_OWNER")
    ledger_owner_reg = '"OWNER_OK"' if reqs["OWNER_ACCEPTANCE_LEDGER_001"] == "ACTIVE_PASS" else '"PENDING_TECHNICAL_SELF_CHECK_PASS_RUN_33871649452"'
    reg = replace_one(reg, r'^(  - id: OWNER_ACCEPTANCE_LEDGER_001(?:\n(?!  - id:).*)*\n    technical_evidence: )[^\n]+$', rf'\1"ops/owner-acceptance-current.json epoch 202609041911 / BETA119_OWNER_ACCEPTANCE_20260904_R1 rev{revision}; fresh-read beta/current PASS; monotonic guard 33871649452 PASS"', "REG_LEDGER_EVIDENCE")
    reg = replace_one(reg, r'^(  - id: OWNER_ACCEPTANCE_LEDGER_001(?:\n(?!  - id:).*)*\n    owner_acceptance: )[^\n]+$', rf'\1{ledger_owner_reg}', "REG_LEDGER_OWNER")
    REG.write_text(reg)
    print("beta119_owner_acceptance_apply=PASS revision=" + str(revision))


def add_impact(reg: str, key: str, invariant_id: str) -> str:
    pattern = rf'^(  "{re.escape(key)}": \[)([^\n]*)(\])$'
    match = re.search(pattern, reg, flags=re.M)
    if not match:
        raise SystemExit("OWNER_ACCEPTANCE_APPLY_FAIL:IMPACT_MISSING:" + key)
    items = [x.strip() for x in match.group(2).split(",") if x.strip()]
    if invariant_id not in items:
        items.append(invariant_id)
    replacement = match.group(1) + ", ".join(items) + match.group(3)
    return reg[:match.start()] + replacement + reg[match.end():]


def apply_beta120(ledger: dict) -> None:
    checklist = ledger.get("checklist") or {}
    if checklist.get("checklist_id") != "BETA120_OWNER_ACCEPTANCE_20260904_R1" or checklist.get("status") != "OWNER_ACCEPTANCE_COMPLETE":
        raise SystemExit("OWNER_ACCEPTANCE_APPLY_FAIL:BETA120_CHECKLIST")
    reqs = {x.get("id"): x.get("status") for x in (ledger.get("owner_scope") or {}).get("requirements", []) if isinstance(x, dict)}
    if reqs.get(B120_ID) != "ACTIVE_PASS":
        raise SystemExit("OWNER_ACCEPTANCE_APPLY_FAIL:BETA120_OWNER_NOT_ACTIVE")

    evidence = "Beta120 LIVE; candidate 33874862142/9937580926; Fast Check 33874862122 PASS; Service + visual/PDA/API36 33876606829 PASS; device/discovery 33895538590/9945644548 PASS; runtime 33895822870/9945717299 PASS; domain 33896047850/9945767325 PASS; terminal 33896192267 publish exact bytes + OTA install/open/readback + finalize PASS; APK SHA256 04d9f4b88e6ff038766357402f7f5831de67649087c839f922897042120b8ef8 size 14429173 signer d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e; Stable/main/authority unchanged."

    doc = DOC.read_text()
    if f"### {B120_ID}\n" not in doc:
        section = f'''\n### {B120_ID}\n- Status: ACTIVE_PASS\n- Scope: Cảnh báo phiên cũ / SUPERADMIN / Ra ca tất cả hợp lệ\n- Rule: `Ra ca tất cả hợp lệ` phải gọi trực tiếp Service authority; xử lý bounded/idempotent theo lô nhỏ; một phiên lỗi không được làm treo toàn lô; labor OPEN phải skip; canonical commitMutation/audit giữ nguyên.\n- Regression: direct Service route + bounded batch + idempotency + failure isolation + labor skip + remaining readback + Stable/authority unchanged.\n- Regression case: `tools/beta120_bulk_exit_contract.py`.\n- Technical evidence: {evidence}\n- OWNER acceptance: PASS — OWNER xác nhận phần `Ra ca` đã OK ngày 2026-09-04.\n- Owner receipt: `ops/beta120-owner-acceptance.json`.\n- Last verified: `0.4.2-beta.120` LIVE.\n'''
        marker = "\n## 4. LOCKED_REQUIREMENT_PENDING_FIX / AWAITING OWNER / DEFERRED\n"
        doc = doc.replace(marker, section + marker, 1) if marker in doc else doc + section
    else:
        doc = update_doc_section(doc, B120_ID, "ACTIVE_PASS", "PASS — OWNER xác nhận phần `Ra ca` đã OK ngày 2026-09-04.", evidence)
    DOC.write_text(doc)

    reg = REG.read_text()
    if f"  - id: {B120_ID}\n" not in reg:
        block = f'''\n  - id: {B120_ID}\n    status: ACTIVE_PASS\n    scope: old-session-bulk-exit\n    rule: "SUPERADMIN 'Ra ca tất cả hợp lệ' phải đi trực tiếp Service authority; xử lý theo lô nhỏ bounded + idempotent; một phiên lỗi không được làm treo các phiên hợp lệ khác; phiên có labor OPEN phải được skip; canonical commitMutation/audit giữ nguyên."\n    regression_minimum: [direct_service_route, bounded_batch, idempotency, failed_session_isolation, labor_skip, remaining_readback, no_stable_authority_change]\n    regression_case: "tools/beta120_bulk_exit_contract.py"\n    technical_candidate: "0.4.2-beta.120 / b8f548d5717156554b8599955f62ab23f9973fc9"\n    technical_evidence: "{evidence}"\n    owner_acceptance: "OWNER_OK_BETA120_BULK_EXIT_2026-09-04"\n    owner_receipt: "ops/beta120-owner-acceptance.json"\n    active_pass: true\n    last_verified: "0.4.2-beta.120 LIVE / terminal run 33896192267 / OWNER acceptance complete 2026-09-04"\n'''
        marker = "\nimpact_map:\n"
        if marker not in reg:
            raise SystemExit("OWNER_ACCEPTANCE_APPLY_FAIL:REGISTRY_MARKER")
        reg = reg.replace(marker, block + marker, 1)
    reg = add_impact(reg, "app/**", B120_ID)
    reg = add_impact(reg, "service/**", B120_ID)

    current_marker = "  - id: CURRENT_PUBLIC_BETA_001\n"
    current_start = reg.find(current_marker)
    if current_start >= 0:
        current_end = reg.find("\n  - id: ", current_start + len(current_marker))
        if current_end < 0:
            current_end = reg.find("\nimpact_map:", current_start)
        section = reg[current_start:current_end]
        reverify = '    latest_reverification: "0.4.2-beta.120 LIVE / source b8f548d5717156554b8599955f62ab23f9973fc9 / terminal 33896192267 / exact OTA-install-readback-finalize PASS / SHA256 04d9f4b88e6ff038766357402f7f5831de67649087c839f922897042120b8ef8; Stable/main/signer/authority unchanged"\n'
        if "    latest_reverification:" in section:
            section = re.sub(r'^    latest_reverification: [^\n]+\n?', reverify, section, count=1, flags=re.M)
        else:
            section = section.rstrip("\n") + "\n" + reverify
        reg = reg[:current_start] + section + reg[current_end:]

    ledger_marker = "  - id: OWNER_ACCEPTANCE_LEDGER_001\n"
    ledger_start = reg.find(ledger_marker)
    if ledger_start >= 0:
        ledger_end = reg.find("\n  - id: ", ledger_start + len(ledger_marker))
        if ledger_end < 0:
            ledger_end = reg.find("\nimpact_map:", ledger_start)
        section = reg[ledger_start:ledger_end]
        evidence_line = f'    latest_reverification: "ops/owner-acceptance-current.json epoch {ledger.get("state_epoch")} / BETA120_OWNER_ACCEPTANCE_20260904_R1 rev{checklist.get("revision")}; Beta120 OWNER acceptance complete; stale lower Beta/revision fencing preserved"\n'
        if "    latest_reverification:" in section:
            section = re.sub(r'^    latest_reverification: [^\n]+\n?', evidence_line, section, count=1, flags=re.M)
        else:
            section = section.rstrip("\n") + "\n" + evidence_line
        reg = reg[:ledger_start] + section + reg[ledger_end:]

    REG.write_text(reg)
    print("beta120_owner_acceptance_apply=PASS")


def main() -> None:
    ledger = json.loads(LEDGER.read_text())
    if ledger.get("schema_version") != 1 or ledger.get("channel") != "BETA":
        raise SystemExit("OWNER_ACCEPTANCE_APPLY_FAIL:LEDGER_SCHEMA")
    public = ledger.get("public_beta") or {}
    if public.get("technical_status") != "PASS_LIVE":
        raise SystemExit("OWNER_ACCEPTANCE_APPLY_FAIL:NOT_PASS_LIVE")
    version = public.get("version_name")
    if version == "0.4.2-beta.119":
        apply_beta119(ledger)
    elif version == "0.4.2-beta.120":
        apply_beta120(ledger)
    else:
        raise SystemExit("OWNER_ACCEPTANCE_APPLY_FAIL:UNSUPPORTED_BETA:" + str(version))


if __name__ == "__main__":
    main()

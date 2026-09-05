#!/usr/bin/env python3
import json
import sys
from pathlib import Path

root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
req_path = root / "ops/beta-release-request.json"
req = json.loads(req_path.read_text(encoding="utf-8"))

EXPECTED = {
    "version_name": "0.4.2-beta.121",
    "version_code": 127,
    "package": "vn.pickpack1291.app.beta.publicbeta",
    "source_sha": "ee482efb41565eee797b9b6c11fe54557c2b67f8",
    "apk_sha256": "5b042c8e1f6d288ef19efe9abc773562c204fb3defd91396e4101adcedc8cc57",
    "apk_size": 14429173,
    "signer_sha256": "d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e",
}
for k, v in EXPECTED.items():
    assert req.get(k) == v, (k, req.get(k), v)
assert req.get("stage") == "pass_live"
assert req.get("live") is True
assert req.get("technical_pass_status") == "PASS"
assert req.get("owner_acceptance") == "PENDING"
assert req.get("ota_readback_status") == "PASS"
assert req.get("publish_run_id") == "33934142254"
assert req.get("stable_publish") == "FORBIDDEN"
assert req.get("authority_change") == "NONE"
assert req.get("apk_transport") == "GITHUB_RELEASE_ONLY"
assert req.get("google_drive_apk") == "FORBIDDEN"

EVIDENCE = (
    "0.4.2-beta.121 Technical PASS/LIVE; source ee482efb41565eee797b9b6c11fe54557c2b67f8; "
    "candidate 33929895214/9958252319; Service 33929895214/9958376646; Fast Check 33932137056; "
    "visual+PDA+API36 33932137068/9959024622 + human PASS 43 screenshots 320x568/360x640/480x800; "
    "device/discovery 33932666498/9959133081; runtime DoD 33933735030/9959507710; "
    "Beta domain 33934032820/9959551837; OTA baseline recovery 33934523152/9959702930; "
    "terminal publish/OTA/install/open/readback/finalize 33934142254; publish 9959732997; "
    "OTA device 9959773897; final 9959777958; SHA256 5b042c8e1f6d288ef19efe9abc773562c204fb3defd91396e4101adcedc8cc57; "
    "size 14429173; signer d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e; "
    "Stable/main/authority unchanged."
)

md = root / "docs/STABLE_INVARIANTS.md"
s = md.read_text(encoding="utf-8").rstrip() + "\n"
marker = "## Beta121 — TECHNICAL_PASS_AWAITING_OWNER"
if marker not in s:
    s += f'''\n\n{marker}\n\nTechnical receipt: `ops/beta121-technical-pass.json`. Regression: `tools/beta121_owner_ui_pda_source_contract.py`. Bốn mục mới chỉ chuyển sang ACTIVE_PASS sau OWNER xác nhận từng mục.\n\n### UI-STATUS-DETAIL-VI-003\n- Status: TECHNICAL_PASS_AWAITING_OWNER\n- Scope: UI / status header + detail dialogs\n- Parent: UI-STATUS-001 ACTIVE_PASS.\n- Rule: 3 ô Mạng / Đồng bộ / Dịch vụ vẫn ghim trên cùng; icon đúng ngữ nghĩa; chi tiết dùng nhãn tiếng Việt hiện hành; Đồng bộ có thao tác `ĐỒNG BỘ NGAY` và không phá header/realtime UI.\n- Regression: header_pinned / network_sync_service_icons / Vietnamese_detail_labels / manual_sync_from_header / no_geometry_regression.\n- Regression case: `tools/beta121_owner_ui_pda_source_contract.py` + visual matrix run 33932137068.\n- Technical evidence: {EVIDENCE}\n- OWNER acceptance: PENDING — Beta121 checklist item 1/4.\n\n### SUPERADMIN-EFFECTIVE-ROLE-003\n- Status: TECHNICAL_PASS_AWAITING_OWNER\n- Scope: SUPERADMIN / effective role\n- Parent: SUPERADMIN_AUTH_002 ACTIVE_PASS.\n- Rule: chỉ actual SUPERADMIN mới được chọn effective USER / ADMIN / SUPERADMIN trong chi tiết Dịch vụ; quyền nghiệp vụ thực tế phải hạ theo effective role; actual role vẫn là authority và user không phải SUPERADMIN không được tự nâng quyền.\n- Regression: actual_super_guard / effective_user / effective_admin / effective_superadmin / no_non_super_elevation / auth_session_preserved.\n- Regression case: `tools/beta121_owner_ui_pda_source_contract.py`.\n- Technical evidence: {EVIDENCE}\n- OWNER acceptance: PENDING — Beta121 checklist item 2/4.\n\n### SETTINGS-REGION-INHOUSE-DROP-001\n- Status: TECHNICAL_PASS_AWAITING_OWNER\n- Scope: Cài đặt / Bảng công Inhouse / Nhận hàng Rớt\n- Rule: Cài đặt chia vùng Tài khoản & quyền / Giao diện / Ứng dụng & cập nhật / Hỗ trợ & nhật ký; Bảng công Inhouse hiển thị `Chờ phát triển` và không giả lập chức năng; bảng Nhận hàng Rớt dùng layout bảng compact có header Thời gian / Vị trí / DO / Số kiện.\n- Regression: settings_regions / inhouse_placeholder_nonfunctional / drop_table_headers / compact_row_geometry / existing_drop_permissions_preserved.\n- Regression case: `tools/beta121_owner_ui_pda_source_contract.py`.\n- Technical evidence: {EVIDENCE}\n- OWNER acceptance: PENDING — Beta121 checklist item 3/4.\n\n### PDA-SOURCE-MASTER-001\n- Status: TECHNICAL_PASS_AWAITING_OWNER\n- Scope: PDA master data / Nguồn\n- Rule: PDA có trường `Nguồn` xuyên Android → GAS → Service; danh mục hiện hành gồm 1291, 1386, 1368, 1399, Inbound, Outbound; không được làm mất nguồn khi đọc/ghi master data.\n- Regression: source_field_android / gas_source_roundtrip / service_source_roundtrip / allowed_source_catalog / existing_pda_identity_preserved.\n- Regression case: `tools/beta121_owner_ui_pda_source_contract.py`.\n- Technical evidence: {EVIDENCE}\n- OWNER acceptance: PENDING — Beta121 checklist item 4/4.\n\n### Beta121 re-verification — OTA-BETA-001\n- Status: ACTIVE_PASS (semantics unchanged; OWNER-accepted invariant re-verified).\n- Rule: giữ nguyên GITHUB_RELEASE_ONLY / exact bytes / Stable-main-authority unchanged.\n- Regression addition: `tools/beta_ota_baseline_recovery_contract.py` bắt buộc recovery previous LIVE exact SHA/size/STABLE-disabled trước target activation khi OTA GAS baseline bị drift; sai SHA/readback phải fail-closed.\n- Evidence: baseline recovery run 33934523152 artifact 9959702930 PASS; exact Beta120 restored before publish; Beta121 publish 33934142254 artifact 9959732997 PASS; OTA install/open/readback artifact 9959773897 PASS; final artifact 9959777958 PASS.\n'''
    md.write_text(s, encoding="utf-8")

reg = root / "qa/stable_invariants.yml"
y = reg.read_text(encoding="utf-8").rstrip() + "\n"
# Re-verify existing OWNER-accepted OTA invariant without creating a duplicate ID.
ota_anchor = "  - id: OTA-BETA-001\n"
assert ota_anchor in y
if "beta121_reverification:" not in y[y.index(ota_anchor): y.find("\n  - id:", y.index(ota_anchor) + len(ota_anchor))]:
    start = y.index(ota_anchor)
    end = y.find("\n  - id:", start + len(ota_anchor))
    if end < 0:
        end = len(y)
    block = y[start:end].rstrip() + (
        "\n    beta121_reverification: \"Beta121 run 33934142254 PASS; exact GitHub Release SHA/size; OTA baseline recovery "
        "33934523152/9959702930 guarded by tools/beta_ota_baseline_recovery_contract.py; OTA device 9959773897; final 9959777958; Stable/main/authority unchanged.\"\n"
    )
    y = y[:start] + block + y[end:]

entries = [
    ("UI-STATUS-DETAIL-VI-003", "ui-status-detail-vi", "UI-STATUS-001", "3 ô status giữ header; icon đúng ngữ nghĩa; chi tiết tiếng Việt; Đồng bộ ngay không phá realtime/header.", "[header_pinned, status_icons, vietnamese_detail_labels, manual_sync_from_header, no_geometry_regression]", "PENDING_BETA121_ITEM_1_OF_4"),
    ("SUPERADMIN-EFFECTIVE-ROLE-003", "superadmin-effective-role", "SUPERADMIN_AUTH_002", "Chỉ actual SUPERADMIN được chọn effective USER/ADMIN/SUPERADMIN; quyền nghiệp vụ hạ theo effective role; non-super không tự nâng quyền.", "[actual_super_guard, effective_user, effective_admin, effective_superadmin, no_non_super_elevation, auth_session_preserved]", "PENDING_BETA121_ITEM_2_OF_4"),
    ("SETTINGS-REGION-INHOUSE-DROP-001", "settings-inhouse-drop", "UI-FORM-CONSISTENCY-002", "Cài đặt chia vùng; Bảng công Inhouse là placeholder Chờ phát triển; Nhận hàng Rớt dùng bảng compact Thời gian/Vị trí/DO/Số kiện.", "[settings_regions, inhouse_placeholder_nonfunctional, drop_table_headers, compact_row_geometry, existing_drop_permissions_preserved]", "PENDING_BETA121_ITEM_3_OF_4"),
    ("PDA-SOURCE-MASTER-001", "pda-source-master", "PDA-EXIT-001", "PDA Nguồn round-trip Android/GAS/Service; catalog 1291,1386,1368,1399,Inbound,Outbound; không mất source trong master data.", "[source_field_android, gas_source_roundtrip, service_source_roundtrip, allowed_source_catalog, existing_pda_identity_preserved]", "PENDING_BETA121_ITEM_4_OF_4"),
]
for iid, scope, parent, rule, regression, owner in entries:
    if f"  - id: {iid}\n" in y:
        continue
    y += f'''\n  - id: {iid}\n    status: TECHNICAL_PASS_AWAITING_OWNER\n    scope: {scope}\n    parent_invariant: {parent}\n    rule: "{rule}"\n    regression_minimum: {regression}\n    regression_case: "tools/beta121_owner_ui_pda_source_contract.py"\n    technical_evidence: "{EVIDENCE}"\n    technical_receipt: "ops/beta121-technical-pass.json"\n    owner_acceptance: "{owner}"\n    active_pass: false\n'''
reg.write_text(y, encoding="utf-8")

receipt = {
    "status": "TECHNICAL_PASS_AWAITING_OWNER",
    "version_name": EXPECTED["version_name"],
    "version_code": EXPECTED["version_code"],
    "package": EXPECTED["package"],
    "source_sha": EXPECTED["source_sha"],
    "candidate_run_id": 33929895214,
    "candidate_artifact_id": 9958252319,
    "apk_sha256": EXPECTED["apk_sha256"],
    "apk_size": EXPECTED["apk_size"],
    "signer_sha256": EXPECTED["signer_sha256"],
    "fast_check_run_id": 33932137056,
    "visual_pda_api36": {"run_id": 33932137068, "artifact_id": 9959024622, "human_visual_sizes": ["320x568", "360x640", "480x800"]},
    "device_regression": {"run_id": 33932666498, "artifact_id": 9959133081},
    "runtime_dod": {"run_id": 33933735030, "artifact_id": 9959507710},
    "beta_domain": {"run_id": 33934032820, "artifact_id": 9959551837},
    "ota_baseline_recovery": {"run_id": 33934523152, "artifact_id": 9959702930},
    "terminal_run_id": 33934142254,
    "publish_artifact_id": 9959732997,
    "ota_device_artifact_id": 9959773897,
    "final_artifact_id": 9959777958,
    "live": True,
    "ota_readback": "PASS",
    "stable_unchanged": True,
    "main_unchanged": True,
    "authority_change": "NONE",
    "apk_transport": "GITHUB_RELEASE_ONLY",
    "google_drive_apk": "FORBIDDEN",
    "owner_checklist_id": "BETA121_OWNER_ACCEPTANCE_20260905_R1",
    "owner_acceptance": "PENDING",
    "invariants": [e[0] for e in entries],
    "next_action": "WAIT_FOR_OWNER_ACCEPTANCE_NUMBERED_CHECKLIST",
}
(root / "ops/beta121-technical-pass.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

current = f'''# CURRENT STATE — PICK PACK 1291\n\n- updated_at: 2026-09-05T00:59:40Z\n- status: BETA121_PASS_LIVE\n- continuity_branch: release/beta121-owner-ui-pda-source-20260905\n- source_sha: {EXPECTED['source_sha']}\n- beta_live: 0.4.2-beta.121 (versionCode 127)\n- package: {EXPECTED['package']}\n- candidate_run: 33929895214\n- candidate_artifact: 9958252319\n- verify_run: 33932137068\n- verify_artifact: 9959024622\n- apk_sha256: {EXPECTED['apk_sha256']}\n- apk_size: 14429173\n- signer_sha256: {EXPECTED['signer_sha256']}\n- terminal_run: 33934142254\n- fast_check: PASS / run 33932137056\n- service_gate: PASS / run 33929895214 / artifact 9958376646\n- visual_matrix: PASS / run 33932137068 / artifact 9959024622 / 320x568 + 360x640 + 480x800\n- human_visual: PASS\n- pda_functional_pre_ota: PASS\n- device_regression: PASS / run 33932666498 / artifact 9959133081\n- runtime_dod: PASS / run 33933735030 / artifact 9959507710\n- beta_domain: PASS / run 33934032820 / artifact 9959551837\n- ota_baseline_recovery: PASS / run 33934523152 / artifact 9959702930\n- beta_ota: exact 0.4.2-beta.121 PASS via GitHub Release\n- beta_ota_url: https://github.com/tam95supra-source/pick-pack-1291/releases/download/v0.4.2-beta.121-publicbeta/pick-pack-1291-public-beta-0.4.2-beta.121.apk\n- ota_install_readback: PASS / run 33934142254 / artifact 9959773897\n- final_receipt: PASS / artifact 9959777958\n- apk_transport: GITHUB_RELEASE_ONLY\n- google_drive_apk: FORBIDDEN\n- stable: unchanged\n- main_sha: 021dac5c6932b3ac5c60ce8fdba562ddf3d9688f\n- authority: SERVICE_PRIMARY / PRODUCTION / epoch 9 / unchanged\n- technical_pass_status: PASS\n- owner_acceptance: PENDING\n- next_action: WAIT_FOR_OWNER_ACCEPTANCE_NUMBERED_CHECKLIST\n'''
(root / "CURRENT_STATE.md").write_text(current, encoding="utf-8")

handover = f'''# PICK PACK 1291 — HANDOFF SCHEMA V2\n\n- schema_version: 2\n- status: READY\n- time_utc: 2026-09-05T00:59:40Z\n- owner: Nguyễn Văn Tâm\n- branch: beta/current\n- continuity_branch: release/beta121-owner-ui-pda-source-20260905\n- archive_file: docs/handovers/HANDOVER_20260905-005940_beta121-technical-pass-owner-pending.md\n\n## Mục tiêu + DoD\nBeta121 LIVE và Technical DoD PASS cho OWNER scope `OWNER_20260905_UI_STATUS_ROLE_SETTINGS_DROP_PDA_SOURCE`; OWNER acceptance còn PENDING.\n\n## LIVE / exact candidate\n- Beta: 0.4.2-beta.121 / versionCode 127 / package {EXPECTED['package']}.\n- Source: {EXPECTED['source_sha']}.\n- Candidate: run 33929895214 / artifact 9958252319.\n- APK SHA256: {EXPECTED['apk_sha256']} / size 14429173 / signer {EXPECTED['signer_sha256']}.\n- GitHub Release + manifest readback: PASS / publish artifact 9959732997.\n- OTA Beta120 → Beta121 install/open/exact readback: PASS / artifact 9959773897.\n- Final receipt: artifact 9959777958.\n- Stable/main/signer/authority: unchanged.\n\n## Pre-OTA gates\n- Service PASS 33929895214/9958376646.\n- Fast Check PASS 33932137056.\n- Visual/PDA/API36 PASS 33932137068/9959024622; human 43 screenshots 320x568/360x640/480x800 PASS.\n- Device/discovery PASS 33932666498/9959133081.\n- Runtime DoD PASS 33933735030/9959507710.\n- Beta domain/readback PASS 33934032820/9959551837.\n- Release lock: ops/beta121-release-lock.json PASS.\n\n## Recovery đã khóa regression\n- Stable GAS primary 404 được phục hồi về canonical deployment; Runtime DoD rerun PASS.\n- OTA GAS baseline drift được phục hồi exact Beta120 trước target activation; recovery 33934523152/9959702930 PASS.\n- Regression: `tools/beta_ota_baseline_recovery_contract.py`.\n- Finalizer metadata `.scope/.service_gate` sai field đã sửa thành `.owner_scope/.service_gate_status`; regression `tools/finalize_handoff_contract.py`.\n\n## OWNER scope — TECHNICAL_PASS_AWAITING_OWNER\n1. UI-STATUS-DETAIL-VI-003 — header Mạng/Đồng bộ/Dịch vụ, icon + chi tiết Việt + Đồng bộ ngay.\n2. SUPERADMIN-EFFECTIVE-ROLE-003 — effective USER/ADMIN/SUPERADMIN hạ quyền thực tế đúng mode.\n3. SETTINGS-REGION-INHOUSE-DROP-001 — Cài đặt chia vùng, Inhouse chờ phát triển, Nhận hàng Rớt dạng bảng compact.\n4. PDA-SOURCE-MASTER-001 — PDA Nguồn xuyên Android/GAS/Service với catalog hiện hành.\n\n## Regression state\n- 4 invariant mới: TECHNICAL_PASS_AWAITING_OWNER, chưa ACTIVE_PASS.\n- OTA-BETA-001: ACTIVE_PASS semantics không đổi, Beta121 re-verification PASS.\n- Technical receipt: ops/beta121-technical-pass.json.\n\n## Blocker\nKhông có.\n\n## NEXT_ACTION\nWAIT_FOR_OWNER_ACCEPTANCE_NUMBERED_CHECKLIST\n'''
(root / "docs/handovers/HANDOVER_CURRENT.md").write_text(handover, encoding="utf-8")
(root / "docs/handovers/HANDOVER_20260905-005940_beta121-technical-pass-owner-pending.md").write_text(handover, encoding="utf-8")

# Fail closed on canonical states.
assert "null" not in handover
assert handover.count("## NEXT_ACTION") == 1
assert "WAIT_FOR_OWNER_ACCEPTANCE_NUMBERED_CHECKLIST" in handover
assert "TECHNICAL_PASS_AWAITING_OWNER" in md.read_text(encoding="utf-8")
assert all((f"  - id: {e[0]}\n" in reg.read_text(encoding="utf-8")) for e in entries)
print("BETA121_POST_RELEASE_METADATA_PASS")

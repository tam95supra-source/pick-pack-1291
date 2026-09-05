# PICK PACK 1291 — HANDOFF SCHEMA V2

- schema_version: 2
- status: READY
- time_utc: 2026-09-05T00:59:40Z
- owner: Nguyễn Văn Tâm
- branch: beta/current
- continuity_branch: release/beta121-owner-ui-pda-source-20260905
- archive_file: docs/handovers/HANDOVER_20260905-005940_beta121-technical-pass-owner-pending.md

## Mục tiêu + DoD
Beta121 LIVE và Technical DoD PASS cho OWNER scope `OWNER_20260905_UI_STATUS_ROLE_SETTINGS_DROP_PDA_SOURCE`; OWNER acceptance còn PENDING.

## LIVE / exact candidate
- Beta: 0.4.2-beta.121 / versionCode 127 / package vn.pickpack1291.app.beta.publicbeta.
- Source: ee482efb41565eee797b9b6c11fe54557c2b67f8.
- Candidate: run 33929895214 / artifact 9958252319.
- APK SHA256: 5b042c8e1f6d288ef19efe9abc773562c204fb3defd91396e4101adcedc8cc57 / size 14429173 / signer d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e.
- GitHub Release + manifest readback: PASS / publish artifact 9959732997.
- OTA Beta120 → Beta121 install/open/exact readback: PASS / artifact 9959773897.
- Final receipt: artifact 9959777958.
- Stable/main/signer/authority: unchanged.

## Pre-OTA gates
- Service PASS 33929895214/9958376646.
- Fast Check PASS 33932137056.
- Visual/PDA/API36 PASS 33932137068/9959024622; human 43 screenshots 320x568/360x640/480x800 PASS.
- Device/discovery PASS 33932666498/9959133081.
- Runtime DoD PASS 33933735030/9959507710.
- Beta domain/readback PASS 33934032820/9959551837.
- Release lock: ops/beta121-release-lock.json PASS.

## Recovery đã khóa regression
- Stable GAS primary 404 được phục hồi về canonical deployment; Runtime DoD rerun PASS.
- OTA GAS baseline drift được phục hồi exact Beta120 trước target activation; recovery 33934523152/9959702930 PASS.
- Regression: `tools/beta_ota_baseline_recovery_contract.py`.
- Finalizer metadata `.scope/.service_gate` sai field đã sửa thành `.owner_scope/.service_gate_status`; regression `tools/finalize_handoff_contract.py`.

## OWNER scope — TECHNICAL_PASS_AWAITING_OWNER
1. UI-STATUS-DETAIL-VI-003 — header Mạng/Đồng bộ/Dịch vụ, icon + chi tiết Việt + Đồng bộ ngay.
2. SUPERADMIN-EFFECTIVE-ROLE-003 — effective USER/ADMIN/SUPERADMIN hạ quyền thực tế đúng mode.
3. SETTINGS-REGION-INHOUSE-DROP-001 — Cài đặt chia vùng, Inhouse chờ phát triển, Nhận hàng Rớt dạng bảng compact.
4. PDA-SOURCE-MASTER-001 — PDA Nguồn xuyên Android/GAS/Service với catalog hiện hành.

## Regression state
- 4 invariant mới: TECHNICAL_PASS_AWAITING_OWNER, chưa ACTIVE_PASS.
- OTA-BETA-001: ACTIVE_PASS semantics không đổi, Beta121 re-verification PASS.
- Technical receipt: ops/beta121-technical-pass.json.

## Blocker
Không có.

## NEXT_ACTION
WAIT_FOR_OWNER_ACCEPTANCE_NUMBERED_CHECKLIST

# PICK PACK 1291 — HANDOFF SCHEMA V2

- schema_version: 2
- status: READY
- time_utc: 2026-09-04T17:01:37Z
- owner: Nguyễn Văn Tâm
- branch: beta/current
- archive_file: docs/handovers/HANDOVER_20260904-170137_beta120-owner-accepted.md

## Mục tiêu + DoD
Beta120 LIVE và OWNER acceptance hoàn tất cho scope dữ liệu đã nghiệm thu và `Ra ca tất cả hợp lệ`.

## LIVE
- BETA: 0.4.2-beta.120 / versionCode 126 / package vn.pickpack1291.app.beta.publicbeta.
- Source: b8f548d5717156554b8599955f62ab23f9973fc9.
- Candidate: run 33874862142 / artifact 9937580926.
- APK SHA256: 04d9f4b88e6ff038766357402f7f5831de67649087c839f922897042120b8ef8 / size 14429173.
- Terminal release/OTA/install/readback/finalize: run 33896192267 PASS.
- Stable/main/signer/authority: unchanged.

## OWNER acceptance
- Dữ liệu checklist 1/2/3: OWNER OK.
- `Ra ca tất cả hợp lệ`: OWNER OK.
- `OLD-SESSION-BULK-EXIT-001`: ACTIVE_PASS.
- Acceptance finalizer: run 33898227143 PASS.
- Receipt: `ops/beta120-owner-acceptance.json`.
- Canonical ledger: `ops/owner-acceptance-current.json` = Beta120 / OWNER_ACCEPTANCE_COMPLETE.

## Regression lock
- Bulk exit phải đi trực tiếp Service authority.
- Xử lý bounded batch + idempotency + failed-session isolation.
- Labor OPEN phải skip; canonical commitMutation/audit giữ nguyên.
- Regression case: `tools/beta120_bulk_exit_contract.py`.

## Blocker
Không có.

## NEXT_ACTION
OWNER_ACCEPTANCE_COMPLETE

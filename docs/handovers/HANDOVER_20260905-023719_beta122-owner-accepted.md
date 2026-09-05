# PICK PACK 1291 — HANDOFF SCHEMA V2

- schema_version: 2
- status: READY
- time_utc: 2026-09-05T02:37:19Z
- owner: Nguyễn Văn Tâm
- branch: beta/current
- technical_receipt: ops/beta122-technical-pass.json
- owner_receipt: ops/beta122-owner-acceptance.json
- archive_file: docs/handovers/HANDOVER_20260905-023719_beta122-owner-accepted.md

## Mục tiêu + DoD
Beta122 LIVE, Technical DoD PASS và OWNER acceptance hoàn tất. OWNER đã nghiệm thu item 2 và 4 OK; item 1 và 3 đã ACTIVE_PASS từ trước và được bảo toàn.

## LIVE / exact candidate
- Beta: 0.4.2-beta.122 / versionCode 128 / package vn.pickpack1291.app.beta.publicbeta.
- Source: fd26d18b0ae81cbc919824141f3670a3fe3b276e.
- Candidate: run 33937101147 / artifact 9960620587.
- APK SHA256: b06d1cf470fa840f53c9641397bf16cdfa3ce5d20651349f4ac3bb6e0ef4b54b / size 14429173 / signer d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e.
- Terminal publish/OTA/install/open/readback/finalize: PASS run 33938535151.
- Publish artifact 9960999680 / OTA device 9961036406 / final 9961041181.
- Stable/main/signer/authority: unchanged.

## OWNER acceptance / invariants
- UI-STATUS-DETAIL-VI-003: ACTIVE_PASS.
- SUPERADMIN-EFFECTIVE-ROLE-003: ACTIVE_PASS — OWNER item 2 OK.
- SETTINGS-REGION-INHOUSE-DROP-001: ACTIVE_PASS.
- PDA-SOURCE-MASTER-001: ACTIVE_PASS — OWNER item 4 OK.
- Acceptance ledger: OWNER_ACCEPTANCE_COMPLETE, state_epoch 202609050937, checklist revision 3.

## Blocker
Không có.

## NEXT_ACTION
OWNER_ACCEPTANCE_COMPLETE

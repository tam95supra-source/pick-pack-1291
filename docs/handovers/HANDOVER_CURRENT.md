# PICK PACK 1291 — HANDOFF SCHEMA V2

- schema_version: 2
- status: READY
- time_utc: 2026-08-31T12:30:25Z
- owner: Nguyễn Văn Tâm
- branch: release/beta102-beta-stable-isolation-20260831
- release_trigger_sha: 379fb80ef0b3ed1a1686b2d06f30d168fdbf17cf
- finalize_commit_sha: 75e47615b1ac52c98d6c9209105e5bf3cb796b3f
- archive_file: docs/handovers/HANDOVER_20260831-123025_beta104-technical-pass-awaiting-owner.md
- technical_dod_status: TECHNICAL_PASS_AWAITING_OWNER
- owner_acceptance: PENDING_BETA104

## LIVE / RELEASE
- LIVE BETA: 0.4.2-beta.104 / versionCode 110 / package vn.pickpack1291.app.beta.publicbeta.
- Exact source: c31bb1b7ad68e6fd114727d8f08508796013bcef.
- Candidate: run 33384004708 / artifact 9754938692.
- APK SHA256: 523b7ca4fe3463acdec8281d6232f36cd15e8df13a5f25585ca4ff4b82f2d6f1.
- Size: 13593589.
- Signer: d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e.
- GitHub Release asset ID 537953189 exact digest/size PASS.
- Terminal run 33391700817 PASS; publish 9757752307; OTA 9757829287; final 9757837384; handoff 9757842679.
- APK transport: GITHUB_RELEASE_ONLY; Google Drive APK FORBIDDEN.

## RELEASE TAIL FRESH PASS
- Human visual exact artifact 9755057622: PASS, 35 screenshots, 320x568 / 360x640 / 480x800.
- SERVICE-DISCOVERY-001 exact-device: 33388577027 / 9756583802 PASS.
- Fast Check: 33388933459 PASS.
- Runtime DoD: 33389060092 / 9756743967 PASS.
- Publish exact locked bytes: PASS.
- OTA preserved-data 0.4.2-beta.102 -> 0.4.2-beta.104: PASS.
- Installed hash/size/signer/version/package exact: PASS.
- Stale pickpack1291.cc.cd preserved across OTA then invalidated without clear/reinstall: PASS.
- environment=BETA; service_audience=PICK_PACK_1291_BETA; service_url=https://pickpack.1291.workers.dev; stable_root_reused=false.
- Finalize/readback: PASS; rollback skipped.

## PASS KẾ THỪA
- Stable verifier/auth/freeze/GAS infrastructure evidence unchanged.
- BETA GAS service/discovery repair v213 inherited; publish ppUpdateCheck contract advanced live deployment to 215 without changing Service authority.
- Existing ACTIVE_PASS invariants remain protected; OTA-BETA-001 evidence refreshed to Beta104.
- Beta102 = historical superseded release.
- Beta103 = ABANDONED_PRE_OTA.

## STABLE / AUTHORITY
- Stable = READY_NOT_LIVE / private / public=false / available=false / no OTA / no promotion.
- main SHA 021dac5c6932b3ac5c60ce8fdba562ddf3d9688f unchanged.
- SERVICE_PRIMARY authority unchanged.

## REGRESSION / OWNER ACCEPTANCE
- ENV-ISOLATION-001 = TECHNICAL_PASS_AWAITING_OWNER.
- SERVICE-DISCOVERY-001 = TECHNICAL_PASS_AWAITING_OWNER.
- ACTIVE_PASS chỉ sau OWNER Nguyễn Văn Tâm xác nhận OK.
- INFRA-RESILIENCE-001 vẫn DEFERRED_BY_OWNER, non-blocking.

## BLOCKER
Không có.

## NEXT_ACTION
OWNER_ACCEPTANCE_BETA104_CHECKLIST

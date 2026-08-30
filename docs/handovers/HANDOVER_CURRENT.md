# PICK PACK 1291 — HANDOFF SCHEMA V2

- schema_version: 2
- status: READY
- time_utc: 2026-08-30T04:39:02Z
- owner: Nguyễn Văn Tâm
- branch: release/beta97-qr-meal-alert-role-20260829
- archive_file: docs/handovers/HANDOVER_20260830-043902_beta99-gas-version-blocker.md
- technical_state: PRE_OTA_PASS_PUBLISH_BLOCKED_OWNER_ACTION

## LIVE / EXACT CANDIDATE
- Beta LIVE remains 0.4.2-beta.98 / versionCode 104.
- Beta99 locked source 660cac5f937c911364a7726661ed4c4b07d92388 / run 33290900322 / artifact 9725965250.
- APK c9cd5c9e93d83250040b2a49be262450eb3f4e947d21516a6c9aaa95d881729b / 13560821 bytes / signer unchanged.
- GitHub Release Beta99 exact asset exists, but OTA manifest remains Beta98.
- Stable/main/signer/authority unchanged.

## TERMINAL PRE-OTA PASS
- Fast Check PASS 33290759871.
- Service-live PASS job 99202629701.
- VERIFY_ONLY exact bytes PASS 33292677865 / job 99206960986 / artifact 9726495444.
- Visual/PDA PASS; API36 Back PASS; human visual PASS 26 screenshots / 3 required sizes.

## PUBLISH BLOCKER
- Publish 33292927542 failed only at GAS deployment contract after exact GitHub Release asset upload.
- GAS version_count=200; deployment version 201; referenced_versions=[201].
- Safe unreferenced recommended delete version: 3.
- beta-restored readback confirms Beta98 remains OTA LIVE.

## OWNER ACCEPTANCE
- 1/3/4/5 OWNER OK.
- 2/6 pending real-device acceptance after Beta99 LIVE.

## GAS VERSION CLEANUP READY
- Guarded batch cleanup script: tools/gas_version_cleanup.py
- Workflow: .github/workflows/gas-version-cleanup.yml
- Request file: ops/gas-version-cleanup-request.json
- DRY_RUN PASS run 33293553042 / artifact 9726697718.
- Inventory: 200 versions; referenced/current deployment version 201.
- Policy preview keep_latest=40 -> delete 160 unreferenced versions 3..162; deleted_count=0.
- Expected after cleanup: 40 versions remain / 160 free slots.
- No destructive delete executed yet.

## OWNER ACTION
Reply exactly: XÓA BATCH 160

## NEXT_ACTION
AFTER_OWNER_APPROVAL_SET_GAS_CLEANUP_REQUEST_ACTION_DELETE_KEEP_40_CONFIRM_THEN_WAIT_TERMINAL_READBACK_AND_RERUN_PUBLISH_EXACT_BETA99_WITHOUT_REBUILD

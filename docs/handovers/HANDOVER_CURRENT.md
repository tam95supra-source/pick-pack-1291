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

## GAS VERSION CLEANUP BLOCKER
- DRY_RUN planning PASS run 33293553042 / artifact 9726697718.
- Planned policy remains: keep newest 40 + every deployment-referenced version.
- Planned delete set remains versions 3..162 (160 versions).
- OWNER approved: XÓA BATCH 160.
- Automated DELETE attempt run 33295218728 failed safely before any deletion.
- Root cause: official Apps Script API does not expose project-version DELETE. Native Project History UI supports Bulk delete versions.
- Current deployment version remains 201; referenced_versions=[201].
- Deleted_count=0. Beta OTA remains Beta98; Beta99 exact candidate/release asset preserved.

## OWNER ACTION
In Apps Script > Nhật ký dự án, use native "Xoá hàng loạt phiên bản" and delete versions 3..162 only. Version 201 must remain.

## NEXT_ACTION
AFTER_OWNER_BULK_DELETES_GAS_VERSIONS_3_TO_162_FRESH_READ_VERSION_COUNT_DEPLOYMENT_201_AND_BETA98_MANIFEST_THEN_RERUN_PUBLISH_EXACT_BETA99_ARTIFACT_9725965250_WITHOUT_REBUILD

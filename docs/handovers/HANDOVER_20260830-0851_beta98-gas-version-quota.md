# PICK PACK 1291 — HANDOFF SCHEMA V2

- schema_version: 2
- status: READY
- time_utc: 2026-08-30T01:50:50Z
- owner: Nguyễn Văn Tâm
- branch: release/beta97-qr-meal-alert-role-20260829
- archive_file: docs/handovers/HANDOVER_20260830-0851_beta98-gas-version-quota.md

## LIVE / TARGET / CANDIDATE
- LIVE BETA remains 0.4.2-beta.97 / versionCode 103 / package vn.pickpack1291.app.beta.publicbeta.
- TARGET Beta98 0.4.2-beta.98 / versionCode 104.
- Exact candidate locked: run 33279188816 / artifact 9722490457 / source 154473b3dcc17c8badcfe345108e59ac3ba6e830.
- APK SHA256 b3085fe35f9bd2f8bed499dc7afcede5f210abdd8021ba379bccad7b795fba4b / size 13544437 / signer d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e.
- Stable/main/signer/authority/provider unchanged.

## PASS evidence
- Fast Check PASS run 33281578813.
- Service-live exact source PASS run 33280777490 / job 99175479666.
- VERIFY_ONLY exact candidate PASS run 33281633060 / artifact 9723200175.
- Visual matrix + direct PDA functional PASS.
- Android 16/API36 Back PASS.
- Human visual PASS: 26 screenshots, 320x568 / 360x640 / 480x800.
- GitHub Release Beta98 exact asset exists and public readback PASS.
- Release credential BETA_RELEASE_TOKEN works after normalization.

## Current blocker
- Publish run 33286565895 failed only at Apps Script version creation.
- Apps Script project has exactly 200 versions (1..200), hitting the hard version-count limit.
- Read-only inventory: deployment_count=2; referenced_versions=[200]; current_deployment_version=200.
- Safe unreferenced oldest versions=[1,2,3,4,5,6,7,8,9,10].
- Recommended one-version cleanup: delete version 1 only.
- Google Apps Script REST exposes versions create/get/list but no delete; deletion must be done manually in Project history UI.
- This is a destructive project-history action and therefore requires OWNER.
- Beta manifest/readback after failed publish is still exact Beta97. No OTA partial activation.
- GitHub Release Beta98/tag remains present with exact locked bytes; next publish will reuse it, not rebuild/reupload.

## Invariants
- Do not delete version 200.
- Do not change deployment IDs.
- Do not rebuild/resign Beta98.
- Do not change Stable/main/signer/authority/provider.
- APK transport remains GITHUB_RELEASE_ONLY; Google Drive APK FORBIDDEN.

## NEXT_ACTION
AFTER_OWNER_DELETES_GAS_PROJECT_HISTORY_VERSION_1_RETRY_PUBLISH_EXACT_ARTIFACT_9722490457_THEN_OTA_INSTALL_LIVE_READBACK_FINALIZE

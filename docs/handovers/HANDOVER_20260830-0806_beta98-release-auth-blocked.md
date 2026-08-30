# PICK PACK 1291 — HANDOFF SCHEMA V2

- schema_version: 2
- status: READY
- time_utc: 2026-08-30T01:06:14Z
- owner: Nguyễn Văn Tâm
- branch: release/beta97-qr-meal-alert-role-20260829
- release_trigger_sha: e5f7704c05dfba4e3b83cec211c3be11ed2c6c8d
- archive_file: docs/handovers/HANDOVER_20260830-0806_beta98-release-auth-blocked.md

## Mục tiêu + DoD
Tiếp tục exact Beta98 đã khóa đến GitHub Release → Beta manifest/API → OTA install/readback → finalize LIVE. Không rebuild/resign exact candidate.

## LIVE / TARGET / CANDIDATE
- LIVE BETA: 0.4.2-beta.97 / versionCode 103 / package vn.pickpack1291.app.beta.publicbeta.
- TARGET: 0.4.2-beta.98 / versionCode 104.
- Exact candidate: run 33279188816; artifact 9722490457; source 154473b3dcc17c8badcfe345108e59ac3ba6e830.
- APK SHA256: b3085fe35f9bd2f8bed499dc7afcede5f210abdd8021ba379bccad7b795fba4b.
- APK size: 13544437.
- Signer: d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e.
- Stable/main/signer/authority/provider unchanged. main=021dac5c6932b3ac5c60ce8fdba562ddf3d9688f.

## Gates inherited PASS
- Fast Check after harness alignment: PASS run 33281578813.
- Service-live exact source: PASS run 33280777490 / job 99175479666.
- VERIFY_ONLY exact candidate: PASS run 33281633060 / artifact 9723200175.
- Visual matrix + direct PDA functional: PASS.
- Android 16 / API36 system Back: PASS.
- Human visual: PASS, 26 real screenshots across 320x568 / 360x640 / 480x800.
- PDA-EXIT-001 technical regression: PASS; legacy pda_serial scalar is rejected as authority.

## Publish failure / root cause
- Publish run 33284770547, attempts 1 and 2, failed before Release creation with HTTP 403 Resource not accessible by integration.
- GitHub docs cause: target source SHA 154473... modifies .github/workflows relative to default branch; Actions GITHUB_TOKEN cannot obtain Workflows:write.
- Beta98 release tag and GitHub Release remain NOT_FOUND after both failures.
- Latest publish pre-readback confirms Beta manifest still Beta97; no post-publish rollback was required.
- Workflow prepared to use repo Actions secret BETA_RELEASE_TOKEN only for publish Release creation. Secret must be fine-grained/GitHub App token scoped to this repository with Contents:write + Workflows:write.
- No PAT/alternate release credential is currently available through repo workflow or connected GitHub tools.

## Blocker OWNER
One credential action is required: add repository Actions secret `BETA_RELEASE_TOKEN` containing an approved fine-grained token/GitHub App token for `tam95supra-source/pick-pack-1291` with **Contents: Read and write** and **Workflows: Read and write**. Do not change main/Stable/signer/authority/provider.

## Invariants
- Exact candidate bytes remain locked; no rebuild/resign.
- OTA-BETA-001 remains GITHUB_RELEASE_ONLY; Google Drive APK FORBIDDEN.
- Stable/main/signer/authority/provider unchanged.
- PDA-EXIT-001 semantics remain authoritative current-session assignments only; no stale scalar fallback.

## NEXT_ACTION
AFTER_OWNER_ADDS_BETA_RELEASE_TOKEN_TRIGGER_PUBLISH_EXACT_ARTIFACT_9722490457_THEN_OTA_INSTALL_LIVE_READBACK_FINALIZE

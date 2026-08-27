# PICK PACK 1291 — HANDOFF SCHEMA V2

- schema_version: 2
- status: READY
- time: 2026-08-27T22:57:00+0700
- owner: Nguyễn Văn Tâm
- branch: feature/beta78-old-session-outbound-service-20260826
- working_head_sha: SELF / resolve fresh branch HEAD
- archive_file: docs/handovers/HANDOVER_20260827-225700_beta81-preflight-parser-recovery.md

## Mục tiêu + DoD
Chốt Beta81 exact candidate 9646920908: device gate đủ ba lỗi PASS, finalize CURRENT_STATE + handoff READY, terminal TXT; không rebuild/resign/rerun candidate/visual/service/publish.

## LIVE / TARGET / CANDIDATE
- BETA OTA contract LIVE: 0.4.2-beta.81 / code 87.
- Release acceptance: PENDING device gate.
- Exact candidate: source 963ed28a90d2bb3e4a950ae8100fef15edfa86c5; artifact 9646920908; SHA256 f796bf8db5ec4575bb9d6d0880650c49abc682fe07c68aed916270f2afea3789; size 13196221; signer d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e.
- Publish 33078179831 / 98537863151 PASS and must be reused.

## Latest terminal evidence
- workflow_dispatch run 33088945149: FAILURE.
- pda-verify 98576199140 failed at "Validate exact locked inputs without republish"; emulator/device gate never started.
- Root error: jq "Cannot index array with string files" while parsing the main approval compare response.
- This run did not republish, rebuild, resign, rerun candidate/visual/service, or alter Beta OTA.
- Fix: replace compare-response predicate with exact main commit readback: main commit must have parent a8c0c0d92522c7173230d4175b4f0d3a4906c8bb and exactly one changed file .github/workflows/beta-release.yml.
- Secondary artifact-upload error downgraded to warn when preflight fails before /tmp/beta81-pda-verify exists.

## Device evidence retained from run 33088069684
- Exact Beta81 OTA download + PackageInstaller install PASS.
- Installed APK SHA/size/signer exact.
- Four flags PASS: reconciliation_home_1_0, reconciliation_qr_1_0, rollover_old_active_preserved, old_resources_preserved.
- Harness QR navigation root cause already fixed by reusing the existing QR screen.

## Main OWNER approval
- OWNER explicitly allowed only .github/workflows/beta-release.yml on main for workflow_dispatch.
- main = 4e728df1265943148a78642123df9dd84f2997c2.
- Stable/signer/authority unchanged.

## No-rerun
Cấm rebuild/resign Beta81; cấm candidate/visual/service/publish rerun. Recovery workflow has no publish job and reuses publish artifact 9648823162.

## Blocker / quyền
ChatGPT GitHub connector has no workflow_dispatch write action. OWNER must click Run workflow once after this preflight parser fix.

## NEXT_ACTION
OWNER_RUN_EXISTING_BETA_RELEASE_WORKFLOW_DISPATCH_ONCE_ON_feature/beta78-old-session-outbound-service-20260826

# PICK PACK 1291 — HANDOFF SCHEMA V2

- schema_version: 2
- status: READY
- time: 2026-08-27T22:36:00+0700
- owner: Nguyễn Văn Tâm
- branch: feature/beta78-old-session-outbound-service-20260826
- working_head_sha: SELF / resolve fresh branch HEAD
- archive_file: docs/handovers/HANDOVER_20260827-223600_beta81-qr-harness-recovery.md

## Mục tiêu + DoD
Chốt Beta81 exact candidate 9646920908: device gate đủ ba lỗi PASS, finalize CURRENT_STATE + handoff READY, terminal TXT; không rebuild/resign/rerun candidate/visual/service/publish.

## LIVE / TARGET / CANDIDATE
- BETA OTA contract LIVE: 0.4.2-beta.81 / code 87.
- Release acceptance: PENDING device gate.
- Exact candidate: source 963ed28a90d2bb3e4a950ae8100fef15edfa86c5; artifact 9646920908; SHA256 f796bf8db5ec4575bb9d6d0880650c49abc682fe07c68aed916270f2afea3789; size 13196221; signer d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e.
- Publish 33078179831 / 98537863151 PASS and must be reused.

## Latest failure evidence
- workflow_dispatch run 33088069684 terminal FAILURE.
- pda-verify 98573171301 FAILURE; finalize skipped; handoff-finalizer SUCCESS.
- Exact OTA install before failure PASS: Beta81 versionName/code, downloaded APK, installed base SHA/size/signer all exact.
- beta81-flags.xml proves PASS before root error: reconciliation_home_1_0, reconciliation_qr_1_0, rollover_old_active_preserved, old_resources_preserved.
- First root error: IllegalStateException:TEXT_NOT_FOUND:Quét QR nhân sự.
- Cause: harness had already entered employee QR screen, then unnecessarily reopened BUSINESS before scanning the old-session fixture. Second open is not an app requirement and broke the verifier flow.
- Fix: reuse the already-open QR screen and call setEmployee() directly. Candidate APK unchanged.

## Main OWNER approval
- OWNER explicitly allowed adding only .github/workflows/beta-release.yml to main for workflow_dispatch.
- main moved from a8c0c0d92522c7173230d4175b4f0d3a4906c8bb to 4e728df1265943148a78642123df9dd84f2997c2.
- Recovery preflight verifies that compare contains exactly that one workflow file and then requires main to remain unchanged.
- Stable/signer/authority unchanged.

## No-rerun
Cấm rebuild/resign Beta81; cấm candidate/visual/service/publish rerun. Recovery workflow has no publish job and reuses publish artifact 9648823162.

## Blocker / quyền
ChatGPT GitHub connector has no workflow_dispatch write action. OWNER must click Run workflow once after this harness fix.

## NEXT_ACTION
OWNER_RUN_EXISTING_BETA_RELEASE_WORKFLOW_DISPATCH_ONCE_ON_feature/beta78-old-session-outbound-service-20260826

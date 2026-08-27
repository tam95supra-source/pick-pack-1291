# PICK PACK 1291 — HANDOFF SCHEMA V2

- schema_version: 2
- status: READY
- time: 2026-08-27T21:47:00+0700
- owner: Nguyễn Văn Tâm
- branch: feature/beta78-old-session-outbound-service-20260826
- working_head_sha: SELF / resolve fresh branch HEAD (this handoff is in that commit)
- archive_file: docs/handovers/HANDOVER_20260827-214700_beta81-device-recovery-blocked.md

## Mục tiêu + DoD
Chốt Beta81 exact candidate 9646920908: device gate đủ ba lỗi PASS, finalize CURRENT_STATE + handoff READY, terminal TXT; không rebuild/resign/rerun candidate/visual/service/publish.

## LIVE / TARGET / CANDIDATE
- BETA OTA LIVE contract: 0.4.2-beta.81 / versionCode 87, publish receipt PASS.
- Release acceptance: PENDING vì PDA local three-fix gate chưa terminal PASS.
- Candidate locked: source 963ed28a90d2bb3e4a950ae8100fef15edfa86c5; artifact 9646920908; SHA256 f796bf8db5ec4575bb9d6d0880650c49abc682fe07c68aed916270f2afea3789; size 13196221; signer d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e.
- Visual 9647045177 PASS; Service 9646805806 PASS; publish job 98537863151 PASS.

## Exact terminal evidence
- Run 33078179831: CANCELLED.
- Publish job 98537863151: SUCCESS.
- PDA job 98538159325: CANCELLED at job timeout; finalize skipped; handoff-finalizer PASS.
- Publish artifact 9648823162: exact Beta81 publish/readback PASS.
- PDA failure artifact 9651008268 proves OTA download + PackageInstaller installed versionName 0.4.2-beta.81 / versionCode 87.
- installed-base.apk SHA256 f796bf8db5ec4575bb9d6d0880650c49abc682fe07c68aed916270f2afea3789, size 13196221; signer exact.
- beta81checks.txt is empty and no final receipt exists.
- Terminal TXT artifact 9651028493 read back; forbids rerun candidate/visual/service/publish.

## Root cause + harness fix
- Failure domain is harness/device gate, not APK/publish: local instrumentation command never returned and consumed the 55-minute job timeout after exact OTA install already succeeded.
- First unbounded harness call was startActivitySync() inside Beta81LocalChecksInstrumentation; OperationsActivity may remain non-idle due realtime/blinking UI.
- Fix: start activity asynchronously with target.startActivity(), bounded 10s package wait; local instrumentation host command bounded to 120s and always captures prefs/window evidence.
- Recovery workflow reuses publish artifact from run 33078179831 and has no publish job, so publish PASS is not rerun.
- Existing .github/workflows/beta-release.yml is now workflow_dispatch-only for this recovery checkpoint.

## Blocker / quyền
- ChatGPT GitHub connector in this session has no workflow_dispatch write action. No OAuth/MFA or repo permission error exists; only the missing dispatch capability blocks automatic start.

## Invariants
- Cấm rebuild/resign Beta81.
- Cấm rerun candidate 33073351925 / visual 9647045177 / service 9646805806 / publish 98537863151.
- Stable/main/signer/authority không đổi.
- Chỉ dùng existing .github/workflows/beta-release.yml trên branch hiện tại.

## NEXT_ACTION
OWNER_RUN_EXISTING_BETA_RELEASE_WORKFLOW_DISPATCH_ONCE_ON_feature/beta78-old-session-outbound-service-20260826

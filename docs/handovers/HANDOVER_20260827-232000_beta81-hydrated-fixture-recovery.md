# PICK PACK 1291 — HANDOFF SCHEMA V2

- schema_version: 2
- status: READY
- time: 2026-08-27T23:20:00+0700
- owner: Nguyễn Văn Tâm
- branch: feature/beta78-old-session-outbound-service-20260826
- working_head_sha: aa40900cf576634e67730bbe53cb94ea6c7048f8
- archive_file: docs/handovers/HANDOVER_20260827-232000_beta81-hydrated-fixture-recovery.md

## Mục tiêu + DoD
Chốt Beta81 exact candidate 9646920908: device gate đủ ba lỗi PASS, finalize CURRENT_STATE + handoff READY, terminal TXT; không rebuild/resign/rerun candidate/visual/service/publish.

## Locked / PASS
- Source 963ed28a90d2bb3e4a950ae8100fef15edfa86c5.
- Candidate 33073351925 / 9646920908; SHA256 f796bf8db5ec4575bb9d6d0880650c49abc682fe07c68aed916270f2afea3789; size 13196221; signer d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e.
- Visual 9647045177 PASS; Service 9646805806 PASS.
- Publish 33078179831 / 98537863151 PASS; exact Beta81 OTA bytes already LIVE.

## Latest terminal evidence
- Run 33091747263 terminal FAILURE.
- pda-verify 98586104552 FAILURE only at scanned old-session warning check.
- Artifact 9654734018 read back.
- Exact OTA + PackageInstaller install PASS; versionName 0.4.2-beta.81 / code 87; OTA-downloaded and installed base exact SHA/size; signer exact.
- Flags PASS: reconciliation_home_1_0, reconciliation_qr_1_0, rollover_old_active_preserved, old_resources_preserved.
- Root error: IllegalStateException:TEXT_NOT_FOUND:CẢNH BÁO: PHIÊN CA CŨ.

## Root cause + fix
- Local projection already proved prior-day ACTIVE session and resources preserved.
- Harness fixture omitted resource_assignments_v64; renderEmployee therefore entered session_resource_snapshot hydration before attaching the employee tree.
- Deterministic harness intentionally pointed Service to offline loopback, so hydration could not complete.
- This is harness-fixture mismatch, not APK failure.
- Fix commit 18e50b4a97cba3ae2883efcb00cbefaa554279ad hydrates old-session fixture with positions_v64 + ACTIVE resource_assignments_v64.
- CURRENT_STATE checkpoint commit aa40900cf576634e67730bbe53cb94ea6c7048f8.
- Preflight: workflow_dispatch-only, no publish job, reuses beta81-publish-33078179831, no app/ source change.

## Main / invariants
- main 4e728df1265943148a78642123df9dd84f2997c2 contains only OWNER-approved workflow file addition from pre-publish main.
- Stable NO_APK, signer and authority unchanged.
- Cấm rebuild/resign/rerun candidate/visual/service/publish.

## Blocker / quyền
ChatGPT GitHub connector still has no workflow_dispatch action; OWNER must click existing workflow once on this branch. No OAuth/MFA blocker.

## NEXT_ACTION
OWNER_RUN_EXISTING_BETA_RELEASE_WORKFLOW_DISPATCH_ONCE_ON_feature/beta78-old-session-outbound-service-20260826

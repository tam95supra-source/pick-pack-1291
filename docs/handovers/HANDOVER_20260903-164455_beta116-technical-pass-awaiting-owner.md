# PICK PACK 1291 — HANDOFF SCHEMA V2

- schema_version: 2
- status: READY
- time_utc: 2026-09-03T16:44:55Z
- owner: Nguyễn Văn Tâm
- branch: release/beta116-owner-scope-20260903
- release_trigger_sha: 769d57a7878bbe636bdf5f28663f97bcb385359f
- archive_file: docs/handovers/HANDOVER_20260903-164455_beta116-technical-pass-awaiting-owner.md

## Mục tiêu + DoD
Beta116 đã Technical PASS/LIVE trên exact locked APK. Toàn bộ candidate/service/visual/PDA/API36/auth/device/runtime/domain/publish/OTA-install-open-readback PASS. Finalize job ban đầu chỉ fail do Git rebase conflict control-plane sau khi OTA đã PASS; canonical state được khôi phục từ exact PASS receipts và finalizer harness đã được sửa. OWNER acceptance còn PENDING.

## LIVE / EXACT EVIDENCE
- LIVE BETA: 0.4.2-beta.116 / versionCode 122 / package vn.pickpack1291.app.beta.publicbeta.
- Source/candidate: cf01dab16e1c62091561ca008a355a8f49326581.
- Candidate: 33767353642 / 9898290631.
- Service: 33767353642 / 9898616640.
- Visual + PDA pre-OTA + API36: 33774026289 / 9901071098; human PASS 43 ảnh ở 320x568 / 360x640 / 480x800.
- Beta Auth: 33776285435 / 9902148937.
- Device regression: 33778316587 / 9902571477.
- Runtime DoD: 33778605857 / 9902663700.
- Domain: 33778957345 / 9902758766.
- Fast Check sau harness fix: 33780103022 PASS.
- Publish: 33780057070 / 9903236359 PASS.
- OTA Beta115 → Beta116 / install / open / exact readback: 33780057070 / 9903336912 PASS.
- Pass-live validation: 33783284600 PASS.
- Final tree targeted release-state/finalizer/registry verification: PASS.
- SHA256: a346d4554e07fc37552c9d8876179860677fc93923a3bd42f9b3f97f5e11f235 / size 14347253.
- Signer: d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e.
- Stable/main/authority: unchanged.
- APK transport: GITHUB_RELEASE_ONLY; Google Drive APK FORBIDDEN.

## Finalize recovery
- Failed finalize trong run 33780057070: rebase conflict tại ops/beta-release-request.json do branch control-plane được cập nhật sau khi run bắt đầu.
- Không có publish/OTA failure; không rollback; không rebuild/resign.
- Fix harness: rebase/fence trước khi render state + explicit technical_pass_status=PASS + owner_acceptance=PENDING + NEXT_ACTION owner checklist.
- Regression khóa tại tools/ci_release_fencing_contract.py.

## Beta116 invariants
11 invariant mới được ghi TECHNICAL_PASS_AWAITING_OWNER trong docs/STABLE_INVARIANTS.md và qa/stable_invariants.yml; chưa có invariant nào được tự nâng ACTIVE_PASS.

## Blocker
Không có blocker kỹ thuật.

## NEXT_ACTION
WAIT_FOR_OWNER_ACCEPTANCE_BETA116_CHECKLIST_1_TO_11

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

## OWNER-reported OTA incident 2026-09-04
- Beta115 thiết bị thật báo Dịch vụ suy giảm và không cập nhật được Beta116.
- OWNER reported Beta115 could not update and UI showed Service degraded. Fresh recovery: service-discovery 33784531907/9904956795 PASS; exact Beta116 Service source cf01dab16e1c62091561ca008a355a8f49326581 redeployed and full service regression 33784753619/9905201718 PASS with test_cleanup PASS; Beta-only live readback 33788505404/9906368570 PASS: Worker /health HTTP 200, GAS service_discovery HTTP 200 -> https://pickpack.1291.workers.dev, update_check from current_version 0.4.2-beta.115 HTTP 200 available=true -> 0.4.2-beta.116 code 122, SHA256 a346d4554e07fc37552c9d8876179860677fc93923a3bd42f9b3f97f5e11f235, size 14347253, GitHub Release URL exact. No APK rebuild/resign/republish; Stable untouched. Initial device degradation exact cause not provable from contaminated first probes.
- Incident receipt: `ops/beta116-ota-service-recovery.json`.
- Trạng thái: ACTIVE_PASS — OWNER xác nhận Beta115 → Beta116 cập nhật thực tế OK.

## OWNER acceptance Beta116 — 2026-09-04
- Accepted: 1,2,3,5,7,8,9,10,11.
- Pending: 4,6 do chưa có dữ liệu đủ nghiệm thu.
- Các yêu cầu tinh chỉnh mới của OWNER được tách thành Beta117, không sửa lịch sử ACTIVE_PASS của scope Beta116.
- Receipt: `ops/beta116-owner-acceptance-partial.json`.

## NEXT_ACTION
IMPLEMENT_BETA117_OWNER_FOLLOWUP_AND_PERFORMANCE_SCOPE

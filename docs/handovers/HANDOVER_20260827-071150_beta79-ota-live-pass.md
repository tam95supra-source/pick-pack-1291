# HANDOVER v2 — PICK PACK 1291

status: READY
task_state: PASS
created_at: 2026-08-27T07:11:50+07:00
owner: Nguyễn Văn Tâm
branch: feature/beta78-old-session-outbound-service-20260826
working_head_sha: 1df224e4d3c3a5ae2322ad37b3cc981e3d4e9aab
archive_file: docs/handovers/HANDOVER_20260827-071150_beta79-ota-live-pass.md

## MỤC TIÊU + DoD
Yêu cầu OWNER: cảnh báo phiên cũ phải mở đúng phiên như flow Quét QR nhân sự, không chỉ hiện message; từ đó có thể Thêm / Sửa / Xóa / Ra ca để kết thúc phiên.
DoD: exact old-session identity -> full QR employee/session UI -> exact-session mutations -> Beta mới build/sign/visual PASS -> publish exact bytes BETA -> OTA/Drive/LIVE readback PASS; Stable/main/signer/authority không đổi.
Kết quả: **PASS toàn bộ DoD**.

## LIVE / TARGET / CANDIDATE
### LIVE
- BETA: 0.4.2-beta.79 / versionCode 85
- package: vn.pickpack1291.app.beta.publicbeta
- source SHA: db96999844a31e7fed7d0f072fd0dd123fae1288
- candidate run/artifact: 33020009122 / 9626192148
- visual artifact: 9626266511
- APK SHA256: 547e1242a7d0bb057332ce38c46313771da33235fc0e384a908c14207e26e056
- size: 13,196,165
- signer SHA256: d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e
- Drive APK ID: 1Q_5UATzS7vh4aaFtSXY7MwXQVam60n9v
- Drive checksum ID: 1aOtKD0LRV4f4anfblAQHdVmlyoiyrmLU
- final publish run/job: 33025774426 attempt 2 / 98367068517 — SUCCESS
- final publish receipt artifact: 9628374003
- receipt artifact digest: sha256:b0c39c9ae2e86d0284b4b769532a8f2f5623db25295b613c57a8d6d97c8b3eae
- publish_mode: REUSED_ALREADY_LIVE_EXACT
- OTA exact bytes: PASS
- Apps Script deployment readback: version 196; gas_code_changed=false
- authority: SERVICE_PRIMARY / PRODUCTION, epoch 9, seq 94, generation m2-prod-reset-20260823-001
- Stable: available=false / NO_APK, unchanged
- main: a8c0c0d92522c7173230d4175b4f0d3a4906c8bb, unchanged

### TARGET
- TARGET Beta79 đã trở thành LIVE.
- Beta78 bị SUPERSEDED.

### CANDIDATE LOCK
- Exact candidate identity giữ nguyên:
  - source: db96999844a31e7fed7d0f072fd0dd123fae1288
  - run/artifact: 33020009122 / 9626192148
  - version/code: 0.4.2-beta.79 / 85
  - package: vn.pickpack1291.app.beta.publicbeta
  - SHA256: 547e1242a7d0bb057332ce38c46313771da33235fc0e384a908c14207e26e056
  - size: 13,196,165
  - signer: d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e

## EXACT EVIDENCE
1. Product fix:
   - OldSessionWarningFeature xác minh exact session_id + MNV + business_date.
   - Callback mở historical payload vào OperationsActivity.openHistoricalSession().
   - Shared renderEmployee/renderActive được tái sử dụng, không tạo UI riêng.
   - Phiên ACTIVE cũ có Thêm / Sửa / Xóa / Ra ca.
   - Conflict refresh của historical mutation fresh-read lại đúng historical_session_detail theo session_id, không nhảy session khác cùng MNV.
2. Build/sign/visual:
   - Run 33020009122 PASS.
   - Candidate artifact 9626192148.
   - Visual artifact 9626266511.
   - Human visual PASS: 320x568, 360x640, 480x800.
3. Release:
   - OWNER đã bật Google Drive API cho project 92085750998.
   - Drive preflight sau enable PASS.
   - Exact Beta79 APK đã upload và public readback SHA/size đúng candidate.
   - Live endpoint không trả version_code; verifier chỉ normalize VC85 sau khi exact public bytes == locked candidate.
   - Một transient GAS readback trả generic APP_GSHEET; bounded exact-candidate retry lần kế tiếp PASS.
   - Final run 33025774426 attempt 2 SUCCESS.
4. Final receipt:
   - status PASS
   - version_name 0.4.2-beta.79
   - version_code 85
   - ota_exact_bytes true
   - stable_unchanged true
   - main_unchanged true
   - authority_change NONE
   - visual_human_inspection PASS

## FILE / COMMIT ĐÃ ĐỔI
- app/src/main/java/vn/pickpack1291/app/beta/OldSessionWarningFeature.kt — 08910a2cc29b8b93f54b27b2234ef4e05c9c0a82
- app/src/main/java/vn/pickpack1291/app/beta/OperationsActivity.kt — 0ed5e24858716a2873b74b2e29cd16983ba6b83b
- app/build.gradle.kts — 8021e68aaa0bcd89c1c993824f6e21d56a2e4861
- .github/workflows/app-fast-check.yml — db96999844a31e7fed7d0f072fd0dd123fae1288
- ops/beta79-visual-inspection.json — 56d717146988fbf838766f933389d7b710edd596
- ops/beta-release-request.json — 06e6064a26f1cc245670940db8ae0cf2e77a7363
- .github/workflows/beta-release.yml — b22016f40976338c051f56be0dbb0446a3db7165
- tools/publish_beta79_ota.sh — latest release verifier head 29a754976b7fc1cfa7743fa9b9d2e9336ca5a454
- CURRENT_STATE.md — 1df224e4d3c3a5ae2322ad37b3cc981e3d4e9aab

## LỖI + ROOT CAUSE + ĐƯỜNG PASS / CẤM LẶP
- UI root cause: old-session detail dùng read-only AlertDialog thay vì shared QR flow. Đã sửa.
- Release blocker cũ: Drive API disabled. OWNER đã enable, blocker hết.
- Harness defect: OTA live JSON thiếu version_code dù SHA/size/URL đúng. Đã sửa verifier theo live contract; cấm rebuild để chữa verifier.
- Transient: một GAS update_check trả APP_GSHEET generic; exact-candidate retry bounded PASS. Không coi là APK failure.
- CẤM lặp: không rebuild/resign Beta79; không rerun visual/build đã PASS khi bytes không đổi; không đổi Stable/main/signer/authority; không redeploy Service chỉ để xác minh lại.

## WORKSPACE / CI / EXTERNAL STATE
- Active branch: feature/beta78-old-session-outbound-service-20260826
- Active workflow allowlist: app-fast-check.yml, beta-release.yml.
- Beta79 candidate/visual run 33020009122 SUCCESS.
- Beta79 final publish run 33025774426 attempt 2 SUCCESS.
- LIVE Drive/OTA readback PASS.
- CURRENT_STATE đã cập nhật Beta79 LIVE.

## VIỆC CÒN LẠI
- Không còn việc trong scope hiện tại.

## BLOCKER / QUYỀN
- Không có blocker OWNER.
- Stable/main/signer/authority không thay đổi.

## INVARIANTS
- Stable giữ nguyên.
- main giữ nguyên.
- signer giữ nguyên.
- authority SERVICE_PRIMARY / PRODUCTION giữ nguyên.
- Service/GAS business authority giữ nguyên.
- Beta79 exact candidate identity ở trên là LIVE bytes.

## NEXT_ACTION
WAIT_FOR_OWNER_NEW_SCOPE.

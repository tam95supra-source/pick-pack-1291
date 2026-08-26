# HANDOVER v2 — PICK PACK 1291

status: READY
task_state: BLOCKED
created_at: 2026-08-27T05:44:55+07:00
owner: Nguyễn Văn Tâm
branch: feature/beta78-old-session-outbound-service-20260826
working_head_sha: e532a96041327ae98daf2016e1f6415462b9965a
archive_file: docs/handovers/HANDOVER_20260827-054455_beta79-drive-api-blocked.md

## MỤC TIÊU + DoD
OWNER yêu cầu cảnh báo phiên cũ không chỉ mở dạng message/read-only. Khi chọn phiên cũ phải mở đúng phiên như flow Quét QR nhân sự để tiếp tục xử lý Thêm / Sửa / Xóa / Ra ca (bắn ra kết thúc phiên).
DoD: exact old session identity -> full QR employee/session UI -> exact-session mutations -> Beta mới build/sign/visual PASS -> publish exact bytes BETA -> OTA/Drive/LIVE readback PASS. Stable/main/signer/authority không đổi.

## LIVE / TARGET / CANDIDATE
### LIVE
- BETA LIVE: 0.4.2-beta.78 / versionCode 84
- package: vn.pickpack1291.app.beta.publicbeta
- APK SHA256: 73ebd3015f214f168af484433b3591b6ed85e784280e9a9f7e38a405291f2c6b
- size: 13,196,165
- signer SHA256: d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e
- beta-before fresh read at failed publisher: available=true, version_name=0.4.2-beta.78, exact SHA/size above
- STABLE fresh read: available=false / reason=NO_APK
- main fresh read: a8c0c0d92522c7173230d4175b4f0d3a4906c8bb
- authority fresh read: SERVICE_PRIMARY / PRODUCTION, epoch 9, service_generation m2-prod-reset-20260823-001
- Apps Script remains version 194; no Beta79 GAS write occurred.

### TARGET
- BETA 0.4.2-beta.79 / versionCode 85
- Full old-session QR actions; Stable/main/authority unchanged.

### CANDIDATE LOCK
- source_sha: db96999844a31e7fed7d0f072fd0dd123fae1288
- build/visual run: 33020009122
- candidate artifact: 9626192148
- visual artifact: 9626266511
- version: 0.4.2-beta.79 / versionCode 85
- package: vn.pickpack1291.app.beta.publicbeta
- APK SHA256: 547e1242a7d0bb057332ce38c46313771da33235fc0e384a908c14207e26e056
- size: 13,196,165
- signer SHA256: d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e
- candidate artifact digest: sha256:c74663de9280f556e288f3862ceec3701f135a970a2db252a19a7b96e2572cdf
- visual artifact digest: sha256:100dfdfc7695bd74ecbd408169c6d645c8d7849dbffb9313c50ea9f75520cb81

## EXACT EVIDENCE
1. Root cause UI Beta78:
   - OldSessionWarningFeature.build() có callback onOpen nhưng callback bị UNUSED.
   - showDetail() tự dựng AlertDialog nên "MỞ ĐÚNG PHIÊN" chỉ xem message.
   - OperationsActivity đã có full flow renderEmployee -> renderActive với Thêm / Sửa / Xóa / Ra ca.
2. Fix Beta79:
   - historical_session_detail trả exact session_id + mnv + business_date.
   - OldSessionWarningFeature xác minh exact identity rồi gọi onOpen(raw).
   - OperationsActivity openHistoricalSession(raw) chuẩn hóa historical payload và gọi renderEmployee(ctx,null).
   - submitResourceMutation khi conflict của historical session fresh-read lại historical_session_detail theo exact session_id, không nhảy sang session khác cùng MNV.
3. Backend semantics đã xác minh:
   - session mutations dùng byId(session_id), không bị giới hạn current date.
   - Không đổi Service/authority/backend trong Beta79.
4. Candidate run 33020009122:
   - source/static gates PASS
   - Gradle build + unit + Beta/Stable debug + Beta release PASS
   - signer lock PASS
   - candidate upload PASS
   - visual automation PASS
5. Human visual PASS:
   - 320x568: old-session warning visible; full Thêm/Sửa/Xóa/Ra ca visible after scroll; no layout break
   - 360x640: PASS tương tự
   - 480x800: full actions visible; no layout break
   - receipt: ops/beta79-visual-inspection.json
6. Publish:
   - run 33020546538: candidate/visual preflight PASS; publisher failed before write at Google Drive preflight HTTP 403.
   - harness corrected to expose deterministic reason and retry only transient errors.
   - run 33020640240: preflight PASS; deterministic failure:
     drive_preflight_http=403 reason=accessNotConfigured
     Google error: SERVICE_DISABLED, service=drive.googleapis.com, consumer=projects/92085750998.
   - failure artifact: 9626395097
   - No Drive upload, no GAS mutation, no Stable/main/authority change occurred.

## FILE / COMMIT ĐÃ ĐỔI
- app/src/main/java/vn/pickpack1291/app/beta/OldSessionWarningFeature.kt — 08910a2cc29b8b93f54b27b2234ef4e05c9c0a82
- app/src/main/java/vn/pickpack1291/app/beta/OperationsActivity.kt — 0ed5e24858716a2873b74b2e29cd16983ba6b83b
- app/build.gradle.kts — 8021e68aaa0bcd89c1c993824f6e21d56a2e4861
- .github/workflows/app-fast-check.yml — db96999844a31e7fed7d0f072fd0dd123fae1288
- ops/beta79-visual-inspection.json — 56d717146988fbf838766f933389d7b710edd596
- ops/beta-release-request.json — 06e6064a26f1cc245670940db8ae0cf2e77a7363
- tools/publish_beta79_ota.sh — bb98cb3b3562ee076e3c1ecf489cbf152f2a14e3; diagnostic harness e532a96041327ae98daf2016e1f6415462b9965a
- .github/workflows/beta-release.yml — b22016f40976338c051f56be0dbb0446a3db7165

## LỖI / ROOT CAUSE / ĐƯỜNG PASS / CẤM LẶP
- Product root cause: UI wiring dùng read-only AlertDialog thay vì callback vào shared QR flow. Đã sửa và build/visual PASS.
- Release blocker root cause: Google Drive API bị disabled/not configured trong OAuth project 92085750998.
- Đường PASS: OWNER bật Google Drive API (drive.googleapis.com) cho project 92085750998; chờ propagation; fresh-read Drive API; publish lại CHÍNH exact candidate artifact 9626192148; verify OTA SHA/size + Stable/main/authority unchanged.
- CẤM: rebuild/resign/version bump; sửa Service/GAS logic ngoài OTA route; retry khi vẫn accessNotConfigured; đổi Stable/main/signer/authority; tạo workflow mới.

## WORKSPACE / CI / EXTERNAL STATE
- Active workflow allowlist giữ nguyên: app-fast-check.yml, beta-release.yml.
- app-fast-check Beta79 run 33020009122 terminal SUCCESS.
- beta-release run 33020640240 terminal FAILURE duy nhất vì Drive API disabled.
- Exact candidate bytes vẫn khóa, chưa publish.
- Google Drive/GAS write stage chưa bắt đầu ở failed run.

## VIỆC CÒN LẠI
- Chỉ còn release transport: bật Drive API -> publish exact bytes -> OTA/Drive/LIVE readback -> cập nhật CURRENT_STATE/handoff thành PASS.

## BLOCKER / QUYỀN OWNER
- Evidence: HTTP 403 PERMISSION_DENIED, reason accessNotConfigured / SERVICE_DISABLED, service drive.googleapis.com, project 92085750998.
- OWNER cần làm đúng 1 thao tác: bật Google Drive API cho Google Cloud project 92085750998.
- Sau khi bật không cần cấp lại signer, không rebuild APK, không đổi OAuth secret trừ khi Google yêu cầu riêng.

## INVARIANTS
- Stable không đổi.
- main không đổi.
- signer không đổi.
- authority SERVICE_PRIMARY / PRODUCTION không đổi.
- Service/GAS business authority không đổi.
- exact Beta79 candidate phải giữ nguyên source/run/artifact/SHA/size/signer ở trên.

## NEXT_ACTION
Sau khi OWNER bật drive.googleapis.com cho project 92085750998 và propagation hoàn tất, fresh-read Drive API rồi rerun publish-only bằng exact candidate artifact 9626192148; nếu publish PASS thì verify OTA exact SHA/size + Stable/main/authority unchanged và cập nhật LIVE Beta79.

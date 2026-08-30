# PICK PACK 1291 — HANDOFF SCHEMA V2

- schema_version: 2
- status: READY
- time_utc: 2026-08-30T12:00:45Z
- owner: Nguyễn Văn Tâm
- branch: release/beta97-qr-meal-alert-role-20260829
- release_trigger_sha: 79ce5796414d3a9030668ed5ec4e8531598e44a0
- archive_file: docs/handovers/HANDOVER_20260830-120045_beta101-pass-live.md

## Mục tiêu + DoD
Release 0.4.2-beta.101 hoàn tất scope beta101-resilience-option-borders-stop-readable-history-full-diagnostics; toàn bộ pre-OTA + GitHub Release exact bytes + OTA install/readback + finalizer PASS.

## LIVE / TARGET / CANDIDATE
- LIVE BETA: 0.4.2-beta.101 / versionCode 107 / package vn.pickpack1291.app.beta.publicbeta.
- TARGET: PASS/LIVE.
- CANDIDATE LOCKED: run 33307618230; artifact 9731018588; source d918de9fe0b132b60c5c4f515395e541da47daf2; SHA256 e29eab9402d847ac5f141f2a51ee164b235d46c3a075a46df4dff69ced0c3097; size 13577205; signer d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e.
- Fast Check: PASS run 33307368813.
- Service: PASS_INHERITED_JOB_99202629701_EXACT_SERVICE_SOURCE_UNCHANGED.
- Visual/PDA pre-OTA: PASS run 33309271079, artifact 9731526178.
- Human visual 320x568 / 360x640 / 480x800: PASS.
- Stable/main/signer/authority: unchanged.

## Evidence
- 3 ô Mạng / Đồng bộ / Dịch vụ ghim trên cùng ở mọi màn scope: PASS.
- QR nhân sự local fast-path giữ nguyên; functional + service regression PASS.
- Điểm danh chỉ chấp nhận ACTIVE session đúng business_date hiện tại; ACTIVE phiên cũ bị chặn: PASS.
- Cảnh báo chưa điểm danh ở trên cùng Nghiệp vụ; USER không thấy/deep-link được Lịch sử: PASS.
- GitHub Release asset exact bytes khớp candidate SHA256/size; OTA tải trực tiếp từ GitHub Release: PASS.
- OTA 0.4.2-beta.100 → 0.4.2-beta.101: download/install exact SHA/size/version/package/signer và mở app: PASS.
- Google Drive APK: FORBIDDEN từ Beta97; không backup/staging/mirror/upload/download/rollback/phân phối APK qua Drive.

## Lỗi/root cause/PASS path
- VERIFY_ONLY harness cũ đếm text guard HISTORY cứng; sửa verifier semantics và exact candidate PASS.
- Publish cũ có luồng Drive APK song song và DriveApp/public APK bị Google chặn; loại bỏ toàn bộ Drive dependency khỏi Beta APK pipeline.
- Canonical Beta APK path: GitHub Actions exact candidate → GitHub Release exact asset → GAS manifest GitHub URL → OTA install/readback → finalizer.
- Rollback canonical: exact LIVE baseline GitHub Actions/GitHub Release → atomic Beta manifest restore; không dùng Drive APK.
- Candidate được build/sign đúng một lần; mọi recovery dùng exact locked bytes, không rebuild/resign.
- Beta101 publish verifier legacy hardcode `screenshot_count==26` làm publish fail pre-write; thay bằng receipt-driven verifier đối chiếu receipt ↔ actual PNG ↔ visual-summary ↔ 3 viewport + human gate.
- Regression verifier PASS run 33310187636: legacy 26 PASS theo receipt; Beta101 35 PASS; lệch count/thiếu viewport/lệch summary/human gate false đều FAIL đúng.
- Manual resilience log 20:12: NORMAL_SERVICE_PRIMARY PASS thực qua Service/idempotency; DEVICE_OFFLINE_LOCAL và SERVICE_GOOGLE_OFFLINE_LOCAL là isolated safe simulation + recovery, không phải physical outage; GOOGLE_UNAVAILABLE_SERVICE kiểm Service thật nhưng Google-down được mô phỏng; Google fallback 2 case FAIL do live GAS drift; LAN chỉ kiểm actual canRoute/submit khi topology đã active.
- GAS RESILIENCE_V1 deployment drift: 205 thiếu routes/functions dù repo có đủ. Patch tối thiểu live HEAD → deployment 206, giữ nguyên ppUpdateCheck Beta101 và authority; post-readback PASS.
- Release pipeline đã thêm live GAS resilience contract guard; Fast Check 33314181358 PASS.

## Blocker
OWNER acceptance item 6 = NOT OK. Manual log 2026-08-30 20:12 cho thấy SERVICE_UNAVAILABLE_GOOGLE và SERVICE_TIMEOUT_GOOGLE FAIL deterministic tại GOOGLE_EMERGENCY_CAPTURE / UNKNOWN_ACTION; LAN = NOT_AVAILABLE / LAN_PREREQUISITE_MISSING.
Root cause Google đã sửa: read-only run 33313877854 xác nhận deployment 205 thiếu toàn bộ RESILIENCE_V1; repair run 33314072135 deploy 206 PASS; post-readback 33314115931 PASS. Cần OWNER rerun trên Beta101 có session thật. LAN cần topology nhiều PDA thật nên CI/single-device không thể chứng minh.

## Invariants
- Stable/main/signer/authority không đổi.
- APK Beta release/OTA/rollback = GITHUB_RELEASE_ONLY.
- Google Drive không được dùng cho APK; GSheet/GAS nghiệp vụ không bị xóa/thay authority.

## NEXT_ACTION
WAIT_FOR_OWNER_BETA101_ITEM_6_RETEST_AFTER_GAS206

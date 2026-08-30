# PICK PACK 1291 — HANDOFF SCHEMA V2

- schema_version: 2
- status: READY
- time_utc: 2026-08-30T10:21:19Z
- owner: Nguyễn Văn Tâm
- branch: release/beta97-qr-meal-alert-role-20260829
- release_trigger_sha: 57d63443ac7aa309c7291aaa274d517ce31d469f
- archive_file: docs/handovers/HANDOVER_20260830-102119_beta100-pass-live.md

## Mục tiêu + DoD
Release 0.4.2-beta.100 hoàn tất scope beta100-isolated-resilience-test-center-status-chip-details; toàn bộ pre-OTA + GitHub Release exact bytes + OTA install/readback + finalizer PASS.

## LIVE / TARGET / CANDIDATE
- LIVE BETA: 0.4.2-beta.100 / versionCode 106 / package vn.pickpack1291.app.beta.publicbeta.
- TARGET: PASS/LIVE.
- CANDIDATE LOCKED: run 33301229802; artifact 9729047360; source c6cddd9df208a26f05b17fa2723827286bf93bd8; SHA256 29270f4435a5e4c7729e4aeb9a6ae516795c14ca0858723df8c9a293a62d9319; size 13577205; signer d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e.
- Fast Check: PASS run 33301081015.
- Service: PASS_INHERITED_JOB_99202629701_EXACT_SERVICE_SOURCE_UNCHANGED.
- Visual/PDA pre-OTA: PASS run 33305842167, artifact 9730487600.
- Human visual 320x568 / 360x640 / 480x800: PASS.
- Stable/main/signer/authority: unchanged.

## Evidence
- 3 ô Mạng / Đồng bộ / Dịch vụ ghim trên cùng ở mọi màn scope: PASS.
- QR nhân sự local fast-path giữ nguyên; functional + service regression PASS.
- Điểm danh chỉ chấp nhận ACTIVE session đúng business_date hiện tại; ACTIVE phiên cũ bị chặn: PASS.
- Cảnh báo chưa điểm danh ở trên cùng Nghiệp vụ; USER không thấy/deep-link được Lịch sử: PASS.
- GitHub Release asset exact bytes khớp candidate SHA256/size; OTA tải trực tiếp từ GitHub Release: PASS.
- OTA 0.4.2-beta.99 → 0.4.2-beta.100: download/install exact SHA/size/version/package/signer và mở app: PASS.
- Google Drive APK: FORBIDDEN từ Beta97; không backup/staging/mirror/upload/download/rollback/phân phối APK qua Drive.

## Lỗi/root cause/PASS path
- VERIFY_ONLY harness cũ đếm text guard HISTORY cứng; sửa verifier semantics và exact candidate PASS.
- Publish cũ có luồng Drive APK song song và DriveApp/public APK bị Google chặn; loại bỏ toàn bộ Drive dependency khỏi Beta APK pipeline.
- Canonical Beta APK path: GitHub Actions exact candidate → GitHub Release exact asset → GAS manifest GitHub URL → OTA install/readback → finalizer.
- Rollback canonical: exact LIVE baseline GitHub Actions/GitHub Release → atomic Beta manifest restore; không dùng Drive APK.
- Candidate được build/sign đúng một lần; mọi recovery dùng exact locked bytes, không rebuild/resign.

## Blocker
Không có.

## Invariants
- Stable/main/signer/authority không đổi.
- APK Beta release/OTA/rollback = GITHUB_RELEASE_ONLY.
- Google Drive không được dùng cho APK; GSheet/GAS nghiệp vụ không bị xóa/thay authority.

## NEXT_ACTION
WAIT_FOR_OWNER_NEW_SCOPE

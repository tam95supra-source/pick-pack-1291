# PICK PACK 1291 — HANDOFF SCHEMA V2

- schema_version: 2
- status: READY
- time_utc: 2026-09-01T10:55:36Z
- owner: Nguyễn Văn Tâm
- branch: release/beta108-document-management
- release_trigger_sha: fdf750e989ddc5bb78baf431bd1a7edd7a66befa
- archive_file: docs/handovers/HANDOVER_20260901-105536_beta108-pass-live.md

## Mục tiêu + DoD
Release 0.4.2-beta.108 hoàn tất scope beta108-document-management-drive-direct-durable-queue-cache-rename-all-hard-delete; toàn bộ pre-OTA + GitHub Release exact bytes + OTA install/readback + finalizer PASS.

## LIVE / TARGET / CANDIDATE
- LIVE BETA: 0.4.2-beta.108 / versionCode 114 / package vn.pickpack1291.app.beta.publicbeta.
- TARGET: PASS/LIVE.
- CANDIDATE LOCKED: run 33491085275; artifact 9793922815; source 378f1c294641c774cee361ae2bd2cc9fc868ee23; SHA256 bd82ca39ca702a771b435ef67ab626cbc36e9771478981912fa20e588bb9bc6e; size 14150645; signer d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e.
- Fast Check: PASS run 33498475427.
- Service: PASS_FRESH_RUN_33497121749.
- Visual/PDA pre-OTA: PASS run 33497121749, artifact 9796518681.
- Human visual 320x568 / 360x640 / 480x800: PASS.
- Stable/main/signer/authority: unchanged.

## Evidence
- 3 ô Mạng / Đồng bộ / Dịch vụ ghim trên cùng ở mọi màn scope: PASS.
- QR nhân sự local fast-path giữ nguyên; functional + service regression PASS.
- Điểm danh chỉ chấp nhận ACTIVE session đúng business_date hiện tại; ACTIVE phiên cũ bị chặn: PASS.
- Cảnh báo chưa điểm danh ở trên cùng Nghiệp vụ; USER không thấy/deep-link được Lịch sử: PASS.
- GitHub Release asset exact bytes khớp candidate SHA256/size; OTA tải trực tiếp từ GitHub Release: PASS.
- OTA 0.4.2-beta.106 → 0.4.2-beta.108: download/install exact SHA/size/version/package/signer và mở app: PASS.
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

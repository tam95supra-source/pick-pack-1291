# PICK PACK 1291 — HANDOFF SCHEMA V2

- schema_version: 2
- status: READY
- time_utc: 2026-09-02T04:29:48Z
- owner: Nguyễn Văn Tâm
- branch: release/beta111-owner-ui-labor-nav
- release_trigger_sha: ac9d3ccdba7a122cce78242180f58f6d05664724
- archive_file: docs/handovers/HANDOVER_20260902-042948_beta111-pass-live.md

## Mục tiêu + DoD
Release 0.4.2-beta.111 hoàn tất scope beta111-owner-ui-labor-navigation-history-delete-document-tick; toàn bộ pre-OTA + GitHub Release exact bytes + OTA install/readback + finalizer PASS.

## LIVE / TARGET / CANDIDATE
- LIVE BETA: 0.4.2-beta.111 / versionCode 117 / package vn.pickpack1291.app.beta.publicbeta.
- TARGET: PASS/LIVE.
- CANDIDATE LOCKED: run 33586428789; artifact 9830403339; source 03b37e5aa2726c273cc1e7c4a2161763bd3c4d2d; SHA256 f67049067e600f4d8439d0ae088889f7b35df8b215e5432a2fcdd54f05f04a4f; size 14216181; signer d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e.
- Fast Check: PASS run 33588839641.
- Service: PASS_FRESH_RUN_33588851239.
- Visual/PDA pre-OTA: PASS run 33589199933, artifact 9831243286.
- Human visual 320x568 / 360x640 / 480x800: PASS.
- Stable/main/signer/authority: unchanged.

## Evidence
- 3 ô Mạng / Đồng bộ / Dịch vụ ghim trên cùng ở mọi màn scope: PASS.
- QR nhân sự local fast-path giữ nguyên; functional + service regression PASS.
- Điểm danh chỉ chấp nhận ACTIVE session đúng business_date hiện tại; ACTIVE phiên cũ bị chặn: PASS.
- Cảnh báo chưa điểm danh ở trên cùng Nghiệp vụ; USER không thấy/deep-link được Lịch sử: PASS.
- GitHub Release asset exact bytes khớp candidate SHA256/size; OTA tải trực tiếp từ GitHub Release: PASS.
- OTA 0.4.2-beta.110 → 0.4.2-beta.111: download/install exact SHA/size/version/package/signer và mở app: PASS.
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

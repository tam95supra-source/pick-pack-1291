# PICK PACK 1291 — HANDOFF SCHEMA V2

- schema_version: 2
- status: READY
- time_utc: 2026-09-03T02:53:33Z
- owner: Nguyễn Văn Tâm
- branch: release/beta113-owner-scope-20260902
- release_trigger_sha: 171324926ac58d38b266baa48934273f528b0756
- archive_file: docs/handovers/HANDOVER_20260903-025333_beta115-pass-live.md

## Mục tiêu + DoD
Release 0.4.2-beta.115 hoàn tất scope beta115-owner-revised-labor-select-today-calendar; toàn bộ pre-OTA + GitHub Release exact bytes + OTA install/readback + finalizer PASS.

## LIVE / TARGET / CANDIDATE
- LIVE BETA: 0.4.2-beta.115 / versionCode 121 / package vn.pickpack1291.app.beta.publicbeta.
- TARGET: PASS/LIVE.
- CANDIDATE LOCKED: run 33703823187; artifact 9874569505; source 429c39f82aacba19351351234f7f66a8d3b655f1; SHA256 af2c267e2101223387fdf4feb86b6ae315fe17b44c09d89c9f6166a8a73d49e5; size 14281717; signer d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e.
- Fast Check: PASS run 33708743727.
- Service: PASS_EXACT_SERVICE_SOURCE_429c39f82aacba19351351234f7f66a8d3b655f1.
- Visual/PDA pre-OTA: PASS run 33705116149, artifact 9875061341.
- Human visual 320x568 / 360x640 / 480x800: PASS.
- Stable/main/signer/authority: unchanged.

## Evidence
- 3 ô Mạng / Đồng bộ / Dịch vụ ghim trên cùng ở mọi màn scope: PASS.
- QR nhân sự local fast-path giữ nguyên; functional + service regression PASS.
- Điểm danh chỉ chấp nhận ACTIVE session đúng business_date hiện tại; ACTIVE phiên cũ bị chặn: PASS.
- Cảnh báo chưa điểm danh ở trên cùng Nghiệp vụ; USER không thấy/deep-link được Lịch sử: PASS.
- GitHub Release asset exact bytes khớp candidate SHA256/size; OTA tải trực tiếp từ GitHub Release: PASS.
- OTA 0.4.2-beta.114 → 0.4.2-beta.115: download/install exact SHA/size/version/package/signer và mở app: PASS.
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

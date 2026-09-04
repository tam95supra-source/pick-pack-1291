# PICK PACK 1291 — HANDOFF SCHEMA V2

- schema_version: 2
- status: READY
- time_utc: 2026-09-04T06:00:57Z
- owner: Nguyễn Văn Tâm
- branch: release/beta118-owner-realtime-bulk-exit-20260904
- release_trigger_sha: 7b8335c223243abd4948eb1923d06bcd085e88e1
- archive_file: docs/handovers/HANDOVER_20260904-060057_beta118-pass-live.md

## Mục tiêu + DoD
Release 0.4.2-beta.118 Technical PASS/LIVE cho scope null; toàn bộ pre-OTA + GitHub Release exact bytes + OTA install/readback + finalizer PASS; OWNER acceptance còn PENDING.

## LIVE / TARGET / CANDIDATE
- LIVE BETA: 0.4.2-beta.118 / versionCode 124 / package vn.pickpack1291.app.beta.publicbeta.
- TARGET: PASS/LIVE.
- CANDIDATE LOCKED: run 33833810807; artifact 9922669910; source 81944b8519cfb7995d78a5c1070c4af3ee2150be; SHA256 5216f0eb09f187aed9cb71dcc21cd145fdc3ba7ea7852c74ffe6f85dea2b478f; size 14429173; signer d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e.
- Fast Check: PASS run 33838741599.
- Service: null.
- Visual/PDA pre-OTA: PASS run 33835144144, artifact 9923142675.
- Human visual 320x568 / 360x640 / 480x800: PASS.
- Stable/main/signer/authority: unchanged.

## Evidence
- 3 ô Mạng / Đồng bộ / Dịch vụ ghim trên cùng ở mọi màn scope: PASS.
- QR nhân sự local fast-path giữ nguyên; functional + service regression PASS.
- Điểm danh chỉ chấp nhận ACTIVE session đúng business_date hiện tại; ACTIVE phiên cũ bị chặn: PASS.
- Cảnh báo chưa điểm danh ở trên cùng Nghiệp vụ; USER không thấy/deep-link được Lịch sử: PASS.
- GitHub Release asset exact bytes khớp candidate SHA256/size; OTA tải trực tiếp từ GitHub Release: PASS.
- OTA 0.4.2-beta.117 → 0.4.2-beta.118: download/install exact SHA/size/version/package/signer và mở app: PASS.
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
WAIT_FOR_OWNER_ACCEPTANCE_NUMBERED_CHECKLIST

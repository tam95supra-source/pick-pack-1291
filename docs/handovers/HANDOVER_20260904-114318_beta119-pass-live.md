# PICK PACK 1291 — HANDOFF SCHEMA V2

- schema_version: 2
- status: READY
- time_utc: 2026-09-04T11:43:18Z
- owner: Nguyễn Văn Tâm
- branch: release/beta119-superadmin-auth-control-plane-20260904
- release_trigger_sha: 6e2b1621d7cb4f4a1f2caba5b49c8870d9795fed
- archive_file: docs/handovers/HANDOVER_20260904-114318_beta119-pass-live.md

## Mục tiêu + DoD
Release 0.4.2-beta.119 Technical PASS/LIVE cho scope null; toàn bộ pre-OTA + GitHub Release exact bytes + OTA install/readback + finalizer PASS; OWNER acceptance còn PENDING.

## LIVE / TARGET / CANDIDATE
- LIVE BETA: 0.4.2-beta.119 / versionCode 125 / package vn.pickpack1291.app.beta.publicbeta.
- TARGET: PASS/LIVE.
- CANDIDATE LOCKED: run 33864111135; artifact 9933396813; source eeb45df6deae267d93a5fb15701a0a394885a549; SHA256 73c072187fb13bab635f27009fda500d0745fced4244a8d8276bc9117f350697; size 14429173; signer d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e.
- Fast Check: PASS run 33867108883.
- Service: null.
- Visual/PDA pre-OTA: PASS run 33864111135, artifact 9933765361.
- Human visual 320x568 / 360x640 / 480x800: PASS.
- Stable/main/signer/authority: unchanged.

## Evidence
- 3 ô Mạng / Đồng bộ / Dịch vụ ghim trên cùng ở mọi màn scope: PASS.
- QR nhân sự local fast-path giữ nguyên; functional + service regression PASS.
- Điểm danh chỉ chấp nhận ACTIVE session đúng business_date hiện tại; ACTIVE phiên cũ bị chặn: PASS.
- Cảnh báo chưa điểm danh ở trên cùng Nghiệp vụ; USER không thấy/deep-link được Lịch sử: PASS.
- GitHub Release asset exact bytes khớp candidate SHA256/size; OTA tải trực tiếp từ GitHub Release: PASS.
- OTA 0.4.2-beta.118 → 0.4.2-beta.119: download/install exact SHA/size/version/package/signer và mở app: PASS.
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

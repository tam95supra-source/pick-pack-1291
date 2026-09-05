# PICK PACK 1291 — HANDOFF SCHEMA V2

- schema_version: 2
- status: READY
- time_utc: 2026-09-05T02:18:32Z
- owner: Nguyễn Văn Tâm
- branch: release/beta122-effective-role-pda-source-ui-20260905
- release_trigger_sha: 8022c5e06b2169c1c0abc338cf8f39ff28e91fbd
- archive_file: docs/handovers/HANDOVER_20260905-021832_beta122-pass-live.md

## Mục tiêu + DoD
Release 0.4.2-beta.122 Technical PASS/LIVE cho scope null; toàn bộ pre-OTA + GitHub Release exact bytes + OTA install/readback + finalizer PASS; OWNER acceptance còn PENDING.

## LIVE / TARGET / CANDIDATE
- LIVE BETA: 0.4.2-beta.122 / versionCode 128 / package vn.pickpack1291.app.beta.publicbeta.
- TARGET: PASS/LIVE.
- CANDIDATE LOCKED: run 33937101147; artifact 9960620587; source fd26d18b0ae81cbc919824141f3670a3fe3b276e; SHA256 b06d1cf470fa840f53c9641397bf16cdfa3ce5d20651349f4ac3bb6e0ef4b54b; size 14429173; signer d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e.
- Fast Check: PASS run 33937614821.
- Service: null.
- Visual/PDA pre-OTA: PASS run 33937614831, artifact 9960788555.
- Human visual 320x568 / 360x640 / 480x800: PASS.
- Stable/main/signer/authority: unchanged.

## Evidence
- 3 ô Mạng / Đồng bộ / Dịch vụ ghim trên cùng ở mọi màn scope: PASS.
- QR nhân sự local fast-path giữ nguyên; functional + service regression PASS.
- Điểm danh chỉ chấp nhận ACTIVE session đúng business_date hiện tại; ACTIVE phiên cũ bị chặn: PASS.
- Cảnh báo chưa điểm danh ở trên cùng Nghiệp vụ; USER không thấy/deep-link được Lịch sử: PASS.
- GitHub Release asset exact bytes khớp candidate SHA256/size; OTA tải trực tiếp từ GitHub Release: PASS.
- OTA 0.4.2-beta.121 → 0.4.2-beta.122: download/install exact SHA/size/version/package/signer và mở app: PASS.
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

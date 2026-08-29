# PICK PACK 1291 — HANDOFF SCHEMA V2

- schema_version: 2
- status: READY
- time_utc: 2026-08-29T12:38:34Z
- owner: Nguyễn Văn Tâm
- branch: release/beta97-qr-meal-alert-role-20260829
- release_trigger_sha: 0f7c34b2121ca460c0e5227cd71b732b5808d3aa
- archive_file: docs/handovers/HANDOVER_20260829-123834_beta97-pass-live.md

## Mục tiêu + DoD
Release 0.4.2-beta.97 hoàn tất scope beta97-owner-status-header-qr-meal-alert-history-role; toàn bộ pre-OTA + GitHub Release exact bytes + OTA install/readback + finalizer PASS.

## LIVE / TARGET / CANDIDATE
- LIVE BETA: 0.4.2-beta.97 / versionCode 103 / package vn.pickpack1291.app.beta.publicbeta.
- TARGET: PASS/LIVE.
- CANDIDATE LOCKED: run 33247859614; artifact 9713456764; source b1c1563ce9489d9154e8d2489976c3c81d4234da; SHA256 522cfd16cc71b416c8c3efe222f8763cbfd159c355359ad781258ea0292d9231; size 13282293; signer d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e.
- Fast Check: PASS run 33247813928.
- Service: PASS_RUN_33247859614_JOB_99088728192_EXACT_SOURCE.
- Visual/PDA pre-OTA: PASS run 33250391599, artifact 9714229229.
- Human visual 320x568 / 360x640 / 480x800: PASS.
- Stable/main/signer/authority: unchanged.

## Evidence
- 3 ô Mạng / Đồng bộ / Dịch vụ ghim trên cùng ở mọi màn scope: PASS.
- QR nhân sự local fast-path giữ nguyên; functional + service regression PASS.
- Điểm danh chỉ chấp nhận ACTIVE session đúng business_date hiện tại; ACTIVE phiên cũ bị chặn: PASS.
- Cảnh báo chưa điểm danh ở trên cùng Nghiệp vụ; USER không thấy/deep-link được Lịch sử: PASS.
- GitHub Release asset exact bytes khớp candidate SHA256/size; OTA tải trực tiếp từ GitHub Release: PASS.
- OTA 0.4.2-beta.96 → 0.4.2-beta.97: download/install exact SHA/size/version/package/signer và mở app: PASS.
- Google Drive APK: FORBIDDEN từ Beta97; không backup/staging/mirror/upload/download/rollback/phân phối APK qua Drive.

## Lỗi/root cause/PASS path
- VERIFY_ONLY harness cũ đếm text guard HISTORY cứng; sửa verifier semantics và exact candidate PASS.
- Publish cũ có luồng Drive APK song song và DriveApp/public APK bị Google chặn; loại bỏ toàn bộ Drive dependency khỏi Beta APK pipeline.
- Canonical Beta APK path: GitHub Actions exact candidate → GitHub Release exact asset → GAS manifest GitHub URL → OTA install/readback → finalizer.
- Rollback canonical: exact LIVE baseline GitHub Actions/GitHub Release → atomic Beta manifest restore; không dùng Drive APK.
- Candidate được build/sign đúng một lần; mọi recovery dùng exact locked bytes, không rebuild/resign.

## Blocker
Không có.

## Bắt buộc đọc ở mọi phiên
- `docs/REGRESSION_GUARD_POLICY.md`: policy chống regression áp dụng chung; chỉ OWNER được thay đổi.

## Invariants
- Stable/main/signer/authority không đổi.
- APK Beta release/OTA/rollback = GITHUB_RELEASE_ONLY.
- Google Drive không được dùng cho APK; GSheet/GAS nghiệp vụ không bị xóa/thay authority.
- Mọi sửa đổi phải tuân `docs/REGRESSION_GUARD_POLICY.md`: business rule/authority/helper duy nhất, legacy không được quyết định nghiệp vụ, mỗi bug có regression test + impact matrix.

## NEXT_ACTION
WAIT_FOR_OWNER_NEW_SCOPE

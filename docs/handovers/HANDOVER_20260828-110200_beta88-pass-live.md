# PICK PACK 1291 — HANDOFF SCHEMA V2

- schema_version: 2
- status: READY
- time_utc: 2026-08-28T11:02:00Z
- owner: Nguyễn Văn Tâm
- branch: release/beta88-owner-10-fixes-20260828
- working_head_sha: 054e074eb9b506bc4ec9ddc8ee9c49aee1a94fb4
- archive_file: docs/handovers/HANDOVER_20260828-110200_beta88-pass-live.md

## Mục tiêu + DoD
Release 0.4.2-beta.88 hoàn tất scope beta88-owner-navigation-staff-audit-reconciliation-attendance-pda-return-pick-account; toàn bộ pre-OTA + OTA install/readback PASS.

## LIVE / TARGET / CANDIDATE
- LIVE BETA: 0.4.2-beta.88 / versionCode 94.
- TARGET: PASS/LIVE.
- CANDIDATE LOCKED: run 33164047646; artifact 9682911659; source a97aa2383ec7d40961ead86f03b8771bc66cce26; SHA256 8e946ccff556cf74117b53fda0b24fd804aee17e9f08fe877faab24ac777bbaa; size 13216757; signer d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e.
- Fast Check: PASS run 33163723865.
- Service: BETA87_LIVE_INHERITS_BETA83_SERVICE_PASS_SERVICE_SOURCE_UNCHANGED.
- Visual/PDA pre-OTA: PASS run 33164047646, artifact 9682977813.
- Human visual 320x568 / 360x640 / 480x800: PASS.
- Stable/main/signer/authority: unchanged.

## Evidence
- 3 ô rà soát nhân sự nằm trên ô quét MNV: PASS.
- Thứ tự công việc: Vị trí → User Pick → PDA → Bàn Pack → User Pack: PASS.
- RESOURCE_CHANGE hiển thị dữ liệu Trước cập nhật / Sau cập nhật khi service có snapshot; bản ghi cũ fallback rõ ràng: PASS.
- Diễn biến trong ca sắp xếp mới nhất → cũ nhất: PASS.
- Sửa/xóa và các thao tác chỉnh sửa được gate bằng mật khẩu HHmm hiện tại theo Asia/Ho_Chi_Minh: PASS.
- SUPERADMIN thực tế được phép dùng thêm mật khẩu tài khoản cố định qua login verification; không hardcode secret: PASS.
- OTA baseline → 0.4.2-beta.88 exact bytes, SHA/size/signer/version và mở app: PASS.

## Lỗi/root cause/PASS path
- Scope Beta86: bỏ polling UI 750 ms, chuyển refresh realtime sang event-driven/partial; không đổi backend/authority.
- Candidate được build/sign đúng một lần từ exact source đã khóa; release harness nhận version từ request.
- Fast Check exact source PASS; verifier stale HH:mm đã được sửa sang HHmm và chạy VERIFY_ONLY trên exact locked candidate.
- Không rebuild/resign candidate sau khi lock.

## Blocker
Không có.

## Invariants
Stable/main/signer/authority không đổi; không thêm provider/backend/authority.

## NEXT_ACTION
WAIT_FOR_OWNER_NEW_SCOPE

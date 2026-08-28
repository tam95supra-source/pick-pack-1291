# PICK PACK 1291 — HANDOFF SCHEMA V2

- schema_version: 2
- status: READY
- time_utc: 2026-08-28T12:52:59Z
- owner: Nguyễn Văn Tâm
- branch: release/beta90-log-accounting-20260828
- working_head_sha: 22b6c9a5df7efc01490cf42ecf593a288eec9bb0
- archive_file: docs/handovers/HANDOVER_20260828-125259_beta90-pass-live.md

## Mục tiêu + DoD
Release 0.4.2-beta.90 hoàn tất scope beta90-log-audit-back-pda-validation-first-log-metadata; toàn bộ pre-OTA + OTA install/readback PASS.

## LIVE / TARGET / CANDIDATE
- LIVE BETA: 0.4.2-beta.90 / versionCode 96.
- TARGET: PASS/LIVE.
- CANDIDATE LOCKED: run 33171110016; artifact 9685712954; source a82fcff43e4d8787b4a3b0e3d621d9f1ae3dfb82; SHA256 9c601d04e3173952e61b5a53aa1dd0a7199172e9ca64919638af4ba7fd3970e2; size 13216757; signer d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e.
- Fast Check: PASS run 33170923870.
- Service: null.
- Visual/PDA pre-OTA: PASS run 33171626028, artifact 9685944321.
- Human visual 320x568 / 360x640 / 480x800: PASS.
- Stable/main/signer/authority: unchanged.

## Evidence
- 3 ô rà soát nhân sự nằm trên ô quét MNV: PASS.
- Thứ tự công việc: Vị trí → User Pick → PDA → Bàn Pack → User Pack: PASS.
- RESOURCE_CHANGE hiển thị dữ liệu Trước cập nhật / Sau cập nhật khi service có snapshot; bản ghi cũ fallback rõ ràng: PASS.
- Diễn biến trong ca sắp xếp mới nhất → cũ nhất: PASS.
- Sửa/xóa và các thao tác chỉnh sửa được gate bằng mật khẩu HHmm hiện tại theo Asia/Ho_Chi_Minh: PASS.
- SUPERADMIN thực tế được phép dùng thêm mật khẩu tài khoản cố định qua login verification; không hardcode secret: PASS.
- OTA baseline → 0.4.2-beta.90 exact bytes, SHA/size/signer/version và mở app: PASS.

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

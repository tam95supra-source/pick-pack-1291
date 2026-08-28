# PICK PACK 1291 — HANDOFF SCHEMA V2

- schema_version: 2
- status: READY
- time_utc: 2026-08-28T15:27:49Z
- owner: Nguyễn Văn Tâm
- branch: release/beta92-availability-ui-changelog-20260828
- working_head_sha: 6e82920f3dc358a6af369f0d97977290e16792d1
- archive_file: docs/handovers/HANDOVER_20260828-152749_beta92-pass-live.md

## Mục tiêu + DoD
Release 0.4.2-beta.92 hoàn tất scope beta92-authoritative-resource-options-no-ui-reset-dual-changelog; toàn bộ pre-OTA + OTA install/readback PASS.

## LIVE / TARGET / CANDIDATE
- LIVE BETA: 0.4.2-beta.92 / versionCode 98.
- TARGET: PASS/LIVE.
- CANDIDATE LOCKED: run 33182370577; artifact 9690348624; source 07a09ee7d555bb1c5f6117ce2deab16ea24c2031; SHA256 87653b32f35ec37bfef1800ee3b957f60ad43390e0ae405872aea88e8bb5e6b9; size 13233141; signer d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e.
- Fast Check: PASS run 33182063652.
- Service: null.
- Visual/PDA pre-OTA: PASS run 33184299969, artifact 9691140872.
- Human visual 320x568 / 360x640 / 480x800: PASS.
- Stable/main/signer/authority: unchanged.

## Evidence
- 3 ô rà soát nhân sự nằm trên ô quét MNV: PASS.
- Thứ tự công việc: Vị trí → User Pick → PDA → Bàn Pack → User Pack: PASS.
- RESOURCE_CHANGE hiển thị dữ liệu Trước cập nhật / Sau cập nhật khi service có snapshot; bản ghi cũ fallback rõ ràng: PASS.
- Diễn biến trong ca sắp xếp mới nhất → cũ nhất: PASS.
- Sửa/xóa và các thao tác chỉnh sửa được gate bằng mật khẩu HHmm hiện tại theo Asia/Ho_Chi_Minh: PASS.
- SUPERADMIN thực tế được phép dùng thêm mật khẩu tài khoản cố định qua login verification; không hardcode secret: PASS.
- OTA baseline → 0.4.2-beta.92 exact bytes, SHA/size/signer/version và mở app: PASS.

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

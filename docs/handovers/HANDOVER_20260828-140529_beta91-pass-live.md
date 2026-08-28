# PICK PACK 1291 — HANDOFF SCHEMA V2

- schema_version: 2
- status: READY
- time_utc: 2026-08-28T14:05:29Z
- owner: Nguyễn Văn Tâm
- branch: release/beta91-pack-timeline-realtime-20260828
- working_head_sha: dfaf7d7e8d5c56dfedc0996af913da8e773e471f
- archive_file: docs/handovers/HANDOVER_20260828-140529_beta91-pass-live.md

## Mục tiêu + DoD
Release 0.4.2-beta.91 hoàn tất scope beta91-pack-table-availability-timeline-realtime-delta-only; toàn bộ pre-OTA + OTA install/readback PASS.

## LIVE / TARGET / CANDIDATE
- LIVE BETA: 0.4.2-beta.91 / versionCode 97.
- TARGET: PASS/LIVE.
- CANDIDATE LOCKED: run 33176109520; artifact 9687753210; source f344fce87895ee58ff4ebff46c178daff44bf9f8; SHA256 5f354c176432d2e80d87ddd1b2e86772a7c6a12fb5a3e491cd59ac5c723ff478; size 13216757; signer d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e.
- Fast Check: PASS run 33175886959.
- Service: null.
- Visual/PDA pre-OTA: PASS run 33177521294, artifact 9688385703.
- Human visual 320x568 / 360x640 / 480x800: PASS.
- Stable/main/signer/authority: unchanged.

## Evidence
- 3 ô rà soát nhân sự nằm trên ô quét MNV: PASS.
- Thứ tự công việc: Vị trí → User Pick → PDA → Bàn Pack → User Pack: PASS.
- RESOURCE_CHANGE hiển thị dữ liệu Trước cập nhật / Sau cập nhật khi service có snapshot; bản ghi cũ fallback rõ ràng: PASS.
- Diễn biến trong ca sắp xếp mới nhất → cũ nhất: PASS.
- Sửa/xóa và các thao tác chỉnh sửa được gate bằng mật khẩu HHmm hiện tại theo Asia/Ho_Chi_Minh: PASS.
- SUPERADMIN thực tế được phép dùng thêm mật khẩu tài khoản cố định qua login verification; không hardcode secret: PASS.
- OTA baseline → 0.4.2-beta.91 exact bytes, SHA/size/signer/version và mở app: PASS.

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

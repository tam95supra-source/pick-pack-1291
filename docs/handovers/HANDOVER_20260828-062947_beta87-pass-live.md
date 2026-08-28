# PICK PACK 1291 — HANDOFF SCHEMA V2

- schema_version: 2
- status: READY
- time_utc: 2026-08-28T06:29:47Z
- owner: Nguyễn Văn Tâm
- branch: release/beta87-owner-ui-data-fixes-20260828
- working_head_sha: e9ca0df6e8ac37e55567fe20fb5b9de906ec294d
- archive_file: docs/handovers/HANDOVER_20260828-062947_beta87-pass-live.md

## Mục tiêu + DoD
Release 0.4.2-beta.87 hoàn tất scope beta87-owner-ui-data-correctness-actions-pack-delete-audit-header-report; toàn bộ pre-OTA + OTA install/readback PASS.

## LIVE / TARGET / CANDIDATE
- LIVE BETA: 0.4.2-beta.87 / versionCode 93.
- TARGET: PASS/LIVE.
- CANDIDATE LOCKED: run 33145848295; artifact 9675780824; source 51e67280d81b1e9070c97f652098c341038d6882; SHA256 4591e4c5842b9af6da6a4898ff56d4b8ad16765acca9294272444ce7b267f865; size 13212605; signer d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e.
- Fast Check: PASS run 33145685732.
- Service: BETA86_LIVE_INHERITS_BETA83_SERVICE_PASS_SERVICE_SOURCE_UNCHANGED.
- Visual/PDA pre-OTA: PASS run 33146411629, artifact 9675981318.
- Human visual 320x568 / 360x640 / 480x800: PASS.
- Stable/main/signer/authority: unchanged.

## Evidence
- 3 ô rà soát nhân sự nằm trên ô quét MNV: PASS.
- Thứ tự công việc: Vị trí → User Pick → PDA → Bàn Pack → User Pack: PASS.
- RESOURCE_CHANGE hiển thị dữ liệu Trước cập nhật / Sau cập nhật khi service có snapshot; bản ghi cũ fallback rõ ràng: PASS.
- Diễn biến trong ca sắp xếp mới nhất → cũ nhất: PASS.
- Sửa/xóa và các thao tác chỉnh sửa được gate bằng mật khẩu HHmm hiện tại theo Asia/Ho_Chi_Minh: PASS.
- SUPERADMIN thực tế được phép dùng thêm mật khẩu tài khoản cố định qua login verification; không hardcode secret: PASS.
- OTA baseline → 0.4.2-beta.87 exact bytes, SHA/size/signer/version và mở app: PASS.

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

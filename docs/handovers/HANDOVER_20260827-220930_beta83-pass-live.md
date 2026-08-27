# PICK PACK 1291 — HANDOFF SCHEMA V2

- schema_version: 2
- status: READY
- time_utc: 2026-08-27T22:09:30Z
- owner: Nguyễn Văn Tâm
- branch: release/beta83-owner-session-ui-auth-20260828
- working_head_sha: cc4fec70b127d1c3664b2b27dc8e3cd25da44a19
- archive_file: docs/handovers/HANDOVER_20260827-220930_beta83-pass-live.md

## Mục tiêu + DoD
Beta83 sửa vị trí rà soát nhân sự, thứ tự thông tin công việc, chi tiết trước/sau cập nhật, timeline mới tới cũ và xác thực thao tác HH:mm; toàn bộ pre-OTA + OTA install/readback PASS.

## LIVE / TARGET / CANDIDATE
- LIVE BETA: 0.4.2-beta.83 / versionCode 89.
- TARGET: PASS/LIVE.
- CANDIDATE LOCKED: run 33105240232; artifact 9660297032; source 919027d08b0abc20f90a39fc40079929b5bd1edf; SHA256 580c0c79f0a52db22872c40c21a62cff0ec10e46f4d72b3164c08e1437482727; size 13196221; signer d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e.
- Fast Check: PASS run 33104514278.
- Service: inherited BETA82 PASS, source unchanged.
- Visual/PDA pre-OTA: PASS run 33120654001, artifact 9666377472.
- Human visual 320x568 / 360x640 / 480x800: PASS.
- Stable/main/signer/authority: unchanged.

## Evidence
- 3 ô rà soát nhân sự nằm trên ô quét MNV: PASS.
- Thứ tự công việc: Vị trí → User Pick → PDA → Bàn Pack → User Pack: PASS.
- RESOURCE_CHANGE hiển thị dữ liệu Trước cập nhật / Sau cập nhật khi service có snapshot; bản ghi cũ fallback rõ ràng: PASS.
- Diễn biến trong ca sắp xếp mới nhất → cũ nhất: PASS.
- Sửa/xóa và các thao tác chỉnh sửa được gate bằng mật khẩu HH:mm hiện tại theo Asia/Ho_Chi_Minh: PASS.
- SUPERADMIN thực tế được phép dùng thêm mật khẩu tài khoản cố định qua login verification; không hardcode secret: PASS.
- OTA Beta82 → Beta83 exact bytes, SHA/size/signer/version và mở app: PASS.

## Lỗi/root cause/PASS path
- Trước cập nhật bị “—”: Android renderer/payload parser không đọc đầy đủ snapshot; Service đã lưu before/after, không đổi backend.
- Candidate attempt đầu dừng trước build vì guard script còn beta.82/code 88; sửa guard, không có APK bị khóa từ attempt lỗi.
- Fast Check đầu tiên lỗi cú pháp nối dòng Kotlin; sửa đúng điểm, run sau PASS.
- Không rebuild/resign candidate sau khi lock.

## Blocker
Không có.

## Invariants
Stable/main/signer/authority không đổi; không thêm provider/backend/authority.

## NEXT_ACTION
WAIT_FOR_OWNER_NEW_SCOPE

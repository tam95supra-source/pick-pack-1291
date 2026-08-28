# PICK PACK 1291 — HANDOFF SCHEMA V2

- schema_version: 2
- status: READY
- time_utc: 2026-08-28T02:27:22Z
- owner: Nguyễn Văn Tâm
- branch: release/beta85-storage-staff-auth-history-20260828
- working_head_sha: 10b4a94c723c7fe91f206972c69fbeef4eb6e393
- archive_file: docs/handovers/HANDOVER_20260828-022722_beta85-pass-live.md

## Mục tiêu + DoD
Beta85 hoàn tất 4 yêu cầu OWNER: dọn APK OTA cũ để không tăng storage theo phiên bản; danh sách rà soát hiển thị Nhà cung cấp • MNV • Họ tên và sort Nhà cung cấp → MNV → Họ tên; xác thực HHmm ±2 phút không text hướng dẫn dư; lịch sử chỉnh sửa đọc đúng payload/payload_json và before/after. Toàn bộ pre-OTA + OTA install/readback PASS.

## LIVE / TARGET / CANDIDATE
- LIVE BETA: 0.4.2-beta.85 / versionCode 91.
- TARGET: PASS/LIVE.
- CANDIDATE LOCKED: run 33129019651; artifact 9669569850; source 6d3716ac2a16f7aa27c16138c086f1c11684c2b9; SHA256 113e505139a8bb49b8d513e9f0bf2830246ea3afb25615eb3ade3f52bdfd7776; size 13212605; signer d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e.
- Fast Check: PASS run 33128870720.
- Service: inherited BETA83 PASS, source unchanged.
- Visual/PDA pre-OTA: PASS run 33135526429, artifact 9671908222.
- Human visual 320x568 / 360x640 / 480x800: PASS.
- Stable/main/signer/authority: unchanged.

## Evidence
- Dung lượng: chỉ dọn file APK OTA do app quản lý trong thư mục Download; không đụng SQLite/cache nghiệp vụ/offline. Regression dọn APK cũ PASS; OTA hậu cài đặt mở app và xác minh APK tải tạm đã bị xóa PASS.
- Rà soát nhân sự: hiển thị Nhà cung cấp • MNV • Họ tên; sort Nhà cung cấp → MNV → Họ tên; UI thật 320x568 xác minh PASS.
- Mật khẩu: HHmm, không phải HH:mm; ±2 phút PASS; không text hướng dẫn dư; Sửa/Xóa dùng chung gate; actual SUPERADMIN giữ fallback mật khẩu tài khoản qua login verification, không hardcode secret.
- Chi tiết chỉnh sửa: merge payload_json + payload; before/after và delta hiện đúng khi có evidence; bản ghi cũ thiếu snapshot không bị bịa dữ liệu: PASS.
- Visual human 320x568 / 360x640 / 480x800: PASS.
- OTA Beta83 → Beta85 exact bytes, SHA/size/signer/version/package và mở app: PASS.

## Lỗi/root cause/PASS path
- Beta84 bị loại trước OTA vì regex raw-string dùng escape sai khiến mọi HHmm bị từ chối. Beta85 sửa đúng regex số 4 chữ số; Fast Check + functional ±2 phút PASS.
- Verify attempt đầu Beta85 lỗi harness tham chiếu biến old82 sau khi nâng baseline; sửa harness old84 + gọi storage regression, giữ exact candidate.
- Pre-publish phát hiện OTA harness kiểm Beta83 versionCode 88 thay vì 89; sửa verifier trước production write, không đổi APK.
- Không rebuild/resign candidate Beta85 sau khi lock.

## Blocker
Không có.

## Invariants
Stable/main/signer/authority không đổi; không thêm provider/backend/authority.

## NEXT_ACTION
WAIT_FOR_OWNER_NEW_SCOPE

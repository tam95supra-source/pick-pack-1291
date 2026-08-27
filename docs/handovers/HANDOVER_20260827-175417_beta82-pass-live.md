# PICK PACK 1291 — HANDOFF SCHEMA V2

- schema_version: 2
- status: READY
- time_utc: 2026-08-27T17:54:17Z
- owner: Nguyễn Văn Tâm
- branch: release/beta82-current-day-reconciliation-20260827
- working_head_sha: 592d94759fe4fecdcf0a81c50afa41295dfe54a9
- archive_file: docs/handovers/HANDOVER_20260827-175417_beta82-pass-live.md

## Mục tiêu + DoD
Beta82 sửa rà soát nhân sự ngày hiện tại, danh sách ca đủ/thiếu, QR session cards, null-safe display và Settings rút gọn; toàn bộ pre-OTA + OTA install/readback PASS.

## LIVE / TARGET / CANDIDATE
- LIVE BETA: 0.4.2-beta.82 / versionCode 88.
- TARGET: PASS/LIVE.
- CANDIDATE LOCKED: run 33097369281; artifact 9657063583; source 70c2be4c2866fc71607bb4ad48229cc3ed2d231f; SHA256 6b09f5ed289e9a26b3fa93e95ee0885b2d2736c13cf7b1be0245f4f3cd216dbc; size 13196221; signer d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e.
- Fast Check: PASS run 33096409068.
- Service: inherited PASS, source unchanged.
- Visual/PDA pre-OTA: PASS run 33099453424, artifact 9657879443.
- Human visual 320x568 / 360x640 / 480x800: PASS.
- Stable/main/signer/authority: unchanged.

## Evidence
- Bỏ text RÀ SOÁT VÀO / RA + ngày: PASS.
- 3 ô ca và danh sách chỉ ngày thực tế hiện tại: PASS.
- Sau quét MNV có 3 ô: PASS.
- Ca đủ mở thẳng list; ca thiếu có RA CA + HIỂN THỊ CHI TIẾT NHÂN SỰ: PASS.
- Bấm MNV trong list mở luồng thông tin phiên như QR: PASS.
- Cảnh báo ngày cũ giữ riêng: PASS.
- null -> -: PASS.
- Thông tin ứng dụng / Cập nhật phiên bản / Nhật ký rút gọn: PASS.
- OTA Beta81 -> Beta82, exact SHA/size/signer/version và mở app: PASS.
- Beta81 update_check available=true Beta82; Beta82 available=false: PASS.

## Lỗi/root cause/PASS path
- Verifier startActivitySync chờ UI idle do animation vô hạn: sửa harness non-idle bounded.
- Accessibility ACTION_CLICK Ca HC trả false: harness fallback coordinate bounds.
- Ảnh Settings ban đầu chưa đưa mục cần duyệt vào viewport: capture harness SHOW_ON_SCREEN; không đổi APK.
- Không rebuild/resign candidate sau lock.

## Blocker
Không có.

## Invariants
Stable/main/signer/authority không đổi; không thêm provider/backend/authority.

## NEXT_ACTION
WAIT_FOR_OWNER_NEW_SCOPE

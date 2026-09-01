# PICK PACK 1291 — HANDOFF SCHEMA V2

- schema_version: 2
- status: READY
- task_state: TECHNICAL_PASS_AWAITING_OWNER
- time_utc: 2026-09-01T13:50:37Z
- owner: Nguyễn Văn Tâm
- branch: release/beta108-document-management
- archive_file: docs/handovers/HANDOVER_20260901-135037_beta109-technical-pass-awaiting-owner.md

## LIVE
- Beta109 LIVE: 0.4.2-beta.109 / versionCode 115 / package vn.pickpack1291.app.beta.publicbeta.
- Exact candidate: source a72d8e20eaebe60235338fd1b9aaebde42507825; run 33506205883; artifact 9799840161.
- SHA256 1c01a58eefe5d0501eccbfe0359a2d5c0b3ec159f5ef37889d757f0984bbc7c8; size 14167029; signer d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e.
- GitHub Release asset 539613285 exact bytes.
- OTA Beta108 -> Beta109 install/open/readback PASS.
- Stable/main/signer/authority unchanged.

## Technical DoD
- Fast Check 33510974424 PASS.
- Service live 33509679186 attempt 2 / 9801444305 PASS; exact duplicate PASS; rotation-aware near-similar PASS.
- Visual/PDA/API36/local durability 33511409449 / 9801982052 PASS; 39 screenshots + human PASS at 320x568 / 360x640 / 480x800.
- Offline category cache PASS.
- Durable selected-image draft restore PASS.
- Device regression 33514582110 / 9803110874 PASS.
- Runtime DoD 33514927663 attempt 2 / 9803295906 PASS.
- Terminal release 33515483109 PASS; publish 9803429207; PDA OTA 9803518172; final 9803526992.
- Release transport GITHUB_RELEASE_ONLY; Google Drive APK FORBIDDEN.

## Invariant
- DOCUMENT-MANAGEMENT-001 = TECHNICAL_PASS_AWAITING_OWNER.
- Không được chuyển ACTIVE_PASS cho tới OWNER xác nhận 2 mục còn lại.
- Mục OWNER đã OK từ Beta108 và phải giữ nguyên: 1,2,5,6,7,8.

## OWNER retest duy nhất
1. Ảnh gần giống có cảnh báo đúng; ảnh trùng hoàn toàn vẫn hoạt động như trước.
2. Khi mất mạng vẫn thấy danh mục, vẫn tiếp tục gửi vào hàng chờ; tắt/mở lại app không mất ảnh đang chọn và khi có mạng hệ thống tự gửi lại.

## Evidence
- ops/beta109-technical-pass.json
- ops/beta109-release-lock.json
- ops/beta109-human-visual-receipt.json
- qa/beta109_document_management_regression.md
- ops/beta-ota-current.json

## Blocker
Không có technical blocker. Đang chờ OWNER acceptance đúng 2 mục trên.

## NEXT_ACTION
WAIT_OWNER_RETEST_ONLY_2_DOCUMENT_ITEMS

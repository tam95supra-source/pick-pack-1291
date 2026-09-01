---
handover_schema: pick-pack-handover/v2
status: READY
created_at: 2026-09-01T13:20:00+07:00
owner: Nguyễn Văn Tâm
project: PICK PACK 1291
active_branch: beta/current
archive_file: docs/handovers/HANDOVER_20260901-132000_beta106-owner-accepted.md
base_or_live_version: 0.4.2-beta.106
task_state: OWNER_ACCEPTED
next_action: WAIT_FOR_OWNER_NEW_SCOPE
---

# BÀN GIAO PHIÊN

## 1. Trạng thái
- Beta LIVE: 0.4.2-beta.106 / versionCode 112 / package `vn.pickpack1291.app.beta.publicbeta`.
- Technical DoD: PASS.
- OWNER acceptance: PASS cho toàn bộ scope Beta106.
- OWNER lưu ý layout còn vài điểm chưa ưng nhưng sẽ chỉnh ở scope sau; không phủ nhận acceptance hiện tại.
- Stable: giữ nguyên READY_NOT_LIVE; không phát hành Stable trong scope này.

## 2. Exact release evidence
- Product source: `57e02d45b436c6bcb64bc5731671044af7c7c86d`.
- Candidate run/artifact: 33473965249 / 9787581956.
- Visual artifact: 9787692571; human PASS 320x568 / 360x640 / 480x800.
- Fast Check: 33476011598 PASS.
- Device regression: 33474768649 / 9787794484 PASS.
- Runtime DoD: 33475078900 / 9787884925 PASS.
- Terminal release: 33476108449 PASS.
- PDA OTA/install/readback: 9788292824 PASS.
- Final artifact: 9788296923 PASS.
- APK SHA256: `ea5bdf9696d9dae77f02fab815df6435a8317a66178bdb4c36bc051aa5bcd000`.
- APK size: 14068725.
- Signer: `d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e`.
- Stable/main/signer/authority unchanged.

## 3. Invariant đã khóa
- `SHIFT-STAFF-DOWNLOAD-QR-001` = ACTIVE_PASS.
- Rule đã khóa: danh sách nhân sự nhóm theo NCC; filter Tất cả/Trong ca/Đã ra ca có count; dòng nhân sự mở QR Vào/Ra; NCC thiếu/null hiển thị `Chưa xác định NCC`, không literal `null`; QR tải Beta dùng latest GitHub Release; Stable fail-closed cho tới khi phát hành.
- Regression: `SHIFT-STAFF-DOWNLOAD-QR-NULL-001`.

## 4. Scope sau
- Các tinh chỉnh layout OWNER muốn làm thêm là scope mới.
- Khi chỉnh layout phải giữ semantics ACTIVE_PASS ở trên; nếu muốn đổi semantics thì phải OWNER chốt lại trước.
- BETA-STABLE-AUDIT-001 và INFRA-RESILIENCE-001 giữ nguyên trạng thái trước đó.
- Stable chưa được tự phát hành.

## 5. NEXT_ACTION
WAIT_FOR_OWNER_NEW_SCOPE

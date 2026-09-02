# PICK PACK 1291 — HANDOFF SCHEMA V2

- schema_version: 2
- status: READY
- task_state: TECHNICAL_PASS_AWAITING_OWNER
- time_utc: 2026-09-02T00:13:24Z
- owner: Nguyễn Văn Tâm
- branch: beta/current
- release_branch: release/beta110-document-labor-attendance
- archive_file: docs/handovers/HANDOVER_20260902-001324_beta110-technical-pass-awaiting-owner.md

## LIVE
- Beta110 LIVE: 0.4.2-beta.110 / versionCode 116 / package vn.pickpack1291.app.beta.publicbeta.
- Exact candidate: source 1faebbf996836d442ec6e99ffba2a589bf3fcbd2; run 33554345340; artifact 9818862858.
- SHA256 ae83831ac6f0412e2d314418f64ef8f4e28e67fbcf2c3b06d7a83810bda93f84; size 14199797; signer d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e.
- GitHub Release asset 540340119 exact bytes.
- Stable/main/signer/authority unchanged.

## Technical DoD PASS
- Fast Check: 33569530461 PASS.
- Service live regression: 33568634524 / 9824237674 PASS.
- Visual/PDA/API36: 33569543281 / 9824551840 PASS; human visual 41 screenshots at 320x568 / 360x640 / 480x800 PASS.
- Device stale-discovery regression: 33570127113 / 9824662041 PASS.
- Runtime DoD: 33573848594 / 9825920815 PASS; backup_restore PASS; Stable public=false/manifest unavailable.
- Terminal release: 33574078129 PASS; publish 9826016343; OTA/install/readback 9826069523; final 9826075161.
- OTA Beta109 → Beta110: exact SHA/size/version/package/signer, installed and opened PASS.
- Technical receipt: ops/beta110-technical-pass.json.
- Release lock: ops/beta110-release-lock.json.

## Invariants awaiting OWNER
1. DOCUMENT-BATCH-001 — TECHNICAL_PASS_AWAITING_OWNER.
2. LABOR-TIME-RANGE-001 — TECHNICAL_PASS_AWAITING_OWNER.
3. MEAL-UI-NULL-001 — TECHNICAL_PASS_AWAITING_OWNER.
4. UI-COPY-DENSITY-001 — TECHNICAL_PASS_AWAITING_OWNER.

DOCUMENT-MANAGEMENT-001 và các ACTIVE_PASS cũ giữ nguyên semantics; Beta110 regression đã reverify PASS.

## OWNER checklist
1. Quản lý biên bản: chọn nhiều ảnh; Một biên bản nhiều trang/Nhiều biên bản; lọc loại; chọn một/nhiều ảnh đã tải để xóa; Lịch sử đúng.
2. Công nhật: chọn giờ/phút bắt đầu-kết thúc; có thể ghi bắt đầu trước/kết thúc sau; OPEN chặn Ra ca; danh sách/cảnh báo OPEN đúng.
3. Điểm danh: layout gọn; dữ liệu thiếu/JSON null hiển thị dấu -; rule ngày hiện tại và cảnh báo cũ giữ nguyên.
4. Các màn nghiệp vụ trong scope Beta110 không còn text giải thích/hướng dẫn kỹ thuật thừa; nội dung nghiệp vụ vẫn đủ.

OWNER trả lời dạng: `1 OK, 2 OK, 3 OK, 4 OK` hoặc đánh dấu mục chưa OK.

## Blocker
Không có blocker kỹ thuật. Chỉ chờ OWNER acceptance theo policy.

## NEXT_ACTION
WAIT_OWNER_BETA110_ACCEPTANCE_CHECKLIST_1_TO_4

# PICK PACK 1291 — HANDOFF SCHEMA V2

- schema_version: 2
- status: READY
- task_state: TECHNICAL_PASS_AWAITING_OWNER
- time_utc: 2026-09-02T04:48:39Z
- owner: Nguyễn Văn Tâm
- branch: release/beta111-owner-ui-labor-nav
- archive_file: docs/handovers/HANDOVER_20260902-044839_beta111-final-technical-pass-await-owner.md

## LIVE
- Beta111 LIVE: 0.4.2-beta.111 / versionCode 117 / package vn.pickpack1291.app.beta.publicbeta.
- Exact candidate: source 03b37e5aa2726c273cc1e7c4a2161763bd3c4d2d; run 33586428789; artifact 9830403339.
- SHA256 f67049067e600f4d8439d0ae088889f7b35df8b215e5432a2fcdd54f05f04a4f; size 14216181; signer d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e.
- Terminal 33590747613 PASS; publish 9831669563; OTA/install/readback 9831721383; final 9831726759.
- Stable/main/signer/authority unchanged.

## Technical DoD
- Fast Check product/regression 33588839641 PASS.
- Service 33588851239 / 9831120144 PASS.
- Visual/PDA/API36 33589199933 / 9831243286 PASS; 41 screenshots + human visual PASS 320x568 / 360x640 / 480x800.
- Device discovery 33590310367 / 9831531954 PASS.
- Runtime DoD 33590505522 attempt 2 / 9831607439 PASS; attempt 1 chỉ gặp Google Sheet 503 transient.
- Terminal release 33590747613 PASS; exact GitHub Release OTA/install/readback/finalize PASS.
- Post-release CI harness: Fast Check 33591900310 PASS; pass_live route verify 33591932637 PASS; final readback 33592181385 PASS.
- Run 33591410014 = SUPERSEDED harness-only route failure trước fix; không publish/rebuild/rollback và không còn là failure hiện hành.
- Receipt: ops/beta111-technical-pass.json + ops/beta111-ci-harness-final-pass.json.

## Invariants chờ OWNER
- NAV-HISTORY-BACK-001: TECHNICAL_PASS_AWAITING_OWNER
- UI-REVIEW-WARNING-001: TECHNICAL_PASS_AWAITING_OWNER
- LABOR-EXACT-SESSION-002: TECHNICAL_PASS_AWAITING_OWNER
- HISTORY-DELETE-CANONICAL-001: TECHNICAL_PASS_AWAITING_OWNER
- DOCUMENT-BATCH-MODE-TICK-002: TECHNICAL_PASS_AWAITING_OWNER
- Mọi ACTIVE_PASS cũ giữ nguyên semantics.

## OWNER checklist
1. Rà soát vào/ra và các cảnh báo liên quan có kích thước, màu, bố cục đồng nhất.
2. Back/vuốt: 1→2→3 phải về 3→2→1; 5→3 phải về 3→5; ở root không vuốt thoát app.
3. Công nhật: wheel giờ/phút kéo dọc không xoay vòng; nhập chỉ BĐ hoặc BĐ+KT đều hoạt động.
4. Công nhật: sửa/correction thời gian được; danh sách theo ngày có cả đang mở/pending và đã hoàn thành.
5. Ra ca khi còn công nhật OPEN tự mở đúng công nhật của đúng nhân sự/phiên; không phát sinh stale LABOR_NOT_OPEN/ATTENDANCE_NOT_ACTIVE.
6. Quản lý biên bản: Một biên bản nhiều trang / Nhiều biên bản dùng lựa chọn tích loại trừ nhau; grouping cũ giữ nguyên.
7. Lịch sử: xóa mục canonical hoạt động; mục local-only/deferred missing không lặp 404/retry.

## Blocker
Không có.

## NEXT_ACTION
OWNER_ACCEPTANCE_BETA111_CHECKLIST_1_TO_7

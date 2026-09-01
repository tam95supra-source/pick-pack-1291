# PICK PACK 1291 — HANDOFF SCHEMA V2

- schema_version: 2
- status: READY
- task_state: OWNER_PARTIAL_ACCEPTANCE_FIX_REQUIRED
- time_local: 2026-09-01T18:32:00+07:00
- owner: Nguyễn Văn Tâm
- branch: release/beta108-document-management
- archive_file: docs/handovers/HANDOVER_20260901-183200_beta108-owner-partial-fix-required.md

## LIVE
- Beta108 LIVE: 0.4.2-beta.108 / versionCode 114.
- Exact terminal release 33499528769 PASS.
- Stable/main/signer/authority unchanged.

## OWNER acceptance
- 1 OK; 2 OK; 5 OK; 6 OK; 7 OK; 8 OK.
- 3 PARTIAL: exact duplicate OK; near-similar không cảnh báo.
- 4 FAIL: mất mạng làm danh mục biến mất; restart làm mất ảnh đang chọn.
- Các mục đã OK phải được giữ nguyên semantics và regression.

## Latest manual log
- manual-20260901-183159-fd9d9ebb-b421-4152-a745-fe3b4b4f7d96.json.
- 18:26:02 +07: Unable to resolve host pickpack.1291.workers.dev.
- 18:31:57 +07: Mạng 112 ms / Đồng bộ Hoàn tất / Dịch vụ Cloudflare.
- Outage mạng/DNS là thật; Service phục hồi bình thường.

## Root cause
- Near-similar: Service chỉ so dHash một hướng với threshold 6; ảnh cùng cảnh khác xoay/góc có thể vượt ngưỡng.
- Offline categories: refreshCategories() xóa last-known categories khi Service fail.
- Selected image: chỉ nằm RAM trước enqueue; restart trước enqueue làm mất ảnh.
- Pending đã enqueue: durable store + WorkManager retry vẫn tồn tại.

## Fix scope duy nhất
1. Rotation-aware perceptual hash + ngưỡng cảnh báo phù hợp; exact duplicate giữ nguyên.
2. Cache danh mục local theo account/environment; network fail giữ last-known-good.
3. Durable selected-image draft; restore sau restart; account scoped; chỉ xóa draft sau enqueue thành công.
4. Regression cho 3 lỗi trên; không thay 1,2,5,6,7,8.

## Invariant
- DOCUMENT-MANAGEMENT-001 = LOCKED_REQUIREMENT_PENDING_FIX.
- Partial acceptance receipt: ops/beta108-owner-acceptance-partial.json.

## NEXT_ACTION
FIX_NEAR_SIMILAR_AND_OFFLINE_DRAFT_ONLY

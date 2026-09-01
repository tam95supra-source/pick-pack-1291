# Beta109 — DOCUMENT-MANAGEMENT-001 regression

Status: ACTIVE_PASS  
Version: 0.4.2-beta.109 / versionCode 115  
Source: a72d8e20eaebe60235338fd1b9aaebde42507825  
Exact APK SHA256: 1c01a58eefe5d0501eccbfe0359a2d5c0b3ec159f5ef37889d757f0984bbc7c8

## Scope sửa từ OWNER partial acceptance Beta108
- Giữ nguyên semantics các mục 1,2,5,6,7,8 đã OWNER xác nhận OK.
- Near-similar: perceptual dHash theo 4 hướng xoay, threshold Hamming 16; exact duplicate vẫn chặn như trước.
- Offline categories: last-known-good cache theo account/environment, lỗi mạng không xóa danh mục khỏi UI.
- Selected image: durable draft theo account, restore sau restart; chỉ xóa draft sau enqueue thành công; WorkManager retry idempotent khi mạng trở lại.

## Evidence PASS Beta109
- Exact candidate: run 33506205883 / artifact 9799840161 / SHA256 1c01a58eefe5d0501eccbfe0359a2d5c0b3ec159f5ef37889d757f0984bbc7c8 / size 14167029.
- Fast Check: run 33510974424 PASS.
- Service live: run 33509679186 attempt 2 / artifact 9801444305 PASS; exact_duplicate_guard=PASS; rotation_aware_near_similar=PASS.
- Visual + direct PDA + API36 + local durability: run 33511409449 / artifact 9801982052 PASS; 39 screenshots; human PASS 320x568 / 360x640 / 480x800.
- document_selected_draft_durable_beta109=true.
- document_category_cache_offline_beta109=true.
- Exact device stale-discovery: run 33514582110 / artifact 9803110874 PASS.
- Runtime DoD: run 33514927663 attempt 2 / artifact 9803295906 PASS.
- Publish + OTA/install/readback + finalize: run 33515483109 PASS; publish 9803429207; PDA 9803518172; final 9803526992.
- GitHub Release asset 539613285 exact SHA256/size; OTA Beta108 → Beta109 exact bytes, installed/opened PASS.
- Stable/main/signer/authority unchanged.

## OWNER acceptance
- Beta108 đã khóa: 1,2,5,6,7,8 OK.
- OWNER xác nhận thêm ngày 2026-09-01 22:04 +07:00:
  1. Near-similar warning: OK; exact duplicate giữ nguyên.
  2. Offline category + durable selected draft + queued auto retry: OK.
- DOCUMENT-MANAGEMENT-001 = ACTIVE_PASS.
- Receipt: ops/beta109-owner-acceptance.json.

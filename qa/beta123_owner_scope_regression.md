# Beta123 OWNER UI / realtime regression

Status: LOCKED_REQUIREMENT_PENDING_FIX until exact candidate Technical DoD PASS; then TECHNICAL_PASS_AWAITING_OWNER. Do not mark ACTIVE_PASS without OWNER acceptance.

## Impacted ACTIVE invariants
- UI-STATUS-001 / UI-STATUS-DETAIL-VI-003: Mạng / Đồng bộ / Dịch vụ pinned; Vietnamese details; manual sync retained.
- QR-LOCAL-001: local-first employee render; Service reconcile cannot rebuild interactive UI.
- MEAL-DATE-001 / MEAL-WARN-001: current-day attendance and warning semantics retained.
- ROLE-HISTORY-001: USER cannot access History.
- HISTORY-DELETE-CANONICAL-001 / HISTORY-SUPERADMIN-CLEANUP-002: canonical tombstone; local terminal cleanup; pending business mutation preserved.
- SUPERADMIN-EFFECTIVE-ROLE-003: effective role remains the business permission authority.
- SETTINGS-REGION-INHOUSE-DROP-001: Settings regions / Inhouse / dropped-goods semantics retained.
- PDA-SOURCE-MASTER-001: PDA source remains canonical and round-trips unchanged.
- OTA-BETA-001 / CHANGELOG-CURRENT-VERSION-001 unchanged.

## New OWNER-locked requirements
1. Settings: USER/ADMIN/SUPERADMIN can clear cache or clear all local app data after confirmation only, no password. Clear data must not call Service deletion; app returns to first-install local state and re-syncs canonical data after next login/start.
2. Settings regions use visually distinct but consistent backgrounds; no region/invariant removal.
3. History: SUPERADMIN can delete all history for selected date using current secure history-delete confirmation; business mutations pending sync are never cancelled. Search hint: `Tìm mã nhân viên, họ tên, nghiệp vụ …`; controls compact; detail Vietnamese and useful, no owner/AI instructional prose.
4. Header: Network shows transport + ping; Service shows actual dynamic provider/route (Cloudflare/LAN/DR/etc.) or `Không hoạt động`; Sync exposes local queue counts.
5. Sync recovery: ADMIN/SUPERADMIN can retry, force retry with immutable event IDs/idempotency, and delete only terminal/safe queue rows. Pending business mutation cannot be permanently deleted.
6. Staff search must debounce/chunk so typing does not synchronously rebuild the list per character.
7. Dropped goods: 50 rows/page, previous/next, time one line, no `Service/D1 xác nhận ngay...` instructional text.
8. Report title `Báo cáo tình hình nhân sự`; choices `Ca 1 và HC`, `C2`, `Cả ngày`; no `Phạm vi báo cáo`; bold table/position labels; day-labor position counts under tenure; actual Pick & Pack section titled `Nhân sự pick & pack thực tế sau khi loại trừ hỗ trợ`; no total-personnel/deduction summary rows.
9. Labor: warning acknowledgement key is employee/session/date scoped, never position-global; new leader/puller still warns; compact selectors; batch actions update UI once; bulk correction supports shared start/end and deduction flag.
10. PDA exchange shows canonical PDA source and keeps PDA identity/source authority.
11. Attendance search hint `Tìm mã nhân viên / họ tên`; local cached state remains visible during background refresh; no full-screen flicker.
12. QR scan: current-shift detailed list is visible before scan and hidden immediately after submit; employee/shift detail is flattened so shift content is not an extra nested detail page.
13. Realtime: local state/warning response target <=100 ms where local data exists; Service reconcile is background/in-place and must not full-screen reload/flicker.

## Negative cases
- USER still cannot open History.
- Settings clear-data never issues server delete/mutation.
- History delete-all cannot delete/cancel pending business mutation.
- Non-admin cannot use sync recovery controls.
- Force retry preserves event ID; no duplicate new event.
- Safe-delete rejects PENDING/RETRY/INFLIGHT business mutations.
- Stale/blank labor session IDs cannot cause acknowledgement to hide warnings for another employee.
- PDA source is never inferred from UI-only cache when canonical master has a value.
- Service response after local QR render cannot erase in-progress selections.
- Stable/main/signer/authority remain unchanged.


## Beta126 remediation — OWNER DOCX scope audit
Status: LOCKED_REQUIREMENT_PENDING_FIX until exact Beta126 candidate passes all gates; then TECHNICAL_PASS_AWAITING_OWNER.

New mandatory regression checks:
- Settings region fills are actually distinct at rendered background level; cache/reset semantics retained for every role.
- Staff search is debounce-driven and cannot synchronously rebuild on every character.
- Report contains `BÁO CÁO TÌNH HÌNH NHÂN SỰ`, `Ca 1 và HC / C2 / Cả ngày`, has `CHI TIẾT CÔNG NHẬT` and `NHÂN SỰ PICK & PACK THỰC TẾ SAU KHI LOẠI TRỪ HỖ TRỢ`, and contains no `Tổng nhân sự` / `Khấu trừ công nhật` summary rows.
- Labor batch create/finish uses bounded concurrency and one UI refresh at completion; no recursive per-person `next(index,ok)` chain.
- Labor bulk edit supports shared BĐ, shared KT and tri-state deduction while preserving fixed-position deduction guards.
- Header Service keeps actual provider/route visible when degraded.
- Previously proven History/queue recovery/Drop/PDA source/Meal local-first/QR roster-hide behavior must remain unchanged.
- Exact candidate visual matrix: 320x568, 360x640, 480x800 with human inspection; PDA functional must exercise Staff search, Report, Labor batch selector/edit, Settings and QR navigation.

# Beta115 OWNER scope regression — revised items 6–8

OWNER: Nguyễn Văn Tâm  
Scope: only the revisions requested after Beta114 partial acceptance.  
Baseline: items 1,2,3,4,5,9,10 from Beta114 remain ACTIVE_PASS and must not regress.

## 6. Công nhật

### Time authority
- Start time remains non-future and must not precede attendance entry.
- Fixed scheduled end caps:
  - Ca 1: 14:00.
  - Ca HC: 17:00.
  - Ca 2: 22:00.
- End time may be preplanned into the future up to the scheduled end while the attendance session is ACTIVE.
- If the worker remains after scheduled shift end, labor may extend only as actual elapsed attendance extends.
- Once attendance has an actual exit_at, labor end must never exceed that exit time.
- Attendance exit must fail closed if a completed/preplanned labor interval still ends in the future; operator must correct labor first.
- End-before-start, interval overlap and more than one OPEN interval remain forbidden.

### Time picker
- Minutes are exactly 00, 15, 30, 45.
- Minute wheel wraps 45 → 00.
- Hour wheel wraps 23 → 00.
- End picker may choose future values; start picker may not.

### Khấu trừ nhân sự
- Boolean true / Có is persisted canonically as deduct_staff=1.
- Report deduction is exact by MNV + shift.
- A deducted employee is removed from their original main-position/tenure population and appears in Hỗ trợ.
- Multiple labor intervals for the same MNV/shift never double-count support.
- If support total is zero, the support block is hidden.
- Existing no-deduction behavior remains unchanged.

### Layout and grouping
- Canonical MNV scan is always above the labor list.
- The same scan remains visible in employee labor context.
- No substitute "Mã nhân viên KHÁC" button is allowed.
- Daily list renders one card per employee/session even when that employee has multiple labor intervals.
- Tapping the employee card opens detail containing every interval.

### Bulk create / finish
- Bulk create supports individual selection plus supplier and position filters, including combined filters.
- Bulk finish supports the same selection model for OPEN labor.
- Both actions require the current real-time action password flow before mutation.
- Each selected employee is re-read from Service immediately before mutation.
- Partial failures are reported explicitly; no failure may be silently discarded.
- Exact labor_id/session identity is preserved.
- Existing idempotency/outbox/authority fencing remains intact.

## 7. Select hierarchy
- Every canonical select must show a small/muted label, a stronger/bold selected value and weaker/normal option rows.
- Explicit regression: "Lý do không vào ca" uses the canonical select layout, not raw AlertDialog setItems.
- Existing common form outline remains unchanged.
- ACTIVE_PASS ReviewAlertUi Beta112 geometry/color semantics remain unchanged.

## 8. Display-only date calendars
- TODAY is always selectable, even when no data exists for today.
- Other empty dates remain visible but dim/disabled.
- Dates with real data remain selectable.
- Edit/correction date-time pickers remain unrestricted and are not converted to display-only behavior.
- Report, History, Labor and Meal Attendance must follow the same TODAY exception.

## Protected ACTIVE_PASS baseline
- CHANGELOG-CURRENT-VERSION-001
- ADMIN-AUDIT-PASSWORD-001
- HISTORY-SUPERADMIN-CLEANUP-002
- UI-EMPLOYEE-SCAN-ROSTER-001
- LABOR-SCAN-PINNED-004
- UI-FORM-BASE-CONSISTENCY-003
- UI-REVIEW-WARNING-001
- NAV-HISTORY-BACK-001
- LABOR-EXACT-SESSION-002
- HISTORY-DELETE-CANONICAL-001
- DOCUMENT-BATCH-MODE-TICK-002
- SHIFT-STAFF-DOWNLOAD-QR-001
- all other existing ACTIVE_PASS invariants.

Release is not allowed until these cases and the full impacted ACTIVE_PASS regression are PASS on the same exact signed Beta115 candidate.

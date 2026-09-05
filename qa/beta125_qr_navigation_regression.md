# Beta125 QR navigation regression

## Locked failures
1. Beta123 regression: after a successful QR employee lookup, the full current-shift roster must not be appended to the employee result.
2. Beta124 pre-OTA regression: `EMPLOYEE_LOADING`/`EMPLOYEE_LOOKUP_ERROR` are implementation states of the same scanned-employee view and must not become extra navigation-history frames.

## Required regression
- QR screen before scan keeps the current-shift roster/list flow.
- Successful scan hides the roster and shows only the scanned employee/session context.
- Scan-in, scan-out, rescan/reconcile and realtime timeline update do not re-append the roster.
- One Back from a scanned employee result returns to the actual QR screen immediately before it.
- Internal loading/error/result transitions do not add fake Back frames.
- Returning to the QR screen restores the roster/list flow.
- Root Back/swipe behavior and other navigation-history semantics stay unchanged.

## Negative guards
- Do not remove `screenBackStack` history semantics.
- Do not force a fixed parent screen.
- Do not reload the Service solely to perform Back.
- Do not re-add `addInlineCurrentShiftStaff(body)` inside `renderEmployee()`.

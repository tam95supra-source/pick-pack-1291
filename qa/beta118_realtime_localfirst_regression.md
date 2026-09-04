# Beta118 realtime/local-first regression

Scope locked from latest OWNER feedback 2026-09-04.

## Required behavior

- Labor batch create/finish updates the visible list in-place from local optimistic cache; no full `laborHome()` rebuild after success.
- A stale Service list must not erase a freshly confirmed local labor row during the bounded reconcile grace window.
- Two consecutive labor rows must remain visible as two rows before background reconcile completes.
- Foreground realtime invalidations carry `event_type`; UI refresh is routed only to the affected warning/module instead of reloading every warning.
- After canonical day projection is saved, LABOR_HOME re-renders from local projection/cache without an extra labor Service list round-trip.
- Old-session warning re-renders from local projection; SUPERADMIN bulk old-session exit applies returned remaining rows immediately.
- PDA exchange keeps its optimistic holder update then reconciles in background.
- Post-meal warning/screen fast refresh remains Service-authoritative for relevant MEAL events, while day-projection completion must not fire a duplicate warning reload.

## Owner follow-up retained

- Document refresh icon on same filter/select/delete row; draft deletion confirmation; helper copy removed.
- Drop receive compact unlabeled row, selected-delete only, max 50/page, pagination and inline action row.
- Old-session bulk exit remains SUPERADMIN + canonical time-password gate; labor sessions skipped; PDA auto-confirmed on bulk exit.

## Regression failure

Any visible full-screen rebuild caused only by a successful local labor mutation, loss of an optimistic second row under stale remote readback, generic day event triggering unrelated warning reload, or regression of the owner follow-up items above is a release blocker.

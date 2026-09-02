# Beta113 owner-scope regression

Status: LOCKED_REQUIREMENT_PENDING_FIX until technical gates pass; then TECHNICAL_PASS_AWAITING_OWNER. Existing ACTIVE_PASS invariants remain unchanged.

## Required checks

1. **Changelog/current version** — Settings must show Beta113 notes for Beta113. A Beta version bump without matching `ReleaseNotes.VERSION_NAME` must fail build.
2. **Password audit** — successful password change must create canonical admin audit action `change_password`; durable routing type `admin_audit` must never replace the business action. No password/proof/verifier in audit payload.
3. **SUPERADMIN History delete** — HHmm ±2 or actual SUPERADMIN password remains required. Canonical Service IDs use `history_delete`; local terminal/unsyncable cards delete locally. Deleting a History card must not silently cancel a still-pending business mutation.
4. **MNV scan** — same 50dp height, stronger 2dp teal boundary and stronger value typography.
5. **Labor layout** — scan/input is above all daily labor list content regardless of list size.
6. **Multi-interval labor** — multiple intervals per employee/business session are allowed; each has its own `labor_id`; max one OPEN; intervals cannot overlap; start/end cannot be future; start cannot precede attendance entry; completed correction cannot exceed attendance exit; edit/finish targets exact labor ID; prior intervals remain visible.
7. **Select hierarchy** — form label is visually distinct from selected value; selected value is stronger than option list text; PDA searchable select follows the same hierarchy.
8. **Data-date calendar** — Report, History, Labor only enable dates containing real data. Empty dates are visible but dim/disabled. Staff start-date/time correction editors remain unrestricted.
9. **Shift reconciliation** — tiles only show quick entered/exited status. Tap shows only pending-to-exit staff with RA CA action. Full current-day staff roster renders inline below scan; after scanning an employee, that employee/session detail renders before the inline roster.
10. **UI consistency** — common form controls use canonical 12dp radius/1dp outline; MNV scan uses intentional 2dp emphasis. `ReviewAlertUi` Beta112 locked 42dp/10.5sp/radius10/stroke2 severity semantics must remain unchanged.

## Gate
`python3 tools/beta113_owner_scope_contract.py` plus existing Beta111/Beta112 contracts, Service TypeScript check, Android unit tests/build, visual matrix 320x568/360x640/480x800, exact-candidate PDA functional and release gates.

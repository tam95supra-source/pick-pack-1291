# Beta106 shift staff null regression

- Scope: shift staff roster / NCC grouping.
- Regression fixture: supplier is JSON null.
- Required result: UI shows `Chưa xác định NCC`; literal `null` must not be visible.
- Automated assertion: `SHIFT_STAFF_VISIBLE_NULL_FOUND` must never fire.
- Exact APK bytes are not changed by this QA-only record.

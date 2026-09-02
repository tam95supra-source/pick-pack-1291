# Beta111 — OWNER UI / Labor / Navigation Regression

OWNER: Nguyễn Văn Tâm
Baseline: Beta110 LIVE OWNER-accepted. All ACTIVE_PASS semantics remain locked.

## Scope locked for Beta111
1. Rà soát vào/ra và cảnh báo dùng cùng visual language: chiều cao, typography, radius/stroke và severity colors nhất quán.
2. System Back và edge-swipe Back follow actual screen history, không dùng bảng parent cố định.
3. Labor authority là Service exact session/business_date/labor_id; cache local không quyết định start/finish/exit.
4. Chọn giờ/phút bằng vertical NumberPicker, wrapSelectorWheel=false.
5. Labor hỗ trợ start-only hoặc start+end; OPEN start/end có thể hoàn tất sau; completed labor có correction qua xác nhận.
6. Exit khi exact Service session còn labor OPEN phải mở thẳng màn labor của đúng session.
7. Labor list theo ngày hiển thị cả OPEN và COMPLETED.
8. Document batch mode dùng tick choices, không Spinner/select.
9. History delete chỉ gửi canonical Service event; 404 target-not-found ở deferred queue là terminal cleanup.

## Regression minimum
- nav 1→2→3→Back=2→Back=1
- nav 5→3→Back=5
- same-screen rerender không tạo history frame giả
- exact-session labor current day / old active session
- stale local labor không quyết định finish/exit
- start-only; start+end; edit start on OPEN; correction COMPLETED
- LABOR_NOT_OPEN / ATTENDANCE_NOT_ACTIVE stale-context regression
- exit OPEN labor redirects exact session
- daily list OPEN + COMPLETED
- non-wrapping hour/minute wheels
- warning/reconciliation geometry/style
- document multipage vs multi-document tick exclusivity
- canonical history delete + terminal 404 cleanup
- all Beta110 ACTIVE_PASS impacted regression remains PASS

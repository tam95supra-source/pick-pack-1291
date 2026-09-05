# Beta127 OWNER R2 regression

Status: LOCKED_REQUIREMENT_PENDING_FIX until exact Beta127 candidate completes all pre-OTA gates.

## Bugs caught after Beta126 false-positive PASS
1. Settings rendered `ĐẶT LẠI DỮ LIỆU` instead of OWNER-required `XÓA DỮ LIỆU ỨNG DỤNG`.
2. Report passed source grep while `BÁO CÁO TÌNH HÌNH NHÂN SỰ` was not visible because `appBar(title)` does not render title text.
3. `CHI TIẾT CÔNG NHẬT` was after Pick & Pack and vanished when support data was empty.

## Mandatory evidence
- Exact-device instrumentation sees the new Settings label and rejects the old label.
- Exact-device instrumentation sees report title, `CHI TIẾT CÔNG NHẬT`, and Pick & Pack result title.
- Static contract locks report ordering and empty-support state.
- Existing full functional/visual/API36/service/runtime/OTA gates remain mandatory; ACTIVE_PASS semantics are unchanged.

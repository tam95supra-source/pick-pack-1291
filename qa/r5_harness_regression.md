# R5 — độ tin cậy của kiểm thử

Nguồn yêu cầu: `ops/OWNER_SCOPE_CURRENT.json`, requirement `R5-15`.

| Phạm vi | Kiểm thử | Kết quả / giới hạn |
|---|---|---|
| LABOR-MULTI-INTERVAL-003 | `node --experimental-vm-modules tools/r5_labor_clock_regression.mjs` | 54 case trên hàm Service thật, SQLite tách biệt và đồng hồ cố định; đủ ba ca, trước/cuối ca, cap giờ ra thực tế, OPEN và ranh giới 60 giây. Auth/push được giả lập; không phải bằng chứng LIVE hoặc UI. |
| QUOTA-REALTIME-DELTA-001 | `python3 tools/r5_measurement_receipt_regression.py` | Raw 500 ms đạt gate mẫu; raw 1.500 ms dù trừ kết nối còn 200 ms vẫn FAIL. Số quy đổi/ngày không được gọi là phép đo đầy đủ. |
| OTA-BETA-001 | `bash tools/beta83_publish_ota.sh` khi scope còn LOCKED | Bị chặn trước khi đọc credential hoặc cập nhật manifest. Bootstrap canonical bắt buộc. |

Regression clock còn được kiểm tra đối chứng: bỏ điều kiện chặn future labor khỏi từng đường `core.ts` hoặc `session_hotfix.ts` trong bản sao tạm thì kiểm thử phải FAIL. Mã nguồn Service chính thức không bị thay đổi.

CI `34044419955`, artifact `9992647389`: 54 clock cases PASS; bước đọc gói Cloudflare bị HTTP 403 ở subscriptions, nên typecheck/deploy phía sau chưa chạy. Đây không phải Service Technical PASS.

Hai mốc của bài test LIVE phải phân biệt: khi giờ kết thúc còn đủ xa, future-exit được kiểm qua HTTP và isolated clock; khi gần/cuối ca, nhánh không thể tạo hợp lệ end_at > now+60s được kiểm bằng exact functions với isolated clock. Receipt luôn ghi nguồn coverage, không ghi nhận một HTTP call chưa chạy.

Trước R5 Technical PASS vẫn cần bằng chứng đủ scope canonical. Mẫu ACK→HTTP delta, phép trừ thời gian kết nối, benchmark reducer và phép tính quy đổi 1.540 events không thay thế đo full day, realtime UI/WS hoặc kiểm thử lỗi.

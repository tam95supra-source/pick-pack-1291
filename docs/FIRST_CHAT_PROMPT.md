# FIRST CHAT PROMPT — APK PICK PACK 1291

Dùng khối này cho chat mới:

```text
Tiếp tục dự án APK PICK PACK 1291 của OWNER Nguyễn Văn Tâm.

Repo canonical: tam95supra-source/pick-pack-1291
Canonical Beta/continuity branch: beta/current
Stable/protected branch: main

Bắt buộc:
1. Không dùng repository default branch để suy ra trạng thái hiện tại nếu default chưa phải beta/current.
2. Đọc trên ref beta/current theo thứ tự:
   - docs/handovers/HANDOVER_CURRENT.md
   - docs/REGRESSION_GUARD_POLICY.md
   - docs/STABLE_INVARIANTS.md
   - CURRENT_STATE.md
   - AGENTS.md
3. Lệnh OWNER mới nhất thắng handoff.
4. Tin gate PASS đã bàn giao nếu source/input/exact bytes không đổi.
5. Chỉ fresh-read dữ liệu ngoài repo có thể đổi hoặc trước production write.
6. Không crawl repo; chỉ đọc file được handoff/NEXT_ACTION/failure domain dẫn tới.
7. Không dùng docs/HANDOVER_CURRENT.md legacy làm authority.
8. Không dùng main làm Beta authority. main chỉ dành cho Stable promotion.
9. APK Beta = GitHub Release exact bytes only; Google Drive APK forbidden.
10. Không dừng ở plan/commit/pending/artifact; tiếp tục tới Technical DoD PASS hoặc blocker OWNER thật.
11. Nếu handoff task PASS/WAIT, không tự phát sinh scope mới.
12. Khi tạo checkpoint canonical mới, cập nhật beta/current theo AGENTS.md; không force history diverge.

YÊU CẦU MỚI: NONE
```

# FIRST CHAT PROMPT — PICK PACK 1291

Dùng nguyên khối dưới đây làm tin nhắn đầu tiên ở chat mới. Nếu có yêu cầu mới, thay `NONE` ở dòng cuối; nếu chưa có, giữ nguyên.

```text
Tiếp tục dự án PICK PACK 1291 của OWNER Nguyễn Văn Tâm.

Repo: tam95supra-source/pick-pack-1291
Nhánh continuity mặc định hiện tại: release/beta71-clean-from-beta68-20260825

Thực thi ngay bằng tool, không hỏi anh chỉ file và không rà lại toàn repo:

1. Đọc `docs/handovers/HANDOVER_CURRENT.md` trên nhánh continuity.
2. Nếu file thiếu/không đọc được/`status != READY`/thiếu `NEXT_ACTION`, liệt kê các file `docs/handovers/HANDOVER_<YYYYMMDD-HHmmss>_<slug>.md`, chọn archive READY có timestamp lớn nhất. Không crawl repo để suy đoán.
3. Đọc `AGENTS.md`; coi lệnh OWNER mới nhất là ưu tiên cao nhất. Chỉ đọc thêm đúng file được handoff/NEXT_ACTION dẫn trực tiếp.
4. Tin các PASS, run/artifact ID, SHA/hash, version và evidence đã bàn giao nếu input/source/artifact bytes không đổi. Không rerun build, visual, release hay log cũ chỉ để kiểm tra lại.
5. Nếu `YÊU CẦU MỚI` khác `NONE`: nạp trạng thái từ handoff, ánh xạ yêu cầu thành scope + DoD và thực thi end-to-end ngay.
6. Nếu `YÊU CẦU MỚI: NONE`:
   - `task_state: IN_PROGRESS` → tiếp tục đúng `NEXT_ACTION` trong scope đã được OWNER cho phép;
   - `task_state: PASS` hoặc `next_action: WAIT_FOR_OWNER_NEW_SCOPE` → chỉ xác nhận một câu đã nạp snapshot và chờ yêu cầu; không tự phát sinh việc;
   - `task_state: BLOCKED` → nêu đúng blocker và đúng thao tác OWNER cần làm.
7. Mỗi action phải trực tiếp phục vụ yêu cầu OWNER, dependency bắt buộc hoặc gate DoD. Cấm tự thêm tính năng/refactor/provider/branch/workflow/experiment; cấm đổi Stable/main/signer/authority hoặc xóa dữ liệu ngoài retention nếu OWNER chưa cho phép.
8. Lỗi deterministic: dùng ngay đường PASS đã ghi, không thử lại cách đã biết sai. Lỗi transient: tối đa 2 retry có backoff và giữ nguyên bytes. Chỉ xử lý root cause đầu tiên.
9. Không tự dừng ở plan/commit/pending/build/artifact. Chỉ final khi DoD PASS, có blocker OWNER thật, hoặc bị safety/policy/protected action chặn.
10. Khi anh yêu cầu chuyển phiên/đổi chat/handoff, trước final phải cập nhật `HANDOVER_CURRENT.md`, tạo archive timestamp cùng nội dung, giữ tối đa 5 archive mới nhất (xóa bản archive cũ nhất khỏi active tree khi có bản thứ 6; không rewrite Git history), readback rồi gửi link canonical.

YÊU CẦU MỚI: NONE
```

Quy tắc dài hạn nằm trong `AGENTS.md`; schema và restore nằm trong `docs/CHAT_HANDOFF_PROTOCOL.md`.

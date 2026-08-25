# CHAT HANDOFF PROTOCOL — PICK PACK 1291

Status: **ACTIVE / mandatory**  
Schema: `pick-pack-handover/v2`

Mục tiêu: mỗi lần OWNER chuyển chat, repo có một snapshot bàn giao đủ để phiên mới tiếp tục ngay; đồng thời giữ tối đa 5 bản archive gần nhất để phục hồi mà không làm phình context.

## 1. Trigger bắt buộc

Áp dụng ngay khi OWNER nói chuyển phiên, đổi chat, sang chat mới, tạo/chốt bàn giao, handoff hoặc kết thúc phiên để làm tiếp ở phiên khác. Đây là lệnh tạo artifact trong repo, không phải chỉ tóm tắt bằng chat.

## 2. Artifact và quy tắc lưu 5 bản

Mỗi lần trigger, AI phải tạo hai file có **cùng nội dung**:

- Canonical: `docs/handovers/HANDOVER_CURRENT.md`.
- Archive: `docs/handovers/HANDOVER_<YYYYMMDD-HHmmss>_<slug>.md`.

Quy tắc retention:

1. `HANDOVER_CURRENT.md` không tính vào giới hạn archive.
2. Sau khi tạo archive mới, liệt kê các file đúng mẫu `HANDOVER_<YYYYMMDD-HHmmss>_<slug>.md`, sắp xếp giảm dần theo timestamp trong tên.
3. Giữ đúng 5 archive mới nhất; nếu có bản thứ 6 thì xóa archive cũ nhất khỏi cây hiện hành trong cùng active branch.
4. Việc xóa archive quá hạn theo mục này đã được OWNER cho phép. Lịch sử Git vẫn là đường phục hồi cho các bản cũ hơn; cấm rewrite history.
5. Không xóa `HANDOVER_CURRENT.md`, evidence release, receipt hoặc tài liệu ngoài nhóm archive chỉ để thực hiện retention.

## 3. Việc phải làm trước khi kết thúc phiên

1. Hoàn thành hoặc dừng tại một điểm atomic an toàn; không để write/deploy mơ hồ.
2. Thu thập trạng thái từ tool output, receipt, commit và evidence đã có; không chạy lại gate PASS chỉ để viết bàn giao.
3. Nếu LIVE thay đổi, cập nhật `CURRENT_STATE.md` trước handoff.
4. Xác định `working_head_sha` là commit cuối chứa thay đổi công việc/cấu hình trước commit handoff.
5. Tạo archive timestamp mới, cập nhật canonical bằng đúng cùng nội dung, rồi áp retention 5 archive.
6. Commit/push vào đúng active branch; không ghi `main` nếu OWNER chưa cho phép.
7. Readback canonical và archive mới; xác minh cùng nội dung, `status: READY`, đủ trường và không có secret.
8. Chỉ final sau khi file đọc được; đưa link canonical và đúng một câu resume.

Nếu remote write thật sự bị chặn, tạo file cùng schema trong workspace và nêu đúng blocker. Không thay bằng một đoạn tóm tắt rời trong chat.

## 4. Cấu trúc bắt buộc

```markdown
---
handover_schema: pick-pack-handover/v2
status: READY
created_at: <ISO-8601 +07:00>
owner: Nguyễn Văn Tâm
project: PICK PACK 1291
active_branch: <branch>
working_head_sha: <SHA trước commit handoff>
archive_file: docs/handovers/HANDOVER_<YYYYMMDD-HHmmss>_<slug>.md
base_or_live_version: <version>
task_state: <IN_PROGRESS|BLOCKED|PASS>
next_action: <một hành động cụ thể, hoặc WAIT_FOR_OWNER_NEW_SCOPE khi PASS>
---

# BÀN GIAO PHIÊN

## 1. Yêu cầu OWNER và Definition of Done
- Mục tiêu đang xử lý, scope được phép, điều cấm và DoD.

## 2. Trạng thái canonical hiện tại
- Phân biệt LIVE/TARGET/CANDIDATE; branch/base/source SHA; architecture/authority; Stable/main/service/signer lock.

## 3. Việc đã hoàn tất
| Hạng mục | Trạng thái | Evidence |
|---|---|---|
- File/commit/run/job/artifact/version/package/SHA256/size/signer/Drive ID khi có.

## 4. Thay đổi trong phiên
- File tạo/sửa/xóa, commit, lý do và thay đổi production/live.

## 5. Lỗi đã gặp và đường PASS
| Fingerprint | Root cause | Cách PASS đã biết | Cách cấm lặp |
|---|---|---|---|

## 6. Trạng thái workspace/CI/external
- Clean/dirty, uncommitted, workflow đang chạy/run cuối, thời điểm fresh-read external.

## 7. Việc còn lại
- Critical path, acceptance gate, blocking và housekeeping.

## 8. NEXT_ACTION — điểm tiếp tục chính xác
- Một tool/command/file/step đầu tiên, expected result và fallback/retry budget.

## 9. Blocker và quyền
- Quyền/MFA/approval còn thiếu và đúng thao tác OWNER cần làm; không chứa secret.

## 10. Invariants không được phá
- Những điều tuyệt đối không đổi/rebuild/retry/promote.

## 11. Resume contract
- Cách phiên mới chọn handoff, phần được tin và điều kiện cần fresh-read.

## 12. Retention/restore
- Archive hiện có, bản bị prune nếu có và cách restore qua Git history.
```

Mục không áp dụng phải ghi `NONE — lý do`, không được xóa. `working_head_sha` không được trỏ vào chính commit tạo handoff vì sẽ tạo tham chiếu vòng.

## 5. Quy tắc tự động cho phiên mới

Áp dụng ở **mọi phiên mới**, kể cả khi OWNER chưa ghi yêu cầu cụ thể:

1. Đọc `docs/handovers/HANDOVER_CURRENT.md` trước.
2. Nếu canonical thiếu, không đọc được, `status != READY`, thiếu `NEXT_ACTION`, hoặc `archive_file` không hợp lệ: liệt kê các archive timestamp, chọn tên có timestamp lớn nhất và dùng bản `status: READY` mới nhất. Không hỏi OWNER chọn file và không crawl repo.
3. Lệnh OWNER mới nhất luôn có ưu tiên cao nhất. Nếu có yêu cầu mới, nạp handoff để lấy trạng thái rồi thực thi yêu cầu mới theo `AGENTS.md`.
4. Nếu không có yêu cầu mới và `task_state: IN_PROGRESS`, tiếp tục ngay từ `NEXT_ACTION` trong đúng scope đã được OWNER cho phép.
5. Nếu không có yêu cầu mới và `task_state: PASS`, hoặc `next_action: WAIT_FOR_OWNER_NEW_SCOPE`, chỉ xác nhận một câu đã nạp snapshot và chờ scope; không tự phát sinh việc.
6. Nếu `task_state: BLOCKED`, nêu đúng blocker và đúng thao tác OWNER đã ghi; không rà soát lại phần PASS.
7. Không mở log/evidence cũ hoặc rerun PASS khi input, source SHA và artifact bytes không đổi. Chỉ fresh-read external state có thể đổi sau `created_at` hoặc ngay trước production write.

## 6. Tiêu chuẩn PASS

Handoff chỉ PASS khi:

- canonical và archive mới cùng nội dung;
- schema v2, `status: READY`, branch, working head, `archive_file` và đúng một `NEXT_ACTION` hợp lệ;
- đầy đủ việc đã làm/còn lại/lỗi/đường PASS/invariants/evidence;
- không chứa secret;
- active tree có không quá 5 archive timestamp;
- phiên mới có thể tiếp tục mà không yêu cầu OWNER kể lại hoặc kiểm tra lại phần đã PASS.

`docs/FIRST_CHAT_PROMPT.md` là prompt khởi động ngắn; file protocol này và `AGENTS.md` là quy tắc vận hành bền vững trong repo.

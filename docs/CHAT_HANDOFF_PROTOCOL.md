# CHAT HANDOFF PROTOCOL — PICK PACK 1291

Status: **ACTIVE / mandatory**  
Schema: `pick-pack-handover/v1`

Mục tiêu: OWNER chuyển sang chat mới và tiếp tục đúng bước còn dở mà không phải kể lại, crawl repo, đọc log cũ hoặc chạy lại gate đã PASS.

## 1. Trigger bắt buộc

Áp dụng ngay khi OWNER dùng một trong các ý sau:

- chuyển phiên, đổi chat, sang chat mới;
- tạo/chốt file bàn giao;
- handoff, bàn giao cho AI/phiên tiếp theo;
- kết thúc phiên này để làm tiếp ở phiên khác.

Đây là yêu cầu tạo artifact, không phải yêu cầu chỉ tóm tắt bằng chat.

## 2. Việc AI phải làm trước khi kết thúc phiên

1. Hoàn thành hoặc dừng tại một điểm atomic an toàn; không bỏ lại write/deploy ở trạng thái không rõ.
2. Thu thập trạng thái từ chính tool output, receipt, commit và evidence đã có; không chạy lại gate PASS chỉ để viết bàn giao.
3. Nếu trạng thái LIVE thay đổi trong phiên, cập nhật `CURRENT_STATE.md`.
4. Tạo hai file có cùng nội dung:
   - canonical: `docs/handovers/HANDOVER_CURRENT.md`;
   - archive: `docs/handovers/HANDOVER_<YYYYMMDD-HHmm>_<slug>.md`.
5. Commit/push hai file vào đúng active branch. Không ghi vào `main` nếu chưa được OWNER cho phép.
6. Tự kiểm tra đủ trường, không có secret và mọi ID/hash đều đến từ evidence.
7. Chỉ final sau khi file đã có link/commit đọc được. Final phải đưa link canonical và đúng một câu resume.

Nếu remote write thật sự bị chặn, tạo cùng file trong workspace, cung cấp link và nêu đúng blocker; không thay bằng một đoạn tóm tắt rời trong chat.

## 3. Nội dung bắt buộc của file bàn giao

File phải dùng đúng cấu trúc sau; không bỏ mục bằng cách ghi chung chung.

```markdown
---
handover_schema: pick-pack-handover/v1
status: READY
created_at: <ISO-8601 +07:00>
owner: Nguyễn Văn Tâm
project: PICK PACK 1291
active_branch: <branch>
head_sha: <current branch SHA>
base_or_live_version: <version>
task_state: <IN_PROGRESS|BLOCKED|PASS>
next_action: <một hành động cụ thể>
---

# BÀN GIAO PHIÊN

## 1. Yêu cầu OWNER và Definition of Done
- Nguyên văn mục tiêu đang xử lý.
- Phạm vi được phép và điều cấm.

## 2. Trạng thái canonical hiện tại
- LIVE/TARGET/CANDIDATE phân biệt rõ.
- Kiến trúc/authority đang áp dụng.
- Branch/base/source SHA hiện hành.
- Stable/main/service/signer lock.

## 3. Việc đã hoàn tất
| Hạng mục | Trạng thái | Evidence |
- File/commit/run/job/artifact/version/package/SHA256/size/signer/Drive ID khi có.
- PASS nào đã khóa và input/bytes tương ứng.

## 4. Thay đổi trong phiên
- File đã tạo/sửa/xóa.
- Commit và lý do kỹ thuật.
- Thay đổi production/live nếu có.

## 5. Lỗi đã gặp và đường PASS
| Fingerprint | Root cause | Cách PASS đã biết | Cách cấm lặp |
- Ghi rõ retry nào không được thử lại.

## 6. Trạng thái workspace/CI/external
- Clean/dirty; uncommitted files.
- Workflow đang chạy hoặc run cuối.
- External state đang chờ, thời điểm fresh-read cuối.

## 7. Việc còn lại
- Danh sách theo thứ tự critical path.
- Acceptance gate cho từng việc.
- Tách blocking và after-release housekeeping.

## 8. NEXT_ACTION — điểm tiếp tục chính xác
- Một tool/command/file/step đầu tiên.
- Expected result.
- Nếu fail: đúng fallback đã biết, giới hạn retry.

## 9. Blocker và quyền
- Thiếu quyền/MFA/approval nào.
- OWNER cần làm gì, nếu có.
- Không ghi secret, token, mật khẩu hoặc signed URL tạm.

## 10. Invariants không được phá
- Những điều tuyệt đối không đổi/rebuild/retry/promote.

## 11. Resume contract
- Phiên mới phải đọc file này trước.
- Không đọc lại lịch sử hoặc rerun PASS khi input/bytes không đổi.
- Tiếp tục trực tiếp từ NEXT_ACTION.
```

Mục không áp dụng phải ghi `NONE — lý do`, không được xóa.

## 4. Quy tắc cho phiên mới

Khi OWNER nói “tiếp tục”, “làm tiếp”, “đã chuyển phiên” hoặc dẫn file bàn giao:

1. Đọc `docs/handovers/HANDOVER_CURRENT.md` trước và coi đây là snapshot continuity canonical.
2. Không crawl repo, không đọc toàn bộ chat cũ, không mở lại log/evidence của mục đã ghi PASS.
3. Tin exact ID/hash/PASS trong bàn giao nếu input, source SHA và artifact bytes không đổi.
4. Bắt đầu ngay từ `NEXT_ACTION`.
5. Chỉ đọc thêm tối đa file domain được bàn giao dẫn trực tiếp khi bước pending cần nó.
6. Chỉ fresh-read phần external có thể đã đổi sau `created_at`, hoặc ngay trước một production write. Fresh-read này không làm mất giá trị của các gate đã PASS.
7. Nếu `HANDOVER_CURRENT.md` thiếu, `status!=READY`, SHA mâu thuẫn hoặc thiếu `NEXT_ACTION`, dừng và sửa handover trước; không tự suy đoán bằng cách crawl toàn repo.

## 5. Tiêu chuẩn chất lượng

Handoff chỉ PASS khi:

- canonical và archive cùng nội dung;
- `status=READY`;
- branch/head SHA/resume point cụ thể;
- mọi công việc đã làm, còn lại, lỗi và cách PASS đều có;
- locked artifact/release identity đầy đủ khi liên quan;
- không chứa secret;
- phiên mới có thể thực hiện bước tiếp theo mà không hỏi OWNER kể lại hoặc kiểm tra lại phần đã PASS.

Tài liệu trạng thái ngoài repo là phụ; file canonical trong repo là nguồn tiếp tục chính.

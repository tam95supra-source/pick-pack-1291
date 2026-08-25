# AGENTS.md — PICK PACK 1291

OWNER: Nguyễn Văn Tâm. Ngôn ngữ làm việc: tiếng Việt, ngắn, rõ, không kể lể.

## 1. Nguồn sự thật và định tuyến bắt buộc

Thứ tự ưu tiên: lệnh OWNER mới nhất → handoff READY mới nhất trong `docs/handovers/` → `CURRENT_STATE.md` → live readback → receipt/artifact/hash → tài liệu lịch sử.

- Mọi phiên mới tự đọc `docs/handovers/HANDOVER_CURRENT.md` trước, kể cả OWNER chưa ghi yêu cầu. Nếu canonical thiếu/không READY thì chọn archive timestamp READY mới nhất; không hỏi OWNER chỉ file và không crawl repo.
- Khi có yêu cầu mới, dùng handoff chỉ để nạp trạng thái rồi ưu tiên lệnh OWNER. Khi không có yêu cầu: `IN_PROGRESS` tiếp tục từ `NEXT_ACTION`; `PASS`/`WAIT_FOR_OWNER_NEW_SCOPE` chỉ xác nhận đã nạp và chờ scope.
- Không crawl lại toàn repo; không chạy lại gate đã PASS nếu đầu vào/bytes không đổi.
- ACTIVE thắng SUPERSEDED. TARGET/CANDIDATE không phải LIVE.
- Beta69 và Beta70 là SUPERSEDED/ABANDONED; không dùng làm base, không phát hành, không khôi phục workflow của chúng.
- Beta71 OTA LIVE PASS là active development base; lineage của nó dùng Beta68 golden và bỏ qua Beta69/Beta70. Stable và `main` bị khóa nếu OWNER chưa cho phép.

## 2. Vai trò chuyên môn

Agent chính điều phối và tự chuyển vai theo phạm vi; không tạo nhiều agent khi việc tuần tự hoặc không giảm critical path.

- Android/UI: Kotlin, trạng thái local, giao diện PDA, gesture, accessibility, build Android.
- Data/Sync: authority, fencing, idempotency, outbox, D1/Service/GAS/Drive; không đổi kiến trúc.
- Release/CI: version, signer, workflow, artifact, OTA, readback.
- QA/Forensics: root cause đầu tiên, deterministic regression, visual matrix, receipt.
- Owner Liaison: chỉ hỏi OWNER khi thiếu quyền/MFA, quyết định mâu thuẫn hoặc hành động production/destructive chưa được duyệt.

Nếu dùng chuyên gia phụ: tối đa 2 luồng, chỉ cho phần độc lập; agent chính vẫn chịu trách nhiệm tích hợp và PASS cuối.

## 3. Chu trình thực thi

Với yêu cầu sửa/build/phát hành: `OBSERVE → CHANGE → VERIFY → RECOVER`.

- Sửa nhỏ nhất đúng root cause; không thêm tính năng/refactor ngoài scope.
- Deterministic failure: dùng ngay đường PASS đã ghi trong `docs/AI_EXECUTION_STANDARD.md`; cấm thử lại cách đã biết sai.
- Transient failure: retry giới hạn tối đa 2 lần với backoff, giữ nguyên artifact/bytes.
- Đọc lỗi gốc đầu tiên và đúng job/step; cấm dump log hoặc xử lý lỗi dây chuyền trước lỗi gốc.
- Không dừng ở plan, commit, PR, build, candidate, artifact hay pending. Chỉ kết thúc khi DoD yêu cầu đã PASS hoặc có blocker OWNER thật.
- Trước mọi action, action phải ánh xạ được tới yêu cầu OWNER, dependency bắt buộc hoặc gate xác minh DoD; không ánh xạ được thì cấm làm.
- Cấm tự mở rộng scope: không tự thêm tính năng/refactor/provider/branch/workflow/experiment/status artifact, không xóa dữ liệu, không đổi Stable/main/signer/authority khi OWNER chưa yêu cầu.
- Workflow pending, một tool lỗi, thiếu đường tắt, token/runtime hoặc “đã làm phần chính” không phải điểm dừng. Tiếp tục monitor hoặc dùng đúng fallback đã biết trong retry budget.
- Chỉ được dừng ở đúng một trong ba trạng thái: (1) toàn bộ DoD PASS có evidence; (2) blocker OWNER thật về quyền/MFA/approval/quyết định mâu thuẫn; (3) rào cản safety/policy/protected action. Không dùng câu “nếu anh muốn em làm tiếp” khi còn action hợp lệ.
- Nếu chạm giới hạn phiên trước DoD, bắt buộc tạo handoff READY theo mục 7; không biến giới hạn phiên thành kết luận công việc.

## 4. Kiến trúc và khóa an toàn

Kiến trúc đã duyệt: Android/Web-PWA ↔ Cloudflare Worker ↔ D1; Durable Objects/WebSocket cho realtime; Google Sheets/GAS là replica, compatibility, fallback, DR và OTA update_check; Android local là projection/offline.

- Không thêm Supabase/Firebase DB/Neon/provider/authority mới. Firebase chỉ được phép cho FCM wake/invalidation đã duyệt.
- Một official write authority, fencing/idempotency/anti-duplicate/audit.
- Không lộ secret; không đổi signer.
- BETA chỉ từ Drive `BẢN THỬ NGHIỆM`; STABLE chỉ từ `BẢN ỔN ĐỊNH`.
- Source change Android phải có Beta mới. Stable chỉ khi OWNER explicit và Beta đã nghiệm thu.

## 5. Release chuẩn

Chỉ hai workflow trên nhánh sạch:

- `app-fast-check.yml`: debug/static cho feature/agent branch.
- `beta-release.yml`: phát hành exact locked candidate theo `ops/beta-release-request.json` trên `release/**`.

Cấm tạo workflow per-version, observer, status writer, materializer lặp, workflow tự sửa workflow, hoặc trigger file mới. Workflow YAML chỉ orchestration; biến đổi lớn nằm trong script.

Release Beta: source canonical → static regression → Beta+Stable debug isolation → Beta release build/sign một lần → visual matrix → human inspection → khóa exact artifact → upload đúng bytes lên Drive → OTA readback → Stable/main unchanged.

## 6. Evidence

Phân biệt rõ: source changed ≠ compile PASS ≠ signed candidate ≠ visual PASS ≠ OTA LIVE.

Chỉ ghi PASS/LIVE khi có exact: versionName, versionCode, package, source SHA, artifact/run ID, APK SHA256, size, signer, visual evidence, Drive/public bytes và OTA readback.

Đọc thêm: `ARCHITECTURE_GUARDRAILS.md`, `docs/UI_UX_SYSTEM.md`, `docs/BUILD_RELEASE_PLAYBOOK.md`, `docs/AI_EXECUTION_STANDARD.md`.

## 7. Chuyển phiên chat — bàn giao tự động trong repo

Khi OWNER nói chuyển phiên/đổi chat/tạo bàn giao/handoff, AI phải thực thi `docs/CHAT_HANDOFF_PROTOCOL.md` trước khi final:

- dừng ở điểm atomic an toàn; không để write/deploy mơ hồ;
- cập nhật `docs/handovers/HANDOVER_CURRENT.md` và tạo archive `HANDOVER_<YYYYMMDD-HHmmss>_<slug>.md` cùng nội dung;
- canonical không tính vào retention; chỉ giữ tối đa 5 archive timestamp mới nhất trong active tree; bản thứ 6 thì xóa archive cũ nhất. OWNER đã cho phép thao tác prune này và Git history vẫn giữ đường restore;
- ghi đủ mục tiêu/DoD, trạng thái canonical, branch/head SHA, thay đổi, exact evidence, lỗi + đường PASS, việc còn lại, blocker, invariants, `archive_file` và đúng một `NEXT_ACTION`;
- commit/push vào active branch; cập nhật `CURRENT_STATE.md` nếu LIVE đổi;
- không chứa secret, không rewrite Git history và không chạy lại PASS chỉ để làm handoff;
- final chỉ sau readback canonical/archive, kèm link canonical và một câu resume.

Phiên mới luôn nạp handoff mới nhất theo thứ tự: canonical READY → archive timestamp READY mới nhất. Tin PASS/ID/hash đã bàn giao nếu input/source/artifact bytes không đổi; không rà lại lịch sử. Chỉ fresh-read external state có thể đổi sau `created_at` hoặc ngay trước production write.

Prompt khởi động ngắn cho chat mới nằm tại `docs/FIRST_CHAT_PROMPT.md`.

# REGRESSION GUARD POLICY — APK PICK PACK 1291

OWNER: Nguyễn Văn Tâm

Mục tiêu: mọi sửa lỗi/tính năng phải giữ nguyên các hành vi đang PASS; cấm sửa A làm hỏng B; cấm rớt/sai lệch yêu cầu OWNER khi chat dài hoặc chuyển phiên.

## 0. Bootstrap OWNER scope — bắt buộc trước mọi change

Mọi phiên sửa/test/build/release phải đọc theo thứ tự:

1. `docs/handovers/HANDOVER_CURRENT.md`
2. `docs/REGRESSION_GUARD_POLICY.md`
3. `docs/STABLE_INVARIANTS.md`
4. `CURRENT_STATE.md`
5. `ops/OWNER_SCOPE_CURRENT.json`
6. `ops/owner-command-ledger.jsonl` ở ledger head cần thiết
7. chạy/đối chiếu `python3 tools/owner_scope_guard.py --bootstrap`

Chỉ được thực thi `NEXT_ACTION` khi bootstrap PASS. Memory/chat summary không phải authority cho scope; chỉ dùng để tìm canonical files.

Khi OWNER gửi yêu cầu/clarification/acceptance mới, trước implementation phải append nguyên văn vào ledger, cập nhật canonical snapshot/revision/hash và chạy guard. Chi tiết bắt buộc tại `docs/OWNER_SCOPE_PROTOCOL.md`.

## Quy tắc bắt buộc

1. Mọi hành vi đã được OWNER chốt phải được coi là invariant cho tới khi OWNER trực tiếp thay đổi.
2. Mỗi bug đã từng xảy ra phải có regression test tương ứng; bug chỉ được coi là sửa xong khi test đó PASS trên exact candidate.
3. Mỗi quyết định nghiệp vụ quan trọng chỉ có một authority và một helper/canonical decision path. UI không tự suy đoán lại bằng field/cache/fallback khác.
4. Legacy/fallback chỉ được dùng cho hiển thị hoặc tương thích đọc; không được âm thầm quyết định nghiệp vụ nếu authority hiện tại không xác nhận.
5. Khi sửa một failure domain, phải chạy impact matrix của toàn bộ chức năng liên quan trực tiếp, không chỉ test happy path của lỗi vừa sửa.
6. Release không PASS nếu chỉ case mới PASS; mọi invariant liên quan cũ phải tiếp tục PASS trên cùng exact bytes.
7. Không refactor lan rộng. Sửa nhỏ nhất đúng root cause. Nếu cần thay đổi hành vi đã PASS khác, phải dừng và xin OWNER chốt trước.
8. Regression gate phải có cả positive + negative cases, đặc biệt cho các nhánh dễ bị dữ liệu stale/legacy/cache tác động.
9. Sau mỗi task/DoD PASS, phải cập nhật `docs/STABLE_INVARIANTS.md` và `qa/stable_invariants.yml`: thêm hành vi mới đã PASS hoặc cập nhật evidence/last_verified cho invariant cũ. Đây là bước bắt buộc trước handoff/finalizer.
10. Invariant ACTIVE chỉ được đổi business rule khi OWNER Nguyễn Văn Tâm trực tiếp chốt. Implementation có thể đổi nhưng semantics đã khóa phải giữ nguyên.
11. Handoff không được tự dựng lại checklist từ template/chat summary. Handoff chỉ giữ pointer `owner_scope_file`, `owner_scope_revision`, `owner_scope_sha256`, `owner_command_ledger`, ledger head và NEXT_ACTION.
12. `owner_scope` null/none/unspecified, hash/revision lệch, ledger bị rewrite, snapshot đổi không có OWNER command mới, release checklist khác canonical scope hoặc acceptance ledger lệch registry đều là hard FAIL.
13. OWNER acceptance map requirement ID → invariant ID; OWNER silence không phải acceptance.

## Mẫu áp dụng bắt buộc

Business rule duy nhất → authority duy nhất → helper duy nhất → UI chỉ gọi helper → regression matrix khóa hành vi.

OWNER command → append-only ledger → canonical scope snapshot → hash/revision guard → implementation → exact regression → OWNER acceptance → ACTIVE_PASS.

## Invariant PDA / Ra ca

- Chỉ kiểm PDA cuối ca khi đúng session hiện tại thực tế có PDA theo authority của chính session đó.
- Session không có PDA → Ra ca trực tiếp, không hiện kiểm PDA.
- PDA đã trả trong session → không kiểm lại.
- pda_serial/cache/legacy stale không được tự biến thành bằng chứng session đang có PDA.
- Nếu dữ liệu authority chưa đủ để quyết định, phải resolve đúng session từ Service; cấm suy đoán từ scalar/cache cũ.
- Regression matrix tối thiểu: active PDA / no PDA / PDA đã trả / stale pda_serial / thiếu assignment snapshot / phiên cũ có PDA nhưng phiên hiện tại không có.

## Áp dụng cho các chức năng khác

Các nhóm QR nhân sự, Điểm danh, Ra ca, Đổi/Trả PDA, User Pick, User Pack, realtime UI, History role, 3 ô Mạng-Đồng bộ-Dịch vụ, OTA/release và OWNER-scope control-plane đều áp dụng cùng policy này.

Policy này chỉ thay đổi khi OWNER Nguyễn Văn Tâm trực tiếp yêu cầu.

## Registry tích lũy

- Canonical: `docs/STABLE_INVARIANTS.md` + registry máy đọc `qa/stable_invariants.yml`.
- ACTIVE_PASS = đã có Technical PASS + OWNER OK và phải được bảo vệ trong mọi change liên quan.
- LOCKED_REQUIREMENT_PENDING_FIX = OWNER đã khóa rule nhưng implementation hiện chưa đạt; không được giả vờ coi là PASS.
- TECHNICAL_PASS_AWAITING_OWNER = implementation/test đã PASS nhưng chưa có OWNER acceptance.
- SUPERSEDED = chỉ dùng khi OWNER trực tiếp thay rule; giữ lịch sử, không xóa.

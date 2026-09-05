# OWNER SCOPE CONTINUITY PROTOCOL — APK PICK PACK 1291

OWNER: Nguyễn Văn Tâm
Status: mandatory control-plane policy

## Mục tiêu

Không phụ thuộc độ dài chat, memory hoặc bản tóm tắt của AI để biết OWNER đã yêu cầu gì. Chat chỉ là nơi OWNER ra lệnh/giải thích/nghiệm thu; repo canonical lưu nguyên bằng chứng và scope hiện hành.

## Canonical sources

1. `ops/owner-command-ledger.jsonl` — append-only ledger từng lệnh/clarification/acceptance của OWNER.
2. `ops/OWNER_SCOPE_CURRENT.json` — snapshot scope hiện hành đã hợp nhất, có revision + SHA256 + mapping requirement → invariant.
3. `docs/handovers/HANDOVER_CURRENT.md` — chỉ trỏ tới scope file/hash/revision/ledger và NEXT_ACTION; không tự chép lại checklist.
4. `CURRENT_STATE.md` — readback trạng thái release + cùng scope pointer/hash/revision.
5. `qa/stable_invariants.yml` + `docs/STABLE_INVARIANTS.md` — semantics đã khóa và trạng thái regression.

## Giao thức nhận lệnh OWNER

Mỗi khi OWNER đưa yêu cầu mới hoặc sửa/làm rõ yêu cầu cũ, trước khi sửa code/service phải hoàn tất transaction control-plane sau:

1. Append nguyên văn message OWNER vào `ops/owner-command-ledger.jsonl`; không sửa/xóa event cũ.
2. Gán `command_id`, sequence tăng đơn điệu, `previous_event_sha256` và `event_sha256` để tạo hash-chain.
3. Cập nhật `ops/OWNER_SCOPE_CURRENT.json`:
   - tăng revision nếu semantics/scope thay đổi;
   - requirement có ID ổn định;
   - giữ acceptance criteria đầy đủ;
   - ghi `source_command_ids`;
   - requirement bị OWNER thay phải chuyển SUPERSEDED, không xóa lịch sử authority.
4. Tính lại `scope_sha256` theo canonical JSON của toàn snapshot, loại riêng trường `scope_sha256`.
5. Cập nhật pointer trong `HANDOVER_CURRENT.md` và `CURRENT_STATE.md`.
6. Chạy `python3 tools/owner_scope_guard.py --bootstrap` và control-plane CI. Chỉ được bắt đầu implementation khi PASS.

Clarification của AI không tự thay scope. Chỉ câu trả lời/lệnh OWNER mới được append thành authority và làm thay đổi snapshot.

## Giao thức phiên chat mới

Mọi phiên mới hoặc phiên tiếp quản phải làm theo thứ tự:

1. Đọc `docs/handovers/HANDOVER_CURRENT.md`.
2. Đọc `docs/REGRESSION_GUARD_POLICY.md`.
3. Đọc `docs/STABLE_INVARIANTS.md` và `qa/stable_invariants.yml` theo impact.
4. Đọc `CURRENT_STATE.md`.
5. Đọc `ops/OWNER_SCOPE_CURRENT.json` và ledger head.
6. Chạy/đối chiếu `tools/owner_scope_guard.py --bootstrap`.
7. Chỉ thực thi `NEXT_ACTION` nếu scope file/hash/revision/ledger đều khớp.

Không được dùng memory/chat summary để thay thế canonical scope. Memory chỉ dùng để tìm file canonical.

## Fail-closed bắt buộc

Guard phải FAIL và dừng mọi change/release/finalizer nếu có một trong các điều kiện:

- `owner_scope` null/none/unspecified/rỗng;
- scope hash không khớp nội dung;
- ledger hash-chain sai, bị sửa/xóa/reorder hoặc sequence giảm;
- snapshot đổi nhưng không có OWNER command mới;
- revision rollback hoặc scope đổi mà revision không tăng;
- handoff/current state trỏ scope hash/revision khác nhau;
- handoff tự chép checklist thay vì reference canonical scope;
- release request đang bind scope hiện hành nhưng checklist thiếu, khác title/acceptance hoặc revision lệch;
- OWNER acceptance COMPLETE nhưng acceptance ledger/receipt/invariant registry chưa ACTIVE_PASS đồng nhất;
- scope requirement mất `source_command_ids` hoặc trỏ command không tồn tại;
- finalizer tạo handoff không có scope file/hash/revision/ledger pointer.

## OWNER acceptance

- Checklist được sinh từ `OWNER_SCOPE_CURRENT.requirements`, không sinh từ template cũ hoặc chat summary.
- OWNER có thể trả `1 OK, 2 chưa OK...`; hệ thống map số → requirement ID → invariant ID.
- Chỉ requirement Technical PASS + OWNER OK mới thành ACTIVE_PASS.
- OWNER silence không phải acceptance.
- Acceptance ledger phải monotonic; trạng thái cũ được giữ làm lịch sử.

## Handoff

`HANDOVER_CURRENT.md` không phải nguồn nội dung yêu cầu. Nó chỉ chứa:

- status READY;
- continuity branch;
- LIVE/candidate evidence cần thiết;
- `owner_scope_file`;
- `owner_scope_id`;
- `owner_scope_revision`;
- `owner_scope_sha256`;
- `owner_command_ledger`;
- `owner_command_ledger_head`;
- NEXT_ACTION.

Khi chuyển chat, prompt có thể ngắn: `Tiếp quản APK PICK PACK 1291 theo HANDOVER_CURRENT; bootstrap canonical OWNER scope và tiếp tục NEXT_ACTION.`

## Release / finalizer

- Release request phải bind scope ID + revision đang dùng.
- Finalizer phải read scope snapshot, verify hash, rồi ghi pointer; cấm hardcode checklist.
- Nếu Android source đổi vẫn tuân release flow hiện hành; policy này không thay đổi Stable/main/signer/authority/provider.
- Control-plane-only change không yêu cầu rebuild APK nếu app/service bytes không đổi.

## Trách nhiệm thao tác

OWNER chỉ cần:

- đưa yêu cầu;
- trả lời clarification thật sự cần thiết;
- nghiệm thu checklist.

ChatGPT/CI chịu trách nhiệm ghi ledger, cập nhật scope snapshot, hash/revision, mapping invariant, handoff, regression guard và readback. OWNER không phải tự kiểm tra xem AI có nhớ thiếu yêu cầu hay không.

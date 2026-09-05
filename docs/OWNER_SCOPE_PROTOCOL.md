# OWNER SCOPE CONTINUITY PROTOCOL — APK PICK PACK 1291

OWNER: Nguyễn Văn Tâm
Status: mandatory control-plane policy

## Mục tiêu

Không phụ thuộc độ dài chat, memory hoặc bản tóm tắt của AI để biết OWNER đã yêu cầu gì. Chat chỉ là nơi OWNER ra lệnh/giải thích/nghiệm thu; repo canonical lưu authority và scope hiện hành.

## Canonical sources

1. `ops/owner-command-ledger.jsonl` — append-only hash-chain của lệnh/clarification/acceptance OWNER.
2. `ops/OWNER_SCOPE_CURRENT.json` — snapshot scope hiện hành, requirement ID ổn định, revision, semantic hash, snapshot hash và mapping requirement → invariant.
3. `docs/handovers/HANDOVER_CURRENT.md` — chỉ trỏ tới canonical scope/hash/revision/ledger và NEXT_ACTION; không tự chép checklist.
4. `CURRENT_STATE.md` — readback release + cùng scope pointers.
5. `qa/stable_invariants.yml` + `docs/STABLE_INVARIANTS.md` — semantics đã khóa và trạng thái regression.
6. `tools/owner_scope_guard.py` — bootstrap/fail-closed guard canonical.
7. `tools/owner_scope_admin.py` — transaction helper cho append OWNER command, rehash/pointer sync và technical state transition.

## Hai hash bắt buộc

- `semantics_sha256`: khóa nội dung OWNER — scope ID, requirement ID/số/title/acceptance/invariant/source commands và governance semantics. Chỉ được đổi khi có OWNER command mới và revision tăng.
- `scope_sha256`: khóa toàn snapshot hiện tại, bao gồm trạng thái/evidence kỹ thuật. Có thể đổi do technical state/evidence nếu `semantics_sha256` giữ nguyên và revision không đổi.

Cơ chế hai hash ngăn hai lỗi đối nghịch: AI không thể âm thầm sửa yêu cầu, nhưng CI vẫn có thể tự chuyển trạng thái kỹ thuật mà không bắt OWNER phải ra một lệnh giả chỉ để cập nhật state.

## Giao thức nhận lệnh OWNER

Mỗi khi OWNER đưa yêu cầu mới hoặc sửa/làm rõ yêu cầu cũ, trước implementation phải hoàn tất một transaction control-plane:

1. Append message OWNER vào `ops/owner-command-ledger.jsonl`; không sửa/xóa/reorder event cũ.
2. Gán `command_id`, sequence tăng đơn điệu, `previous_event_sha256`, `event_sha256`.
3. Cập nhật `ops/OWNER_SCOPE_CURRENT.json`:
   - tăng revision nếu semantics/scope thay đổi;
   - requirement ID giữ ổn định;
   - giữ đầy đủ title/acceptance criteria;
   - ghi `source_command_ids`;
   - rule cũ bị OWNER thay phải SUPERSEDED, không xóa lịch sử.
4. Tính lại `semantics_sha256`, sau đó `scope_sha256`.
5. Đồng bộ pointers vào `HANDOVER_CURRENT.md` và `CURRENT_STATE.md`.
6. Chạy `python3 tools/owner_scope_guard.py --bootstrap` + control-plane CI; chỉ implementation khi PASS.

Clarification do AI đề xuất không tự thay scope. Chỉ câu trả lời/lệnh OWNER mới được thêm vào authority ledger và làm đổi semantic hash.

### Secret / credential / dữ liệu nhạy cảm

Repo canonical là nơi lưu yêu cầu, không phải secret store. Nếu OWNER message chứa secret/password/token/signer/credential hoặc dữ liệu không được phép public:

- không ghi plaintext phần nhạy cảm vào ledger;
- giữ nguyên phần nghiệp vụ;
- thay phần secret bằng marker `[REDACTED_SECRET:<hash-prefix>]` và có thể lưu hash của original text để audit;
- `public_repo_secret_guard.py` luôn có quyền chặn cao hơn;
- secret thật chỉ ở secret store phù hợp.

Việc redact secret không được dùng để rút gọn/làm mất requirement nghiệp vụ.

## Technical state transition

Implementation/CI có thể tự chuyển `LOCKED_REQUIREMENT_PENDING_FIX → TECHNICAL_PASS_AWAITING_OWNER` hoặc cập nhật evidence mà không cần OWNER command mới nếu và chỉ nếu:

- semantic hash không đổi;
- revision không đổi;
- ledger không bị sửa/shrink/reorder;
- snapshot hash và pointers được tính lại;
- regression/technical evidence tương ứng PASS.

`ACTIVE_PASS` vẫn bắt buộc có OWNER explicit OK theo regression policy hiện hành.

## Giao thức phiên chat mới

Mọi phiên mới/tiếp quản phải:

1. đọc `docs/handovers/HANDOVER_CURRENT.md`;
2. đọc `docs/REGRESSION_GUARD_POLICY.md`;
3. đọc `docs/STABLE_INVARIANTS.md` và `qa/stable_invariants.yml` theo impact;
4. đọc `CURRENT_STATE.md`;
5. đọc `ops/OWNER_SCOPE_CURRENT.json` + ledger head;
6. chạy/đối chiếu `python3 tools/owner_scope_guard.py --bootstrap`;
7. chỉ thực thi NEXT_ACTION nếu file/revision/semantic hash/snapshot hash/ledger đều khớp.

Không dùng memory/chat summary để thay canonical scope. Memory chỉ giúp tìm canonical files.

## Fail-closed bắt buộc

Guard phải FAIL trước change/release/finalizer nếu có một trong các điều kiện:

- scope ID null/none/unspecified/rỗng;
- semantic hash hoặc snapshot hash sai;
- ledger hash-chain sai, bị sửa/xóa/reorder/shrink;
- semantic hash đổi nhưng không có OWNER command mới;
- semantic hash đổi mà revision không tăng;
- revision tăng khi semantics không đổi;
- handoff/current state trỏ hash/revision/ledger khác snapshot;
- handoff tự chép checklist thay vì reference canonical scope;
- release request bind sai scope/revision hoặc checklist thiếu/khác title/acceptance;
- OWNER acceptance COMPLETE nhưng receipt/acceptance ledger/invariant registry không đồng nhất ACTIVE_PASS;
- requirement/governance trỏ source command không tồn tại;
- finalizer không verify bootstrap hoặc không ghi canonical pointers.

## OWNER acceptance

- Checklist sinh từ `OWNER_SCOPE_CURRENT.requirements`, không từ template/chat summary.
- OWNER có thể trả `1 OK, 2 chưa OK...`; hệ thống map số → requirement ID → invariant ID.
- Chỉ Technical PASS + OWNER OK mới ACTIVE_PASS.
- OWNER silence không phải acceptance.
- Acceptance ledger monotonic; lịch sử cũ được giữ.

## Handoff

`HANDOVER_CURRENT.md` không phải nguồn nội dung yêu cầu. Nó chỉ chứa status/branch/LIVE evidence cần thiết và các pointer:

- `owner_scope_file`;
- `owner_scope_id`;
- `owner_scope_revision`;
- `owner_scope_semantics_sha256`;
- `owner_scope_sha256`;
- `owner_command_ledger`;
- `owner_command_ledger_head`;
- NEXT_ACTION.

Prompt chuyển chat có thể chỉ là: `Tiếp quản APK PICK PACK 1291 theo HANDOVER_CURRENT; bootstrap canonical OWNER scope và tiếp tục NEXT_ACTION.`

## Release / finalizer

- Release request phải bind canonical scope ID + revision.
- Finalizer phải bootstrap guard, đọc snapshot canonical, ghi pointer/hash; cấm hardcode/copy checklist.
- Android source đổi vẫn theo release flow hiện hành.
- Control-plane-only change không rebuild APK nếu app/service bytes không đổi.
- Stable/main/signer/authority/provider không đổi bởi policy này.

## Trách nhiệm thao tác

OWNER chỉ cần:

- đưa yêu cầu;
- trả lời clarification thật sự cần;
- nghiệm thu checklist.

ChatGPT/CI chịu trách nhiệm ledger, scope snapshot, hashes/revision, requirement↔invariant mapping, handoff, regression guard, release binding và readback. OWNER không phải tự kiểm tra AI có nhớ thiếu hay diễn giải lệch yêu cầu hay không.

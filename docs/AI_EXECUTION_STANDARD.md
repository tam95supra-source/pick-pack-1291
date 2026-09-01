# AI EXECUTION STANDARD — APK PICK PACK 1291

Status: ACTIVE

## 1. Phân loại lỗi

1. Deterministic: cùng input luôn fail → sửa root cause trước khi rerun.
2. Transient: timeout/transport/rate-limit → retry có giới hạn, giữ exact artifact/bytes.
3. Harness: fixture/parser/emulator/workflow sai → sửa harness, không rebuild APK đúng.
4. Authority/permission: fresh-read exact target; chỉ hỏi OWNER khi thiếu quyền/MFA/protected approval.

## 2. Đường PASS chuẩn

### Workflow parse / jobs rỗng
- Sửa YAML/harness gốc.
- Không tạo observer/per-version workflow để né lỗi.

### Compile cascade
- Sửa lỗi compiler/root cause đầu tiên.
- Không chồng patch v2/v3/v4 trên sai baseline.

### Candidate đã khóa
- Không rebuild/re-sign để sửa verifier, visual harness, transport hoặc receipt.
- Mọi verify/publish phải tải lại exact candidate.

### Visual fail nhưng APK đúng
- Sửa fixture/parser/UIAutomator/emulator.
- Giữ candidate bytes.
- Human inspect đủ viewport bắt buộc.

### OTA transport
- APK Beta chỉ GitHub Release exact bytes.
- Retry exact upload/download khi transient.
- Google Drive APK path là legacy/forbidden; không phục hồi.

### OTA schema
- Fresh-read live update contract.
- Tách response update-available và no-update.
- Không rebuild chỉ vì verifier dùng schema cũ.

### Provider/DR
- Fresh-read quota/config trước write.
- Free-only; paid action phải fail closed.
- Restore + checksum/compare mới được gọi backup PASS.
- Cross-environment credential/restore phải reject.

### Beta/Stable
- Header/environment/audience mismatch phải fail closed.
- Không copy Beta mutable state sang Stable.
- Stable public activation chỉ khi OWNER promotion authorization.
- Stable failure rollback Stable riêng.

### Branch authority
- Không dùng `main` để suy ra Beta hiện tại.
- Current Beta authority là `beta/current`.
- Feature/release branch mới phải base từ `beta/current`.
- Không force `beta/current` qua lịch sử diverge; resolve có evidence.
- `main` chỉ đổi trong Stable promotion.

## 3. Ngưỡng dừng

Chỉ dừng khi:
- Technical DoD PASS đang chờ OWNER;
- OWNER acceptance hoàn tất;
- blocker OWNER thật;
- safety/protected action.

Pending/commit/artifact/diagnosis không phải điểm dừng.

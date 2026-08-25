---
handover_schema: pick-pack-handover/v2
status: READY
created_at: 2026-08-25T16:00:52+07:00
owner: Nguyễn Văn Tâm
project: PICK PACK 1291
active_branch: release/beta71-clean-from-beta68-20260825
working_head_sha: 70e1cd27c410a34b28bff58cd94602f3aa206398
archive_file: docs/handovers/HANDOVER_20260825-160052_beta73-visual-retry-cap-blocked.md
base_or_live_version: 0.4.2-beta.72
target_version: 0.4.2-beta.73
task_state: BLOCKED
next_action: OWNER_AUTHORIZE_ONE_ADDITIONAL_VISUAL_ONLY_RETRY
---

# BÀN GIAO — BETA73 EXACT CANDIDATE, VISUAL HARNESS BLOCKED BỞI RETRY CAP

## 1. Mục tiêu + DoD OWNER

Hoàn tất Beta73 cho toàn bộ scope OWNER đã patch, giữ exact candidate, không rebuild/resign. Chỉ PASS khi:

1. Settings human visual PASS tại `320x568`, `360x640`, `480x800`.
2. Publish đúng exact artifact `9552942024` lên Beta.
3. OTA/Drive/LIVE readback khớp URL, SHA256, size, versionName, versionCode, package, signer.
4. Stable/main/signer/authority không đổi.
5. Cập nhật LIVE state/handoff sau release.

OWNER đặt retry cap mới nhất: tối đa **2 visual retry** sau run timeout; không được tạo thêm run khi chưa có quyền vượt cap.

## 2. LIVE / TARGET / CANDIDATE

### LIVE — giữ nguyên Beta72

- Version: `0.4.2-beta.72`
- versionCode: `78`
- Package: `vn.pickpack1291.app.beta.publicbeta`
- Candidate run/artifact cũ: `32808558173` / `9549037310`
- SHA256: `fdeb006122f065591e82fe912a4a615c9c42a149568c2fc32f7d5b35db353caf`
- Stable: `0.1.0-stable`, code `1`, publish FORBIDDEN.
- Main baseline fresh-read trước scope: `a8c0c0d92522c7173230d4175b4f0d3a4906c8bb`.

### TARGET — Beta73

- Version: `0.4.2-beta.73`
- versionCode: `79`
- Chưa LIVE, chưa OTA publish.

### CANDIDATE LOCKED — bất biến

- Build run: `32820317675`
- Artifact: `9552942024`
- Android source SHA trong `release-meta.json`: `2d726828bdd83efe21e9cd41db8d5c06d16f5272`
- Version: `0.4.2-beta.73`
- versionCode: `79`
- Package: `vn.pickpack1291.app.beta.publicbeta`
- SHA256: `ad037c1a17d245f90ead59539c5595cc5df6a568b8657ce636cc43d101175fd2`
- Size: `13130629`
- Signer SHA256: `d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e`
- Stable identity inside candidate metadata: `0.1.0-stable`, code `1`, publish `FORBIDDEN`.
- Service change: `NONE`.
- GAS source flag: `FORGOT_PASSWORD_PREVIEW`.
- Exact candidate ZIP was re-downloaded locally from artifact and `release-meta.json` + APK bytes matched all identity above.

## 3. Visual evidence + root cause

### Run gốc `32823314240`

- Exact artifact download: PASS.
- Exact SHA/size verify: PASS.
- Job: `97725904592`.
- Terminal: `cancelled` do workflow timeout ~60 phút.
- Root cause confirmed từ log: `python3 tools/run_beta73_visual.py` chạy từ `07:49:07Z` tới `08:47:33Z` không thoát.
- `probe_text()` dùng `adb shell am instrument -w ...` không có child timeout.
- Partial visual artifact: `9555794126`, zip digest `4756fdeb6995b135699592e5da520e33d8567da5dd42f820bb49568c2ba66d60`.
- Partial evidence chỉ có 320x568 ảnh `01`–`15`; chưa có ảnh Settings `16/17`. Điều này xác nhận treo tại probe Settings đầu tiên, không phải APK visual fail.

### Retry #1 — `32829005892`

- Exact artifact download + SHA/size: PASS.
- Job: `97743280973`.
- Terminal: `failure`.
- Lỗi gốc đầu tiên: generated materialized harness `SyntaxError` tại Java probe source (`out.putString(...)`).
- Chưa chạy Settings probe; chưa chạm Android source/APK.

### Retry #2 — `32829283026`

- Exact artifact download + SHA/size: PASS.
- Job: `97744121321`.
- Terminal: `failure`.
- Lỗi gốc đầu tiên: generated wrapper `SyntaxError: unexpected character after line continuation character` tại chuỗi preflight 320.
- Chưa chạy Settings probe; chưa chạm Android source/APK.

Hai retry OWNER cho phép đã tiêu hết. Không được trigger retry #3 khi chưa có lệnh OWNER mới.

## 4. Harness hiện tại sau khi dừng run

Chỉ sửa harness, không trigger workflow:

- `tools/run_beta73_visual.py`
- Commit hiện tại: `70e1cd27c410a34b28bff58cd94602f3aa206398`
- Cách sửa: quay về exact harness `ebd95abf772ac4982b94d19c521a9861bc12da51` đã từng compile/chạy, chỉ text-patch:
  - `am instrument -w` qua `subprocess.run(... timeout=15)`.
  - Catch `subprocess.TimeoutExpired`.
  - Ghi `probe-<tag>-timeout.txt`.
  - Fail-fast và force-stop probe phụ.
  - Thêm Settings preflight 320 trước matrix bằng `repr(preflight_code)` để tránh lỗi escape/quote đã gặp.
  - Preflight bắt buộc xác nhận `OperationsActivity`, marker `ĐỔI MẬT KHẨU`, sau cuộn marker `NHẬT KÝ` rồi mới cho matrix tiếp tục.
- Harness mới **chưa được thực thi** vì retry cap đã hết; không được tự tuyên bố PASS.

## 5. File/commit đã đổi trong chặng visual này

- `tools/run_beta73_visual.py`
  - `9357e5b8449a0fffa621a814ac1083450d10cd79`: timeout/preflight attempt #1 — SUPERSEDED vì syntax defect.
  - `996b07d5dfe71432f553a15ca9ae2deaae6b274d`: proven-base wrapper attempt — SUPERSEDED vì preflight escape syntax defect.
  - `70e1cd27c410a34b28bff58cd94602f3aa206398`: current harness fix, chưa chạy.
- `ops/beta-release-request.json`
  - `687985362dfd4ee5459cfc3feabf33857b5cbbac`: trigger retry #1.
  - `ed86884c9a7a296092244eefa14eed0f1b5d38f1`: trigger retry #2.
- Không sửa Android source sau candidate lock.
- Không rebuild/resign/version bump.
- Không publish Stable/main.

## 6. Workspace / CI / external state

- Branch: `release/beta71-clean-from-beta68-20260825`.
- Working head trước handoff: `70e1cd27c410a34b28bff58cd94602f3aa206398`.
- Không có workflow visual đang chạy từ retry budget được phép.
- Beta73 chưa OTA publish; Beta72 vẫn LIVE.
- Stable/main/signer/authority chưa có production write trong chặng visual.
- Worker không deploy; source repo chưa được chứng minh khớp LIVE v64 nên vẫn cấm deploy mù.
- Exact artifact bytes vẫn là `9552942024` / `ad037c1a...5fd2` / `13130629`.

## 7. Blocker OWNER thật

**Blocker:** OWNER đã đặt giới hạn tối đa 2 visual retry và cả 2 đã bị tiêu bởi lỗi harness trước khi Settings probe có thể chạy. Tiếp tục trigger run #3 sẽ trực tiếp vi phạm lệnh OWNER mới nhất.

**Một thao tác OWNER cần làm:** cho phép **đúng 1 visual-only retry bổ sung** bằng exact artifact `9552942024`, dùng harness commit `70e1cd27c410a34b28bff58cd94602f3aa206398`; vẫn cấm build/sign/version bump/Android source.

Sau khi được phép, không sửa `ops/beta-release-request.json` theo cách tạo candidate mới; chỉ trigger visual-only exact artifact, verify SHA/size trước visual, probe 320 trước, rồi 360/480 nếu 320 PASS.

## 8. Việc còn lại sau khi blocker được gỡ

1. Chạy đúng 1 visual-only retry trên exact artifact.
2. Nếu probe 320 fail: dừng ngay tại lỗi probe; không full matrix.
3. Nếu automation PASS: tải evidence và human inspect Settings 320/360/480 + các màn bắt buộc.
4. Khóa human visual receipt.
5. Publish exact candidate `9552942024` lên Beta; không rebuild/resign.
6. Fresh-read OTA/Drive/LIVE + signer/package/version/SHA/size.
7. Xác minh Stable/main/signer/authority unchanged.
8. Cập nhật CURRENT_STATE + handoff PASS.

## 9. Invariants

- Beta73 exact candidate không được thay bytes.
- Không tạo Beta74.
- Không rebuild/resign candidate.
- Harness failure chỉ sửa harness.
- Stable/main/signer/authority/provider không đổi nếu OWNER chưa explicit.
- Worker không deploy mù.
- Không tin automation PASS thay cho human pixel inspection.
- Không publish trước human visual PASS.

## 10. NEXT_ACTION

`OWNER_AUTHORIZE_ONE_ADDITIONAL_VISUAL_ONLY_RETRY`

Resume point sau authorization: trigger đúng visual-only workflow hiện có bằng exact artifact `9552942024`; Settings 320 preflight phải PASS trước khi chạy tiếp 360/480.

## 11. Retention

- Canonical: `docs/handovers/HANDOVER_CURRENT.md`.
- Archive mới: `docs/handovers/HANDOVER_20260825-160052_beta73-visual-retry-cap-blocked.md`.
- Archive timestamp v2 trước đó: `HANDOVER_20260825-104218_handoff-retention-v2.md`, `HANDOVER_20260825-124600_beta72-live-pass.md`.
- `HANDOVER_20260825-1028_beta71-live-context-bootstrap.md` là legacy không đủ HHmmss, không tính retention v2.
- Sau archive mới vẫn <= 5 archive timestamp v2; không prune.

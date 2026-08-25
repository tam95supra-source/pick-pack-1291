# BUILD / RELEASE PLAYBOOK — PICK PACK 1291

Status: **ACTIVE / authoritative**  
Updated: 2026-08-25

Mục tiêu: giảm runtime và số lần thử, nhưng không giảm compile, channel isolation, signer, visual hoặc OTA readback.

## 1. Nguyên tắc cố định

- Nguồn sự thật: lệnh OWNER → `CURRENT_STATE.md` → live readback → receipt/artifact/hash.
- ACTIVE thắng SUPERSEDED; candidate/build PASS không đồng nghĩa LIVE.
- Sửa root cause nhỏ nhất. Lỗi deterministic không retry; lỗi transient tối đa 2 retry có backoff.
- Không rebuild hoặc re-sign sau khi candidate đã khóa.
- BETA chỉ đọc/ghi Drive `BẢN THỬ NGHIỆM`; STABLE chỉ `BẢN ỔN ĐỊNH`.
- Stable, signer, provider, business authority và `main` chỉ đổi khi OWNER yêu cầu rõ.

## 2. Cài đặt áp dụng toàn dự án

| Phạm vi | Cấu hình cố định | Hiệu quả |
|---|---|---|
| AI | `.codex/config.toml`, `AGENTS.md`, `.codex/agents/*.toml` | reasoning/verbosity có giới hạn, tối đa 2 luồng độc lập, tự định tuyến vai |
| Trạng thái | `CURRENT_STATE.md` | đầu task đọc một file thay vì crawl lịch sử |
| Lỗi đã biết | `docs/AI_EXECUTION_STANDARD.md` | fingerprint → đúng đường PASS, cấm retry mù |
| Gradle | `org.gradle.parallel=true`, `org.gradle.caching=true`, heap 3 GiB | cache và song song mặc định, không phải thêm lại mỗi chat |
| CI | chỉ `app-fast-check.yml` và `beta-release.yml` trên nhánh release sạch | không còn bùng nổ workflow lịch sử |
| Release request | `ops/beta-release-request.json` | version/run/artifact/SHA/signer/stage có một nguồn sự thật |

Giữ `org.gradle.configuration-cache=false` cho tới khi một bài test Beta+Stable riêng chứng minh tương thích; không đổi flag này chỉ để thử tốc độ.

## 3. Hai workflow duy nhất

### `app-fast-check.yml`

Dành cho thay đổi Android trên `agent/**`, `feature/**` và pull request:

- static guard;
- `:app:assembleBetaDebug`;
- `:app:assembleStableDebug`;
- Gradle cache + parallel;
- concurrency hủy run cũ cùng ref.

Không sign, không publish, không probe production và không ghi receipt.

### `beta-release.yml`

Dành cho release branch sạch và request file:

- một writer, không observer/status/finalizer;
- candidate/publish được định danh bằng request;
- secrets chỉ tồn tại trong runner;
- upload evidence ở cuối, kể cả khi gate fail;
- không tự sửa workflow;
- logic lớn nằm trong `tools/*`, YAML chỉ orchestration.

Cấm thêm workflow per-version. Khi có Beta mới, cập nhật request và script release đã kiểm chứng trong cùng đường cố định.

## 4. Luồng thay đổi chuẩn

1. Đọc `CURRENT_STATE.md` và đúng failure domain.
2. Tạo thay đổi trên source canonical từ live base đã duyệt.
3. Chạy Fast Check; xử lý lỗi compiler đầu tiên.
4. Materialize source một lần; marker/anchor phải duy nhất.
5. Candidate build/sign đúng một lần.
6. Khóa identity: versionName, versionCode, package, source SHA, run ID, artifact ID, APK SHA-256, size, signer.
7. Visual dùng exact artifact; nếu harness lỗi thì sửa harness, không rebuild.
8. Human inspect 36 ảnh: 320x568, 360x640, 480x800.
9. Publish exact locked bytes; transport retry có giới hạn.
10. Readback APK public và so SHA/size; kiểm tra current-version no-update; so Stable/main trước-sau.
11. Chỉ ghi LIVE/PASS sau receipt cuối.

## 5. Candidate lock

Release metadata tối thiểu:

- `version_name`, `version_code`, `package`;
- `source_sha`;
- `candidate_run_id`, `candidate_artifact_id`;
- `apk_sha256`, `apk_size`;
- signer SHA-256 cố định  
  `d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e`;
- `stable_publish=FORBIDDEN` nếu OWNER chưa cho phép.

Không build/sign lại để sửa verifier, fixture, parser, UIAutomator, Drive transport hoặc response schema.

## 6. OTA contract thực tế

### Máy cũ phát hiện bản mới

`available=true` phải có và khớp:

- `source=GOOGLE_DRIVE`;
- `channel=BETA`;
- target `version_name`;
- `apk_url`;
- exact `sha256`;
- exact `size`.

Sau đó tải bytes thật từ `apk_url` và Drive file ID, so lại SHA-256/size.

### Máy đã ở target

`available=false` phải khớp `source/channel/version_name/size`.

Phản hồi này có thể cố ý không trả `sha256`, `apk_url` và `version_code`. Không ép schema của phản hồi “có cập nhật” sang phản hồi “không cập nhật”.

### Channel isolation

- Stable snapshot trước/sau phải giống nhau.
- Beta target không được xuất hiện trong Stable.
- `main` SHA trước/sau phải giống nhau.

## 7. Đường PASS cho lỗi thường gặp

| Fingerprint | Đường PASS bắt buộc |
|---|---|
| Nhiều workflow cùng fail / jobs rỗng | nhánh sạch, allowlist 2 workflow, validate YAML |
| Workflow mới 404/422 | workflow cố định + request trigger |
| Kotlin anchor/cascade | đúng baseline, marker duy nhất, sửa lỗi đầu tiên |
| Visual fail nhưng APK launch đúng | sửa harness/fixture/parser, giữ exact artifact |
| OTA transport timeout | retry exact bytes tối đa 2 lần; không rebuild/re-sign |
| OTA schema lệch | fresh-read contract live; sửa verifier |
| Missing `gradlew` | `gradle/actions/setup-gradle` + lệnh `gradle` |
| SDK tải lặp | dùng SDK 36/build-tools 36.0.0 có sẵn, pinned fallback khi thiếu |
| Push/receipt race | concurrency một writer; không observer commit |
| Stable/main thay đổi ngoài ý muốn | dừng publish, fresh-read exact target, không tự promote |

Chi tiết đầy đủ: `docs/AI_EXECUTION_STANDARD.md`.

## 8. Baseline hiện tại

- Beta68 là golden base lịch sử dùng để tạo Beta71.
- Beta69 và Beta70 đã bỏ khỏi active lineage.
- Beta71 `0.4.2-beta.71`, code 77, OTA LIVE PASS.
- Receipt: `ops/beta71-release-result.json`.
- Stable và `main` unchanged.

## 9. Điểm dừng hợp lệ

Chỉ dừng khi toàn bộ Definition of Done PASS hoặc có blocker OWNER thật như quyền/MFA/approval chưa thể thay thế. “Đã commit”, “build PASS”, “có artifact”, “đang pending” hoặc “đã chẩn đoán” không phải điểm dừng.

# AI EXECUTION STANDARD — lỗi đã biết và đường PASS

Status: ACTIVE. Mục tiêu: không tiêu tốn runtime vào retry mù hoặc lặp lại cách đã biết sai.

## Phân loại trước khi hành động

1. Deterministic: cùng input luôn lỗi → sửa root cause, thêm regression, không retry.
2. Transient: timeout/transport/rate limit → tối đa 2 retry có backoff, giữ nguyên bytes.
3. Harness: APK đúng nhưng fixture/parser/emulator sai → sửa harness, không rebuild/resign APK.
4. Authority/permission: fresh-read exact target; chỉ hỏi OWNER nếu thật sự thiếu quyền/MFA/approval.

## Fingerprint → root cause → đường PASS

### Workflow run failure và jobs=[]

- Root cause thường gặp: YAML không hợp lệ hoặc workflow cũ hỏng được GitHub parse trên mọi push.
- PASS: xóa workflow lỗi khỏi active branch bằng một Git tree commit; giữ allowlist workflow cố định; validate YAML trước push.
- Cấm: tạo thêm observer/diagnostic/finalizer để quan sát cùng lỗi.

### Hàng loạt workflow failure sau một commit

- Root cause: hàng trăm workflow lịch sử có trigger rộng hoặc YAML hỏng.
- PASS: nhánh release sạch chỉ giữ `app-fast-check.yml` và `beta-release.yml`.
- Cấm: retry từng workflow hoặc thêm marker cho từng bản.

### Workflow mới không dispatch được / 404 / 422

- Root cause: file chưa được GitHub đăng ký hoặc sai ref.
- PASS: dùng workflow cố định và trigger request file; không tạo workflow per release.

### Kotlin patch anchor missing / compile cascade

- Root cause: replacement một dòng phụ thuộc whitespace hoặc patch nối tiếp trên source không đúng baseline.
- PASS: dùng exact Beta68 chain một lần, marker duy nhất, fail ngay anchor đầu; sửa lỗi compiler đầu tiên; materialize source canonical.
- Cấm: sửa lần lượt lỗi cascade hoặc chồng thêm script v2/v3/v4 không hợp nhất.

### Build lại nhiều lần cho cùng release

- Root cause: build, visual, upload tách thành workflow tự rebuild.
- PASS: build/sign candidate đúng một lần; visual và publish tải lại exact artifact theo run/artifact/SHA/size/signer.
- Cấm: rebuild/resign sau candidate lock.

### Visual matrix lỗi nhưng APK launch được

- Root cause đã gặp: shell/parser/UIAutomator/idle animation/fixture.
- PASS: kiểm tra candidate identity trước; sửa harness; dùng exact candidate; human inspect ảnh 320x568, 360x640, 480x800.
- Cấm: đổi APK để làm harness PASS.

### Sai version do hardcode cũ

- PASS: request chứa target; source, APK badging và metadata phải khớp; versionCode tăng đơn điệu. Beta71 = code 77.
- Cấm: lấy tên workflow làm version truth.

### Missing gradlew / SDK download lặp

- PASS: `gradle/actions/setup-gradle` + `gradle`; ưu tiên SDK 36/build-tools 36.0.0 có sẵn, pinned bootstrap chỉ khi thiếu.

### Push race / receipt conflict

- PASS: concurrency một release; không observer commit; receipt cuối không nằm trên critical path; materialization commit chỉ một lần.
- Cấm: nhiều job cùng ghi `ops/*` hoặc pull/rebase vòng lặp.

### OTA transport lỗi

- PASS: giữ exact locked artifact; retry transport giới hạn; xác minh Drive/public SHA; không build/sign lại.
- GAS helper tạm phải nonce-gated, exact folder/SHA/size, và luôn restore source/deployment bằng trap.

### OTA response schema lệch

- PASS: fresh-read live `update_check` và tách hai contract:
  - máy cũ, `available=true`: bắt buộc `source/channel/version_name/apk_url/sha256/size` khớp exact bytes;
  - máy đang ở target, `available=false`: chỉ yêu cầu `source/channel/version_name/size`; feed có thể cố ý bỏ `sha256`, `apk_url` và `version_code`.
- Danh tính APK được khóa bằng candidate metadata + phản hồi `available=true` + SHA của bytes tải thật; không ép trường không tồn tại vào phản hồi no-update.
- Cấm: kết luận APK lỗi, rebuild hoặc re-sign từ verifier schema cũ.

### Stable/main bị động chạm

- PASS: fresh-read trước và sau; Stable snapshot và main SHA phải y nguyên.
- Cấm: promote Stable hoặc merge main khi OWNER chưa explicit.

## Ngưỡng dừng

Chỉ dừng khi PASS toàn DoD hoặc OWNER blocker thật. CI pending, artifact có rồi, đã chẩn đoán, đã commit hay “đang đợi” không phải điểm dừng.

# PROMPT TIẾP QUẢN VÀ HOÀN TẤT TỐI ƯU QUOTA — PICK PACK 1291

Ngày lập: 07/09/2026, giờ Việt Nam. Baseline live chụp lúc **23:52:15 ngày 06/09/2026 (16:52:15 UTC)**.
Mục đích: gửi nguyên file cho phiên ChatGPT có mức suy luận Cao **và có quyền thực thi trên repository/CI/dịch vụ liên quan**. Đây là lệnh làm việc, không phải yêu cầu viết thêm một kế hoạch chung.

## 1. Lệnh thực hiện và kết luận cần giữ

Tôi là OWNER Nguyễn Văn Tâm. Hãy tiếp quản dự án **tam95supra-source/pick-pack-1291**, hoàn tất tối ưu quota/read/write cho **2 web + 3 PDA đồng thời, khoảng 200 NLĐ vào/ra mỗi ngày, 200 công nhật, sử dụng tối đa tài nguyên nghiệp vụ, khoảng 50 đơn rớt/ngày**. Chuẩn bị cả Beta hiện tại và Stable riêng tư READY_NOT_LIVE để sau khi Beta được tôi nghiệm thu, Stable chỉ cần promotion tính năng và chạy các bước kiểm tra tự động, không phải cấu hình hạ tầng thủ công lại.

Không dùng Supabase, không thêm provider, không mua gói, không bật overage/billing, không bỏ audit/idempotency hay giảm realtime để tiết kiệm. D1/Service vẫn là canonical authority; Google là replica/fallback có fencing; Render/Deno/Turso là DR thụ động.

**Kết luận audit hiện tại: tối ưu toàn mô hình CHƯA PASS.** Có code candidate và một số kiểm thử PASS; chưa có evidence đạt đầy đủ tải, quota, UI/realtime và Stable runtime. Không biến “đã có code”, “workflow xanh”, “tính toán dưới quota” thành “đã setup xong”.

Phương án chốt để triển khai: **local-first + mutation ACK mang canonical patch + WebSocket invalidation nhỏ + indexed delta; background chạy theo dirty/due; Google batch qua một cơ chế kiểm soát quota bao phủ các đường gọi; ngân sách cộng toàn tài khoản; Stable riêng tư được provision bằng cấu hình có thể chạy lại an toàn và để yên khi chưa sử dụng.** Triển khai từ mã hiện có, sửa đúng phần thiếu, không viết lại hệ thống.

Trong hai phút đầu, xác định có đọc/sửa repo, chạy CI, xem receipt và truy cập dịch vụ bằng secrets đã cấu hình hay không. Không in token. Mức “Cao” không tự cấp những quyền này. Nếu thiếu quyền thực thi, nói đúng khả năng thiếu và hoàn thành phần có thể làm; không giả báo đang deploy. Không bắt OWNER cấp lại CLOUDFLARE_API_TOKEN khi quyền đọc đã PASS.

## 2. Tiếp quản canonical: thực hiện trước mọi sửa đổi

1. Đọc explicit ref **beta/current**, không dùng default main để suy ra Beta.
2. Đọc AGENTS.md, docs/handovers/HANDOVER_CURRENT.md, CURRENT_STATE.md, docs/REGRESSION_GUARD_POLICY.md, docs/STABLE_INVARIANTS.md và các chỉ dẫn trực tiếp.
3. Chạy:
   ```bash
   python3 tools/owner_scope_guard.py --bootstrap
   ```
4. Đọc ops/OWNER_SCOPE_CURRENT.json sau PASS. Nếu nội dung mới hơn snapshot dưới đây, canonical mới hơn thắng.
5. Lệnh audit hiện tại đã được ghi **CMD-20260906-009-full-quota-audit-handoff.txt**, ledger sequence 9. Không append lại 007/009. Nếu việc OWNER gửi prompt này bổ sung semantics/lệnh triển khai mới, ghi đúng lệnh mới một lần theo docs/OWNER_SCOPE_PROTOCOL.md; không tự sửa hash để vượt guard.
6. Kiểm tra ops/beta-release-request.json và workflows trước chạy: release request cũ còn **revision 6**, còn scope hiện tại là **revision 7**. Một số exact service/stable workflows cũng kiểm cứng rev6. Cập nhật binding theo protocol vào scope thực tế, giữ candidate bytes; không bỏ guard, không chạy lại job cũ như thể nó kiểm scope mới.
7. Làm trên branch hậu duệ của beta/current; sau checkpoint kiểm tra đạt yêu cầu thì fast-forward beta/current, cấm force; main chỉ dùng promotion Stable khi OWNER cho phép riêng.

Snapshot locator đã biết:

| Trường | Giá trị |
|---|---|
| Repository | tam95supra-source/pick-pack-1291 |
| Branch đang làm tại audit | release/beta130-r5-rev6-20260906 — tên branch không biểu thị revision hiện hành |
| Commit chứa mã audit + scope7 | b0519ce240d57510428db52cc295838101250afa |
| Scope ID | OWNER_20260906_R5_QUOTA_REALTIME |
| Revision / số requirement | 7 / 15 |
| Semantics SHA256 | 4fb15aa87623325fa7ffc4e4e37b9a0b9ce95d90fdf502fce366189e53fdf600 |
| Snapshot SHA256 | a15bd89635475b0da7b36876a2a23932cbfebcda6282e705d3f19409c036117d |
| Ledger head | f7399a9b95275ac5ece0c027be137a87aff33c4694aedb105363325c1ea44f3f |
| Requirement 1–12 | ACTIVE_PASS; giữ nguyên semantics |
| Requirement 13,14 | TECHNICAL_PASS_AWAITING_OWNER; không nhận thay OWNER |
| Requirement 15 | LOCKED_REQUIREMENT_PENDING_FIX |
| Lệnh gốc chi tiết | ops/owner-commands/CMD-20260906-007-quota-realtime.md |
| SHA256 lệnh 007 | 6ce22c182785d447bfc1d2684c38a42cb5c060941514873700913fe96eeef31d |

Mã/handoff cuối phiên audit được lưu sau commit b0519...; phải lấy HEAD beta/current mới nhất. Các ID trong file này là locator kiểm tra, không hardcode vào nghiệp vụ.

## 3. LIVE khác candidate như thế nào

| Hạng mục | Trạng thái thực tế / evidence |
|---|---|
| Beta APK công khai gần nhất | 0.4.2-beta.128, versionCode 134, package vn.pickpack1291.app.beta.publicbeta |
| Beta128 source | 5569d1e931436e02d118ed8ab57f2143de43b9f7 |
| Beta128 APK | SHA256 04b135c554c6de6aa979b113a3435cec65063c87e79f232d8c8ea28e1d75f4ce; 14.461.941 bytes |
| Signer giữ nguyên | d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e |
| Beta GitHub Release đọc mới | v0.4.2-beta.128-publicbeta; published 2026-09-05T17:38:47Z; chưa có release Beta130 |
| Beta Worker live | pickpack; version 128f2e49-a27c-4a3d-b04e-d0a4f3ecae9c, 100%; deploy 2026-09-06T15:38:48Z |
| Đối chiếu Service live | Version trên khớp recovery exact Beta128 PASS trong run 34042735653, job 101512294618 |
| Authority read trực tiếp | SERVICE_PRIMARY / PRODUCTION / epoch 9 / seq 3305 / generation m2-prod-reset-20260823-001 |
| Candidate APK chưa public | Beta130, 0.4.2-beta.130, code 136 |
| Candidate build | run 34031376706, artifact 9988766781 |
| Candidate app source / service fence | 99fbdae3c54a8bad42bf102a480dd19378ad1f92 / d5442338e7413d46a8344a3682f7e08276309630 |
| Candidate APK | SHA256 f6011a2088350c7ec0062caf2af0762eedfd14be68f03bdbc41f06a104070287; 14.478.325 bytes; cùng signer |
| Stable Service hiện hữu | pickpack1291-stable-private; version b876eda2-043a-41e3-8d0a-25022f9822b9; deploy 2026-08-31T05:04:40Z |
| Stable trạng thái | READY_NOT_LIVE; không có bằng chứng R5 runtime mới đã deploy |
| Stable package | vn.pickpack1291.app.stable |
| Health audit | URL cấu hình Beta /health trả HTTP403; chưa có health PASS mới qua đúng URL runtime được resolve |
| OTA/install trên 3 PDA | Có receipt Beta128 cũ; audit này không đọc GAS manifest mới hoặc xác nhận bản cài trên từng PDA |

Đừng kết luận outage chỉ từ /health 403: management API và D1 authority vẫn đọc được. Dùng resolver đúng account subdomain, chỉ một endpoint Beta đã xác định, kiểm URL/WAF/authorization; không quét hàng loạt URL hay retry 403 vô hạn.

**Rollback Service không đồng nghĩa rollback schema:** live Beta vẫn có day_revision_state, push_wake_outbox, session_special_projection_outbox, quota_policy, quota_usage. Trước migration phải kiểm tra tương thích các bảng đã tồn tại và checkpoint, không giả định DB trở về nguyên trạng Beta128.

## 4. Số liệu LIVE đã đo: dùng lại, không audit lại toàn bộ

Receipt: **ops/r5-quota-audit-20260906.json** trong repo, cùng file audit chương trình tools/r5_quota_readonly_audit.py.
Run [34046817302](https://github.com/tam95supra-source/pick-pack-1291/actions/runs/34046817302), job 101523222111, artifact 9993346708, digest sha256:7c0d23df801a1957d3611e4d2af34be571ca98a67eeef6eee8aa8ed8537031c1.
Workflow SUCCESS chỉ xác nhận script audit đã chạy xong; receipt vẫn có mục chưa truy cập được.

Chi phí audit: **30 HTTP calls**, D1 truy vấn trực tiếp **212 rows-read / 0 rows-written**, không deploy, không synthetic business mutation. Một health call có thể phát sinh thêm read không nằm trong meta trực tiếp này.

### 4.1. D1 ngày UTC 06/09, tính đến 16:52 UTC

| Phạm vi | Rows-read | Rows-written | % Free read 5M | % Free write 100k |
|---|---:|---:|---:|---:|
| Beta DB | 2.919.334 | 44.309 | 58,39% | 44,31% |
| Stable DB | 28.103 | 99 | 0,56% | 0,10% |
| Các DB ID khác trong analytics | 95.588 | 25.159 | 1,91% | 25,16% |
| **Toàn tài khoản được trả về** | **3.043.025** | **69.567** | **60,86%** | **69,57%** |

Tổng query counters: 79.990 read queries, 15.105 write queries. Analytics có 66 DB IDs cho ngày này nhưng inventory chỉ còn 3 DB. Nhiều ID có thể thuộc DB test đã xóa; đó là **suy luận**, chưa đối chiếu từng run. Phải cộng quota của chúng; xóa DB không hoàn lại quota trong ngày.

Ngày UTC 05/09: tổng 3.657.102 reads / 40.063 writes. Không so phần ngày 06/09 với cả ngày 05/09 rồi tuyên bố phần trăm tối ưu. Analytics có thể trễ/lấy mẫu thích ứng; cần đối chiếu telemetry nếu dùng để nghiệm thu chính xác.

Phản ánh “đã tốn khoảng 70% quota ghi” của OWNER phù hợp snapshot 69,57%. Chưa có bảng attribution để gán toàn bộ lượng dùng này cho AI, CI hay người dùng thật. Audit chỉ rõ các query/harness có evidence, không suy đoán trách nhiệm cho phần còn lại.

| DB đang tồn tại | ID | Dung lượng bytes |
|---|---|---:|
| pick-pack-1291-service-prod | b619df89-528d-4126-a948-de0425037b11 | 4.915.200 |
| pick-pack-1291-service-stable | 47fd0d8d-c96a-435c-85c2-4b12aceedf2c | 643.072 |
| pick-pack-1291-primary | 19a7c8e9-9fc0-4b04-a545-bcbe84b1bcb1 | 372.736 |
| Tổng inventory | 3 DB | 5.931.008 |

Dung lượng hiện tại dưới Free không chứng minh 45 ngày ở tải cực đại vẫn dưới ngưỡng.

### 4.2. Workers và lịch chạy

| Worker | Requests ngày UTC | Subrequests | Errors | Lịch thực tế |
|---|---:|---:|---:|---|
| pickpack | 3.988 | 8.007 | 323 | mỗi phút |
| pickpack1291-stable-private | 1.092 | 402 | 0 | mỗi phút |

Tổng request trong kết quả: 5.080. Subrequest không tự cộng thẳng vào inbound request quota; vẫn chịu giới hạn invocation riêng.
CPU GraphQL trả raw: Beta P50=7626/P99=77994; Stable P50=6574/P99=28698. Chưa xác minh đơn vị và phân loại invocation trong audit; không đổi thành ms hay dùng để PASS giới hạn CPU Free. 323 errors cũng chưa phân loại nguyên nhân hay gắn toàn bộ cho lần thử R5.

Cả hai Workers đang bật observability/log invocation với sampling 100%, lưu logs; redact_query_string=false. Cần kiểm payload/query string, sampling và quota logs. Không log secrets/PII; không xóa log nghiệp vụ/audit bắt buộc để giảm quota.

**Stable chưa public vẫn có cron thật mỗi phút.** READY_NOT_LIVE trong JSON chưa đảm bảo nó không tiêu tài nguyên.

### 4.3. Google và DR

| Tài nguyên | Metadata mới đọc |
|---|---|
| Beta main Sheet | 1E7ZWz-4eMcBliQxDYBVoogIoeSYyiaXGwj0I6mbMm78; 17 tabs; 992.051 allocated cells |
| Beta outbound Sheet | 1tl6har_8vGSVsVlcErfQwjX1YgvN3o-FRG5wQV4VTEM; 2 tabs; 53.196 allocated cells |
| Stable main Sheet | 1Z5tKgGjQxcQqKY-UJO2nOVvM3dA0_VtJx5ayKjWSAy0; 14 tabs; 141.200 allocated cells |
| Stable outbound Sheet | 1Z_TlJ5CdrSb2duUeTPY1rmi0W6vP69c8Ml3QbDkd2Wo; 3 tabs; 9.100 allocated cells |
| Drive storage | limit 16.106.127.360 bytes; usage 1.091.508.759; trash 160.832.910 |
| Beta quota_policy | Sheets DAILY=250; PROJECT_MINUTE=100; READ_MINUTE=30; WRITE_MINUTE=30 |
| Beta quota_usage hiện có | GOOGLE_SHEETS_DAILY used=250/hard_limit=250, cập nhật 2026-09-06T07:24:38.054Z =14:24 VN |
| Render Beta + Stable | pick-pack-1291-dr-beta / pick-pack-1291-dr-stable: plan free, Singapore, suspended, autoDeploy=no |
| Deno | pp1291-dr-beta / pp1291-dr-stable tồn tại; chưa đọc được usage/plan trong kết quả metadata |
| Turso | GET organizations trả403; không có evidence usage/billing mới |

Allocated cells là kích thước lưới đã cấp, không phải số ô chứa dữ liệu. Counter Sheets 250 là **meter của ứng dụng**, không phải tổng Google API usage và không chứng minh mọi đường gọi đều được kiểm soát. Không trộn Sheets API quota với Apps Script Spreadsheet service hay URL Fetch quota.

Chưa xác minh trực tiếp: Google API read/write theo project/user, Apps Script execution/trigger/URL Fetch theo ngày, Drive tốc độ tăng do ảnh/tài liệu, DO duration/storage/request-equivalent, FCM thực gửi, Turso usage/overage, Deno usage/entitlement, Render tổng giờ tháng. Không ghi PASS các mục này vì token tồn tại hay resource tạo xong.

### 4.4. Không phân loại nhầm Cloudflare plan

Token mới đọc được subscriptions và Workers settings: **quyền đọc này PASS**.
Account trả default_usage_model=standard; subscription đọc được là Cloudflare Free Plan, scope=zone, plan_id=free, price=0, state=Paid.

- Zone Free không xác nhận Workers Free.
- state=Paid đi kèm price=0 không chứng minh hóa đơn có tiền.
- default_usage_model=standard là tín hiệu cần đối chiếu; chưa đủ để xác nhận chính xác Workers subscription/entitlement hiện tại.
- Guard cũ dừng BLOCKED_NON_FREE theo model standard. Không tự bỏ guard hoặc tiếp tục deploy bằng giả định. Kiểm tra đúng sản phẩm/entitlement bằng nguồn được cấp quyền; sửa cách phân loại nếu chứng cứ cho thấy guard sai.
- Lệnh gốc §6 yêu cầu dừng triển khai cấu hình khi actual account khác Free. Nếu xác nhận Workers thật sự Paid, tiếp tục làm patch/test cục bộ, hoàn thành phương án cụ thể rồi nêu đúng quyết định OWNER còn thiếu trước deploy. Không tự nâng/hạ plan, không xóa DO namespace, không ghi OWNER đã đồng ý giữ Paid.
- Google tài liệu nói phí vượt quota dự kiến triển khai sau trong năm 2026; không ghi rằng đã bắt đầu tính phí nếu chưa có bằng chứng.

## 5. Top nguyên nhân có số đo và phần candidate còn thiếu

### 5.1. Read amplification thật trên live Beta

| Query / nhóm đường gọi | Lượt query | Rows-read ngày UTC | Hành động |
|---|---:|---:|---|
| events WHERE event_type IN… ORDER BY authority_seq DESC LIMIT… | 658 | 808.569 | Old special projector; dùng terminal outbox/checkpoint, không quét lại recent history |
| Legacy status recent LEFT JOIN events GROUP BY + MAX(source_row) | 51 | 125.388 | Status đọc revision rows bounded |
| SELECT event_id first_event ORDER BY committed_at, event_id LIMIT… | 34 | 83.350 | Truy đúng caller/index; chưa gán chắc cho nghiệp vụ hay harness |
| Status recent LEFT JOIN events GROUP BY | 41 | 80.076 | Loại scan events khỏi status |
| events WHERE actor_role IN… ORDER BY authority_seq DESC LIMIT… | 31 | 76.018 | Truy đúng caller, chuyển incremental/terminal nếu phù hợp |
| Capacity UNION COUNT(*) năm bảng | 18 | 54.378 | Bỏ full count mỗi30 phút; metadata/checkpoint, due6h/ngày |
| resource_daily_consumption theo first_event_id | 246 | 50.676 | EXPLAIN, kiểm index/selectivity; cân write amplification trước thêm index |
| Harness COUNT pending outbound JOIN events theo actor | 39 | 49.296 | Verification cũng đốt reads; thay assertion bounded theo fixture IDs |

Đây là top fingerprints, không phải toàn bộ query. Không cộng lặp lại chúng vào account total. File receipt chứa fingerprint SHA256 và số liệu gốc.

### 5.2. Write amplification thật

| Query | Calls | Rows-written | Ý nghĩa |
|---|---:|---:|---|
| events INSERT dạng1 | 944 | 6.608 | 7 billed writes/lần trong mẫu |
| events INSERT dạng2 | 379 | 2.653 | cũng 7/lần |
| sheet outbox INSERT dạng1 | 1.019 | 4.076 | 4/lần |
| sheet outbox INSERT dạng2 | 545 | 2.180 | cũng 4/lần |
| claimed_at heartbeat của batch INFLIGHT | 505 | 4.592 | Claim/heartbeat gây write phụ trợ lớn |
| batch failure/retry UPDATE | 60 | 2.856 | Retry khuếch đại |
| expired INFLIGHT recovery UPDATE | 993 | 2.624 | Cron/recovery ghi lặp |
| individual outbox claim UPDATE | 1.203 | 2.406 | 2/lần |

Mô hình cũ giả định khoảng9 writes/event không đủ tin cậy: **với đường event + sheet-outbox quan sát, chỉ hai INSERT đã là7 + 4 = 11 writes**, chưa tính authority, projections, revision, lease, ACK, retry. Không áp11 cho mọi event nếu đường đi khác; phải đo theo từng loại nghiệp vụ và index thực của candidate.

Ở2.000 events, giả sử tất cả đi qua đường11 writes thì riêng hai INSERT đã22.000 writes. Đây là phép tính cảnh báo, **không phải số đo candidate**. Target20k không được tự nới. Tính lower bound cần thiết, tối ưu index/outbox lifecycle có chứng minh đúng, rồi đo lại. Nếu không đạt target nhưng còn dưới100k, báo riêng TARGET_FAIL/FREE_LIMIT_PASS và hai lựa chọn cụ thể trước release theo lệnh gốc.

### 5.3. Candidate: phần làm được và phần chưa đủ

| Phần | Source đã kiểm tra | Nhận định chính xác |
|---|---|---|
| Revision + day delta | service/src/sync_contract.ts; legacy_sync_portable.ts; migrations0015–0017 | Có đường bounded revision/indexed delta trong candidate; chưa phải bằng chứng live dùng đường mới |
| Master delta | sync_contract.ts | Chỉ tải namespace đổi revision; một namespace vẫn có thể là SELECT toàn employees/catalog/resources. Không gọi đó là row-level master delta |
| Web | service/public/app.js | Có sửa delta/coalescing/patch; cần trace trình duyệt thật để chứng minh không full refresh, không mất focus/scroll |
| Android | ForegroundSyncCoordinator.kt, M2BackgroundSync.kt, OperationalDataStore.kt, M2Firebase.kt | Có orchestration/delta code; race foreground/WorkManager/FCM và3 PDA chưa được đo đủ |
| Special projector | service/src/session_hotfix.ts, outbox mới | Có terminal outbox candidate; oldscan808.569 reads vẫn thuộc đường live hiện tại |
| FCM | service/src/push.ts | Có wake coalesced; vẫn đọc devices/pending và loop gửi. Phải tính idle/fanout/ACK thật |
| Quota limiter | service/src/quota_budget.ts | Chỉ có4 metric Sheets. Chưa có circuit breaker cho D1/Workers/DO/toàn tài khoản |
| Meter overhead | quota_budget.ts | Reservation theo daily/project-minute/kind-minute có ghi DB; phải tính chính meter vào write budget |
| Scheduler/capacity | service/src/entry_product.ts, d1_maintenance.ts | Capacity full-count vẫn mỗi30 phút; model cron100rows giả định chưa đúng |
| Document audit | document_management.ts | Dirty guard giảm idle replay, nhưng retry đọc tối đa200 audit gần nhất; cần chứng minh backlog lớn hơn200 không bị bỏ sót rồi clear dirty |
| Stable Google path | outbound_beta78.ts, stable_sheet_bridge.ts | get/put/append ở Stable return qua GAS bridge trước limiter direct Sheets. Bridge không gọi quota_budget; chưa đọc đầy đủ GAS để khẳng định toàn đường có limiter tương đương |
| Stable parity | config/stable_r5_parity.json, r5_stable_parity_guard.py | Shared-code/config declarations; không chứng minh Stable đang chạy code/config R5 mới |

Không tự coi cả candidate sai. Giữ patch có giá trị, dùng đúng failure domain để bổ sung.

## 6. Bảng PASS/chưa PASS dùng làm điểm xuất phát

| Hạng mục | Kết luận | Evidence / giới hạn |
|---|---|---|
| Canonical bootstrap/scope7 | PASS kiểm tra quản trị | Control-plane 34046817207 |
| Token đọc Cloudflare | PASS quyền đã thử | Audit mới; không cần xin token lại |
| D1 inventory hiện tại trong Free size/count | PASS tại thời điểm chụp | 3 DB, tổng5.931.008bytes; không bao phủ forecast |
| Beta128 recovery | PASS bản phục hồi đã đối chiếu | run 34042735653 + Worker version mới đọc |
| B115 late-day clock regression | PASS phạm vi hàm/clock | 54 cases tại34044419955/job 101516806011; không phải UI/5 client |
| Guard không dùng adjusted latency làm PASS | PASS kiểm tra harness | tools/r5_measurement_receipt_regression.py 2/2; thiếu telemetry phải fail |
| Beta app Fast Check | PASS build/check đã chạy | 34044419954; checkpoint34045040736; không phải kiểm tải |
| Stable preflight cũ | PASS phạm vi workflow cũ | 34009295654/source 66e8450e45929fbe7b402fc208f50046a09f20ab; compile/schema local, không deploy |
| Render trạng thái cold standby | PASS metadata | Hai services free/suspended/autoDeploy=no; chưa có monthly usage |
| Current-day D1 so Free hard quota | DƯỚI TRẦN tại snapshot | 60,86%read/69,57%write; chưa phải PASS vận hành tải yêu cầu |
| Target500k read/20k write ngày hiện tại | KHÔNG ĐẠT nếu xét tổng ngày | Tổng ngày gồm CI/test/business, chưa tách attribution |
| R5 exact service workflow gần nhất | CHƯA PASS | 34044419955 attempt2 dừng preflight plan, deploy skipped |
| Realtime p95<=1s/p99<=2s | CHƯA PASS candidate hiện tại | Mẫu cũ1637/2679ms tại34038425566/artifact 9991028943; không ngoại suy thành số đo code mới |
| Full2 web + 3 PDA + 200 NLĐ + 200 công nhật + 50 đơn | CHƯA CÓ EVIDENCE | Model1540 cũ thiếu riêng50 đơn; chưa chạy full scenario thật |
| UI local100 ms/no blink/focus/scroll | CHƯA CÓ EVIDENCE R5 đủ | Không dùng benchmark Python gán integer làm UI latency |
| Idle60 phút/retention7&45 ngày | CHƯA CÓ EVIDENCE đầy đủ | Capacity còn full scan, Stable còn cron |
| Account-level circuit breaker | CHƯA HOÀN TẤT | Sheets-only meter; paths/parity còn thiếu |
| Stable setup xong để promotion không làm tay | CHƯA PASS | Có resource riêng nhưng runtime cũ, triggers hoạt động và GAS parity chưa đo |
| Actual plan/usage tất cả provider | CHƯA XÁC MINH ĐỦ | Workers entitlement/DO/Google/GAS/Deno/Turso gaps |
| Technical DoD/OWNER acceptance R5 | CHƯA PASS | R5-15 LOCKED; OWNER 13/14 còn pending |

tools/r5_full_technical_dod.py có static assertions, model1540 và benchmark không phải ứng dụng. Tên output R5_PREPROD_INTEGRATED_PASS hoặc workflow34009689182 xanh **không chứng minh full technical DoD**. Hãy đổi taxonomy/report để static, simulated, measured và OWNER accepted luôn tách biệt.

## 7. Mô hình tải: sửa đúng thiếu sót50 đơn và “max tài nguyên”

Kế thừa200 người/ngày, không hiểu thành200 users online ngoài5 clients. Hai web là hai phiên đồng thời trong scenario; không tự cộng Stable thành client thứ6. Sau promotion phải có thêm scenario Beta và Stable cùng tồn tại, vì quota cùng account không được nhân đôi.

| Nhóm | Mô hình gốc | Số canonical events tham chiếu |
|---|---|---:|
| NLĐ vào/ra | 200×2 | 400 |
| Công nhật bắt đầu/kết thúc | 200×2 | 400 |
| Resource/pack thay đổi | 200×2 theo giả định gốc | 400 |
| Suất ăn/trạng thái khi bật | 200×1 | 200 |
| Subtotal gốc | | 1.400 |
| 50 đơn rớt, chỉ tạo mới | 50×1 | thêm50 |
| Subtotal +10% correction/admin | 1.450×1,1 | 1.595 |
| Stress thêm sửa/xóa đơn nếu nghiệp vụ hỗ trợ | tối đa50×3 thay cho50×1 | 1.705 gồm10% |

Dùng **2.000 canonical events/ngày làm envelope kiểm thử bảo thủ đề xuất**, bao phủ1595/1705 và dư thao tác hỗ trợ; đây là giả định kỹ thuật cần lập manifest từ endpoints thật, không phải lượng dùng đã đo hay nghĩa mặc định của “max”.

Trước code/test, đọc catalog/leases/rules hiện hành để ghi rõ: số tài nguyên thực, loại PDA/pack/bàn, số đổi/người/ngày, thao tác cấp/thu hồi tự động có tạo event riêng hay nằm trong mutation vào/ra, các mutation đơn rớt thực có hỗ trợ. Không nhân đôi event cho cùng mutation, không giả có endpoint edit/delete. Nếu max thực lớn hơn2.000, cập nhật manifest và phép tính tương ứng, không lặng lẽ cắt tải.

Tách mutation mới và transport retry: gửi lại cùng idempotency key phải không tạo event mới nhưng vẫn tính request/read/CPU. Soạn ngày test gồm profile thường, burst60mutations/phút×10phút, cạnh tranh tài nguyên, admin/correction,50 đơn thật; aggregate event count phải khớp manifest.

“Max dữ liệu” còn gồm ảnh/tài liệu/backup: dùng số category/report/ảnh và upload caps thật trong repo, kích thước byte thực của fixtures, retention được phép. Không mặc định mỗi đơn có1 ảnh hoặc dùng row-size bịa để dự báo. Báo công thức bytes/ngày × retention + indexes + backup overlap; dữ liệu không giới hạn theo thời gian không thể được bảo đảm nằm trong một gói Free hữu hạn.

Hai giai đoạn phải có số liệu:
- **Hiện tại:** Beta5 clients hoạt động; Stable private không có business traffic; cộng CI, cron, DR.
- **Sau promotion:** Stable5 clients hoạt động; Beta idle hoặc vẫn test có ngân sách. Nếu cả hai cùng chạy5 clients ở max, tính hai tải cộng vào cùng account, không lấy một Free limit cho mỗi environment.

## 8. Ngân sách, reset và fail-safe

Giới hạn công khai được đối chiếu ngày06/09/2026; actual plan của account phải xác minh riêng. Đây là ngưỡng nghiệm thu, không phải lời đảm bảo đã đạt.

| Dịch vụ | Free tham chiếu | Target/guard giữ từ yêu cầu OWNER |
|---|---|---|
| D1 | 5M reads/ngày,100k writes/ngày; 500 MB/DB,5 GB/account,10 DB; 50 queries/invocation, Time Travel 7 ngày | target500k reads/20k writes; alert1M/40k; fail-safe2,5M/60k; DB nominal<350 MB, alert400 MB, chuẩn bị trước425 MB |
| Workers | 100k requests/ngày/account; 10 ms CPU HTTP invocation Free | target20k requests; alert50k; đo route/invocation CPU, không nhầm elapsed với CPU |
| Durable Objects SQLite | 100k request-equivalent/ngày; 13.000GB-s/ngày; SQLite5M reads/100k writes/ngày,5 GBstorage | target20k request-equivalent; hibernation thực; đo storage/compute riêng, không gộp nhầm với D1 |
| Sheets API | 300read và300write/phút/project; 60mỗi loại/phút/user/project | limiter<=30read/30write user/min, <=100project/min; target250 calls/ngày cho workload; tính mọi path/env cùng quota principal |
| Apps Script consumer | URLFetch20k/ngày; trigger90phút/ngày; 6 phút/execution | target2k URL Fetch/ngày,30 phút trigger/ngày,3 phút/run |
| FCM | default600k messages/phút/project | coalesced wake; actual entitlement/counter riêng |
| Turso Free | 100DB,5 GB,500M read/10M write tháng,3 GB sync/tháng, PITR1 ngày | DR passive, overageoff, giữ safety cap config |
| Deno Deploy Free | 1M request/tháng,20 GiBegress,10 giờ CPU,150 GiB-hr,10 apps,15 builds/giờ | DR passive; normal<=1krequest/tháng, <=1 giờCPU/tháng |
| Render Free | 750 instance-hours/tháng theo workspace; sleep sau15 phútidle | không keepalive, cold standby; không giữ canonical trên ephemeral disk |
| Drive/Sheets storage | actual Drive15 GiB; Sheet có giới hạn riêng | theo dõi bytes/cells thật, ảnh và backup growth; không tự xóa dữ liệu OWNER |

D1/Workers/DO daily Free reset00:00UTC =07:00ViệtNam. Apps Script quota theo user và chu kỳ riêng, không tự giả reset giốngCloudflare. Bảng vận hành phải hiển thị cả UTC window và business date.

Target phải có bảng **Beta + Stable + CI/test + maintenance/DR + headroom = tổng account**; nếu chia token bucket theo environment thì tổng allocation không vượt trần chung. Google chung OAuth/project: hai limiter riêng30+30 có thể dùng hết60read/min/user; cần coordinator quota hoặc phân bổ bảo thủ có dự phòng. Không chia sẻ business data/session giữaenv chỉ để cộng quota.

Circuit breaker:
1. Ưu tiên auth/canonical mutation.
2. Delta/reconcile bounded để giữ realtime.
3. Recovery outbox.
4. Replica/FCM.
5. Report/repair/capacity không khẩn cấp.
Tới alert, hoãn4–5, backoff jitter, không retrystorm. Tới fail-safe, giữ ngân sách cho1–3. Nếu dịch vụ hết hard quota vẫn phải giữ local outbox và hiện trạng thái pending trung thực, không ACK giả. Không hứa “không gián đoạn” khi quota hay mạng thực sự không còn.

D1 meta theo request dùng để tổng hợp có giới hạn; không tạo một write meter cho mọi SQL rồi tự đốt budget. Meter/alerts cần đo overhead và có fail-closed cho tác vụ phụ trợ; provider analytics trễ không đủ làm hard limiter thời gian thực một mình.

## 9. Công việc triển khai cụ thể theo thứ tự

### P0 — chặn việc kiểm thử tiếp tục đốt quota, hoàn thiện bằng chứng quyền/plan

- Dùng receipt hiện có, chỉ fresh-read metrics tối thiểu ngay trước một hành động có thể đổi runtime.
- Snapshot ngày06/09 đã vượt fail-safe60k writes; **không chạy thêm synthetic cloud writes trong window đó**. Reset/ngày mới phải đọc lại, không reset meter để lách.
- Không tạo/xóa nhiều D1 remote để mỗi job “test sạch”. Dùng Miniflare/Wrangler local/SQLite và fixtures có clock kiểm soát.
- Định nghĩa test budget/cost ledger và preflight chặn job trước credentials/mutations.
- Sửa bindings rev6→scope mới theo protocol. Giữ raw latency và missing telemetry fail.
- Xác minh Workers plan đúng sản phẩm; giải quyết health URL bằng read-only hẹp. Turso403 chỉ retry khi input/quyền thực đổi.

### P1 — loại các scan và sync trùng

- Status chỉ đọc tối đa7revision rows và metadata bounded, không LEFTJOIN/GROUPBYevents.
- Mutation atomically cập nhật ledger/projections/revision và trả canonical patch+cursor; origin client không cần gọi status lần nữa.
- Các client khác debounce100–250ms, single-flight delta theo namespace/day/cursor; cursor chỉ advance sau local transaction thành công.
- Bootstrap chỉ cold start/cache invalid/cursor gap; normal invalidation không full snapshot.
- Master namespace snapshot chỉ chấp nhận khi có bound đo được; namespace lớn phải delta/index riêng.
- Web giữ focus/scroll/form/modal/selection; không thay toàn bộ DOM khi không đổi.
- Android foreground/WorkManager/FCM chung watermark/orchestrator; không catch-up sau mọi foreground sync PASS.
- DO dùng Hibernation API thật, không giữ timer/app heartbeat làm nó luôn active. WS hint không có PII/full snapshot. FCM là wake dự phòng, lỗi push không chặn commit.

### P2 — giảm write và Google calls

- Đo event/projection/index/outbox lifecycle theo từng nghiệp vụ, gồm50 đơn. Loại index thật sự dư bằng EXPLAIN+constraints+regression, không bỏ uniqueness/audit/fencing để đạt con số.
- Claim theo batch bounded, giảm heartbeat/ACK/attempt write thừa; expired claims kiểm index/time, retry có due.
- Special correction/delete và document audit cần terminal checkpoint không bỏ backlog; bỏ recent N replay làm nguồn chân lý.
- Google replication batch25–50 hoặc adaptive payload/time, group tab/action; batchGet/batchUpdate, mapping row có checksum; không full-column IDscan mỗi batch.
- Retry timeout-after-write phải idempotent; sửa hàng thủ công có bounded repair.
- Stable GAS bridge phải có giới hạn tương đương cho actual Google operations. Đếm mộtHTTP bridge call không đồng nghĩa mộtSheet call. Bao phủ primary/outbound/DR/document paths, Apps Script triggers và manual admin entrypoints.
- Khi limiter chạm250, không mất outbox, không retry mỗi phút vô hạn; xử lý backlog theo due/budget/lag. Lag<=30 phút ở tải được nghiệm thu phải thật sự đạt, không tự nới lag để đạt quota.

### P3 — cron/retention/storage/quan sát

- Dispatcher mỗi phút được giữ nếu chỉ kiểm due/dirty O(1); idle không scan events/bảngbusiness. Capacity6 giờ/ngày hoặc theo threshold, dùng provider metadata/bounded counters.
- Tách operational/log/audit counters. Hạn chế invocation log sampling phù hợp, redact query string, không log payload/tokens.
- Retention45 ngày chỉ xóa ngày backup VERIFIED bao phủ và không cònopen/active/pending/review. Count/checksum/restore chạy bounded, không full scan lặp trong hot path.
- Forecast đo byte growth trên fixture7 ngày/45 ngày; gồmindex/outbox/tombstone/ảnh/Drivebackup; không làm đầy production để test.
- DR không nhận traffic thường, không keepalive Render/Deno. Verify fencing/backup/restore có kiểm soát, không tự autoactivate.

### P4 — setup Stable sẵn một lần, vẫn riêng tư

Tạo/cập nhật cấu hình và automation dùng chung source, khác bindings; không tạo một bản implementation riêng sẽ lệch Beta.

| Thành phần | Beta | Stable READY_NOT_LIVE cần hoàn thiện |
|---|---|---|
| Worker/DB | pickpack / service-prod | private Worker / service-stable đã có; apply migrations idempotent và đúng generation |
| Secrets/audience | BETA | STABLE riêng; chỉ kiểm tên/tồn tại, không copy credentials nghiệp vụ Beta |
| Google primary/outbound/GAS | Beta resources | resource riêng đã có; quota/bridge/triggers parity thực, mapping rõ |
| Android | publicbeta package | stable flavor/package/signing hợp lệ; không đổi tên APK Beta |
| Web | Beta runtime | privatepreview cùng source; public domain vẫn khóa |
| OTA/manifest | GitHub exactBeta APK | stable channel riêng, public manifest vẫn khóa |
| Local/LAN/FCM | Beta namespace | env/topic/cache/session/LAN tách hoàn toàn |
| Cron/recovery | chạy khi có due | **gỡ/disable lịch active không cần thiết cho private idle**, cấu hình activation lưu sẵn để promotion bật tự động |
| DR | Beta fenced | Stable riêng, suspended/private, không keepalive |
| Promotion | accepted Beta source | command/workflow tự check prerequisites, apply onlydelta, readback, rollback riêngStable |

Scope mới cho phép chuẩn bị Stable riêng tư. Main/public Stable/OTApublic/trafficactivation vẫn cần lệnh promotion riêng. Nếu private Stable có pending/data đang dùng, kiểm tra bounded trước disablecron; không bỏ dữ liệu hay cắt consumer chưa xác minh.

“Không setup lại” nghĩa không phải nhập tay secret IDs, tạo lạiDB/Sheet/DR, sửaURL/flavor/limiter mỗi lần. Vẫn cần buildStable đúngflavor, migration/preflight và smoke tự động theo exact source đã nghiệm thu. Các thay đổi schema tương lai phải qua migration, không thể hứa mọi feature tương lai không có bước nâng cấp.

## 10. Kiểm thử ít tốn quota nhưng có giá trị nghiệm thu

### 10.1. Ngân sách kiểm thử đề xuất

Tạo ops/r5-test-cost-ledger.json hoặc receipt tương đương gồm source/artifact hash, scope, provider, UTC window, budget before, cost actual, retry reason, terminal status.

- Local CI: thực thi toàn bộ ngày2.000 events và7/45 ngàyfixture trước; không cloud seeding.
- Một bounded remote canary khi preflight đủ headroom: khởi điểm tối đa **10.000 rowsread,1.000 rowswrite,300 Worker requests,20 Google calls** cho một đợt, tính cả cleanup và migrations. Đây là ngân sách kỹ thuật đề xuất, không thay targetOWNER; nếu không đủ một gate có ý nghĩa thì chia nhỏ có proof và giải thích trước, không tăng âm thầm.
- Vì hiện đã chạm250 Sheets meter, không dùng lại Google live để diễn tập mà không freshbudget.
- Một lần chạy/commit đã sửa đúng failure domain. Transient retry tối đa1 lần exact bytes trong ngân sách; deterministic fail phải sửa trước retry.
- Không rerun toàn bộPASS khi source/input/artifact không đổi. Không tải APK lại nhiều lần để verifyhash đã có.
- Test remote DB vẫn dùng chung accountquota dù tách DB. Localmock không được gọi “actual Cloudflare billing”.

### 10.2. Gates cần có và cách phân biệt evidence

| Gate | Evidence bắt buộc |
|---|---|
| Status O(1) | actual function+DB fixture0/1540/10000 events; EXPLAIN+bounded reads; không chỉ regex |
| Fullscenario | manifest ít nhất bao phủ200 NLĐ/200 công/50 đơn/max resources,5 clients; state/checksum/event count/outbox khớp |
| Idempotency/offline | duplicate ID, timeout after commit, out-of-order, cursor gap, authority change; không mất/trùng canonical event |
| Realtime | nguồn thao tác→UI client khác p95<=1 s, p99<=2 s, mạng bình thường; ACK→HTTPdelta riêng chỉ là số đo một phần |
| Local UI | p95<=100 ms bằng Android/web instrumentation; giữ focus/scroll/form; không dùng benchmark Python thay UI |
| Concurrency | stale version/resource contention/open labor blocks EXIT; failed resource change giữ lease cũ |
| Single-flight | burst100 hints, foreground/WorkManager/FCM race; số requests bounded, cursor advance atomic |
| Google | actual call counts kể cả GAS, terminal ACK/idempotent timeout/row shift; lag<=30 phút,250 calls target |
| Idle/maintenance | idle60 phút sốread/write rõ; không full scan; retention7/45 ngàyfixture giữbackup/open/pending guards |
| Free | D1/Worker/DO/Google/GAS/DR/storage summed account; tínhretry/index/meter/CI |
| Stable | chínhcode+migrations+configcandidate kiểmprivate Stable; cross-env reject; idlequiet; promotion dry run không tạo lại resource |
| Backup/recovery | checksum/count verified, restore fenced, rollback Service/schema compatible; không rollback nhầm env |

Full-day synthetic local + boundedCloudflare per-route measurement cho ra **forecast đã hiệu chuẩn**, không phải “đã đo một ngày live”. Muốn PASS theo tiêu chí “measured full-day”, cần counter của một ca/ngày vận hành thật hoặc isolated full scenario cloud được cấp đủ ngân sách. Không đốt quota để lấp khoảng trống; ghi đúng pending gate và quan sát tự nhiên bằng telemetry chi phí thấp. Tạo schedule thật nếu công cụ và authorization cho phép; không hứa theo dõi ngầm sau khi chat kết thúc.

Receipt mỗi gate phải ghi source SHA, APK hash nếu dùng, scope hash, fixture/profile, môi trường, timewindow, request/rows/bytes, loại evidence STATIC/LOCAL_RUNTIME/CLOUD_MEASURED/LIVE_SHIFT/OWNER_ACCEPTED. Thiếu dữ liệu => NOT_VERIFIED/FAIL, không fallback sang model để PASS.

## 11. Đường release và trạng thái kết thúc

- Candidate Beta130 APK đã khóa: nếu chỉ sửa Service/harness thì giữ exact APK bytes; không rebuild/resign.
- Nếu cần thay Android source, phải tạo Beta mới theo protocol, version/source/artifact mới rõ ràng; không âm thầm sửa candidate đã khóa.
- Impacted regression, Service convergence, visual/human/PDA functional, release lock rồi mới GitHub Release exact bytes, manifest/OTA, install/open/readback.
- APK transport **GITHUB_RELEASE_ONLY**; cấm Drive APK staging/mirror/rollback.
- Không publish khi R5-15 LOCKED hoặc gates chưa đạt; không tự ghi OWNER acceptance13/14/15.
- Khi oldharness trượt B115 late-day, dùng54 case clock đã có; không nới business future guard.
- Raw elapsed gate phải giữ; không trừ DNS/TCP/TLS để biến1637ms thànhPASS.
- Stable chỉ promotion accepted Beta source với Stable flavor/bindings. Giữpublic Stable/main khóa tới lệnh riêng.

Kết thúc phải giao đủ:
1. Commit/branch canonical, patch list và lý do cụ thể.
2. Bảng PASS/FAIL/NOT_VERIFIED theo tất cả phạm vi ở trên; không ghi “100%PASS” khi cógap.
3. Before/after cùng workload/timewindow; sốabsolute và %Free cộngaccount; labeledactual/forecast.
4. Beta đangLIVEversion nào; candidate gì; đã cài PDA hay chưa; Stable đã provision gì/còn public khóa ở đâu.
5. Một lệnh/workflow promotion Stable đã chạy dryrun với exact accepted source khi đủ điều kiện; không yêu cầu setup tay lại.
6. Cost ledger của chính phiên làm việc.
7. Bàn giao canonical+archive theo docs/CHAT_HANDOFF_PROTOCOL.md; giữ5archive hợp lệ; đúng một NEXT_ACTION nếu còn việc; fast-forward beta/current sau checkpoint PASS.
8. Nếu thực sự bị quyền/billing/OWNER acceptance chặn, nêu **đúng một hành động còn cần** sau khi đã hoàn thành code/test có thể làm. Không kết thúc bằng “anh có muốn em tiếp tục không”.

Đây là công việc triển khai có thể giao cho AI có quyền thực thi. Chỉ lựa chọn mức suy luận Cao không bảo đảm kết quả. Tiêu chuẩn đánh giá là code đã áp dụng, số đo thật, test phù hợp và release/readback đúng, không phải lời hứa.

## 12. Nguồn đối chiếu và đường dẫn thực thi

Nguồn dự án:
- [Canonical handoff](https://github.com/tam95supra-source/pick-pack-1291/blob/beta/current/docs/handovers/HANDOVER_CURRENT.md)
- [Scope canonical](https://github.com/tam95supra-source/pick-pack-1291/blob/beta/current/ops/OWNER_SCOPE_CURRENT.json)
- [Audit receipt](https://github.com/tam95supra-source/pick-pack-1291/blob/beta/current/ops/r5-quota-audit-20260906.json)
- [Audit run](https://github.com/tam95supra-source/pick-pack-1291/actions/runs/34046817302)
- [Service attempt2 bị chặn trước deploy](https://github.com/tam95supra-source/pick-pack-1291/actions/runs/34044419955)
- [Stable preflight cũ](https://github.com/tam95supra-source/pick-pack-1291/actions/runs/34009295654)
- [Beta128 public release](https://github.com/tam95supra-source/pick-pack-1291/releases/tag/v0.4.2-beta.128-publicbeta)

Nguồn chính thức hỗ trợ giới hạn ở mục8; không đồng nghĩa account đã được xác nhận dùng đúng plan:
- [D1 pricing](https://developers.cloudflare.com/d1/platform/pricing/), [D1 limits](https://developers.cloudflare.com/d1/platform/limits/).
- [Workers pricing](https://developers.cloudflare.com/workers/platform/pricing/), [Workers limits](https://developers.cloudflare.com/workers/platform/limits/).
- [Durable Objects pricing](https://developers.cloudflare.com/durable-objects/platform/pricing/).
- [Sheets API limits](https://developers.google.com/workspace/sheets/api/limits), [Apps Script quotas](https://developers.google.com/apps-script/guides/services/quotas).
- [FCM throttling](https://firebase.google.com/docs/cloud-messaging/throttling-and-quotas).
- [Turso pricing](https://turso.tech/pricing), [Deno Deploy pricing](https://deno.com/deploy/pricing), [Render Free](https://render.com/docs/free).
- [ChatGPT Work và công việc có công cụ](https://learn.chatgpt.com/docs/get-started-with-work): khả năng thực thi phụ thuộc công cụ/quyền được kết nối trong phiên, không chỉ tên mức suy luận.

**Hành động đầu tiên của phiên tiếp quản:** đọc beta/current/HANDOVER_CURRENT → bootstrap canonical → mở receipt audit và sửa P0/P1 theo failure đã xác định, không khởi động lại một vòng rà soát toàn dự án.


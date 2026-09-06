# PROMPT TRIỂN KHAI TỐI ƯU QUOTA + REALTIME — PICK & PACK 1291

> Ngày lập: 2026-09-06  
> Mục đích: dán nguyên nội dung file này vào một phiên AI có quyền làm việc với repository để phân tích, triển khai, kiểm thử và bàn giao.  
> Ngôn ngữ làm việc/bàn giao: tiếng Việt.  
> Nguyên tắc: không mua thêm dịch vụ, không bật overage, không đổi nghiệp vụ hiện hành, không hy sinh realtime UI.

---

## 1. Vai trò và mục tiêu bắt buộc

Bạn là kỹ sư chính chịu trách nhiệm tối ưu toàn bộ mô hình đồng bộ của dự án Pick & Pack 1291. Hãy tiếp quản repository theo đúng canonical protocol, đo baseline thực tế, thiết kế và triển khai tối thiểu cần thiết để:

1. Chịu tải tối đa **3 PDA Android + 2 web hoạt động đồng thời**.
2. Xử lý tối đa khoảng **200 nhân sự/ngày**.
3. Mỗi người có tối đa:
   - 1 lượt vào + 1 lượt ra;
   - 1 ca công nhật gồm bắt đầu + kết thúc;
   - 2 lần thao tác/đổi bàn pack/PDA-resource;
   - có thể thêm 1 sự kiện suất ăn/trạng thái tương đương nếu nghiệp vụ bật.
4. Giữ nguyên UI local-first và realtime:
   - thao tác trên thiết bị phát sinh phải phản hồi UI mục tiêu `<= 100 ms`;
   - thiết bị khác nhìn thấy dữ liệu mới mục tiêu `p95 <= 1 giây`, `p99 <= 2 giây` khi mạng bình thường;
   - không trắng màn hình, không nháy, không reset scroll/form, không tải lại toàn trang sau mỗi thay đổi.
5. Giảm tối đa D1 rows-read, rows-written, Worker requests, Google Sheets/API/Apps Script calls và các write phụ trợ.
6. Luôn nằm an toàn trong Free plan hiện hành, có headroom lớn; **không bật billing/overage, không nâng plan, không thêm dịch vụ trả phí**.
7. Giữ nguyên Service/D1 là canonical authority; Google chỉ là replica/fallback/DR; Render + Deno + Turso chỉ là DR thụ động có fencing.

Không chỉ viết kế hoạch chung. Hãy thực hiện theo chu trình **OBSERVE → CHANGE → VERIFY → RECOVER**, đưa ra số liệu trước/sau và chỉ phát hành khi mọi gate PASS.

---

## 2. Yêu cầu tiếp quản canonical trước khi sửa code

Đây là yêu cầu OWNER mới. Trước implementation:

1. Fetch ref `beta/current` mới nhất và làm việc từ ref này; không tin default branch, bản clone cũ hoặc nội dung chat.
2. Đọc đầy đủ `AGENTS.md` và các tài liệu bootstrap/canonical mà file này trỏ tới.
3. Chạy:

   ```bash
   python3 tools/owner_scope_guard.py --bootstrap
   ```

4. Đọc requirement từ `ops/OWNER_SCOPE_CURRENT.json` sau khi bootstrap PASS.
5. Append nguyên văn yêu cầu OWNER vào append-only owner command ledger, cập nhật canonical scope snapshot/revision/hash và chạy guard lại theo `docs/OWNER_SCOPE_PROTOCOL.md` trước khi implementation.
6. Không làm mất hoặc tự động đánh dấu accepted các requirement đang chờ OWNER.
7. Nếu bootstrap/ledger/hash/revision không khớp: dừng, phục hồi canonical evidence và báo blocker; không đoán tiếp từ prompt này.

Snapshot đã quan sát khi lập prompt chỉ dùng làm **locator để đối chiếu**, không phải authority cố định:

- `beta/current` quan sát tại commit `b8907e77f36cf62a41fc7134776a460de357f794`.
- LIVE Beta quan sát: `0.4.2-beta.128`, versionCode `134`.
- LIVE source SHA quan sát: `5569d1e931436e02d118ed8ab57f2143de43b9f7`.
- package quan sát: `vn.pickpack1291.app.beta.publicbeta`.
- authority quan sát: `SERVICE_PRIMARY / PRODUCTION / epoch 9 / generation m2-prod-reset-20260823-001`.
- Current handoff quan sát: READY, scope `OWNER_20260906_R4_LIVE_SYNC_SEED100`, revision 4; R4-13 và R4-14 đang chờ OWNER acceptance.

Nếu canonical mới hơn khác các giá trị trên, canonical mới hơn thắng hoàn toàn.

---

## 3. Kiến trúc và invariant hiện hành phải giữ

Mô hình đã xác nhận:

- Android/PWA ↔ Cloudflare Worker + D1.
- D1 giữ canonical event ledger và projections; mọi mutation chính thức đi qua Service Business Core.
- Durable Object WebSocket chỉ là realtime invalidation/hint, không phải authority.
- Android SQLite và web IndexedDB là projection/cache/outbox local-first.
- Firebase FCM chỉ là background wake, không chứa dữ liệu nghiệp vụ nhạy cảm.
- Google Sheets/GAS là replica, compatibility/fallback có kiểm soát và DR; không phải concurrent writer khi Service primary.
- Render + Deno + Turso là DR thụ động, fenced, không tự động trở thành writer.
- Beta và Stable tách hoàn toàn. Stable hiện READY_NOT_LIVE; không đổi Stable/main/signer/provider/authority nếu OWNER chưa yêu cầu.
- Không đưa Supabase hoặc một provider mới vào kiến trúc.
- Retention D1 45 ngày chỉ được xóa khi backup VERIFIED bao phủ ngày đó và không còn active/open/pending/review cần giữ.

Các invariant/contract hiện hành phải tiếp tục PASS, đặc biệt:

- `UI-REALTIME-100MS-006`
- `ATTENDANCE-LOCAL-FIRST-003`
- `QR-INLINE-SHIFT-NAV-003`
- `LABOR-BULK-REALTIME-007`
- `LOCAL-FIRST-RECONCILE-002`
- `QR-LOCAL-001`
- `UI-PERFORMANCE-COMPACT-005`

Không chuyển business decision xuống UI. UI được optimistic/local-first để nhanh, nhưng Service vẫn xác nhận/reconcile canonical, giữ idempotency, authority epoch/generation, optimistic versioning, resource lease và toàn bộ quy tắc vào/ra/công nhật hiện hành.

---

## 4. Mô hình tải bắt buộc dùng để tính và test

Giải thích giả định “bàn pack 2 lần”: mỗi người phát sinh tối đa 2 mutation resource/pack trong ngày. Nếu OWNER xác nhận ý nghĩa khác, hãy thay đúng tham số và chạy lại toàn bộ mô hình; không âm thầm đổi giả định.

| Nhóm nghiệp vụ | Công thức | Sự kiện/ngày |
|---|---:|---:|
| Vào + ra | 200 × 2 | 400 |
| Công nhật start + finish | 200 × 2 | 400 |
| Đổi/thao tác bàn pack tối đa 2 lần | 200 × 2 | 400 |
| Core subtotal |  | **1.200** |
| Suất ăn/trạng thái tùy chọn | 200 × 1 | 200 |
| Dự phòng correction/retry/admin 10% trên 1.400 | 1.400 × 10% | 140 |
| Kịch bản thiết kế cực đại |  | **1.540 canonical events/ngày** |

Thiết bị/phiên đồng thời: **3 PDA + 2 web = 5 clients**.

Phải test ít nhất:

- tải đều cả ca;
- burst 60 mutations/phút trong 10 phút;
- cả 5 clients cùng mở đúng một business date;
- đổi pack/resource cạnh tranh và stale version;
- mất WebSocket, mất FCM, offline/reconnect, duplicate event ID, out-of-order, timeout sau commit, browser background/foreground;
- một PDA có outbox pending trong khi các client khác tiếp tục hoạt động;
- full 1.540-event synthetic day và retention window 7 ngày/45 ngày.

Không dùng phép tính ước lượng làm evidence cuối. Mọi rows-read/rows-written thật phải lấy từ D1 `meta`, Cloudflare Analytics/GraphQL hoặc dashboard và gắn được vào route/query fingerprint.

---

## 5. Baseline kỹ thuật đã rà soát — phải xác minh lại trên canonical mới nhất

### P0 — các nguồn khuếch đại quota lớn nhất

1. `service/public/app.js`
   - `refresh()` gọi `/v1/sync/status`, sau đó full `/v1/bootstrap`, rồi `refreshEvents()` gọi `/v1/delta` tới 250 bản ghi.
   - Mỗi `DAY_CHANGED`, `MASTER_CHANGED` hoặc `visibilitychange` lại gọi gần như toàn bộ luồng trên và render lại DOM diện rộng.
   - Với 2 web, đây là nguồn rows-read và nháy UI lớn nhất.

2. `service/src/legacy_sync_portable.ts`
   - `m2ClientSyncStatus` tính revision bằng truy vấn recent 7 business dates rồi `LEFT JOIN events ... GROUP BY`.
   - Hot path sync-status vì vậy quét lượng event tăng theo dữ liệu, không phải O(1).

3. `service/src/compat.ts`
   - `compatDay` đọc toàn bộ sessions, labor và events của ngày rồi dựng lại history/reports mỗi khi ngày thay đổi.
   - Đây là full-day snapshot, không phải delta.

4. Android:
   - `app/src/main/java/vn/pickpack1291/app/beta/ForegroundSyncCoordinator.kt`: mỗi `DAY_CHANGED` gọi sync-status rồi full `sync_day`.
   - `app/src/main/java/vn/pickpack1291/app/beta/M2OutboxWorker.kt`: `M2WorkScheduler`/catch-up có thể gọi sync-status/sync-day thêm một lượt sau foreground path.
   - `ExistingWorkPolicy.KEEP` giảm trùng worker nhưng không giải quyết hai orchestration path cùng làm một việc.

5. `service/src/session_hotfix.ts`
   - `flushSessionSpecialProjections` chạy mỗi phút, chọn lại recent correction/delete events và project lại Google.
   - Projector đọc sheet RA/history diện rộng và có thể lặp cùng event mãi; phải chuyển thành durable terminal outbox/checkpoint, không rescan recent history.

### P1 — write/call amplification

6. `service/src/replication.ts`
   - Batch nhỏ (quan sát là 10), lặp đọc metadata/header/full event-ID columns và operational indexes trước/sau mỗi batch.
   - Với 1.200–1.540 events/ngày, số vòng và Google API reads/writes bị khuếch đại, replication lag có thể kéo dài.

7. `service/src/push.ts`
   - Cron gần đây quét events, tạo một `push_outbox` row cho từng event, gửi tới từng Android device, rồi cập nhật trạng thái từng push/device.
   - FCM chỉ cần wake theo revision; không cần durable fan-out theo từng event.

8. `service/src/index.ts` và cron wiring liên quan
   - Mỗi phút chạy nhiều processor/check dù hệ thống idle.
   - Repair/capacity/retention cần chuyển sang due/dirty/checkpoint phù hợp; capacity snapshot không cần quét và ghi mỗi 30 phút khi không có nguy cơ.

9. Baseline mutation write
   - Một business mutation đã có các write canonical bắt buộc: authority state/revision, immutable event, replication outbox, assertion và projection/resource lease liên quan.
   - Cloudflare còn tính write trên index bị tác động. Chỉ bỏ write phụ trợ dư thừa; không phá ledger/audit/idempotency.

### Ước lượng cảnh báo, chưa phải billing evidence

- Với khoảng 1.200 events/ngày, web hiện có thể tạo xấp xỉ `2 × 1.200 × (status scan ~600 + bootstrap ~1.000 + delta 250) ≈ 4,44 triệu` logical rows-read/ngày chỉ riêng hai web.
- Nếu chạy kịch bản 1.540 events, cùng full-refresh pattern có thể vượt 5 triệu rows-read chỉ riêng web; Android full-day reconcile và catch-up trùng làm tổng cao hơn nữa.
- Write hiện có thể nằm cỡ hàng chục nghìn/ngày do projection/index/push/heartbeat/replication; phải đo thật, không chốt từ ước lượng.

---

## 6. Free-plan envelope và ngân sách vận hành bắt buộc

Trước khi thay đổi, đối chiếu lại dashboard/config và tài liệu chính thức. Nếu quota đã đổi hoặc tài khoản thực tế khác Free plan, dừng triển khai cấu hình và báo OWNER.

| Dịch vụ | Free limit tham chiếu 2026-09-06 | Ngân sách vận hành đề xuất |
|---|---|---|
| Cloudflare D1 | 5M rows-read/ngày; 100k rows-written/ngày; 500 MB/DB; 5 GB/account; 10 DB; 7 ngày Time Travel; tối đa 50 query/Worker invocation | mục tiêu `<=500k reads/ngày`, alert 1M, fail-safe 2,5M; mục tiêu `<=20k writes/ngày`, alert 40k, fail-safe 60k; DB nominal `<350 MB`, alert 400 MB, chuẩn bị rollover/cutover trước 425 MB |
| Cloudflare Workers | 100k requests/ngày/account; 10 ms CPU/invocation trên Free | mục tiêu `<=20k requests/ngày`, alert 50k; không poll HTTP; không đưa vòng lặp/scan nặng vào request path |
| Durable Objects | 100k billed requests/ngày; 13.000 GB-s/ngày; có WebSocket Hibernation. Outgoing WS và protocol ping không bị tính request; incoming application messages được quy đổi 20:1 | dùng hibernation; mục tiêu `<=20k request-equivalent/ngày`; WS chỉ gửi revision/hint nhỏ, không gửi snapshot |
| Google Sheets API | 300 read + 300 write/phút/project; 60 read + 60 write/phút/user/project; batch tính một API request; khuyến nghị payload <=2 MB | hard limiter `<=30 read` và `<=30 write/phút/user`; `<=100/phút/project`; mục tiêu `<=250 API calls/ngày` cho replication ở kịch bản này; exponential backoff + jitter |
| Google Apps Script, lấy mức consumer bảo thủ | URL Fetch 20k/ngày; trigger runtime 90 phút/ngày; 6 phút/execution | mục tiêu `<=2k URL Fetch/ngày`, `<=30 phút trigger/ngày`, mỗi run `<=3 phút`; không trigger per event |
| Firebase FCM | HTTP v1 default 600k messages/phút/project | quota FCM không phải nút thắt; mục tiêu bỏ per-event/per-device write amplification, chỉ wake coalesced, payload không nhạy cảm |
| Turso Free | 100 DB; 5 GB storage; 500M rows-read/tháng; 10M rows-written/tháng; 3 GB sync/tháng; 1 ngày PITR | DR passive; normal traffic gần 0; mỗi DR DB giữ dưới safety cap trong `config/provider_free_limits.json`; overage tắt |
| Deno Deploy Free | 1M requests/tháng; 20 GiB egress; 10 giờ active CPU; 150 GiB-hr memory; 10 apps; 15 builds/giờ | DR passive; chỉ health/drill có kiểm soát; mục tiêu <=1.000 requests và <=1 giờ CPU/tháng trong trạng thái bình thường |
| Render Free | 750 instance-hours/tháng; sleep sau 15 phút idle; cold start khoảng 1 phút; filesystem ephemeral | cold standby, không keepalive; local filesystem không giữ authority/data; không kích hoạt tự động |

Lưu ý bắt buộc:

- D1 tính **rows scanned**, không phải chỉ rows trả về; index làm tăng write nhưng thường giảm read mạnh. Quyết định index phải có EXPLAIN + D1 meta trước/sau.
- Free limits D1/Workers reset 00:00 UTC; dashboard vận hành phải hiển thị thêm business timezone để không hiểu sai ngày.
- Google đã thông báo vượt request quota có thể phát sinh charge qua billing account trong 2026. Vì vậy phải dùng application limiter/hard stop dưới quota và xác minh billing/overage không bật.
- Không tạo probe 5 giây vào Worker/D1. Với 5 clients, probe đó riêng đã là 57.600 request/16 giờ hoặc 86.400 request/24 giờ. Dùng native connectivity + RTT của request thật; chỉ edge ping không chạm D1 khi foreground và số đo stale, tối đa 1 lần/60 giây/client.

Nguồn chính thức cần đối chiếu:

- https://developers.cloudflare.com/d1/platform/pricing/
- https://developers.cloudflare.com/d1/platform/limits/
- https://developers.cloudflare.com/workers/platform/limits/
- https://developers.cloudflare.com/workers/platform/pricing/
- https://developers.google.com/workspace/sheets/api/limits
- https://developers.google.com/apps-script/guides/services/quotas
- https://firebase.google.com/docs/cloud-messaging/throttling-and-quotas
- https://turso.tech/pricing
- https://deno.com/deploy/pricing
- https://render.com/docs/free

---

## 7. Kiến trúc đích bắt buộc

### 7.1. Realtime = local optimistic + invalidation + indexed delta

Luồng chuẩn:

1. Người dùng thao tác.
2. Client ghi local outbox/idempotency envelope và cập nhật projection/UI ngay; không chờ mạng.
3. Mutation gửi Service; Service commit canonical atomically.
4. Mutation response trả ngay canonical entity patch/snapshot + `business_date revision` + cursor/authority envelope để client phát sinh không phải gọi thêm sync-status.
5. Service phát WebSocket hint rất nhỏ: environment, namespace/business date, latest revision/cursor; không chứa full snapshot.
6. Các client khác coalesce hint 100–250 ms, single-flight một delta pull từ cursor hiện có.
7. Client apply canonical patches atomically vào SQLite/IndexedDB, rồi mới advance cursor; UI chỉ patch đúng row/card/count bị đổi.
8. Nếu WS mất, reconnect gửi cursor và lấy delta. FCM chỉ đánh thức Android background. Nếu cursor nằm ngoài retention/gap/schema mismatch thì server trả `RESET_REQUIRED`; lúc đó mới tải targeted day/master snapshot hoặc full bootstrap.

Yêu cầu an toàn:

- Invalidation có thể mất/trùng/out-of-order mà dữ liệu vẫn hội tụ đúng nhờ cursor/revision/idempotency.
- Không advance cursor trước khi local transaction thành công.
- Optimistic event đã ACK vẫn overlay cho tới khi canonical patch/snapshot tương ứng được lưu, tránh UI lùi trạng thái.
- Server trả canonical patch; client không tái triển khai quy tắc nghiệp vụ khác với Business Core.
- Delta phân trang có giới hạn, ví dụ 100–250 events/page; giữ single-flight và backpressure.
- Master data dùng namespace revision riêng; chỉ tải namespace thay đổi, không bootstrap toàn bộ.

### 7.2. Revision/status phải O(1)

Tạo/hoàn thiện một projection nhỏ kiểu `day_revision_state`/`sync_revision_state`, được update trong cùng canonical mutation transaction, có khóa/index đúng theo environment + authority epoch/generation + business_date/namespace.

- Sync-status chỉ đọc tối đa 7 revision rows + retention floor/checkpoint rows, không join/group/scan bảng `events`.
- Không chạy `GROUP BY events` trên hot path.
- Backfill/migration phải có checkpoint, bounded batch, rollback và verify checksum/count.
- Revision monotonic, fenced bởi environment/epoch/generation, không tạo split-brain.

### 7.3. Web

- Cold start: render cache IndexedDB ngay; chỉ bootstrap một lần nếu cache/cursor thiếu hoặc invalid.
- `DAY_CHANGED`: delta của đúng ngày/cursor, không gọi full `refresh()`/bootstrap.
- `MASTER_CHANGED`: chỉ fetch master namespace đã đổi.
- `visibilitychange`: nếu cursor stale thì delta reconcile; không full refresh mặc định.
- Không replace toàn bộ `innerHTML` nếu dữ liệu không đổi; dùng keyed/targeted patches.
- Giữ scroll, focus, selection, form draft, modal và optimistic state.
- Chặn concurrent refresh bằng single-flight; gộp burst 100–250 ms; cancel/ignore stale response.

### 7.4. Android

- Có đúng một sync orchestrator cho foreground/catch-up theo environment + business date.
- Foreground WS path và WorkManager không cùng gọi sync-status/sync-day cho một revision.
- WorkManager chỉ chạy khi: network vừa phục hồi, FCM background wake, outbox thật sự pending, cursor gap hoặc scheduled bounded recovery.
- Không schedule catch-up sau mọi foreground sync thành công.
- `ExistingWorkPolicy.KEEP` vẫn giữ nhưng phải thêm single-flight/revision watermark để chặn duplicate logical work.
- Hai WS day/master có thể giữ nếu cần; WebSocket protocol ping 20 giây không phải D1 read và không tự coi là lỗi quota. Dùng DO Hibernation, tránh application heartbeat/payload dư thừa.

### 7.5. FCM wake coalescing

- Không tạo một durable `push_outbox` row cho mỗi canonical event.
- Dựa vào latest day revision + last-sent revision/watermark; debounce/collapse theo environment + business date.
- Nếu bảo mật và environment fencing cho phép, dùng topic/collapse key để không loop từng thiết bị; payload chỉ có wake/revision, không PII/business detail.
- Foreground client ưu tiên WebSocket, không cần FCM để giữ realtime.
- Không update `push_devices` success sau mỗi send; chỉ cập nhật aggregate health/last success khi thật sự hữu ích.
- Retry bounded + exponential backoff; lỗi push không chặn canonical mutation.

### 7.6. Google replication

- Durable outbox với terminal state/checkpoint rõ ràng; không rescan “recent N events” mỗi phút.
- Batch 25–50 events hoặc adaptive theo payload/time; group theo sheet/tab/action.
- Mỗi cycle chỉ một bounded idempotency/index read cần thiết và vài `batchGet`/`batchUpdate`; không đọc full event-ID/full operational columns trước và sau từng batch.
- Lưu/checksum mapping row/index đủ để update; có bounded repair khi manual sheet edit làm mapping lệch.
- Timeout-after-write phải retry idempotent, không tạo duplicate.
- Replication lag mục tiêu `<=30 phút`; Google hỏng không chặn D1 canonical path.
- `session_hotfix` correction/delete phải có outbox riêng hoặc dùng chung outbox có type, ACK terminal và poison/review state; tuyệt đối không project lại cùng event vô hạn.

### 7.7. Cron/maintenance theo dirty + due

- Một dispatcher phút chỉ đọc O(1) due/dirty/checkpoint và pending-outbox index.
- Chỉ chạy processor khi thực sự có việc.
- Repair 30 phút chỉ chạy khi dirty/inconsistent hoặc đến bounded schedule.
- Capacity snapshot chuyển 6 giờ/lần hoặc hằng ngày, và chạy sớm khi gần threshold; không full-scan/ghi mỗi 30 phút khi idle.
- Retention hằng ngày; giữ toàn bộ VERIFIED-backup/open/pending guards.
- Bất kỳ maintenance failure nào cũng không được chặn enter/exit/labor/resource canonical mutations.

### 7.8. Quota circuit breaker

Tạo quan sát và policy theo ưu tiên:

1. canonical mutation + auth;
2. indexed delta/realtime reconcile;
3. outbox recovery;
4. Google replication/push;
5. report/repair/capacity/maintenance không cấp thiết.

Khi chạm alert budget, trì hoãn/coalesce các mục 4–5 trước; không làm mất dữ liệu. Khi tiến gần fail-safe, tắt job không thiết yếu, giữ headroom cho mutation và delta. Không tự bật paid/overage. Cảnh báo không được tự tạo thêm scan D1 lớn.

---

## 8. Thứ tự triển khai để giảm rủi ro

### Phase 0 — Observe/canonical

- Hoàn tất owner ledger/scope guard.
- Lấy 7 ngày Cloudflare metrics hiện có theo DB/route/time; tách Beta/Stable.
- Instrument D1 `meta.rows_read`, `rows_written`, duration, route name, normalized query fingerprint và sample rate hợp lý; không log PII/payload/secret.
- Ghi baseline Worker requests, DO/WebSocket connections/messages, FCM sends, Sheets calls, Apps Script execution time, replication lag, outbox depth, D1 size.
- Reproduce 5-client scenario hiện tại trong test/staging; không bắn synthetic load vào production.

### Phase 1 — P0 read reduction

- O(1) revision state/status.
- Web delta-only after invalidation + targeted DOM patch.
- Android one-orchestrator/single-flight; bỏ duplicate sync-day.
- Mutation response mang canonical patch + revision.

### Phase 2 — P0/P1 background amplification

- Terminal special projection outbox.
- Google batch/index/checkpoint optimization.
- FCM watermark/coalescing.
- Dirty/due cron dispatcher.

### Phase 3 — Guardrail + recovery

- Quota dashboard/alerts/circuit breaker.
- Bounded bootstrap/reset path, migration rollback, replay and backup verify.
- Retention/capacity schedule tối ưu nhưng giữ safety contract.

### Phase 4 — Verify + release

- CI/static/contract/load/failure tests.
- Beta staged rollout/canary; quan sát một ca thật; rollback nếu gate fail.
- Nếu Android source thay đổi, bắt buộc theo toàn bộ Beta release flow, exact APK bytes, signer/package/version/OTA/install-open-readback và canonical finalizer/handoff. Không phát hành Stable.

---

## 9. Definition of Done — mọi mục phải có evidence

### Correctness và realtime

- Tất cả canonical invariants/regression suite hiện hành PASS.
- 1.540-event day, 3 PDA + 2 web: không mất/trùng/sai thứ tự cuối cùng; eventual state giống canonical.
- UI local response `p95 <=100 ms` cho hành động được optimistic hỗ trợ.
- Remote convergence mạng bình thường `p95 <=1 giây`, `p99 <=2 giây`.
- Không blink/blank/full-page reload, không reset scroll/focus/form.
- Resource contention, OPEN labor blocks EXIT, failed resource change retains previous, idempotent replay và authority fencing đều PASS.

### Read/write/request

- Sync-status đọc bounded rows độc lập với 0/1.540/10.000 events; không có events scan/group trên hot path.
- Sau cold start, một WS invalidation không được gọi full bootstrap/full sync-day trong normal path.
- Full bootstrap normal-shift `<=1/client`; mục tiêu 0 sau khi cache đã warm.
- D1 measured total cho full test day:
  - target `<=500.000 rows-read/ngày`;
  - target `<=20.000 rows-written/ngày`;
  - tuyệt đối không vượt fail-safe budget đã nêu.
- Workers requests `<=20.000/ngày` trong mô hình test; không có HTTP/D1 poll 5 giây.
- Báo cáo cả số tuyệt đối, per business event, per client và mức giảm % so với baseline.

### Background/replication

- Không event nào trong `session_hotfix`/special projector bị project lại sau terminal ACK trừ repair có evidence.
- Google replication lag `<=30 phút`; Sheets limiter dưới 30 read/write/phút/user và target <=250 API calls/ngày cho test day.
- FCM chỉ wake coalesced; không per-event × per-device durable amplification; push outage không làm mutation fail.
- Idle 60 phút: chỉ có số query/write tối thiểu đã liệt kê rõ; không có full scans định kỳ.
- Render/Deno/Turso không nhận normal production traffic khi SERVICE_PRIMARY khỏe.

### Storage/recovery/security

- D1 size đo thực, retention 45 ngày có forecast và threshold; không ước lượng giả kích thước row.
- Backup/restore/replay checksum/count PASS; retention không xóa active/open/pending/unverified data.
- Beta/Stable/environment/epoch/generation isolation PASS.
- Không secret/PII trong log, WS hint hoặc FCM payload.
- Không bật billing, paid plan, overage, quota increase hoặc provider mới.

### Evidence package

Tạo một bảng before/after tối thiểu gồm:

- route/query fingerprint;
- call count;
- D1 rows-read/rows-written;
- Worker/DO request-equivalent;
- response p50/p95/p99;
- bytes transferred;
- UI local latency và remote convergence;
- Sheets read/write calls, Apps Script runtime;
- replication lag/outbox depth;
- D1 size/forecast;
- test/run/artifact IDs và exact commit/build hashes.

Không ghi “PASS” nếu chưa có receipt/log/metric reproducible.

---

## 10. Test/guard bắt buộc bổ sung

1. Static guard cấm `events JOIN/GROUP BY` trong sync-status hot path.
2. Contract test chứng minh status rows-read là hằng số khi event table tăng.
3. Contract test chứng minh `DAY_CHANGED` trên web/Android chỉ kéo delta và không gọi bootstrap/sync-day normal path.
4. Single-flight test cho burst 100 hints: số delta requests bounded, không concurrent overwrite cursor.
5. Cursor loss/out-of-retention test: chỉ targeted reset/bootstrap một lần, sau đó trở lại delta.
6. Mutation-timeout-after-commit và duplicate ID test: đúng một canonical event/projection.
7. Offline outbox + reconnect + stale authority test.
8. Five-client convergence/load test cho 1.540 events và burst profile.
9. Web visual/runtime test giữ focus/scroll/form, không nháy.
10. Android WorkManager + foreground + FCM race test, chứng minh không duplicate logical sync.
11. Google retry/timeout/manual-row-shift/idempotency test.
12. Quota circuit-breaker test: maintenance bị hoãn nhưng mutation/delta vẫn hoạt động.
13. Retention + VERIFIED backup + active/open/pending guard test.
14. Beta/Stable cross-environment rejection và DR fencing test.

---

## 11. Những điều cấm

- Không polling toàn hệ thống 5 giây hoặc refresh theo timer dày.
- Không dùng full bootstrap/full-day snapshot cho mỗi realtime event.
- Không biến WebSocket/FCM thành nguồn dữ liệu canonical.
- Không cho UI tự suy ra business authority khác Service.
- Không bỏ immutable event/audit/idempotency/resource lease để tiết kiệm write.
- Không xóa dữ liệu/retention sớm khi backup chưa VERIFIED.
- Không auto-activate Render/Deno/Turso hay tạo split-brain.
- Không sửa Stable/main/signer/provider/authority ngoài scope.
- Không hardcode URL, DB ID, deployment ID, Sheet ID, secret, epoch/generation hoặc artifact ID từ prompt này.
- Không chạy load test phá quota lên LIVE.
- Không đánh dấu OWNER acceptance thay OWNER.

---

## 12. Cách trả kết quả cho OWNER

Trả lời ngắn gọn nhưng đủ evidence theo đúng thứ tự:

1. Canonical scope/commit tiếp quản và bootstrap result.
2. Baseline đo thật; top nguyên nhân theo rows-read/written/request.
3. Thay đổi đã làm theo file/contract, giải thích vì sao không đổi nghiệp vụ.
4. Bảng tính 1.540 events, 5 clients: before/after và % Free quota.
5. Realtime/UI, offline/replay, Google replication, DR/fencing test receipts.
6. CI/release/rollback evidence và trạng thái LIVE nếu OWNER cho phép phát hành.
7. Các mục còn cần OWNER nghiệm thu; tuyệt đối không tự đánh dấu accepted.

Nếu không thể đạt target 500k reads/20k writes/20k requests nhưng vẫn dưới hard Free limits, hãy dừng trước release và trình bày chính xác route/query còn tốn quota cùng hai phương án giảm tiếp. Không tự nâng plan.

---

## 13. Kết quả kiến trúc mong đợi ở tải cực đại

Ở normal path, 1 business mutation chỉ cần:

- một canonical transaction có các write bất biến thật sự cần thiết;
- một mutation response chứa canonical patch/revision;
- một WebSocket invalidation nhỏ tới clients liên quan;
- mỗi client chỉ kéo delta mới bằng index/cursor và patch UI/local projection;
- Google/FCM xử lý coalesced theo batch/watermark ở background.

Số read không được tăng theo kiểu `số events × toàn bộ snapshot × số clients`. Nó phải gần với `cold bootstrap hữu hạn + số delta rows thực sự mới × số clients`, có batching/coalescing và headroom đủ lớn cho Free plan.

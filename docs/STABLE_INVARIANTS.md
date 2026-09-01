# STABLE INVARIANTS — APK PICK PACK 1291

OWNER: Nguyễn Văn Tâm  
Status: ACTIVE / mandatory  
Purpose: danh sách tích lũy các hành vi đã được OWNER chốt và/hoặc đã PASS để các lần sửa sau không làm hỏng chức năng đang ổn định.

## 1. Cách dùng bắt buộc

1. Mọi phiên sửa/test/build/release phải đọc file này sau `HANDOVER_CURRENT.md` và `REGRESSION_GUARD_POLICY.md`.
2. Trước khi sửa, xác định các invariant ACTIVE có thể bị ảnh hưởng bởi file/domain sẽ chạm tới và đưa chúng vào impact matrix.
3. Sau khi task PASS, mọi hành vi mới hoặc lỗi cũ đã được xác minh ổn định phải được thêm/cập nhật vào file này trước handoff/finalizer.
4. Invariant ACTIVE không được sửa/xóa/nới lỏng chỉ vì implementation thay đổi. Chỉ OWNER Nguyễn Văn Tâm được phép thay đổi business rule.
5. Khi OWNER thay đổi rule, giữ lịch sử bằng cách chuyển invariant cũ sang SUPERSEDED, ghi lệnh OWNER/evidence thay thế; không xóa lịch sử.
6. Một case đang FAIL hoặc chưa có evidence PASS không được ghi là ACTIVE_PASS. Ghi vào LOCKED_REQUIREMENT_PENDING_FIX nếu OWNER đã chốt rule nhưng implementation chưa đạt.
7. PASS release yêu cầu: case mới PASS + toàn bộ invariant ACTIVE liên quan tiếp tục PASS trên cùng exact candidate/bytes.

## 2. Schema invariant

Mỗi invariant tối thiểu có:
- ID
- Status: ACTIVE_PASS | LOCKED_REQUIREMENT_PENDING_FIX | TECHNICAL_PASS_AWAITING_OWNER | SUPERSEDED
- Scope/domain
- Rule cố định
- Authority/canonical decision path
- Regression/negative cases bắt buộc
- Evidence gần nhất: version/source/run/artifact hoặc OWNER confirmation
- Introduced/last_verified
- Notes nếu có

## 3. ACTIVE_PASS hiện hành

### UI-STATUS-001
- Status: ACTIVE_PASS
- Scope: UI / mọi màn trong scope ứng dụng
- Rule: 3 ô Mạng / Đồng bộ / Dịch vụ luôn ghim trên cùng; không được mất, đổi vị trí tùy tiện hoặc bị rerender đẩy khỏi header.
- Regression: kiểm tra các module bị chạm + visual matrix liên quan.
- Evidence: Beta101 exact-candidate visual/PDA PASS run 33309271079, artifact 9731526178; human visual 35 screenshots at 320x568 / 360x640 / 480x800 PASS; terminal publish/OTA/install/readback/finalize run 33310230934, final artifact 9731780051 PASS.
- Last verified: 0.4.2-beta.101.

### QR-LOCAL-001
- Status: ACTIVE_PASS
- Scope: QR nhân sự
- Rule: giữ local fast-path; quét nhân sự hiển thị dữ liệu local nhanh rồi Service reconcile nền; không được biến thành reload/reset UI đang thao tác.
- Regression: local fast-path + service reconcile + không reset interactive employee form.
- Evidence: Beta101 exact-candidate verify PASS run 33309271079; terminal publish/OTA/install/readback/finalize run 33310230934 PASS.
- Last verified: 0.4.2-beta.101.

### MEAL-DATE-001
- Status: ACTIVE_PASS
- Scope: Điểm danh nhân sự
- Rule: điểm danh chỉ chấp nhận ACTIVE session đúng business_date hiện tại; ACTIVE phiên cũ không được tính là session hiện tại.
- Regression: current-day ACTIVE accepted; old-day ACTIVE rejected.
- Evidence: Beta101 exact-candidate verify PASS run 33309271079; terminal publish/OTA/install/readback/finalize run 33310230934 PASS.
- Last verified: 0.4.2-beta.101.

### MEAL-WARN-001
- Status: ACTIVE_PASS
- Scope: Nghiệp vụ / Điểm danh
- Rule: cảnh báo nhân sự chưa điểm danh phải hiển thị ở phía trên theo scope đã chốt.
- Regression: warning render + realtime refresh không phá header.
- Evidence: Beta101 exact-candidate verify PASS run 33309271079; terminal publish/OTA/install/readback/finalize run 33310230934 PASS.
- Last verified: 0.4.2-beta.101.

### ROLE-HISTORY-001
- Status: ACTIVE_PASS
- Scope: Role / History
- Rule: USER không thấy tab History và không được truy cập History bằng deep-link; ADMIN/SUPERADMIN theo quyền hiện hành.
- Regression: tab hidden + deep-link blocked cho USER.
- Evidence: Beta101 exact-candidate verify PASS run 33309271079; terminal publish/OTA/install/readback/finalize run 33310230934 PASS.
- Last verified: 0.4.2-beta.101.

### OTA-BETA-001
- Status: ACTIVE_PASS
- Scope: Beta APK release/OTA/rollback
- Rule: Beta APK = GITHUB_RELEASE_ONLY; Google Drive APK FORBIDDEN cho backup/staging/mirror/upload/download/rollback/distribution.
- Authority: GitHub Actions exact candidate → GitHub Release exact bytes → Beta manifest/update API → OTA exact readback.
- Regression: exact SHA256/size/version/package/signer, Stable/main/authority unchanged.
- Publish-verifier regression: receipt-driven screenshot evidence; actual-count mismatch / missing viewport / summary mismatch / human gate false phải FAIL; Beta104 Fast Check run 33388933459 PASS.
- Evidence: Beta106 terminal run 33476108449 PASS; publish artifact 9788246064; OTA/install/readback artifact 9788292824; final artifact 9788296923; exact candidate run 33473965249 / artifact 9787581956; SHA256 ea5bdf9696d9dae77f02fab815df6435a8317a66178bdb4c36bc051aa5bcd000 / size 14068725 / signer d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e; OTA 0.4.2-beta.104 → 0.4.2-beta.106 exact SHA/size/version/package/signer + install/open PASS; Stable/main/authority unchanged.
- Last verified: 0.4.2-beta.106.

## 4. LOCKED_REQUIREMENT_PENDING_FIX / AWAITING OWNER / DEFERRED

### PDA-EXIT-001
- Status: ACTIVE_PASS
- Scope: Ra ca / PDA
- OWNER rule: chỉ kiểm PDA cuối ca khi đúng session hiện tại thực tế có PDA theo authority của chính session đó.
- Không PDA → Ra ca trực tiếp, không hiện kiểm PDA.
- PDA đã trả → không kiểm lại.
- `pda_serial` / cache / legacy stale hoặc PDA của phiên cũ không được tự biến thành bằng chứng session hiện tại có PDA.
- Nếu authority chưa đủ dữ liệu phải resolve đúng session từ Service; cấm suy đoán từ scalar/cache cũ.
- Regression matrix tối thiểu: active PDA / no PDA / PDA đã trả / stale pda_serial / thiếu assignment snapshot / phiên cũ có PDA nhưng phiên hiện tại không có.
- Technical evidence: OWNER-accepted Beta99 baseline remains ACTIVE_PASS; reverified on Beta101 exact candidate visual/PDA run 33309271079 and terminal publish/OTA/install/readback/finalize run 33310230934 PASS.
- OWNER acceptance: PASS — item 1 OK và item 2 OK trên Beta99. Latest manual evidence 2026-08-30 13:21 + OWNER confirmation: session_work_update Đổi/Trả PDA hoạt động, không còn USER_PICK_UNAVAILABLE. Khóa ACTIVE_PASS từ Beta99.

### ENV-ISOLATION-001
- Status: ACTIVE_PASS
- Scope: Beta/Stable environment isolation / HTTP / GAS / LAN-NSD / release
- OWNER rule: Beta và Stable phải tách environment/audience, data/accounts/service/GAS/OTA/LAN mutable state; cross-environment automatic write/fallback/auth/session/manifest/LAN sharing bị cấm. Stable giữ READY_NOT_LIVE/private/public=false cho tới lệnh promotion riêng của OWNER.
- Regression: distinct BETA/STABLE environment+audience; cross/missing environment request bị reject; D1/Sheet/GAS tách; LAN/NSD type tách; BETA GAS discovery trỏ canonical BETA Service; Stable không OTA/public/promotion; Stable/main/signer/authority không đổi.
- Technical evidence: Beta104 source c31bb1b7ad68e6fd114727d8f08508796013bcef; candidate 33384004708 / 9754938692; exact-device SERVICE-DISCOVERY-001 33388577027 / 9756583802 PASS; Fast Check 33388933459 PASS; runtime DoD 33389060092 / 9756743967 PASS; terminal publish/OTA/install/readback/finalize 33391700817 PASS; publish 9757752307; OTA preserved-data 9757829287; final 9757837384; exact APK SHA256 523b7ca4fe3463acdec8281d6232f36cd15e8df13a5f25585ca4ff4b82f2d6f1 / size 13593589 / signer d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e; BETA environment/audience/Worker readback PASS; Stable available=false, main unchanged.
- Prior OWNER failure: Beta102 stale discovery connectivity failure. Technical remediation is PASS on Beta104; OWNER re-acceptance remains required.
- OWNER acceptance: PASS — Beta104 checklist 1–6 OK, 2026-08-31 20:22 +07:00. Locked ACTIVE_PASS.

### SERVICE-DISCOVERY-001
- Status: ACTIVE_PASS
- Scope: Android dynamic Service discovery/cache
- OWNER rule: BETA phải kết nối Service qua environment-scoped dynamic discovery; stale cache từ endpoint/environment cũ không được điều khiển Service session/read/sync/outbox sau OTA hoặc isolation cutover.
- Failure evidence: manual-20260831-172725-4aaccadf-0df6-4d6d-9eca-589b274b1659.json — Beta102/adminbeta; session_http=-1; UnknownHostException tới pickpack1291.cc.cd; runtime_error=SESSION_EXCHANGE_FAILED trong khi canonical BETA discovery trỏ BETA Worker riêng.
- Regression required: cache phải match exact BuildConfig environment/audience; stale/missing-env cache bị invalidate; discoverySnapshot honor TTL/force; live session/direct-read/sync/outbox/resilience path refresh discovery; Android không hardcode Stable root hoặc provider URL.
- Technical evidence: Beta106 exact-device run 33474768649 / artifact 9787794484 PASS; terminal OTA 33476108449 / artifact 9788292824 PASS on exact candidate ea5bdf9696d9dae77f02fab815df6435a8317a66178bdb4c36bc051aa5bcd000. Post-OTA regression accepts both safe states: stale cache survives until explicit discovery check and is then rewritten, or the app eagerly rewrites it during startup; in both cases final cache must be environment=BETA, audience=PICK_PACK_1291_BETA, canonical Beta Service URL, stable_root_reused=false. First publish attempt 33475493287 proved exact install but harness incorrectly required stale cache to remain; Beta104 rollback 9788091781 PASS, harness fixed, same exact Beta106 bytes republished and terminal PASS.
- Technical candidate: 0.4.2-beta.106 LIVE.
- OWNER acceptance: PASS — Beta104 checklist 1–6 OK, 2026-08-31 20:22 +07:00. Locked ACTIVE_PASS.

### SHIFT-STAFF-DOWNLOAD-QR-001
- Status: TECHNICAL_PASS_AWAITING_OWNER
- Scope: Rà soát ca / danh sách nhân sự / Cài đặt QR tải ứng dụng
- Rule: danh sách chi tiết nhân sự theo ca nhóm theo NCC; các bộ lọc Tất cả / Trong ca / Đã ra ca hiển thị số lượng ngay trên tiêu đề; dòng nhân sự giữ họ tên, MNV, vị trí và giờ vào/ra; chạm nhân sự mở trực tiếp luồng QR Vào/Ra hiện có. NCC rỗng hoặc JSON null phải hiển thị `Chưa xác định NCC`, tuyệt đối không hiển thị literal `null`. Cài đặt có QR tải ứng dụng; Beta trỏ GitHub Release mới nhất, Stable vẫn fail-closed cho tới khi OWNER phát hành Stable.
- Regression: SHIFT-STAFF-DOWNLOAD-QR-NULL-001 / qa/beta106_shift_staff_null_regression.md; kiểm tra grouped NCC + filter counts + no visible null + tap employee → QR + download QR + Stable unavailable.
- Technical evidence: source 57e02d45b436c6bcb64bc5731671044af7c7c86d; candidate run 33473965249 / artifact 9787581956; visual artifact 9787692571 / 36 screenshots / human PASS 320x568, 360x640, 480x800; Fast Check 33476011598 PASS; exact-device 33474768649 / 9787794484 PASS; runtime DoD 33475078900 / 9787884925 PASS; terminal publish/OTA/install/readback/finalize 33476108449 PASS; PDA artifact 9788292824; final artifact 9788296923; exact APK SHA256 ea5bdf9696d9dae77f02fab815df6435a8317a66178bdb4c36bc051aa5bcd000 / size 14068725 / signer d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e.
- OWNER acceptance: PENDING — Technical PASS không tự chuyển ACTIVE_PASS.
- Last verified: 0.4.2-beta.106.


### INFRA-RESILIENCE-001
- Status: TECHNICAL_PASS_AWAITING_OWNER
- Scope: infra / DR / durable event path
- Rule: durable local + provisional Google ledger + single-writer LAN/cloud DR + backup/rollover/fencing phải giữ canonical event/idempotency và không tự đổi authority/provider.
- Technical evidence: service-live PASS job 99202629701 inherited because exact service source unchanged; Beta101 exact-candidate verify run 33309271079; terminal publish/OTA/install/readback/finalize run 33310230934 PASS. OWNER manual log 2026-08-30 20:12 phát hiện Google fallback FAIL deterministic UNKNOWN_ACTION và LAN NOT_AVAILABLE. Read-only GAS deployment probe 33313877854 xác nhận deployment 205 thiếu RESILIENCE_V1; repair 33314072135 deploy 206 PASS, post-readback 33314115931 PASS; ppUpdateCheck Beta101/Stable/main/signer/authority/provider không đổi. Release guard Fast Check 33314181358 PASS.
- Test fidelity: NORMAL_SERVICE_PRIMARY dùng Service/idempotency thật. Google fallback sau GAS206 là safe live-path drill. DEVICE_OFFLINE_LOCAL và SERVICE_GOOGLE_OFFLINE_LOCAL là isolated simulation + real recovery, không phải physical outage. GOOGLE_UNAVAILABLE_SERVICE dùng Service thật nhưng Google-down được mô phỏng. LAN chỉ có giá trị khi có topology multi-device thực sự active.
- OWNER acceptance: DEFERRED_BY_OWNER ngày 2026-08-30. Item 6 tạm pending, không phải PASS, không chặn scope phát triển khác; chỉ rerun Beta101/GAS206 + LAN topology thật khi OWNER mở lại scope backup/DR trước khi ACTIVE_PASS.


### BETA-STABLE-AUDIT-001
- Status: TECHNICAL_PASS_AWAITING_OWNER
- Scope: Beta/Stable full isolation / private Stable readiness / future promotion
- Rule: Beta104 LIVE remains the accepted development environment; Stable is an independent READY_NOT_LIVE environment with separate package/runtime/data/auth/GSheet/GAS/DR/release state. Cross-environment write/auth/session/fallback/manifest/data reuse is forbidden. Stable public root/manifest/OTA/promotion remain disabled until a fresh explicit OWNER promotion authorization.
- Regression: exact accepted Beta product source unchanged; Stable private APK side-by-side install; runtime environment/audience mismatch reject; auth and data canary isolation; GAS destination/idempotency/cleanup; provider DR restore/cross-token/cross-restore; canonical quota guard; promotion dry-run; Stable publish fail-closed; FCM-only environment scoping; final impacted regression.
- Technical evidence: accepted Beta source c31bb1b7ad68e6fd114727d8f08508796013bcef / Beta104 terminal 33391700817; Stable private APK run 33401278044 artifact 9761451846; Turso 33413666617/9766154727; Deno 33416165785/9767094401; Render 33417320129/9767567227; promotion dry-run 33419578736/9768397541; final CI 33419578501; final impacted regression 33420663673/9768750476 PASS. Stable manifest/OTA/public/promotion all false; no Beta transactional/account/session/outbox/log state copied.
- Common-mode note: free providers can retain provider/account-wide availability risk; resource/credential/write-path isolation and canonical quota/kill-switch guards prevent cross-environment data contamination and planned Beta quota exhaustion, but this invariant does not claim immunity from a provider-wide outage.
- OWNER acceptance: DEFERRED_BY_OWNER_UNTIL_FIRST_STABLE_RELEASE — OWNER quyết định 2026-09-01 07:14 +07:00; checklist 1–18 chỉ nghiệm thu sau khi phát triển Beta mới, chốt Beta và phát hành Stable lần đầu.
- Last verified: 2026-09-01 / audit branch release/audit-beta104-stable-private-20260831.


## 5. Quy tắc tích lũy sau mỗi task

Khi DoD PASS:
1. Liệt kê hành vi mới/bugfix đã được xác minh.
2. Nếu là rule mới: cấp ID mới và thêm ACTIVE_PASS.
3. Nếu củng cố rule cũ: cập nhật evidence/last_verified, không thay nội dung rule.
4. Nếu phát hiện invariant cũ bị lỗi: chuyển/ghi rõ trạng thái cần sửa, không che giấu bằng PASS của case khác.
5. Handoff/finalizer phải ghi các invariant đã thêm/cập nhật và evidence exact.
6. Phiên sau phải dùng danh sách này làm regression baseline trước mọi change.

File này là canonical registry cho hành vi đã khóa của APK PICK PACK 1291.

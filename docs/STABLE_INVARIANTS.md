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

- Latest Beta110 re-verification: exact source 1faebbf996836d442ec6e99ffba2a589bf3fcbd2; candidate 33554345340/9818862858; Service 33568634524/9824237674; visual/PDA/API36 33569543281/9824551840; Fast Check 33569530461; device 33570127113/9824662041; runtime 33573848594/9825920815; terminal 33574078129; publish 9826016343; OTA/install/readback 9826069523; final 9826075161. Stable/main/signer/authority unchanged.
- Latest Beta111 re-verification: 0.4.2-beta.111 LIVE / source 03b37e5aa2726c273cc1e7c4a2161763bd3c4d2d / candidate 33586428789/9830403339 / Fast Check 33588839641 / Service 33588851239/9831120144 / visual+PDA+API36 33589199933/9831243286 + human PASS 41 screenshots / device 33590310367/9831531954 / runtime 33590505522 attempt2/9831607439 / terminal 33590747613 / publish 9831669563 / OTA-install-readback 9831721383 / final 9831726759 / SHA256 f67049067e600f4d8439d0ae088889f7b35df8b215e5432a2fcdd54f05f04a4f / size 14216181 / signer d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e; Stable/main/authority unchanged.

### QR-LOCAL-001
- Status: ACTIVE_PASS
- Scope: QR nhân sự
- Rule: giữ local fast-path; quét nhân sự hiển thị dữ liệu local nhanh rồi Service reconcile nền; không được biến thành reload/reset UI đang thao tác.
- Regression: local fast-path + service reconcile + không reset interactive employee form.
- Evidence: Beta101 exact-candidate verify PASS run 33309271079; terminal publish/OTA/install/readback/finalize run 33310230934 PASS.
- Last verified: 0.4.2-beta.101.

- Latest Beta110 re-verification: exact source 1faebbf996836d442ec6e99ffba2a589bf3fcbd2; candidate 33554345340/9818862858; Service 33568634524/9824237674; visual/PDA/API36 33569543281/9824551840; Fast Check 33569530461; device 33570127113/9824662041; runtime 33573848594/9825920815; terminal 33574078129; publish 9826016343; OTA/install/readback 9826069523; final 9826075161. Stable/main/signer/authority unchanged.
- Latest Beta111 re-verification: 0.4.2-beta.111 LIVE / source 03b37e5aa2726c273cc1e7c4a2161763bd3c4d2d / candidate 33586428789/9830403339 / Fast Check 33588839641 / Service 33588851239/9831120144 / visual+PDA+API36 33589199933/9831243286 + human PASS 41 screenshots / device 33590310367/9831531954 / runtime 33590505522 attempt2/9831607439 / terminal 33590747613 / publish 9831669563 / OTA-install-readback 9831721383 / final 9831726759 / SHA256 f67049067e600f4d8439d0ae088889f7b35df8b215e5432a2fcdd54f05f04a4f / size 14216181 / signer d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e; Stable/main/authority unchanged.

### MEAL-DATE-001
- Status: ACTIVE_PASS
- Scope: Điểm danh nhân sự
- Rule: điểm danh chỉ chấp nhận ACTIVE session đúng business_date hiện tại; ACTIVE phiên cũ không được tính là session hiện tại.
- Regression: current-day ACTIVE accepted; old-day ACTIVE rejected.
- Evidence: Beta101 exact-candidate verify PASS run 33309271079; terminal publish/OTA/install/readback/finalize run 33310230934 PASS.
- Last verified: 0.4.2-beta.101.

- Latest Beta110 re-verification: exact source 1faebbf996836d442ec6e99ffba2a589bf3fcbd2; candidate 33554345340/9818862858; Service 33568634524/9824237674; visual/PDA/API36 33569543281/9824551840; Fast Check 33569530461; device 33570127113/9824662041; runtime 33573848594/9825920815; terminal 33574078129; publish 9826016343; OTA/install/readback 9826069523; final 9826075161. Stable/main/signer/authority unchanged.

### MEAL-WARN-001
- Status: ACTIVE_PASS
- Scope: Nghiệp vụ / Điểm danh
- Rule: cảnh báo nhân sự chưa điểm danh phải hiển thị ở phía trên theo scope đã chốt.
- Regression: warning render + realtime refresh không phá header.
- Evidence: Beta101 exact-candidate verify PASS run 33309271079; terminal publish/OTA/install/readback/finalize run 33310230934 PASS.
- Last verified: 0.4.2-beta.101.

- Latest Beta110 re-verification: exact source 1faebbf996836d442ec6e99ffba2a589bf3fcbd2; candidate 33554345340/9818862858; Service 33568634524/9824237674; visual/PDA/API36 33569543281/9824551840; Fast Check 33569530461; device 33570127113/9824662041; runtime 33573848594/9825920815; terminal 33574078129; publish 9826016343; OTA/install/readback 9826069523; final 9826075161. Stable/main/signer/authority unchanged.

### ROLE-HISTORY-001
- Status: ACTIVE_PASS
- Scope: Role / History
- Rule: USER không thấy tab History và không được truy cập History bằng deep-link; ADMIN/SUPERADMIN theo quyền hiện hành.
- Regression: tab hidden + deep-link blocked cho USER.
- Evidence: Beta101 exact-candidate verify PASS run 33309271079; terminal publish/OTA/install/readback/finalize run 33310230934 PASS.
- Last verified: 0.4.2-beta.101.

- Latest Beta110 re-verification: exact source 1faebbf996836d442ec6e99ffba2a589bf3fcbd2; candidate 33554345340/9818862858; Service 33568634524/9824237674; visual/PDA/API36 33569543281/9824551840; Fast Check 33569530461; device 33570127113/9824662041; runtime 33573848594/9825920815; terminal 33574078129; publish 9826016343; OTA/install/readback 9826069523; final 9826075161. Stable/main/signer/authority unchanged.

### OTA-BETA-001
- Status: ACTIVE_PASS
- Scope: Beta APK release/OTA/rollback
- Rule: Beta APK = GITHUB_RELEASE_ONLY; Google Drive APK FORBIDDEN cho backup/staging/mirror/upload/download/rollback/distribution.
- Authority: GitHub Actions exact candidate → GitHub Release exact bytes → Beta manifest/update API → OTA exact readback.
- Regression: exact SHA256/size/version/package/signer, Stable/main/authority unchanged.
- Publish-verifier regression: receipt-driven screenshot evidence; actual-count mismatch / missing viewport / summary mismatch / human gate false phải FAIL; Beta104 Fast Check run 33388933459 PASS.
- Evidence: Beta109 terminal run 33515483109 PASS; publish artifact 9803429207; OTA/install/readback artifact 9803518172; final artifact 9803526992; exact candidate run 33506205883 / artifact 9799840161; SHA256 1c01a58eefe5d0501eccbfe0359a2d5c0b3ec159f5ef37889d757f0984bbc7c8 / size 14167029 / signer d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e; GitHub Release asset 539613285 exact; OTA 0.4.2-beta.108 → 0.4.2-beta.109 exact SHA/size/version/package/signer + install/open PASS; Stable/main/authority unchanged.
- Last verified: 0.4.2-beta.109.

## 4. LOCKED_REQUIREMENT_PENDING_FIX / AWAITING OWNER / DEFERRED

- Latest Beta110 re-verification: exact source 1faebbf996836d442ec6e99ffba2a589bf3fcbd2; candidate 33554345340/9818862858; Service 33568634524/9824237674; visual/PDA/API36 33569543281/9824551840; Fast Check 33569530461; device 33570127113/9824662041; runtime 33573848594/9825920815; terminal 33574078129; publish 9826016343; OTA/install/readback 9826069523; final 9826075161. Stable/main/signer/authority unchanged.
- Latest Beta111 re-verification: 0.4.2-beta.111 LIVE / source 03b37e5aa2726c273cc1e7c4a2161763bd3c4d2d / candidate 33586428789/9830403339 / Fast Check 33588839641 / Service 33588851239/9831120144 / visual+PDA+API36 33589199933/9831243286 + human PASS 41 screenshots / device 33590310367/9831531954 / runtime 33590505522 attempt2/9831607439 / terminal 33590747613 / publish 9831669563 / OTA-install-readback 9831721383 / final 9831726759 / SHA256 f67049067e600f4d8439d0ae088889f7b35df8b215e5432a2fcdd54f05f04a4f / size 14216181 / signer d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e; Stable/main/authority unchanged.

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

- Latest Beta110 re-verification: exact source 1faebbf996836d442ec6e99ffba2a589bf3fcbd2; candidate 33554345340/9818862858; Service 33568634524/9824237674; visual/PDA/API36 33569543281/9824551840; Fast Check 33569530461; device 33570127113/9824662041; runtime 33573848594/9825920815; terminal 33574078129; publish 9826016343; OTA/install/readback 9826069523; final 9826075161. Stable/main/signer/authority unchanged.
- Latest Beta111 re-verification: 0.4.2-beta.111 LIVE / source 03b37e5aa2726c273cc1e7c4a2161763bd3c4d2d / candidate 33586428789/9830403339 / Fast Check 33588839641 / Service 33588851239/9831120144 / visual+PDA+API36 33589199933/9831243286 + human PASS 41 screenshots / device 33590310367/9831531954 / runtime 33590505522 attempt2/9831607439 / terminal 33590747613 / publish 9831669563 / OTA-install-readback 9831721383 / final 9831726759 / SHA256 f67049067e600f4d8439d0ae088889f7b35df8b215e5432a2fcdd54f05f04a4f / size 14216181 / signer d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e; Stable/main/authority unchanged.

### ENV-ISOLATION-001
- Status: ACTIVE_PASS
- Scope: Beta/Stable environment isolation / HTTP / GAS / LAN-NSD / release
- OWNER rule: Beta và Stable phải tách environment/audience, data/accounts/service/GAS/OTA/LAN mutable state; cross-environment automatic write/fallback/auth/session/manifest/LAN sharing bị cấm. Stable giữ READY_NOT_LIVE/private/public=false cho tới lệnh promotion riêng của OWNER.
- Regression: distinct BETA/STABLE environment+audience; cross/missing environment request bị reject; D1/Sheet/GAS tách; LAN/NSD type tách; BETA GAS discovery trỏ canonical BETA Service; Stable không OTA/public/promotion; Stable/main/signer/authority không đổi.
- Technical evidence: Beta104 source c31bb1b7ad68e6fd114727d8f08508796013bcef; candidate 33384004708 / 9754938692; exact-device SERVICE-DISCOVERY-001 33388577027 / 9756583802 PASS; Fast Check 33388933459 PASS; runtime DoD 33389060092 / 9756743967 PASS; terminal publish/OTA/install/readback/finalize 33391700817 PASS; publish 9757752307; OTA preserved-data 9757829287; final 9757837384; exact APK SHA256 523b7ca4fe3463acdec8281d6232f36cd15e8df13a5f25585ca4ff4b82f2d6f1 / size 13593589 / signer d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e; BETA environment/audience/Worker readback PASS; Stable available=false, main unchanged.
- Prior OWNER failure: Beta102 stale discovery connectivity failure. Technical remediation is PASS on Beta104; OWNER re-acceptance remains required.
- OWNER acceptance: PASS — Beta104 checklist 1–6 OK, 2026-08-31 20:22 +07:00. Locked ACTIVE_PASS.

- Latest Beta110 re-verification: exact source 1faebbf996836d442ec6e99ffba2a589bf3fcbd2; candidate 33554345340/9818862858; Service 33568634524/9824237674; visual/PDA/API36 33569543281/9824551840; Fast Check 33569530461; device 33570127113/9824662041; runtime 33573848594/9825920815; terminal 33574078129; publish 9826016343; OTA/install/readback 9826069523; final 9826075161. Stable/main/signer/authority unchanged.
- Latest Beta111 re-verification: 0.4.2-beta.111 LIVE / source 03b37e5aa2726c273cc1e7c4a2161763bd3c4d2d / candidate 33586428789/9830403339 / Fast Check 33588839641 / Service 33588851239/9831120144 / visual+PDA+API36 33589199933/9831243286 + human PASS 41 screenshots / device 33590310367/9831531954 / runtime 33590505522 attempt2/9831607439 / terminal 33590747613 / publish 9831669563 / OTA-install-readback 9831721383 / final 9831726759 / SHA256 f67049067e600f4d8439d0ae088889f7b35df8b215e5432a2fcdd54f05f04a4f / size 14216181 / signer d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e; Stable/main/authority unchanged.

### SERVICE-DISCOVERY-001
- Status: ACTIVE_PASS
- Scope: Android dynamic Service discovery/cache
- OWNER rule: BETA phải kết nối Service qua environment-scoped dynamic discovery; stale cache từ endpoint/environment cũ không được điều khiển Service session/read/sync/outbox sau OTA hoặc isolation cutover.
- Failure evidence: manual-20260831-172725-4aaccadf-0df6-4d6d-9eca-589b274b1659.json — Beta102/adminbeta; session_http=-1; UnknownHostException tới pickpack1291.cc.cd; runtime_error=SESSION_EXCHANGE_FAILED trong khi canonical BETA discovery trỏ BETA Worker riêng.
- Regression required: cache phải match exact BuildConfig environment/audience; stale/missing-env cache bị invalidate; discoverySnapshot honor TTL/force; live session/direct-read/sync/outbox/resilience path refresh discovery; Android không hardcode Stable root hoặc provider URL.
- Technical evidence: Beta109 exact-device run 33514582110 / artifact 9803110874 PASS; terminal OTA 33515483109 / artifact 9803518172 PASS on exact candidate 1c01a58eefe5d0501eccbfe0359a2d5c0b3ec159f5ef37889d757f0984bbc7c8. Post-OTA readback: stale_cache_state_before_post_ota_check=ALREADY_REWRITTEN_BY_APP, stale_discovery_preserved_across_ota=false, stale_discovery_safe_after_ota=true; canonical Beta discovery remained safe.
- Technical candidate: 0.4.2-beta.109 LIVE.
- OWNER acceptance: PASS — Beta104 checklist 1–6 OK, 2026-08-31 20:22 +07:00. Locked ACTIVE_PASS.

- Latest Beta110 re-verification: exact source 1faebbf996836d442ec6e99ffba2a589bf3fcbd2; candidate 33554345340/9818862858; Service 33568634524/9824237674; visual/PDA/API36 33569543281/9824551840; Fast Check 33569530461; device 33570127113/9824662041; runtime 33573848594/9825920815; terminal 33574078129; publish 9826016343; OTA/install/readback 9826069523; final 9826075161. Stable/main/signer/authority unchanged.
- Latest Beta111 re-verification: 0.4.2-beta.111 LIVE / source 03b37e5aa2726c273cc1e7c4a2161763bd3c4d2d / candidate 33586428789/9830403339 / Fast Check 33588839641 / Service 33588851239/9831120144 / visual+PDA+API36 33589199933/9831243286 + human PASS 41 screenshots / device 33590310367/9831531954 / runtime 33590505522 attempt2/9831607439 / terminal 33590747613 / publish 9831669563 / OTA-install-readback 9831721383 / final 9831726759 / SHA256 f67049067e600f4d8439d0ae088889f7b35df8b215e5432a2fcdd54f05f04a4f / size 14216181 / signer d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e; Stable/main/authority unchanged.

### SHIFT-STAFF-DOWNLOAD-QR-001
- Status: ACTIVE_PASS
- Scope: Rà soát ca / danh sách nhân sự / Cài đặt QR tải ứng dụng
- Rule: danh sách chi tiết nhân sự theo ca nhóm theo NCC; các bộ lọc Tất cả / Trong ca / Đã ra ca hiển thị số lượng ngay trên tiêu đề; dòng nhân sự giữ họ tên, MNV, vị trí và giờ vào/ra; chạm nhân sự mở trực tiếp luồng QR Vào/Ra hiện có. NCC rỗng hoặc JSON null phải hiển thị `Chưa xác định NCC`, tuyệt đối không hiển thị literal `null`. Cài đặt có QR tải ứng dụng; Beta trỏ GitHub Release mới nhất, Stable vẫn fail-closed cho tới khi OWNER phát hành Stable.
- Regression: SHIFT-STAFF-DOWNLOAD-QR-NULL-001 / qa/beta106_shift_staff_null_regression.md; kiểm tra grouped NCC + filter counts + no visible null + tap employee → QR + download QR + Stable unavailable.
- Technical evidence: source 57e02d45b436c6bcb64bc5731671044af7c7c86d; candidate run 33473965249 / artifact 9787581956; visual artifact 9787692571 / 36 screenshots / human PASS 320x568, 360x640, 480x800; Fast Check 33476011598 PASS; exact-device 33474768649 / 9787794484 PASS; runtime DoD 33475078900 / 9787884925 PASS; terminal publish/OTA/install/readback/finalize 33476108449 PASS; PDA artifact 9788292824; final artifact 9788296923; exact APK SHA256 ea5bdf9696d9dae77f02fab815df6435a8317a66178bdb4c36bc051aa5bcd000 / size 14068725 / signer d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e.
- OWNER acceptance: PASS — `ops/beta106-owner-acceptance.json`; OWNER xác nhận toàn bộ scope Beta106 về cơ bản OK ngày 2026-09-01; các tinh chỉnh layout sau này là scope mới và không phủ nhận acceptance hiện tại.
- Last verified: 0.4.2-beta.106.


### DOCUMENT-MANAGEMENT-001
- Status: ACTIVE_PASS
- Scope: Quản lý biên bản / Google Drive / D1 / xác nhận thao tác
- OWNER rule 2026-09-01: Sửa loại biên bản = đổi tên toàn bộ dữ liệu lịch sử thuộc loại đó và đổi tên toàn bộ file tương ứng trên Google Drive. Xóa loại biên bản = xóa hẳn file Drive + bản ghi biên bản + danh mục; chỉ giữ receipt kỹ thuật tối thiểu (ai, khi nào, số lượng, mã job), không giữ nội dung/ảnh/tên file cũ.
- Xác nhận: cả Sửa và Xóa phải dùng đúng canonical confirmation hiện tại của app: HHmm giờ Việt Nam, inclusive ±2 phút; SUPERADMIN giữ đường re-auth mật khẩu tài khoản như logic hiện hành.
- Consistency: mutation phải chạy dạng durable job/checkpoint; upload mới bị fence trong lúc mutation; retry/crash không được tạo trạng thái nửa chừng.
- Regression tối thiểu: drive direct upload / no D1 blob / exact duplicate block / near-duplicate warning / durable pending queue / post-Drive resume / bounded cache / account-scoped retry / rename all D1 metadata / rename all Drive names / hard delete Drive + records / durable mutation resume / exact confirmation HHmm ±2 / Beta-Stable isolation / offline category cache / durable selected-image draft restore.
- Technical evidence Beta109: source a72d8e20eaebe60235338fd1b9aaebde42507825; candidate 33506205883 / 9799840161; exact APK SHA256 1c01a58eefe5d0501eccbfe0359a2d5c0b3ec159f5ef37889d757f0984bbc7c8 / size 14167029 / signer d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e.
- Service live: run 33509679186 attempt 2 / artifact 9801444305 PASS; exact duplicate guard PASS; rotation-aware near-similar PASS.
- Visual/PDA/API36/local durability: run 33511409449 / artifact 9801982052 PASS; 39 screenshots + human visual PASS 320x568 / 360x640 / 480x800; document_selected_draft_durable_beta109=true; document_category_cache_offline_beta109=true.
- Fast Check: run 33510974424 PASS.
- Exact-device stale-discovery regression: run 33514582110 / artifact 9803110874 PASS.
- Runtime DoD: run 33514927663 attempt 2 / artifact 9803295906 PASS.
- Terminal publish/OTA/install/readback/finalize: run 33515483109 PASS; publish artifact 9803429207; PDA OTA artifact 9803518172; final artifact 9803526992; GitHub Release asset 539613285 exact SHA256/size; OTA 0.4.2-beta.108 → 0.4.2-beta.109 exact bytes, install/open PASS; Stable/main/signer/authority unchanged.
- Regression case: qa/beta109_document_management_regression.md + tools/document_management_contract.py + tools/beta89_service_live_gate.sh + tools/Beta83UiChecksInstrumentation.java.
- Technical receipt: ops/beta109-technical-pass.json.
- Technical candidate: 0.4.2-beta.109 LIVE.
- OWNER acceptance: PASS — Beta108 đã khóa các mục 1,2,5,6,7,8; OWNER xác nhận thêm 2 mục còn lại OK ngày 2026-09-01 22:04 +07:00.
- OWNER final acceptance receipt: ops/beta109-owner-acceptance.json.
- ACTIVE_PASS: khóa toàn bộ semantics DOCUMENT-MANAGEMENT-001 trên Beta109; mọi thay đổi semantics sau này cần OWNER SUPERSEDE.
- Last verified: 0.4.2-beta.109 LIVE / terminal run 33515483109 / OWNER acceptance complete 2026-09-01 22:04 +07:00.


- Latest Beta110 re-verification: exact source 1faebbf996836d442ec6e99ffba2a589bf3fcbd2; candidate 33554345340/9818862858; Service 33568634524/9824237674; visual/PDA/API36 33569543281/9824551840; Fast Check 33569530461; device 33570127113/9824662041; runtime 33573848594/9825920815; terminal 33574078129; publish 9826016343; OTA/install/readback 9826069523; final 9826075161. Stable/main/signer/authority unchanged.
- Latest Beta111 re-verification: 0.4.2-beta.111 LIVE / source 03b37e5aa2726c273cc1e7c4a2161763bd3c4d2d / candidate 33586428789/9830403339 / Fast Check 33588839641 / Service 33588851239/9831120144 / visual+PDA+API36 33589199933/9831243286 + human PASS 41 screenshots / device 33590310367/9831531954 / runtime 33590505522 attempt2/9831607439 / terminal 33590747613 / publish 9831669563 / OTA-install-readback 9831721383 / final 9831726759 / SHA256 f67049067e600f4d8439d0ae088889f7b35df8b215e5432a2fcdd54f05f04a4f / size 14216181 / signer d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e; Stable/main/authority unchanged.

### DOCUMENT-BATCH-001
- Status: ACTIVE_PASS
- Scope: Quản lý biên bản / batch UI + durable mutation
- Rule: hỗ trợ chọn nhiều ảnh; upload theo `Một biên bản nhiều trang` hoặc `Nhiều biên bản`; lọc theo loại; chọn một/nhiều ảnh đã tải để hard-delete qua mutation bền vững; thao tác phải xuất hiện trong Lịch sử.
- Parent invariant: DOCUMENT-MANAGEMENT-001 vẫn ACTIVE_PASS, semantics rename/hard-delete/Drive/direct-upload không đổi.
- Regression: multi gallery select / durable multi draft / multipage group / multiple-document group / category filter / bulk selected delete / delete resume / document history.
- Technical evidence Beta110: service run 33568634524 artifact 9824237674 PASS (multipage_group, selected_delete, reindex, history); visual/PDA/API36 run 33569543281 artifact 9824551840 PASS; Fast Check 33569530461 PASS; terminal release 33574078129 PASS; OTA/install/readback artifact 9826069523 exact bytes.
- Technical receipt: `ops/beta110-technical-pass.json`.
- OWNER acceptance: PASS — OWNER xác nhận toàn bộ Beta110 OK ngày 2026-09-02 07:43 +07:00; receipt `ops/beta110-owner-acceptance.json`.
- UI follow-up: một số điểm chưa ưng chỉ mang tính giao diện, sẽ là scope chỉnh sửa mới; không phủ nhận acceptance hiện tại.
- Last verified: 0.4.2-beta.110 LIVE / terminal run 33574078129 / OWNER acceptance complete.
- Latest Beta111 re-verification: 0.4.2-beta.111 LIVE / source 03b37e5aa2726c273cc1e7c4a2161763bd3c4d2d / candidate 33586428789/9830403339 / Fast Check 33588839641 / Service 33588851239/9831120144 / visual+PDA+API36 33589199933/9831243286 + human PASS 41 screenshots / device 33590310367/9831531954 / runtime 33590505522 attempt2/9831607439 / terminal 33590747613 / publish 9831669563 / OTA-install-readback 9831721383 / final 9831726759 / SHA256 f67049067e600f4d8439d0ae088889f7b35df8b215e5432a2fcdd54f05f04a4f / size 14216181 / signer d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e; Stable/main/authority unchanged.

### LABOR-TIME-RANGE-001
- Status: ACTIVE_PASS
- Scope: Công nhật / Ra ca / Nghiệp vụ
- Rule: dùng bộ chọn giờ-phút; cho phép ghi bắt đầu trước và kết thúc sau; labor OPEN chặn Ra ca; màn Công nhật và Nghiệp vụ phải hiển thị/cảnh báo người còn labor OPEN.
- Regression: time picker only / explicit start / explicit end / start without end / end after start / OPEN labor exit block / OPEN labor list / OPEN labor warning.
- Technical evidence Beta110: service run 33568634524 artifact 9824237674 PASS (`beta110_labor_time_range=PASS open_exit_block=PASS completed_range=PASS`); visual/PDA/API36 33569543281/9824551840 PASS; terminal 33574078129 + OTA/install/readback 9826069523 PASS.
- Technical receipt: `ops/beta110-technical-pass.json`.
- OWNER acceptance: PASS — OWNER xác nhận toàn bộ Beta110 OK ngày 2026-09-02 07:43 +07:00; receipt `ops/beta110-owner-acceptance.json`.
- UI follow-up: một số điểm chưa ưng chỉ mang tính giao diện, sẽ là scope chỉnh sửa mới; không phủ nhận acceptance hiện tại.
- Last verified: 0.4.2-beta.110 LIVE / terminal run 33574078129 / OWNER acceptance complete.
- Latest Beta111 re-verification: 0.4.2-beta.111 LIVE / source 03b37e5aa2726c273cc1e7c4a2161763bd3c4d2d / candidate 33586428789/9830403339 / Fast Check 33588839641 / Service 33588851239/9831120144 / visual+PDA+API36 33589199933/9831243286 + human PASS 41 screenshots / device 33590310367/9831531954 / runtime 33590505522 attempt2/9831607439 / terminal 33590747613 / publish 9831669563 / OTA-install-readback 9831721383 / final 9831726759 / SHA256 f67049067e600f4d8439d0ae088889f7b35df8b215e5432a2fcdd54f05f04a4f / size 14216181 / signer d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e; Stable/main/authority unchanged.

### MEAL-UI-NULL-001
- Status: ACTIVE_PASS
- Scope: Điểm danh / UI null-safe
- Rule: layout gọn, đủ thông tin; mọi dữ liệu thiếu hoặc JSON null hiển thị `-`; không thay đổi MEAL-DATE-001 và MEAL-WARN-001.
- Regression: compact layout / no visible null / dash for missing / current-day write only / warning preserved.
- Technical evidence Beta110: visual/PDA/API36 33569543281/9824551840 + human visual 41 screenshots 320x568/360x640/480x800 PASS; Fast Check 33569530461; service meal regression trong 33568634524 PASS; terminal 33574078129 PASS.
- Technical receipt: `ops/beta110-technical-pass.json`.
- OWNER acceptance: PASS — OWNER xác nhận toàn bộ Beta110 OK ngày 2026-09-02 07:43 +07:00; receipt `ops/beta110-owner-acceptance.json`.
- UI follow-up: một số điểm chưa ưng chỉ mang tính giao diện, sẽ là scope chỉnh sửa mới; không phủ nhận acceptance hiện tại.
- Last verified: 0.4.2-beta.110 LIVE / terminal run 33574078129 / OWNER acceptance complete.

### UI-COPY-DENSITY-001
- Status: ACTIVE_PASS
- Scope: nội dung chữ / mật độ màn nghiệp vụ
- Rule: không hiển thị text giải thích kiểu AI/OWNER hoặc hướng dẫn kỹ thuật thừa; ưu tiên nội dung nghiệp vụ và diện tích hiển thị.
- Regression: no owner/AI helper copy / compact document copy / compact labor copy / compact attendance copy.
- Technical evidence Beta110: Fast Check 33569530461 PASS; visual/PDA/API36 33569543281/9824551840 + human visual PASS; terminal 33574078129 PASS.
- Technical receipt: `ops/beta110-technical-pass.json`.
- OWNER acceptance: PASS — OWNER xác nhận toàn bộ Beta110 OK ngày 2026-09-02 07:43 +07:00; receipt `ops/beta110-owner-acceptance.json`.
- UI follow-up: một số điểm chưa ưng chỉ mang tính giao diện, sẽ là scope chỉnh sửa mới; không phủ nhận acceptance hiện tại.
- Last verified: 0.4.2-beta.110 LIVE / terminal run 33574078129 / OWNER acceptance complete.

### NAV-HISTORY-BACK-001
- Status: ACTIVE_PASS
- Scope: Điều hướng / system Back / edge swipe
- Rule: Back quay về đúng màn hình thực tế ngay trước đó trong navigation history. Ví dụ 1→2→3 thì Back 3→2→1; 5→3 thì Back 3→5. Không dùng parent cố định theo screenState.
- Regression: actual stack / same-screen rerender không tạo frame giả / root không bị swipe thoát.
- Technical evidence Beta111: 0.4.2-beta.111 LIVE / source 03b37e5aa2726c273cc1e7c4a2161763bd3c4d2d / candidate 33586428789/9830403339 / Fast Check 33588839641 / Service 33588851239/9831120144 / visual+PDA+API36 33589199933/9831243286 + human PASS 41 screenshots / device 33590310367/9831531954 / runtime 33590505522 attempt2/9831607439 / terminal 33590747613 / publish 9831669563 / OTA-install-readback 9831721383 / final 9831726759 / SHA256 f67049067e600f4d8439d0ae088889f7b35df8b215e5432a2fcdd54f05f04a4f / size 14216181 / signer d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e; Stable/main/authority unchanged.
- Technical receipt: `ops/beta111-technical-pass.json`.
- OWNER acceptance: PENDING — chờ checklist Beta111 1–7.
- OWNER acceptance Beta111: OWNER_ITEM_2_OK_2026-09-02T12:44+07:00; receipt `ops/beta111-owner-acceptance-partial.json`.

### UI-REVIEW-WARNING-001
- Status: ACTIVE_PASS
- Scope: Rà soát vào-ra / cảnh báo
- Rule: các ô rà soát và cảnh báo liên quan đồng nhất chiều cao, typography, radius/stroke và ngôn ngữ màu theo mức độ.
- Implementation Beta112: dùng chung `ReviewAlertUi`; fixed 42dp / 10.5sp / radius 10dp / stroke 2dp; cảnh báo cùng đỏ canonical, rà soát đủ xanh canonical; loại bỏ min-size/font-padding/state animator mặc định gây lệch Android Button.
- Regression: `qa/beta112_review_warning_regression.md` + `tools/beta112_review_warning_contract.py` + runtime flag `review_warning_shared_style_beta112`; giữ toàn bộ Beta111 owner-scope regressions.
- Technical evidence Beta112: candidate 33596529877/9833670469; SHA256 d5de4fea496a1be4926f3acc49f82fb60eb9065de694e075251ca493ce298e76; Fast Check 33612134466 PASS; visual/PDA/API36 33597157250/9833913262 PASS, 42 screenshots + human PASS 320x568/360x640/480x800; device 33611415963/9839191113 PASS; runtime 33612695867/9839670809 PASS; terminal publish/OTA/install/readback/finalize 33612994423 PASS; GitHub Release asset 540918700 exact bytes; Stable/main/signer/authority unchanged.
- Auth parity recovery during pre-OTA: 33612548361/9839580952 PASS; no password rotation, no D1 mutation, no session revocation; prior runtime failure 33611682634 superseded.
- Technical receipt: `ops/beta112-technical-pass.json`.
- OWNER acceptance: PASS — OWNER xác nhận `1 OK` ngày 2026-09-02 18:44 +07:00; receipt `ops/beta112-owner-acceptance.json`.
- Last verified: 0.4.2-beta.112 LIVE / OWNER acceptance complete.

### LABOR-EXACT-SESSION-002
- Status: ACTIVE_PASS
- Scope: Công nhật / Ra ca
- Parent: LABOR-TIME-RANGE-001 ACTIVE_PASS giữ nguyên.
- Rule: Service exact session/business_date/labor_id là authority; cache local không quyết định start/finish/exit. Bộ chọn giờ-phút là wheel dọc không wrap. Cho phép chọn BĐ+KT cùng lần hoặc chỉ BĐ rồi KT sau; giờ có thể sửa theo đường xác nhận. Ra ca gặp labor OPEN mở thẳng đúng labor của đúng session. Danh sách theo ngày có cả pending/done.
- Regression: exact current/old active session / stale local / start-only / start+end / edit OPEN / correction COMPLETED / exit redirect / daily list / LABOR_NOT_OPEN + ATTENDANCE_NOT_ACTIVE stale regression.
- Technical evidence Beta111: 0.4.2-beta.111 LIVE / source 03b37e5aa2726c273cc1e7c4a2161763bd3c4d2d / candidate 33586428789/9830403339 / Fast Check 33588839641 / Service 33588851239/9831120144 / visual+PDA+API36 33589199933/9831243286 + human PASS 41 screenshots / device 33590310367/9831531954 / runtime 33590505522 attempt2/9831607439 / terminal 33590747613 / publish 9831669563 / OTA-install-readback 9831721383 / final 9831726759 / SHA256 f67049067e600f4d8439d0ae088889f7b35df8b215e5432a2fcdd54f05f04a4f / size 14216181 / signer d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e; Stable/main/authority unchanged.
- Technical receipt: `ops/beta111-technical-pass.json`.
- OWNER acceptance: PENDING — chờ checklist Beta111 1–7.
- OWNER acceptance Beta111: OWNER_ITEMS_3_4_5_OK_2026-09-02T12:44+07:00; receipt `ops/beta111-owner-acceptance-partial.json`.

### HISTORY-DELETE-CANONICAL-001
- Status: ACTIVE_PASS
- Scope: Lịch sử
- Rule: chỉ event canonical Service được gửi xóa; local-only không gửi; target-not-found của deferred delete là terminal cleanup để không lặp 404.
- Regression: canonical delete / local-only fence / terminal 404 / no retry loop.
- Technical evidence Beta111: 0.4.2-beta.111 LIVE / source 03b37e5aa2726c273cc1e7c4a2161763bd3c4d2d / candidate 33586428789/9830403339 / Fast Check 33588839641 / Service 33588851239/9831120144 / visual+PDA+API36 33589199933/9831243286 + human PASS 41 screenshots / device 33590310367/9831531954 / runtime 33590505522 attempt2/9831607439 / terminal 33590747613 / publish 9831669563 / OTA-install-readback 9831721383 / final 9831726759 / SHA256 f67049067e600f4d8439d0ae088889f7b35df8b215e5432a2fcdd54f05f04a4f / size 14216181 / signer d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e; Stable/main/authority unchanged.
- Technical receipt: `ops/beta111-technical-pass.json`.
- OWNER acceptance: PENDING — chờ checklist Beta111 1–7.
- OWNER acceptance Beta111: OWNER_ITEM_7_OK_2026-09-02T12:44+07:00; receipt `ops/beta111-owner-acceptance-partial.json`.

### DOCUMENT-BATCH-MODE-TICK-002
- Status: ACTIVE_PASS
- Scope: Quản lý biên bản
- Parent: DOCUMENT-BATCH-001 ACTIVE_PASS giữ nguyên semantics grouping.
- Rule: `Một biên bản nhiều trang` và `Nhiều biên bản` dùng lựa chọn dạng tích loại trừ nhau, không Spinner/select.
- Regression: default multipage / multi-document / exclusive tick / single image disabled / grouping unchanged.
- Technical evidence Beta111: 0.4.2-beta.111 LIVE / source 03b37e5aa2726c273cc1e7c4a2161763bd3c4d2d / candidate 33586428789/9830403339 / Fast Check 33588839641 / Service 33588851239/9831120144 / visual+PDA+API36 33589199933/9831243286 + human PASS 41 screenshots / device 33590310367/9831531954 / runtime 33590505522 attempt2/9831607439 / terminal 33590747613 / publish 9831669563 / OTA-install-readback 9831721383 / final 9831726759 / SHA256 f67049067e600f4d8439d0ae088889f7b35df8b215e5432a2fcdd54f05f04a4f / size 14216181 / signer d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e; Stable/main/authority unchanged.
- Technical receipt: `ops/beta111-technical-pass.json`.
- OWNER acceptance: PENDING — chờ checklist Beta111 1–7.
- OWNER acceptance Beta111: OWNER_ITEM_6_OK_2026-09-02T12:44+07:00; receipt `ops/beta111-owner-acceptance-partial.json`.


### CHANGELOG-CURRENT-VERSION-001
- Status: LOCKED_REQUIREMENT_PENDING_FIX
- Scope: Cài đặt / thông tin phiên bản
- Rule: changelog hiển thị trong app phải khớp chính xác versionName đang chạy; bump Beta mà chưa cập nhật ReleaseNotes phải fail build.
- Regression: Beta versionName / ReleaseNotes.VERSION_NAME exact match + verifyBetaReleaseNotes preBuild gate.
- Regression case: `qa/beta113_owner_scope_regression.md` + `tools/beta113_owner_scope_contract.py`.
- OWNER acceptance: PENDING Beta113.

### ADMIN-AUDIT-PASSWORD-001
- Status: LOCKED_REQUIREMENT_PENDING_FIX
- Scope: Tài khoản / đổi mật khẩu / lịch sử
- Rule: đổi mật khẩu thành công phải ghi audit canonical `change_password`; durable outbox routing `admin_audit` không được thay thế business action; tuyệt đối không đưa password/proof/verifier vào audit.
- Regression: password mutation success + admin audit canonical + no sensitive audit payload + no false sync failure.
- Regression case: `qa/beta113_owner_scope_regression.md` + `tools/beta113_owner_scope_contract.py`.
- OWNER acceptance: PENDING Beta113.

### HISTORY-SUPERADMIN-CLEANUP-002
- Status: LOCKED_REQUIREMENT_PENDING_FIX
- Parent: HISTORY-DELETE-CANONICAL-001 ACTIVE_PASS.
- Scope: Lịch sử / SUPERADMIN
- Rule: SUPERADMIN được xóa mọi thẻ lịch sử bằng xác nhận bảo mật hiện hành. Event canonical dùng Service tombstone; local terminal/không thể đồng bộ xóa cục bộ. Xóa thẻ lịch sử không được âm thầm hủy business mutation còn pending.
- Regression: canonical tombstone / local terminal cleanup / pending outbox preserved / HHmm ±2 hoặc mật khẩu SUPERADMIN.
- Regression case: `qa/beta113_owner_scope_regression.md` + `tools/beta113_owner_scope_contract.py`.
- OWNER acceptance: PENDING Beta113.

### LABOR-MULTI-INTERVAL-003
- Status: LOCKED_REQUIREMENT_PENDING_FIX
- Parent: LABOR-EXACT-SESSION-002 ACTIVE_PASS.
- Scope: Công nhật / nhiều khoảng trong một phiên
- Rule: một phiên có thể có nhiều khoảng công nhật riêng với labor_id riêng; tối đa một khoảng OPEN; không chồng thời gian; không tự gộp; sửa/kết thúc đúng labor_id; mốc thời gian phải nằm trong biên phiên và không ở tương lai; toàn bộ khoảng phải hiển thị.
- Regression: sequential intervals / one-open guard / overlap guard / attendance bounds / future guard / exact edit-finish / all intervals visible.
- Regression case: `qa/beta113_owner_scope_regression.md` + `tools/beta113_owner_scope_contract.py`.
- OWNER acceptance: PENDING Beta113.

### UI-DATA-DATE-SELECT-001
- Status: LOCKED_REQUIREMENT_PENDING_FIX
- Scope: lịch chọn ngày để xem dữ liệu
- Rule: lịch dùng để hiển thị dữ liệu chỉ cho chọn ngày thực sự có dữ liệu; ngày trống vẫn thấy nhưng mờ và disabled. Lịch dùng để sửa/thay đổi ngày giờ nghiệp vụ không áp dụng giới hạn này.
- Regression: Report/History/Labor data-only dates + edit-date exemption.
- Regression case: `qa/beta113_owner_scope_regression.md` + `tools/beta113_owner_scope_contract.py`.
- OWNER acceptance: PENDING Beta113.

### UI-EMPLOYEE-SCAN-ROSTER-001
- Status: LOCKED_REQUIREMENT_PENDING_FIX
- Scope: quét nhân viên / rà soát ca / danh sách nhân sự
- Rule: ô scan giữ kích thước nhưng nổi bật hơn; danh sách nhân sự hôm nay hiển thị trực tiếp dưới scan; khi đã scan thì thông tin nhân viên/phiên ở trên danh sách chung. Ô rà soát chỉ phục vụ số vào-ra và danh sách chưa ra + nút Ra ca.
- Regression: scan emphasis / inline roster / scanned-session-first / reconciliation pending-only.
- Regression case: `qa/beta113_owner_scope_regression.md` + `tools/beta113_owner_scope_contract.py`.
- OWNER acceptance: PENDING Beta113.

### UI-FORM-CONSISTENCY-002
- Status: LOCKED_REQUIREMENT_PENDING_FIX
- Parent: UI-REVIEW-WARNING-001 ACTIVE_PASS giữ nguyên component cảnh báo.
- Scope: giao diện chung / form / select
- Rule: form controls dùng hierarchy tiêu đề–giá trị rõ ràng, common radius/stroke/kích thước thống nhất; MNV scan được phép nhấn mạnh 2dp có chủ đích; ReviewAlertUi Beta112 giữ nguyên 42dp/10.5sp/radius10/stroke2 và semantic màu đã OWNER chốt.
- Regression: common outline / spinner hierarchy / searchable PDA select hierarchy / locked ReviewAlertUi unchanged / visual matrix.
- Regression case: `qa/beta113_owner_scope_regression.md` + `tools/beta113_owner_scope_contract.py`.
- OWNER acceptance: PENDING Beta113.


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

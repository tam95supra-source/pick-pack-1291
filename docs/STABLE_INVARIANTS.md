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

### CHANGELOG-CURRENT-VERSION-001
- Status: ACTIVE_PASS
- Scope: Cài đặt / thông tin phiên bản
- Rule: changelog hiển thị trong app phải khớp chính xác versionName đang chạy; bump Beta mà chưa cập nhật ReleaseNotes phải fail build.
- Regression: Beta versionName / ReleaseNotes.VERSION_NAME exact match + verifyBetaReleaseNotes preBuild gate.
- Regression case: `qa/beta113_owner_scope_regression.md` + `tools/beta113_owner_scope_contract.py`.
- Technical evidence Beta114: source `5686da2cc6fdb2bf845456bda9e703eb68e9f1f0`; candidate `33691947969/9870515268`; Fast Check `33698830085` PASS; visual/PDA/API36 `33698830042/9872907916` PASS; device `33697808957/9872457667` PASS; runtime `33698019451/9872504979` PASS; terminal `33699803398` PASS; publish `9873117701`; OTA/install/readback `9873169722`; final `9873176752`; SHA256 `cc611efc72a3cd0af413f316b6182adb281d398c189f5bb9d613235722b296bd`; size `14232565`; Stable/main/signer/authority unchanged.
- Technical receipt: `ops/beta114-technical-pass.json`.
- OWNER acceptance: PASS — OWNER 2026-09-03 08:06 +07:00.
- Owner receipt: `ops/beta114-owner-acceptance-partial.json`.

### ADMIN-AUDIT-PASSWORD-001
- Status: ACTIVE_PASS
- Scope: Tài khoản / đổi mật khẩu / lịch sử
- Rule: đổi mật khẩu thành công phải ghi audit canonical `change_password`; durable outbox routing `admin_audit` không được thay thế business action; tuyệt đối không đưa password/proof/verifier vào audit.
- Regression: password mutation success + admin audit canonical + no sensitive audit payload + no false sync failure.
- Regression case: `qa/beta113_owner_scope_regression.md` + `tools/beta113_owner_scope_contract.py`.
- Technical evidence Beta114: source `5686da2cc6fdb2bf845456bda9e703eb68e9f1f0`; candidate `33691947969/9870515268`; Fast Check `33698830085` PASS; visual/PDA/API36 `33698830042/9872907916` PASS; device `33697808957/9872457667` PASS; runtime `33698019451/9872504979` PASS; terminal `33699803398` PASS; publish `9873117701`; OTA/install/readback `9873169722`; final `9873176752`; SHA256 `cc611efc72a3cd0af413f316b6182adb281d398c189f5bb9d613235722b296bd`; size `14232565`; Stable/main/signer/authority unchanged.
- Technical receipt: `ops/beta114-technical-pass.json`.
- OWNER acceptance: PASS — OWNER 2026-09-03 08:06 +07:00.
- Owner receipt: `ops/beta114-owner-acceptance-partial.json`.

### HISTORY-SUPERADMIN-CLEANUP-002
- Status: ACTIVE_PASS
- Parent: HISTORY-DELETE-CANONICAL-001 ACTIVE_PASS.
- Scope: Lịch sử / SUPERADMIN
- Rule: SUPERADMIN được xóa mọi thẻ lịch sử bằng xác nhận bảo mật hiện hành. Event canonical dùng Service tombstone; local terminal/không thể đồng bộ xóa cục bộ. Xóa thẻ lịch sử không được âm thầm hủy business mutation còn pending.
- Regression: canonical tombstone / local terminal cleanup / pending outbox preserved / HHmm ±2 hoặc mật khẩu SUPERADMIN.
- Regression case: `qa/beta113_owner_scope_regression.md` + `tools/beta113_owner_scope_contract.py`.
- Technical evidence Beta114: source `5686da2cc6fdb2bf845456bda9e703eb68e9f1f0`; candidate `33691947969/9870515268`; Fast Check `33698830085` PASS; visual/PDA/API36 `33698830042/9872907916` PASS; device `33697808957/9872457667` PASS; runtime `33698019451/9872504979` PASS; terminal `33699803398` PASS; publish `9873117701`; OTA/install/readback `9873169722`; final `9873176752`; SHA256 `cc611efc72a3cd0af413f316b6182adb281d398c189f5bb9d613235722b296bd`; size `14232565`; Stable/main/signer/authority unchanged.
- Technical receipt: `ops/beta114-technical-pass.json`.
- OWNER acceptance: PASS — OWNER 2026-09-03 08:06 +07:00.
- Owner receipt: `ops/beta114-owner-acceptance-partial.json`.

### UI-EMPLOYEE-SCAN-ROSTER-001
- Status: ACTIVE_PASS
- Scope: quét nhân viên / rà soát ca / danh sách nhân sự
- Rule: ô scan giữ kích thước nhưng nổi bật hơn; danh sách nhân sự hôm nay hiển thị trực tiếp dưới scan; khi đã scan thì thông tin nhân viên/phiên ở trên danh sách chung. Ô rà soát chỉ phục vụ số vào-ra và danh sách chưa ra + nút Ra ca.
- Regression: scan emphasis / inline roster / scanned-session-first / reconciliation pending-only.
- Regression case: `qa/beta113_owner_scope_regression.md` + `tools/beta113_owner_scope_contract.py`.
- Technical evidence Beta114: source `5686da2cc6fdb2bf845456bda9e703eb68e9f1f0`; candidate `33691947969/9870515268`; Fast Check `33698830085` PASS; visual/PDA/API36 `33698830042/9872907916` PASS; device `33697808957/9872457667` PASS; runtime `33698019451/9872504979` PASS; terminal `33699803398` PASS; publish `9873117701`; OTA/install/readback `9873169722`; final `9873176752`; SHA256 `cc611efc72a3cd0af413f316b6182adb281d398c189f5bb9d613235722b296bd`; size `14232565`; Stable/main/signer/authority unchanged.
- Technical receipt: `ops/beta114-technical-pass.json`.
- OWNER acceptance: PASS — OWNER 2026-09-03 08:06 +07:00.
- Owner receipt: `ops/beta114-owner-acceptance-partial.json`.

### LABOR-SCAN-PINNED-004
- Status: ACTIVE_PASS
- Scope: Công nhật / scan MNV / layout.
- Rule: ô scan/nhập MNV luôn ở trên danh sách công nhật và vẫn hiện khi đang xem thông tin công nhật của một nhân sự; không thay bằng nút "Mã nhân viên KHÁC".
- Regression: scan_above_list / scan_visible_in_context / no_other_employee_substitute.
- Technical evidence: Beta114 technical PASS.
- OWNER acceptance: PASS — checklist item 5, 2026-09-03 08:06 +07:00.
- Owner receipt: `ops/beta114-owner-acceptance-partial.json`.

### UI-FORM-BASE-CONSISTENCY-003
- Status: ACTIVE_PASS
- Scope: common form base / ReviewAlertUi.
- Rule: bố cục/outline form chung đã chốt và ReviewAlertUi Beta112 phải giữ nguyên. Riêng hierarchy của select chưa được coi là PASS cho tới khi OWNER nghiệm thu item 7.
- Regression: common_outline_preserved / review_alert_unchanged / select_semantics_not_relaxed.
- Technical evidence: Beta114 technical PASS.
- OWNER acceptance: PASS — checklist item 10, 2026-09-03 08:06 +07:00.
- Owner receipt: `ops/beta114-owner-acceptance-partial.json`.


### OLD-SESSION-BULK-EXIT-001
- Status: ACTIVE_PASS
- Scope: Cảnh báo phiên cũ / SUPERADMIN / Ra ca tất cả hợp lệ
- Rule: `Ra ca tất cả hợp lệ` phải gọi trực tiếp Service authority; xử lý bounded/idempotent theo lô nhỏ; một phiên lỗi không được làm treo toàn lô; labor OPEN phải skip; canonical commitMutation/audit giữ nguyên.
- Regression: direct Service route + bounded batch + idempotency + failure isolation + labor skip + remaining readback + Stable/authority unchanged.
- Regression case: `tools/beta120_bulk_exit_contract.py`.
- Technical evidence: Beta120 LIVE; candidate 33874862142/9937580926; Fast Check 33874862122 PASS; Service + visual/PDA/API36 33876606829 PASS; device/discovery 33895538590/9945644548 PASS; runtime 33895822870/9945717299 PASS; domain 33896047850/9945767325 PASS; terminal 33896192267 publish exact bytes + OTA install/open/readback + finalize PASS; APK SHA256 04d9f4b88e6ff038766357402f7f5831de67649087c839f922897042120b8ef8 size 14429173 signer d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e; Stable/main/authority unchanged.
- OWNER acceptance: PASS — OWNER xác nhận phần `Ra ca` đã OK ngày 2026-09-04.
- Owner receipt: `ops/beta120-owner-acceptance.json`.
- Last verified: `0.4.2-beta.120` LIVE.

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





### LABOR-MULTI-INTERVAL-003
- Status: ACTIVE_PASS
- Parent: LABOR-EXACT-SESSION-002 ACTIVE_PASS.
- Scope: Công nhật / nhiều khoảng trong một phiên
- Rule: một phiên điểm danh có nhiều khoảng công nhật riêng theo `labor_id`; tối đa một khoảng OPEN; các khoảng không chồng/không tự gộp. Giờ bắt đầu không ở tương lai/không trước giờ vào ca. Giờ kết thúc được phép nhập trước trong tương lai tới cuối ca cố định (Ca 1 14:00, Ca HC 17:00, Ca 2 22:00); nếu NLĐ làm quá ca thì chỉ được kéo dài theo thời gian thực tế phiên và không vượt giờ ra thực tế. Sửa/kết thúc đúng `labor_id`. Tạo/kết thúc hàng loạt phải xác nhận mật khẩu thời gian thực.
- Regression: multiple_intervals / one_open / no_overlap / no_auto_merge / exact_labor_id / start_not_future / shift_end_cap / overtime_elapsed_or_exit_cap / deduct_support_exact / grouped_employee_card / batch_create_filters / batch_finish_filters / password_gate.
- Regression case: `qa/beta113_owner_scope_regression.md` + `tools/beta113_owner_scope_contract.py`.
- Technical evidence: 0.4.2-beta.115 LIVE; APK candidate source 3f343ea1be0dbace5df995e4c81e1cdca9defd24; service source 429c39f82aacba19351351234f7f66a8d3b655f1; candidate 33703823187/9874569505; visual+human 33705116149/9875061341; device regression 33705707420/9875164876; service 33707525071/9875965938; runtime 33708224737/9876009359; Fast Check 33708743727 PASS; terminal 33709045943; publish 9876309366; OTA/install/open/readback 9876353676; final 9876357969; SHA256 af2c267e2101223387fdf4feb86b6ae315fe17b44c09d89c9f6166a8a73d49e5; size 14281717; signer d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e; Stable/main/signer/authority unchanged.
- Owner receipt: `ops/beta115-owner-acceptance.json`.
- Last verified: 0.4.2-beta.115 LIVE / terminal run 33709045943 / OWNER acceptance complete 2026-09-03T10:08:00+07:00.
- OWNER acceptance: PASS — OWNER xác nhận toàn bộ checklist Beta115 OK lúc 2026-09-03T10:08:00+07:00.

### UI-DATA-DATE-SELECT-001
- Status: ACTIVE_PASS
- Scope: lịch chọn ngày để xem dữ liệu
- Rule: lịch chỉ để xem dữ liệu bật các ngày có dữ liệu và luôn bật ngày HÔM NAY kể cả chưa có dữ liệu; các ngày trống khác vẫn mờ/disabled. Lịch sửa/chỉnh ngày giờ nghiệp vụ không bị giới hạn.
- Regression: report/history/labor/điểm danh / today_always_selectable / other_empty_dim_disabled / edit-date exemption.
- Regression case: `qa/beta113_owner_scope_regression.md` + `tools/beta113_owner_scope_contract.py`.
- Technical evidence: 0.4.2-beta.115 LIVE; APK candidate source 3f343ea1be0dbace5df995e4c81e1cdca9defd24; service source 429c39f82aacba19351351234f7f66a8d3b655f1; candidate 33703823187/9874569505; visual+human 33705116149/9875061341; device regression 33705707420/9875164876; service 33707525071/9875965938; runtime 33708224737/9876009359; Fast Check 33708743727 PASS; terminal 33709045943; publish 9876309366; OTA/install/open/readback 9876353676; final 9876357969; SHA256 af2c267e2101223387fdf4feb86b6ae315fe17b44c09d89c9f6166a8a73d49e5; size 14281717; signer d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e; Stable/main/signer/authority unchanged.
- Owner receipt: `ops/beta115-owner-acceptance.json`.
- Last verified: 0.4.2-beta.115 LIVE / terminal run 33709045943 / OWNER acceptance complete 2026-09-03T10:08:00+07:00.
- OWNER acceptance: PASS — OWNER xác nhận toàn bộ checklist Beta115 OK lúc 2026-09-03T10:08:00+07:00.


### UI-FORM-CONSISTENCY-002
- Status: ACTIVE_PASS
- Parent: UI-REVIEW-WARNING-001 ACTIVE_PASS giữ nguyên component cảnh báo.
- Scope: giao diện chung / form / select
- Rule: mọi select phải theo cùng hierarchy: nhãn nhỏ/muted, giá trị đang chọn nổi bật/bold, danh sách lựa chọn nhẹ hơn/normal; bao gồm select lý do không vào ca và các catalog select. Base form outline đã OWNER chốt và ReviewAlertUi Beta112 phải giữ nguyên.
- Regression: all_selects_canonical / reason_select_canonical / spinner hierarchy / PDA searchable select hierarchy / base outline preserved / locked ReviewAlertUi unchanged.
- Regression case: `qa/beta113_owner_scope_regression.md` + `tools/beta113_owner_scope_contract.py`.
- Technical evidence: 0.4.2-beta.115 LIVE; APK candidate source 3f343ea1be0dbace5df995e4c81e1cdca9defd24; service source 429c39f82aacba19351351234f7f66a8d3b655f1; candidate 33703823187/9874569505; visual+human 33705116149/9875061341; device regression 33705707420/9875164876; service 33707525071/9875965938; runtime 33708224737/9876009359; Fast Check 33708743727 PASS; terminal 33709045943; publish 9876309366; OTA/install/open/readback 9876353676; final 9876357969; SHA256 af2c267e2101223387fdf4feb86b6ae315fe17b44c09d89c9f6166a8a73d49e5; size 14281717; signer d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e; Stable/main/signer/authority unchanged.
- Owner receipt: `ops/beta115-owner-acceptance.json`.
- Last verified: 0.4.2-beta.115 LIVE / terminal run 33709045943 / OWNER acceptance complete 2026-09-03T10:08:00+07:00.
- OWNER acceptance: PASS — OWNER xác nhận toàn bộ checklist Beta115 OK lúc 2026-09-03T10:08:00+07:00.


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


## 4B. Beta116 — TECHNICAL_PASS_AWAITING_OWNER

Technical receipt: `ops/beta116-technical-pass.json`. Regression: `qa/beta116_owner_scope_regression.md` + `tools/beta116_owner_scope_contract.py`. Chỉ chuyển ACTIVE_PASS sau OWNER xác nhận từng mục.

### DOCUMENT-DRAFT-NOTE-UX-003
- Status: ACTIVE_PASS
- Scope: document-draft-note-ui
- Rule: Biên bản dùng icon CRUD; trước tải lên cho phép chọn/xóa/chọn tất cả ảnh nháp và lưu chú thích riêng từng ảnh/trang xuyên draft→pending→upload→Service.
- Regression: icon_crud / draft_multi_select / select_all / delete_selected_before_upload / per_page_note_durable.
- Technical evidence: 0.4.2-beta.116 Technical PASS/LIVE; candidate source cf01dab16e1c62091561ca008a355a8f49326581; candidate 33767353642/9898290631; Service 33767353642/9898616640; visual+PDA/API36 33774026289/9901071098 + human PASS 43 screenshots 320x568/360x640/480x800; Beta Auth 33776285435/9902148937; device 33778316587/9902571477; runtime 33778605857/9902663700; domain 33778957345/9902758766; Fast Check 33780103022 PASS; publish 33780057070/9903236359; OTA install/open/readback 33780057070/9903336912; SHA256 a346d4554e07fc37552c9d8876179860677fc93923a3bd42f9b3f97f5e11f235; size 14347253; signer d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e; Stable/main/authority unchanged.
- OWNER acceptance: PENDING — checklist Beta116 item 1/11.

### DOCUMENT-GROUP-VIEWER-004
- Status: ACTIVE_PASS
- Scope: document-group-viewer
- Rule: Nhóm ảnh biên bản hỗ trợ vuốt giữa trang và pinch zoom; viewer không làm đổi semantics grouping đã ACTIVE_PASS.
- Regression: group_viewer / swipe_pages / pinch_zoom / grouping_semantics_unchanged.
- Technical evidence: 0.4.2-beta.116 Technical PASS/LIVE; candidate source cf01dab16e1c62091561ca008a355a8f49326581; candidate 33767353642/9898290631; Service 33767353642/9898616640; visual+PDA/API36 33774026289/9901071098 + human PASS 43 screenshots 320x568/360x640/480x800; Beta Auth 33776285435/9902148937; device 33778316587/9902571477; runtime 33778605857/9902663700; domain 33778957345/9902758766; Fast Check 33780103022 PASS; publish 33780057070/9903236359; OTA install/open/readback 33780057070/9903336912; SHA256 a346d4554e07fc37552c9d8876179860677fc93923a3bd42f9b3f97f5e11f235; size 14347253; signer d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e; Stable/main/authority unchanged.
- OWNER acceptance: PENDING — checklist Beta116 item 2/11.

### PDA-SERIAL-DERIVE-002
- Status: ACTIVE_PASS
- Scope: pda-resource-serial
- Rule: Tài nguyên PDA tự suy ra 5 số cuối Seri từ mã/tên canonical; không nhập tay và key PDA không chứa khoảng trắng.
- Regression: derive_last5 / no_manual_serial / no_whitespace_key.
- Technical evidence: 0.4.2-beta.116 Technical PASS/LIVE; candidate source cf01dab16e1c62091561ca008a355a8f49326581; candidate 33767353642/9898290631; Service 33767353642/9898616640; visual+PDA/API36 33774026289/9901071098 + human PASS 43 screenshots 320x568/360x640/480x800; Beta Auth 33776285435/9902148937; device 33778316587/9902571477; runtime 33778605857/9902663700; domain 33778957345/9902758766; Fast Check 33780103022 PASS; publish 33780057070/9903236359; OTA install/open/readback 33780057070/9903336912; SHA256 a346d4554e07fc37552c9d8876179860677fc93923a3bd42f9b3f97f5e11f235; size 14347253; signer d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e; Stable/main/authority unchanged.
- OWNER acceptance: PENDING — checklist Beta116 item 3/11.

### REPORT-LABOR-DEDUCTION-002
- Status: TECHNICAL_PASS_AWAITING_OWNER
- Scope: staff-report-labor
- Rule: Báo cáo nhân sự giữ Tổng nhân sự trước khấu trừ, tách Khấu trừ công nhật, Picker thực tế và Packer thực tế.
- Regression: gross_total_preserved / labor_deduction_separate / picker_actual / packer_actual.
- Technical evidence: 0.4.2-beta.116 Technical PASS/LIVE; candidate source cf01dab16e1c62091561ca008a355a8f49326581; candidate 33767353642/9898290631; Service 33767353642/9898616640; visual+PDA/API36 33774026289/9901071098 + human PASS 43 screenshots 320x568/360x640/480x800; Beta Auth 33776285435/9902148937; device 33778316587/9902571477; runtime 33778605857/9902663700; domain 33778957345/9902758766; Fast Check 33780103022 PASS; publish 33780057070/9903236359; OTA install/open/readback 33780057070/9903336912; SHA256 a346d4554e07fc37552c9d8876179860677fc93923a3bd42f9b3f97f5e11f235; size 14347253; signer d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e; Stable/main/authority unchanged.
- OWNER acceptance: PENDING — checklist Beta116 item 4/11.

### DROP-RECEIVE-CRUD-001
- Status: ACTIVE_PASS
- Scope: drop-receive
- Rule: Nhận hàng rớt có icon CRUD, DO/Số kiện cùng dòng, danh sách chi tiết, chọn nhiều/chọn tất cả và xóa selected qua canonical password gate.
- Regression: crud_icons / do_package_inline / list_detail / multi_select / delete_selected_password.
- Technical evidence: 0.4.2-beta.116 Technical PASS/LIVE; candidate source cf01dab16e1c62091561ca008a355a8f49326581; candidate 33767353642/9898290631; Service 33767353642/9898616640; visual+PDA/API36 33774026289/9901071098 + human PASS 43 screenshots 320x568/360x640/480x800; Beta Auth 33776285435/9902148937; device 33778316587/9902571477; runtime 33778605857/9902663700; domain 33778957345/9902758766; Fast Check 33780103022 PASS; publish 33780057070/9903236359; OTA install/open/readback 33780057070/9903336912; SHA256 a346d4554e07fc37552c9d8876179860677fc93923a3bd42f9b3f97f5e11f235; size 14347253; signer d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e; Stable/main/authority unchanged.
- OWNER acceptance: PENDING — checklist Beta116 item 5/11.

### LOCAL-FIRST-RECONCILE-002
- Status: TECHNICAL_PASS_AWAITING_OWNER
- Scope: local-first-reconcile
- Rule: Đổi/Trả PDA và Công nhật hiển thị local trước rồi reconcile nền; chi tiết Công nhật vẫn lấy authority theo exact Service session, không dùng local projection làm business truth.
- Regression: local_first_render / background_reconcile / exact_service_session / no_local_authority_override.
- Technical evidence: 0.4.2-beta.116 Technical PASS/LIVE; candidate source cf01dab16e1c62091561ca008a355a8f49326581; candidate 33767353642/9898290631; Service 33767353642/9898616640; visual+PDA/API36 33774026289/9901071098 + human PASS 43 screenshots 320x568/360x640/480x800; Beta Auth 33776285435/9902148937; device 33778316587/9902571477; runtime 33778605857/9902663700; domain 33778957345/9902758766; Fast Check 33780103022 PASS; publish 33780057070/9903236359; OTA install/open/readback 33780057070/9903336912; SHA256 a346d4554e07fc37552c9d8876179860677fc93923a3bd42f9b3f97f5e11f235; size 14347253; signer d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e; Stable/main/authority unchanged.
- OWNER acceptance: PENDING — checklist Beta116 item 6/11.

### ATTENDANCE-QR-FILTER-002
- Status: ACTIVE_PASS
- Scope: attendance-qr-filter
- Rule: Điểm danh và QR vào/ra có bộ lọc Ca/NCC/Vị trí; Điểm danh có tìm MNV/họ tên và ô scan nổi bật; click semantics danh sách ca giữ canonical Beta115.
- Regression: shift_filter / ncc_filter / position_filter / employee_search / scan_emphasis / canonical_click_semantics.
- Technical evidence: 0.4.2-beta.116 Technical PASS/LIVE; candidate source cf01dab16e1c62091561ca008a355a8f49326581; candidate 33767353642/9898290631; Service 33767353642/9898616640; visual+PDA/API36 33774026289/9901071098 + human PASS 43 screenshots 320x568/360x640/480x800; Beta Auth 33776285435/9902148937; device 33778316587/9902571477; runtime 33778605857/9902663700; domain 33778957345/9902758766; Fast Check 33780103022 PASS; publish 33780057070/9903236359; OTA install/open/readback 33780057070/9903336912; SHA256 a346d4554e07fc37552c9d8876179860677fc93923a3bd42f9b3f97f5e11f235; size 14347253; signer d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e; Stable/main/authority unchanged.
- OWNER acceptance: PENDING — checklist Beta116 item 7/11.

### LABOR-FIXED-ROLE-REVIEW-005
- Status: ACTIVE_PASS
- Scope: labor-role-review
- Rule: Công nhật có cảnh báo kiểm tra các vị trí cố định Tổ trưởng/Kéo hàng/5S nhưng không tự sinh công nhật; nút tạo/kết thúc nhanh giữ trọng số UI đã chốt và exact-session authority.
- Regression: fixed_role_warning / no_auto_labor / quick_button_weight / exact_session_authority.
- Technical evidence: 0.4.2-beta.116 Technical PASS/LIVE; candidate source cf01dab16e1c62091561ca008a355a8f49326581; candidate 33767353642/9898290631; Service 33767353642/9898616640; visual+PDA/API36 33774026289/9901071098 + human PASS 43 screenshots 320x568/360x640/480x800; Beta Auth 33776285435/9902148937; device 33778316587/9902571477; runtime 33778605857/9902663700; domain 33778957345/9902758766; Fast Check 33780103022 PASS; publish 33780057070/9903236359; OTA install/open/readback 33780057070/9903336912; SHA256 a346d4554e07fc37552c9d8876179860677fc93923a3bd42f9b3f97f5e11f235; size 14347253; signer d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e; Stable/main/authority unchanged.
- OWNER acceptance: PENDING — checklist Beta116 item 8/11.

### ADMIN-OTHER-PASSWORD-003
- Status: ACTIVE_PASS
- Scope: admin-password
- Rule: SUPERADMIN đổi mật khẩu từng tài khoản sau privileged re-auth; thao tác một tài khoản mỗi lần và verifier generation vẫn ở canonical BetaApiClient.
- Regression: superadmin_only / one_account_at_time / privileged_reauth / canonical_verifier.
- Technical evidence: 0.4.2-beta.116 Technical PASS/LIVE; candidate source cf01dab16e1c62091561ca008a355a8f49326581; candidate 33767353642/9898290631; Service 33767353642/9898616640; visual+PDA/API36 33774026289/9901071098 + human PASS 43 screenshots 320x568/360x640/480x800; Beta Auth 33776285435/9902148937; device 33778316587/9902571477; runtime 33778605857/9902663700; domain 33778957345/9902758766; Fast Check 33780103022 PASS; publish 33780057070/9903236359; OTA install/open/readback 33780057070/9903336912; SHA256 a346d4554e07fc37552c9d8876179860677fc93923a3bd42f9b3f97f5e11f235; size 14347253; signer d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e; Stable/main/authority unchanged.
- OWNER acceptance: PENDING — checklist Beta116 item 9/11.

### LAN-GLOBAL-TEST-002
- Status: ACTIVE_PASS
- Scope: lan-global-test
- Rule: LAN test toàn cục dùng Service authority + epoch, đồng bộ trạng thái app và chỉ route test qua canRouteForTest/submitTest; production LAN route giữ tách biệt.
- Regression: global_test_mode / epoch / service_authority / test_route_isolated / production_route_separate.
- Technical evidence: 0.4.2-beta.116 Technical PASS/LIVE; candidate source cf01dab16e1c62091561ca008a355a8f49326581; candidate 33767353642/9898290631; Service 33767353642/9898616640; visual+PDA/API36 33774026289/9901071098 + human PASS 43 screenshots 320x568/360x640/480x800; Beta Auth 33776285435/9902148937; device 33778316587/9902571477; runtime 33778605857/9902663700; domain 33778957345/9902758766; Fast Check 33780103022 PASS; publish 33780057070/9903236359; OTA install/open/readback 33780057070/9903336912; SHA256 a346d4554e07fc37552c9d8876179860677fc93923a3bd42f9b3f97f5e11f235; size 14347253; signer d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e; Stable/main/authority unchanged.
- OWNER acceptance: PENDING — checklist Beta116 item 10/11.

### UI-TAP-FEEDBACK-004
- Status: ACTIVE_PASS
- Scope: tap-feedback
- Rule: Phản hồi bấm nhẹ chỉ dùng transform scale ngắn, không layout animation và không làm đổi geometry ACTIVE_PASS.
- Regression: transform_only / short_scale / no_layout_animation / active_geometry_preserved.
- Technical evidence: 0.4.2-beta.116 Technical PASS/LIVE; candidate source cf01dab16e1c62091561ca008a355a8f49326581; candidate 33767353642/9898290631; Service 33767353642/9898616640; visual+PDA/API36 33774026289/9901071098 + human PASS 43 screenshots 320x568/360x640/480x800; Beta Auth 33776285435/9902148937; device 33778316587/9902571477; runtime 33778605857/9902663700; domain 33778957345/9902758766; Fast Check 33780103022 PASS; publish 33780057070/9903236359; OTA install/open/readback 33780057070/9903336912; SHA256 a346d4554e07fc37552c9d8876179860677fc93923a3bd42f9b3f97f5e11f235; size 14347253; signer d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e; Stable/main/authority unchanged.
- OWNER acceptance: PENDING — checklist Beta116 item 11/11.


### OTA-BETA-LIVE-RECOVERY-002
- Status: ACTIVE_PASS
- Scope: Beta OTA / Service recovery / update_check.
- Rule: Beta115 phải tự lấy được Beta116 qua environment-scoped update_check khi Internet hoạt động; Service recovery không được yêu cầu xóa dữ liệu app; APK vẫn GitHub Release exact bytes.
- Regression: fresh Worker health + GAS service_discovery + update_check(current=Beta115) exact version/hash/size/GitHub URL; stale discovery cache phải tự rewrite; Service recovery giữ authority/Stable và cleanup test fixture.
- Technical evidence: OWNER reported Beta115 could not update and UI showed Service degraded. Fresh recovery: service-discovery 33784531907/9904956795 PASS; exact Beta116 Service source cf01dab16e1c62091561ca008a355a8f49326581 redeployed and full service regression 33784753619/9905201718 PASS with test_cleanup PASS; Beta-only live readback 33788505404/9906368570 PASS: Worker /health HTTP 200, GAS service_discovery HTTP 200 -> https://pickpack.1291.workers.dev, update_check from current_version 0.4.2-beta.115 HTTP 200 available=true -> 0.4.2-beta.116 code 122, SHA256 a346d4554e07fc37552c9d8876179860677fc93923a3bd42f9b3f97f5e11f235, size 14347253, GitHub Release URL exact. No APK rebuild/resign/republish; Stable untouched. Initial device degradation exact cause not provable from contaminated first probes.
- OWNER acceptance: OK — OWNER xác nhận cập nhật Beta115 → Beta116 trên thiết bị thật thành công.


## 5. Quy tắc tích lũy sau mỗi task

Khi DoD PASS:
1. Liệt kê hành vi mới/bugfix đã được xác minh.
2. Nếu là rule mới: cấp ID mới và thêm ACTIVE_PASS.
3. Nếu củng cố rule cũ: cập nhật evidence/last_verified, không thay nội dung rule.
4. Nếu phát hiện invariant cũ bị lỗi: chuyển/ghi rõ trạng thái cần sửa, không che giấu bằng PASS của case khác.
5. Handoff/finalizer phải ghi các invariant đã thêm/cập nhật và evidence exact.
6. Phiên sau phải dùng danh sách này làm regression baseline trước mọi change.

File này là canonical registry cho hành vi đã khóa của APK PICK PACK 1291.

## 4C. Beta117 — TECHNICAL_PASS_AWAITING_OWNER

Technical receipt: `ops/beta117-technical-pass.json`. Regression: `tools/beta117_owner_followup_contract.py`. Chỉ chuyển các invariant mới sang ACTIVE_PASS sau OWNER xác nhận từng mục. Hai invariant Beta116 còn pending tiếp tục giữ nguyên semantics và được re-verify trên Beta117.

### DOCUMENT-COMPACT-MULTI-EDIT-005
- Status: TECHNICAL_PASS_AWAITING_OWNER
- Scope: document-management / draft-actions / edit
- Parent: DOCUMENT-DRAFT-NOTE-UX-003 ACTIVE_PASS.
- Rule: 0/1 ảnh draft không hiện chế độ một/nhiều; vùng ảnh chờ tải rỗng phải ẩn; từ 2 ảnh mới mở chọn nhiều; Chọn tất cả/Xóa/Tải lên cùng hàng compact; fullscreen; cho sửa loại/note và xóa một/nhiều ảnh đúng document group.
- Regression: empty_pending_hidden / mode_hidden_zero_one / mode_multi_two_plus / compact_action_row / fullscreen / edit_category_note / delete_one_many / canonical_document_group.
- Technical evidence: 0.4.2-beta.117 Technical PASS/LIVE; candidate source d8ea2c2f31549647e8676b40dc536d2b1b80e6e5; candidate 33800745880/9911117214; fresh Service 33821884023/9918676363; visual/PDA/API36 33816769626/9916961610 + human PASS 43 screenshots 320x568/360x640/480x800; Beta Auth 33817394774/9917295154; device/discovery 33818941214/9917593203; Stable private primary recovery 33821666160/9918483812; runtime 33822369696/9918733617; domain 33822700732/9918901726; Fast Check 33821883976 PASS; terminal 33822875354; publish 9918907009; OTA install/open/readback 9918960606; final 9918965646; SHA256 b3454574547eece69ea44c51b2f88da93dd142eb5d1afb82e7fbd0f293cc0d87; size 14396405; signer d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e; Stable/main/authority unchanged.
- OWNER acceptance: PENDING — checklist Beta117 item 1/8.

### DOCUMENT-CROSS-GROUP-VIEWER-005
- Status: TECHNICAL_PASS_AWAITING_OWNER
- Scope: document-viewer
- Parent: DOCUMENT-GROUP-VIEWER-004 ACTIVE_PASS.
- Rule: viewer biên bản vuốt liên tục qua toàn bộ ảnh/biên bản trong tập đang xem, hỗ trợ pinch zoom và kéo X/Y; đổi ảnh không tạo adapter/rerender thừa.
- Regression: cross_group_swipe / pinch / pan_xy / adapter_reuse / exact_group_metadata.
- Technical evidence: 0.4.2-beta.117 Technical PASS/LIVE; candidate source d8ea2c2f31549647e8676b40dc536d2b1b80e6e5; candidate 33800745880/9911117214; fresh Service 33821884023/9918676363; visual/PDA/API36 33816769626/9916961610 + human PASS 43 screenshots 320x568/360x640/480x800; Beta Auth 33817394774/9917295154; device/discovery 33818941214/9917593203; Stable private primary recovery 33821666160/9918483812; runtime 33822369696/9918733617; domain 33822700732/9918901726; Fast Check 33821883976 PASS; terminal 33822875354; publish 9918907009; OTA install/open/readback 9918960606; final 9918965646; SHA256 b3454574547eece69ea44c51b2f88da93dd142eb5d1afb82e7fbd0f293cc0d87; size 14396405; signer d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e; Stable/main/authority unchanged.
- OWNER acceptance: PENDING — checklist Beta117 item 2/8.

### DROP-RECEIVE-COMPACT-LIST-002
- Status: TECHNICAL_PASS_AWAITING_OWNER
- Scope: drop-receive
- Parent: DROP-RECEIVE-CRUD-001 ACTIVE_PASS.
- Rule: danh sách Nhận hàng rớt mới nhất trước, format compact HH:mm dd/MM/yyyy | vị trí | DO | Số kiện; ADMIN/SUPERADMIN được xóa qua canonical auth, USER không được nâng quyền.
- Regression: newest_first / compact_datetime_location_do_package / admin_delete / superadmin_delete / user_forbidden.
- Technical evidence: 0.4.2-beta.117 Technical PASS/LIVE; candidate source d8ea2c2f31549647e8676b40dc536d2b1b80e6e5; candidate 33800745880/9911117214; fresh Service 33821884023/9918676363; visual/PDA/API36 33816769626/9916961610 + human PASS 43 screenshots 320x568/360x640/480x800; Beta Auth 33817394774/9917295154; device/discovery 33818941214/9917593203; Stable private primary recovery 33821666160/9918483812; runtime 33822369696/9918733617; domain 33822700732/9918901726; Fast Check 33821883976 PASS; terminal 33822875354; publish 9918907009; OTA install/open/readback 9918960606; final 9918965646; SHA256 b3454574547eece69ea44c51b2f88da93dd142eb5d1afb82e7fbd0f293cc0d87; size 14396405; signer d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e; Stable/main/authority unchanged.
- OWNER acceptance: PENDING — checklist Beta117 item 3/8.

### UI-PERFORMANCE-COMPACT-005
- Status: TECHNICAL_PASS_AWAITING_OWNER
- Scope: UI performance / compact select / tap feedback
- Parent: UI-TAP-FEEDBACK-004 ACTIVE_PASS + UI-FORM-CONSISTENCY-002 ACTIVE_PASS.
- Rule: các danh sách lớn render theo chunk/generation và search debounce để giảm lag PDA; select/spinner compact nhưng giữ khả năng đọc/chạm; tap feedback 0.95 → 1.01 chỉ transform, không đổi geometry/layout.
- Regression: chunked_render / generation_cancel / search_debounce / compact_select / transform_only / no_layout_animation.
- Technical evidence: 0.4.2-beta.117 Technical PASS/LIVE; candidate source d8ea2c2f31549647e8676b40dc536d2b1b80e6e5; candidate 33800745880/9911117214; fresh Service 33821884023/9918676363; visual/PDA/API36 33816769626/9916961610 + human PASS 43 screenshots 320x568/360x640/480x800; Beta Auth 33817394774/9917295154; device/discovery 33818941214/9917593203; Stable private primary recovery 33821666160/9918483812; runtime 33822369696/9918733617; domain 33822700732/9918901726; Fast Check 33821883976 PASS; terminal 33822875354; publish 9918907009; OTA install/open/readback 9918960606; final 9918965646; SHA256 b3454574547eece69ea44c51b2f88da93dd142eb5d1afb82e7fbd0f293cc0d87; size 14396405; signer d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e; Stable/main/authority unchanged.
- OWNER acceptance: PENDING — checklist Beta117 item 4/8.

### LABOR-FIXED-ROLE-BULK-006
- Status: TECHNICAL_PASS_AWAITING_OWNER
- Scope: labor fixed-role bulk
- Parent: LABOR-FIXED-ROLE-REVIEW-005 ACTIVE_PASS.
- Rule: Tổ trưởng/Kéo hàng/5S cho phép chọn nhiều/chọn tất cả đúng candidate, áp một khoảng giờ hàng loạt và ACK riêng theo từng NLĐ/session; không tự sinh công nhật và không đổi exact-session authority.
- Regression: fixed_role_candidates / select_many / select_all / batch_time / per_employee_ack / no_auto_labor / exact_session_authority.
- Technical evidence: 0.4.2-beta.117 Technical PASS/LIVE; candidate source d8ea2c2f31549647e8676b40dc536d2b1b80e6e5; candidate 33800745880/9911117214; fresh Service 33821884023/9918676363; visual/PDA/API36 33816769626/9916961610 + human PASS 43 screenshots 320x568/360x640/480x800; Beta Auth 33817394774/9917295154; device/discovery 33818941214/9917593203; Stable private primary recovery 33821666160/9918483812; runtime 33822369696/9918733617; domain 33822700732/9918901726; Fast Check 33821883976 PASS; terminal 33822875354; publish 9918907009; OTA install/open/readback 9918960606; final 9918965646; SHA256 b3454574547eece69ea44c51b2f88da93dd142eb5d1afb82e7fbd0f293cc0d87; size 14396405; signer d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e; Stable/main/authority unchanged.
- OWNER acceptance: PENDING — checklist Beta117 item 5/8.

### LAN-MANUAL-REAL-003
- Status: TECHNICAL_PASS_AWAITING_OWNER
- Scope: LAN production manual mode
- Parent: LAN-GLOBAL-TEST-002 ACTIVE_PASS.
- Rule: LAN thực tế thủ công tách hoàn toàn LAN test; chỉ SUPERADMIN bật/tắt; có trạng thái pending/not-ready; khi Service hội tụ lại phải reconcile an toàn, giữ fencing/idempotency và không tự đổi authority/provider.
- Regression: manual_vs_test_isolation / superadmin_only / global_state / pending_not_ready / safe_reconcile / authority_unchanged.
- Technical evidence: 0.4.2-beta.117 Technical PASS/LIVE; candidate source d8ea2c2f31549647e8676b40dc536d2b1b80e6e5; candidate 33800745880/9911117214; fresh Service 33821884023/9918676363; visual/PDA/API36 33816769626/9916961610 + human PASS 43 screenshots 320x568/360x640/480x800; Beta Auth 33817394774/9917295154; device/discovery 33818941214/9917593203; Stable private primary recovery 33821666160/9918483812; runtime 33822369696/9918733617; domain 33822700732/9918901726; Fast Check 33821883976 PASS; terminal 33822875354; publish 9918907009; OTA install/open/readback 9918960606; final 9918965646; SHA256 b3454574547eece69ea44c51b2f88da93dd142eb5d1afb82e7fbd0f293cc0d87; size 14396405; signer d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e; Stable/main/authority unchanged.
- OWNER acceptance: PENDING — checklist Beta117 item 6/8.

### Beta117 re-verification — REPORT-LABOR-DEDUCTION-002
- Status: TECHNICAL_PASS_AWAITING_OWNER (giữ nguyên).
- Rule/semantics: không đổi so với Beta116 item 4; Tổng nhân sự trước khấu trừ, Khấu trừ công nhật, Picker thực tế, Packer thực tế tách riêng.
- Beta117 evidence: 0.4.2-beta.117 Technical PASS/LIVE; candidate source d8ea2c2f31549647e8676b40dc536d2b1b80e6e5; candidate 33800745880/9911117214; fresh Service 33821884023/9918676363; visual/PDA/API36 33816769626/9916961610 + human PASS 43 screenshots 320x568/360x640/480x800; Beta Auth 33817394774/9917295154; device/discovery 33818941214/9917593203; Stable private primary recovery 33821666160/9918483812; runtime 33822369696/9918733617; domain 33822700732/9918901726; Fast Check 33821883976 PASS; terminal 33822875354; publish 9918907009; OTA install/open/readback 9918960606; final 9918965646; SHA256 b3454574547eece69ea44c51b2f88da93dd142eb5d1afb82e7fbd0f293cc0d87; size 14396405; signer d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e; Stable/main/authority unchanged.
- OWNER acceptance: PENDING — checklist Beta117 item 7/8.

### Beta117 re-verification — LOCAL-FIRST-RECONCILE-002
- Status: TECHNICAL_PASS_AWAITING_OWNER (giữ nguyên).
- Rule/semantics: không đổi so với Beta116 item 6; Đổi/Trả PDA và Công nhật local-first rồi reconcile nền, exact Service session vẫn là business authority.
- Beta117 evidence: 0.4.2-beta.117 Technical PASS/LIVE; candidate source d8ea2c2f31549647e8676b40dc536d2b1b80e6e5; candidate 33800745880/9911117214; fresh Service 33821884023/9918676363; visual/PDA/API36 33816769626/9916961610 + human PASS 43 screenshots 320x568/360x640/480x800; Beta Auth 33817394774/9917295154; device/discovery 33818941214/9917593203; Stable private primary recovery 33821666160/9918483812; runtime 33822369696/9918733617; domain 33822700732/9918901726; Fast Check 33821883976 PASS; terminal 33822875354; publish 9918907009; OTA install/open/readback 9918960606; final 9918965646; SHA256 b3454574547eece69ea44c51b2f88da93dd142eb5d1afb82e7fbd0f293cc0d87; size 14396405; signer d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e; Stable/main/authority unchanged.
- OWNER acceptance: PENDING — checklist Beta117 item 8/8.



### REVIEW-100-SESSIONS-001
- Status: TECHNICAL_PASS_AWAITING_OWNER
- Scope: Rà soát / projection 100 session owner test.
- Rule: Rà soát phải hiển thị exact canonical ACTIVE/in-only set theo business_date; Ca 1/Ca HC/Ca 2 phải hội tụ không phân biệt hoa/thường; expected/actual MNV + session_id bằng nhau hai chiều, không thừa/trùng/thiếu/sai nguồn và giữ đúng vị trí.
- Regression: exact 100 unique MNV/session_id / bidirectional set diff zero / case-insensitive shift projection / three shift buckets / positions / in-only / no wrong source / actual Android UI / local-first persistence.
- Technical evidence: diagnosis 33829110432/9921008888; fix ae80424706de74c72dea460e82bdd429090944cc; exact candidate 33833810807/9922669910 SHA256 5216f0eb09f187aed9cb71dcc21cd145fdc3ba7ea7852c74ffe6f85dea2b478f; visual/PDA API29 33835144144/9923142675; API36 Back 33835843259/9923339401; exact-100 Android UI 33836246626/9923402264 PASS; local-first/realtime 33837587706/9923826221 PASS (2 rows 341ms, retained 1.8s, third 41ms, warning 10/19ms).
- Release state: Beta118 NOT LIVE / NOT OTA; Beta117 remains LIVE.
- OWNER acceptance: PENDING — checklist 1–3.


## SUPERADMIN-AUTH-002 — PENDING OWNER ACCEPTANCE

- Status: `LOCKED_REQUIREMENT_PENDING_FIX` until Beta119 Technical DoD PASS; then `TECHNICAL_PASS_AWAITING_OWNER` until OWNER explicitly accepts.
- Preserve a valid SUPERADMIN session across in-place app update/restart; explicit logout/revocation/401 remains authoritative.
- Exactly two SUPERADMIN credential methods: (1) input 1..20 characters containing server-current `HHmm` within ±5 minutes, arbitrary prefix/suffix and no device binding; (2) exactly 8 random decimal digits delivered by email and single-use.
- Successful OTP use atomically rotates and emails the next OTP. Time-window login does not rotate/send OTP. Legacy/static SUPERADMIN password login is disabled.
- Public GitHub/log/artifact/handoff must never contain plaintext password/OTP/session/Gmail OAuth secret or an offline-usable verifier.
- Regression: `qa/beta119_superadmin_auth_regression.md`, `tools/beta119_superadmin_auth_contract.py`, `.github/workflows/superadmin-auth-regression.yml`.

## Beta119 — Technical PASS awaiting OWNER acceptance

### CURRENT_PUBLIC_BETA_001
- Status: ACTIVE_PASS
- Scope: Control plane / Beta current pointer
- Rule: `beta/current` và `CURRENT_STATE.md` phải nhận diện Beta public LIVE mới nhất; Beta/checklist cũ không được ghi đè trạng thái mới hơn.
- Regression: `tools/beta_current_sync_contract.py` + `tools/owner_acceptance_ledger_guard.py`; monotonic Beta/version/checklist fence; fast-forward only; post-sync readback.
- Technical evidence: Beta119 LIVE 0.4.2-beta.119 / source `eeb45df6deae267d93a5fb15701a0a394885a549`; terminal run `33868929441`; release/OTA/finalize PASS; acceptance ledger `BETA119_OWNER_ACCEPTANCE_20260904_R1` revision 1.
- OWNER acceptance: PASS — OWNER checklist item 1 OK, 2026-09-04 19:11 +07:00.

### SUPERADMIN_AUTH_002
- Status: ACTIVE_PASS
- Scope: Auth / SUPERADMIN / Android + GAS
- Rule: phiên đăng nhập hợp lệ phải được giữ qua update/process restart; SUPERADMIN chỉ có 2 credential method: chuỗi 1..20 ký tự chứa `HHmm` thời gian server trong ±5 phút, hoặc OTP Gmail đúng 8 chữ số dùng một lần; OTP dùng thành công tự cấp/gửi mã kế tiếp; time login không rotate/gửi OTP; static SUPERADMIN password login bị vô hiệu; không lưu credential secret plaintext trong GitHub public.
- Regression: `tools/beta119_superadmin_auth_contract.py`; live SUPERADMIN auth run `33865867111`; auth convergence run `33867109026` đồng thời chứng minh ADMIN thường vẫn password/challenge PASS và Stable isolation PASS.
- Technical evidence: Beta119 exact candidate `33864111135/9933396813`; Fast Check `33867108883`; terminal publish/OTA/install/open/readback/finalize `33868929441`; SHA256 `73c072187fb13bab635f27009fda500d0745fced4244a8d8276bc9117f350697`.
- OWNER acceptance: PASS — OWNER checklist items 2, 3, 4 OK, 2026-09-04 19:11 +07:00.

### OWNER_ACCEPTANCE_LEDGER_001
- Status: ACTIVE_PASS
- Scope: Control plane / OWNER acceptance continuity
- Rule: checklist/acceptance phải lưu bền trong GitHub, monotonic theo state epoch + Beta version + checklist revision; chat/memory/handoff chỉ dùng để điều hướng, không được làm authority và không được hồi quy về checklist Beta cũ.
- Regression: `tools/owner_acceptance_ledger_guard.py`; `ops/owner-acceptance-current.json`; lower epoch/Beta/revision rejected; OWNER silence không phải acceptance.
- Technical evidence: Beta119 ledger state epoch `202609041911`, checklist `BETA119_OWNER_ACCEPTANCE_20260904_R1`, revision 4; fresh-read `beta/current` preserved Beta119/revision; monotonic control-plane guard run `33871649452` PASS including stale acceptance rejection.
- OWNER acceptance: PASS — OWNER confirmed.


## Beta121 — TECHNICAL_PASS_AWAITING_OWNER

Technical receipt: `ops/beta121-technical-pass.json`. Regression: `tools/beta121_owner_ui_pda_source_contract.py`. Bốn mục mới chỉ chuyển sang ACTIVE_PASS sau OWNER xác nhận từng mục.

### UI-STATUS-DETAIL-VI-003
- Status: ACTIVE_PASS
- Scope: UI / status header + detail dialogs
- Parent: UI-STATUS-001 ACTIVE_PASS.
- Rule: 3 ô Mạng / Đồng bộ / Dịch vụ vẫn ghim trên cùng; icon đúng ngữ nghĩa; chi tiết dùng nhãn tiếng Việt hiện hành; Đồng bộ có thao tác `ĐỒNG BỘ NGAY` và không phá header/realtime UI.
- Regression: header_pinned / network_sync_service_icons / Vietnamese_detail_labels / manual_sync_from_header / no_geometry_regression.
- Regression case: `tools/beta121_owner_ui_pda_source_contract.py` + visual matrix run 33932137068.
- Technical evidence: 0.4.2-beta.121 Technical PASS/LIVE; source ee482efb41565eee797b9b6c11fe54557c2b67f8; candidate 33929895214/9958252319; Service 33929895214/9958376646; Fast Check 33932137056; visual+PDA+API36 33932137068/9959024622 + human PASS 43 screenshots 320x568/360x640/480x800; device/discovery 33932666498/9959133081; runtime DoD 33933735030/9959507710; Beta domain 33934032820/9959551837; OTA baseline recovery 33934523152/9959702930; terminal publish/OTA/install/open/readback/finalize 33934142254; publish 9959732997; OTA device 9959773897; final 9959777958; SHA256 5b042c8e1f6d288ef19efe9abc773562c204fb3defd91396e4101adcedc8cc57; size 14429173; signer d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e; Stable/main/authority unchanged.
- OWNER acceptance: PASS — OWNER item 1 OK, 2026-09-05 08:20 +07:00.

### SUPERADMIN-EFFECTIVE-ROLE-003
- Status: LOCKED_REQUIREMENT_PENDING_FIX
- Scope: SUPERADMIN / effective role
- Parent: SUPERADMIN_AUTH_002 ACTIVE_PASS.
- Rule: chỉ actual SUPERADMIN mới được chọn effective USER / ADMIN / SUPERADMIN trong chi tiết Dịch vụ; quyền nghiệp vụ thực tế phải hạ theo effective role; actual role vẫn là authority và user không phải SUPERADMIN không được tự nâng quyền.
- Regression: actual_super_guard / effective_user / effective_admin / effective_superadmin / no_non_super_elevation / auth_session_preserved.
- Regression case: `tools/beta121_owner_ui_pda_source_contract.py`.
- Technical evidence: 0.4.2-beta.121 Technical PASS/LIVE; source ee482efb41565eee797b9b6c11fe54557c2b67f8; candidate 33929895214/9958252319; Service 33929895214/9958376646; Fast Check 33932137056; visual+PDA+API36 33932137068/9959024622 + human PASS 43 screenshots 320x568/360x640/480x800; device/discovery 33932666498/9959133081; runtime DoD 33933735030/9959507710; Beta domain 33934032820/9959551837; OTA baseline recovery 33934523152/9959702930; terminal publish/OTA/install/open/readback/finalize 33934142254; publish 9959732997; OTA device 9959773897; final 9959777958; SHA256 5b042c8e1f6d288ef19efe9abc773562c204fb3defd91396e4101adcedc8cc57; size 14429173; signer d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e; Stable/main/authority unchanged.
- OWNER acceptance: NOT OK — khi hạ về USER vẫn thấy Lịch sử; OWNER yêu cầu toàn bộ quyền nghiệp vụ hạ thực sự như USER/ADMIN, chỉ bộ chọn quyền trong chi tiết Dịch vụ được giữ theo actual SUPERADMIN.

### SETTINGS-REGION-INHOUSE-DROP-001
- Status: ACTIVE_PASS
- Scope: Cài đặt / Bảng công Inhouse / Nhận hàng Rớt
- Rule: Cài đặt chia vùng Tài khoản & quyền / Giao diện / Ứng dụng & cập nhật / Hỗ trợ & nhật ký; Bảng công Inhouse hiển thị `Chờ phát triển` và không giả lập chức năng; bảng Nhận hàng Rớt dùng layout bảng compact có header Thời gian / Vị trí / DO / Số kiện.
- Regression: settings_regions / inhouse_placeholder_nonfunctional / drop_table_headers / compact_row_geometry / existing_drop_permissions_preserved.
- Regression case: `tools/beta121_owner_ui_pda_source_contract.py`.
- Technical evidence: 0.4.2-beta.121 Technical PASS/LIVE; source ee482efb41565eee797b9b6c11fe54557c2b67f8; candidate 33929895214/9958252319; Service 33929895214/9958376646; Fast Check 33932137056; visual+PDA+API36 33932137068/9959024622 + human PASS 43 screenshots 320x568/360x640/480x800; device/discovery 33932666498/9959133081; runtime DoD 33933735030/9959507710; Beta domain 33934032820/9959551837; OTA baseline recovery 33934523152/9959702930; terminal publish/OTA/install/open/readback/finalize 33934142254; publish 9959732997; OTA device 9959773897; final 9959777958; SHA256 5b042c8e1f6d288ef19efe9abc773562c204fb3defd91396e4101adcedc8cc57; size 14429173; signer d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e; Stable/main/authority unchanged.
- OWNER acceptance: PASS — OWNER item 3 OK, 2026-09-05 08:20 +07:00.

### PDA-SOURCE-MASTER-001
- Status: LOCKED_REQUIREMENT_PENDING_FIX
- Scope: PDA master data / Nguồn
- Rule: PDA có trường `Nguồn` xuyên Android → GAS → Service; danh mục hiện hành gồm 1291, 1386, 1368, 1399, Inbound, Outbound; không được làm mất nguồn khi đọc/ghi master data.
- Regression: source_field_android / gas_source_roundtrip / service_source_roundtrip / allowed_source_catalog / existing_pda_identity_preserved.
- Regression case: `tools/beta121_owner_ui_pda_source_contract.py`.
- Technical evidence: 0.4.2-beta.121 Technical PASS/LIVE; source ee482efb41565eee797b9b6c11fe54557c2b67f8; candidate 33929895214/9958252319; Service 33929895214/9958376646; Fast Check 33932137056; visual+PDA+API36 33932137068/9959024622 + human PASS 43 screenshots 320x568/360x640/480x800; device/discovery 33932666498/9959133081; runtime DoD 33933735030/9959507710; Beta domain 33934032820/9959551837; OTA baseline recovery 33934523152/9959702930; terminal publish/OTA/install/open/readback/finalize 33934142254; publish 9959732997; OTA device 9959773897; final 9959777958; SHA256 5b042c8e1f6d288ef19efe9abc773562c204fb3defd91396e4101adcedc8cc57; size 14429173; signer d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e; Stable/main/authority unchanged.
- OWNER acceptance: NOT OK — Nguồn chưa hiển thị trong thông tin PDA và danh sách PDA ở Tài nguyên; data/GSheet đã có nhưng Android UI/edit chưa hoàn tất.

### Beta121 re-verification — OTA-BETA-001
- Status: ACTIVE_PASS (semantics unchanged; OWNER-accepted invariant re-verified).
- Rule: giữ nguyên GITHUB_RELEASE_ONLY / exact bytes / Stable-main-authority unchanged.
- Regression addition: `tools/beta_ota_baseline_recovery_contract.py` bắt buộc recovery previous LIVE exact SHA/size/STABLE-disabled trước target activation khi OTA GAS baseline bị drift; sai SHA/readback phải fail-closed.
- Evidence: baseline recovery run 33934523152 artifact 9959702930 PASS; exact Beta120 restored before publish; Beta121 publish 33934142254 artifact 9959732997 PASS; OTA install/open/readback artifact 9959773897 PASS; final artifact 9959777958 PASS.

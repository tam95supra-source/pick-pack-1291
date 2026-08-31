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
- Publish-verifier regression: receipt-driven screenshot evidence; legacy receipt 26 PASS, Beta101 receipt 35 PASS, actual-count mismatch / missing viewport / summary mismatch / human gate false FAIL; Fast Check run 33377060461 PASS.
- Evidence: Beta102 terminal run 33377501045; final artifact 9752558407; GitHub Release asset v0.4.2-beta.102-publicbeta SHA256 6178085afb3d5b9d7e3a913ca38d3842dd7b2d6db585ac2bbe04a95dcaa5c0b1 / size 13593589; OTA 0.4.2-beta.101 → 0.4.2-beta.102 exact SHA/size/version/package/signer + install/open PASS; publish fresh GAS readback deployment 213 PASS; Stable unchanged.
- Last verified: 0.4.2-beta.102.

## 4. LOCKED_REQUIREMENT_PENDING_FIX

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
- Status: TECHNICAL_PASS_AWAITING_OWNER
- Scope: Beta/Stable environment isolation / HTTP / GAS / LAN-NSD / release
- OWNER rule: Beta và Stable phải tách environment/audience, data/accounts/service/GAS/OTA/LAN mutable state; cross-environment automatic write/fallback/auth/session/manifest/LAN sharing bị cấm. Stable giữ READY_NOT_LIVE/private/public=false cho tới lệnh promotion riêng của OWNER.
- Regression: distinct BETA/STABLE environment+audience; cross/missing environment request bị reject; D1/Sheet/GAS tách; LAN/NSD type tách; BETA GAS discovery trỏ canonical BETA Service; Stable không OTA/public/promotion; Stable/main/signer/authority không đổi.
- Technical evidence: exact Beta102 source 8653e8e1a8c0585a4dcab95ccb3da0636650d8a5; BETA GAS source-only repair run 33376373374 artifact 9752024220 → deployment 213; independent/publish fresh readback 33376476824 + publish run 33377501045 xác nhận BETA/PICK_PACK_1291_BETA canonical Worker; Fast Check 33377060461 PASS; runtime DoD 33377306088 artifact 9752375833 PASS (D1=3, BETA auth=5, Stable auth=1, GAS=3, backup/restore PASS, Stable public=false); terminal publish/OTA/install/readback/finalize run 33377501045 PASS, final artifact 9752558407.
- Release identity: 0.4.2-beta.102 / versionCode 108 / package vn.pickpack1291.app.beta.publicbeta / SHA256 6178085afb3d5b9d7e3a913ca38d3842dd7b2d6db585ac2bbe04a95dcaa5c0b1 / size 13593589 / signer d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e.
- OWNER acceptance: PENDING — chưa được chuyển ACTIVE_PASS trước phản hồi nghiệm thu của Nguyễn Văn Tâm.

### INFRA-RESILIENCE-001
- Status: TECHNICAL_PASS_AWAITING_OWNER
- Scope: infra / DR / durable event path
- Rule: durable local + provisional Google ledger + single-writer LAN/cloud DR + backup/rollover/fencing phải giữ canonical event/idempotency và không tự đổi authority/provider.
- Technical evidence: service-live PASS job 99202629701 inherited because exact service source unchanged; Beta101 exact-candidate verify run 33309271079; terminal publish/OTA/install/readback/finalize run 33310230934 PASS. OWNER manual log 2026-08-30 20:12 phát hiện Google fallback FAIL deterministic UNKNOWN_ACTION và LAN NOT_AVAILABLE. Read-only GAS deployment probe 33313877854 xác nhận deployment 205 thiếu RESILIENCE_V1; repair 33314072135 deploy 206 PASS, post-readback 33314115931 PASS; ppUpdateCheck Beta101/Stable/main/signer/authority/provider không đổi. Release guard Fast Check 33314181358 PASS.
- Test fidelity: NORMAL_SERVICE_PRIMARY dùng Service/idempotency thật. Google fallback sau GAS206 là safe live-path drill. DEVICE_OFFLINE_LOCAL và SERVICE_GOOGLE_OFFLINE_LOCAL là isolated simulation + real recovery, không phải physical outage. GOOGLE_UNAVAILABLE_SERVICE dùng Service thật nhưng Google-down được mô phỏng. LAN chỉ có giá trị khi có topology multi-device thực sự active.
- OWNER acceptance: DEFERRED_BY_OWNER ngày 2026-08-30. Item 6 tạm pending, không phải PASS, không chặn scope phát triển khác; chỉ rerun Beta101/GAS206 + LAN topology thật khi OWNER mở lại scope backup/DR trước khi ACTIVE_PASS.

## 5. Quy tắc tích lũy sau mỗi task

Khi DoD PASS:
1. Liệt kê hành vi mới/bugfix đã được xác minh.
2. Nếu là rule mới: cấp ID mới và thêm ACTIVE_PASS.
3. Nếu củng cố rule cũ: cập nhật evidence/last_verified, không thay nội dung rule.
4. Nếu phát hiện invariant cũ bị lỗi: chuyển/ghi rõ trạng thái cần sửa, không che giấu bằng PASS của case khác.
5. Handoff/finalizer phải ghi các invariant đã thêm/cập nhật và evidence exact.
6. Phiên sau phải dùng danh sách này làm regression baseline trước mọi change.

File này là canonical registry cho hành vi đã khóa của APK PICK PACK 1291.

# PICK PACK 1291 — HANDOFF SCHEMA V2

- schema_version: 2
- status: READY
- time_utc: 2026-09-05T12:02:14Z
- corrected_scope_at_utc: 2026-09-05T12:05:00Z
- owner: Nguyễn Văn Tâm
- branch: release/beta126-owner-scope-20260905
- release_trigger_sha: 9b5393986af87c993b647978ccc176929e2c1ed4
- archive_file: docs/handovers/HANDOVER_20260905-120214_beta126-pass-live.md

## Mục tiêu + DoD
Release 0.4.2-beta.126 Technical PASS/LIVE cho toàn bộ continuity scope OWNER: 11 yêu cầu follow-up + yêu cầu hiệu năng dữ liệu lớn toàn app + các refinement Beta123/Beta124/Beta125 về QR/điều hướng + remediation Beta126. Toàn bộ pre-OTA, full ACTIVE_PASS regression, visual/human/PDA/API36, fresh discovery/device, runtime DoD, release lock, GitHub Release exact bytes, OTA install/readback và finalizer đều PASS. OWNER acceptance còn PENDING.

## LIVE / TARGET / CANDIDATE
- LIVE BETA: 0.4.2-beta.126 / versionCode 132 / package vn.pickpack1291.app.beta.publicbeta.
- TARGET: PASS/LIVE, chờ OWNER nghiệm thu.
- CANDIDATE LOCKED: run 33963619992; artifact 9968783758; source 9bfcad4bb218d5865fe6ae220352c44cd4bd8cf0; SHA256 211229dff3bcabc8151b4753914a3439185b5bbfe69fcad9f3faecbfa4fac4bb; size 14461941; signer d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e.
- Full ACTIVE_PASS regression: PASS run 33964356946.
- Visual/PDA/API36 pre-OTA: PASS run 33963619992, artifact 9968868014; 44 screenshots; 320x568 / 360x640 / 480x800 human-inspected PASS.
- Fresh discovery/device: PASS run 33964502604, artifact 9969005524.
- Runtime DoD: PASS run 33964635091, artifact 9969035647.
- Publish: PASS run 33964725581, artifact 9969070202.
- OTA install/readback: PASS run 33964725581, artifact 9969099501.
- Final: PASS run 33964725581, artifact 9969103461.
- Stable/main/signer/authority: unchanged.

## Evidence cốt lõi
- GitHub Release tag: v0.4.2-beta.126-publicbeta.
- APK URL: https://github.com/tam95supra-source/pick-pack-1291/releases/download/v0.4.2-beta.126-publicbeta/pick-pack-1291-public-beta-0.4.2-beta.126.apk
- Publish exact bytes/readback: version/code/package/SHA256/size/signer khớp candidate lock; rebuild=false; resign=false.
- OTA 0.4.2-beta.125 → 0.4.2-beta.126: download/install exact SHA/size/version/package/signer, mở app PASS.
- Fresh discovery: BETA / PICK_PACK_1291_BETA, stale Stable root không reuse, cache rewrite PASS.
- Runtime DoD: quota/fencing, tested backup restore, Beta/Stable DB+Sheet+GAS separation, cross-environment guards, GAS idempotency, Stable READY_NOT_LIVE, không candidate manifest leak: PASS.
- Google Drive APK: FORBIDDEN; Beta APK transport = GITHUB_RELEASE_ONLY.

## Remediation Beta126
- Cài đặt: vùng cài đặt có màu nền phân biệt thực sự; giữ xóa cache/đặt lại dữ liệu cục bộ đã PASS.
- Nhân sự: search debounce, không rebuild đồng bộ theo từng ký tự.
- Dịch vụ suy giảm: vẫn giữ provider/route thực tế.
- Báo cáo: bỏ 2 summary row thừa `Tổng nhân sự` / `Khấu trừ công nhật`; giữ đúng Nhân sự Pick & Pack thực tế sau loại trừ hỗ trợ + chi tiết công nhật/theo vị trí.
- Công nhật: batch create/finish bounded-parallel; refresh UI một lần; thêm `SỬA NHIỀU` BĐ/KT/khấu trừ.
- Các PASS trước đó được giữ bằng regression guard, không làm lại logic đã khóa nếu bytes/source không đổi.

## Checklist OWNER nghiệm thu 1–14
1. Quản lý biên bản: action compact cùng hàng; ẩn vùng rỗng; chế độ nhiều ảnh chỉ hiện khi >=2; sửa note/type từng ảnh; xóa một/nhiều; grouping/history/audit giữ đúng.
2. Viewer biên bản: vuốt ảnh kế/trước xuyên biên bản; zoom >1x pan X/Y; fullscreen; layout logic gọn cho PDA.
3. PDA serial: tự lấy 5 số cuối; không nhập tay; không lỗi khoảng trắng.
4. Báo cáo nhân sự Beta126: không còn 2 dòng summary thừa `Tổng nhân sự` / `Khấu trừ công nhật`; hiển thị Nhân sự Pick & Pack thực tế sau loại trừ hỗ trợ + chi tiết công nhật/theo vị trí. Nếu chưa có dữ liệu thật để test thì giữ PENDING, không chốt giả.
5. Nhận hàng rớt: format/căn chỉnh `HH:mm dd/MM/yyyy | CX… | DO:… | Số kiện: …`; mới nhất → cũ nhất; ADMIN+ xóa với auth phá hủy canonical.
6. Đổi/trả PDA + công nhật local-first: UI local, reconcile nền, exact Service session authority; không nhầm phiên/không tái phát user pick-pack unavailable. Nếu thiếu dữ liệu thật thì giữ PENDING.
7. Điểm danh/QR dữ liệu lớn: không lag nặng; select compact/phản hồi; scan/realtime đúng trên PDA yếu.
8. Công nhật vị trí cố định + select global + Beta126 batch edit: chọn nhiều người; time range áp dụng toàn bộ; ack chỉ đúng một người không ẩn cảnh báo người khác; select compact; batch create/finish bounded-parallel; `SỬA NHIỀU` BĐ/KT/khấu trừ.
9. SUPERADMIN reset mật khẩu user khác: đúng một target; privileged reauth; chỉ target đổi; user khác không ảnh hưởng.
10. LAN thật: SUPERADMIN toggle; bật có hiệu lực ngay; tách hoàn toàn LAN test/7 mode resilience; tắt reconcile an toàn giữ fencing/idempotency/durable outbox/anti-duplicate/audit; Stable/main/provider-authority không đổi.
11. Tap feedback: khoảng 120% Beta116; transform-only; không reflow/layout animation/jank; geometry ổn định.
12. Hiệu năng toàn app với dữ liệu lớn/PDA yếu: attendance, QR, staff, labor, history, biên bản, hàng rớt; không ANR/OOM; filter/select/scan responsive; realtime correctness giữ nguyên.
13. QR navigation refinement: scan/result/loading/lookup-error cùng logical frame; Back một lần về đúng scan; sau scan Back không rebuild roster; gesture/system Back theo lịch sử thực tế.
14. Release thật: Beta126/versionCode132; OTA từ Beta125 qua GitHub Release exact candidate; install/readback exact bytes; Google Drive APK không được dùng.

## Sai sót finalizer đã sửa
Finalizer Beta126 lại ghi `scope null` và sinh handoff thiên về scope QR cũ dù `ops/beta-release-request.json` đã có `owner_scope=OWNER_20260905_DOCX_FULL_SCOPE_BETA126`. Đây chỉ là lỗi sinh tài liệu/handoff. Sửa docs-only này không thay APK/service/GAS bytes, không rebuild/resign, không làm mất Technical PASS và không yêu cầu rerun các gate đã PASS.

## Blocker
Không có blocker kỹ thuật. Technical DoD PASS; đang chờ OWNER nghiệm thu checklist 1–14.

## Invariants
- Stable/main/signer/authority không đổi.
- APK Beta release/OTA/rollback = GITHUB_RELEASE_ONLY.
- Google Drive không được dùng cho APK; GSheet/GAS nghiệp vụ không bị xóa/thay authority.
- OWNER silence không phải acceptance; chỉ mục OWNER xác nhận OK mới được khóa ACTIVE_PASS.

## NEXT_ACTION
WAIT_FOR_OWNER_ACCEPTANCE_NUMBERED_CHECKLIST_1_TO_14

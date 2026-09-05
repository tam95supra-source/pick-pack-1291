# PICK PACK 1291 — HANDOFF SCHEMA V2

- schema_version: 2
- status: READY
- time_utc: 2026-09-05T10:43:04Z
- corrected_scope_at_utc: 2026-09-05T10:50:00Z
- owner: Nguyễn Văn Tâm
- branch: release/beta125-navigation-frame-20260905
- release_trigger_sha: a0a7bb6773bf540d41798cf544f221972094ca14
- archive_file: docs/handovers/HANDOVER_20260905-104304_beta125-pass-live.md

## Mục tiêu + DoD
Release 0.4.2-beta.125 Technical PASS/LIVE cho toàn bộ continuity scope OWNER 11 follow-up requirements từ Beta116/Beta117, yêu cầu performance dữ liệu lớn toàn app, các refinement tiếp nối Beta123/Beta124/Beta125 và QR navigation frame; toàn bộ pre-OTA + GitHub Release exact bytes + OTA install/readback + finalizer PASS; OWNER acceptance còn PENDING.

## LIVE / TARGET / CANDIDATE
- LIVE BETA: 0.4.2-beta.125 / versionCode 131 / package vn.pickpack1291.app.beta.publicbeta.
- TARGET: PASS/LIVE.
- CANDIDATE LOCKED: run 33955316061; artifact 9966233235; source eac95af57d1bdb7d16547e99b0b269a9d3a32456; SHA256 ee4040086c7683776c3b1713f7a024ee9daf73d977c05b24983e5cdc7c04f878; size 14445557; signer d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e.
- Fast Check: PASS run 33960990339.
- Visual/PDA pre-OTA: PASS run 33960305554, artifact 9967776375.
- Human visual 320x568 / 360x640 / 480x800: PASS, 44 screenshots.
- API36: PASS run 33960764189.
- Runtime DoD: PASS run 33960990350.
- Publish/OTA/install/readback/finalizer: PASS run 33961204941.
- Stable/main/signer/authority: unchanged.

## Evidence
- GitHub Release asset exact bytes khớp candidate SHA256/size; OTA tải trực tiếp từ GitHub Release: PASS.
- OTA 0.4.2-beta.122 → 0.4.2-beta.125: download/install exact SHA/size/version/package/signer và mở app: PASS.
- Candidate được build/sign đúng một lần; recovery chỉ dùng exact locked bytes, không rebuild/resign.
- Google Drive APK: FORBIDDEN.
- ACTIVE_PASS regressions và impacted functional/visual/device/runtime gates đã PASS theo release receipts.

## OWNER checklist bắt buộc — BETA125_OWNER_ACCEPTANCE_20260905_R1
1. Quản lý biên bản: action compact cùng hàng; ẩn vùng rỗng; chế độ nhiều ảnh chỉ hiện khi >=2; sửa note/loại ảnh; xoá một/nhiều ảnh.
2. Viewer biên bản: vuốt xuyên biên bản; pan X/Y khi zoom; fullscreen; layout mới gọn/rõ trên PDA.
3. PDA serial: tự lấy đúng 5 số cuối, không nhập tay/whitespace regression.
4. Báo cáo nhân sự: Tổng trước khấu trừ; khấu trừ công nhật riêng; Picker/Packer thực tế. Nếu chưa có dữ liệu đủ test thì giữ PENDING, không giả OK.
5. Nhận hàng rớt: format/căn hàng thống nhất; mới nhất→cũ nhất; ADMIN+ xoá đúng quyền/xác thực.
6. Đổi/trả PDA + công nhật local-first: UI local-first, reconcile nền, exact Service session authority, không nhầm session/user pick-user pack unavailable. Nếu thiếu dữ liệu test thì giữ PENDING.
7. Điểm danh/QR dữ liệu lớn: không lag nặng, select chọn được và compact, scan/realtime đúng trên PDA yếu.
8. Công nhật vị trí cố định + global select: bulk nhiều NLĐ, áp dụng khoảng giờ, ack đúng từng người, cảnh báo người khác còn giữ, select toàn app compact nhưng usable.
9. SUPERADMIN reset mật khẩu user khác: đúng một user, privileged re-auth, user khác không bị ảnh hưởng.
10. LAN thật: chỉ SUPERADMIN bật/tắt; bật là active ngay kể cả Service sống; tách hoàn toàn LAN test/7 resilience modes; tắt reconcile an toàn về Service, giữ fencing/idempotency/outbox/anti-duplicate/audit.
11. Tap feedback: mạnh khoảng 120% Beta116, transform-only, không reflow/giật, touch geometry ổn định.
12. Performance toàn app với dữ liệu lớn/PDA yếu: Điểm danh, QR, danh sách nhân sự, công nhật, lịch sử, biên bản, hàng rớt; không ANR/OOM; filter/select/scan vẫn phản hồi, không hy sinh realtime correctness.
13. Beta125 QR navigation refinement: scan/result/lookup error cùng logical frame; Back một lần về đúng màn QR thực tế; sau scan Back không dựng lại toàn bộ roster; gesture Back theo lịch sử truy cập thật.
14. Release thực tế: Beta125/versionCode131; OTA/install/readback đúng exact candidate, GitHub Release only.

## Sai sót đã sửa
- Finalizer release đã ghi nhầm `scope null` và làm checklist bị co thành 7 mục thiên về QR.
- Đây là lỗi handoff/checklist generation; không thay đổi APK bytes hay trạng thái Technical PASS.
- Canonical OWNER acceptance phải dùng checklist đầy đủ ở trên.

## Blocker
Không có.

## Invariants
- Stable/main/signer/authority không đổi.
- APK Beta release/OTA/rollback = GITHUB_RELEASE_ONLY.
- Google Drive không được dùng cho APK; GSheet/GAS nghiệp vụ không bị xóa/thay authority.
- OWNER acceptance chỉ chuyển ACTIVE_PASS theo từng mục OWNER xác nhận OK.

## NEXT_ACTION
WAIT_FOR_OWNER_ACCEPTANCE_NUMBERED_CHECKLIST_1_TO_14

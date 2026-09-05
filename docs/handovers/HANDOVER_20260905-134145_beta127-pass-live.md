# PICK PACK 1291 — HANDOFF SCHEMA V2

- schema_version: 2
- status: READY
- time_utc: 2026-09-05T13:41:45Z
- owner: Nguyễn Văn Tâm
- branch: release/beta127-owner-r2-complete-20260905
- release_trigger_sha: 4ea93c4e47361171646ced9f659fa6f54039fbb1
- archive_file: docs/handovers/HANDOVER_20260905-134145_beta127-pass-live.md
- owner_scope: OWNER_20260905_CHAT_ORIGINAL_10_PLUS_GLOBAL_REALTIME_BETA127
- owner_checklist_id: BETA127_OWNER_ACCEPTANCE_20260905_R2
- owner_checklist_revision: 2

## Mục tiêu + DoD
Release 0.4.2-beta.127 Technical PASS/LIVE cho scope OWNER_20260905_CHAT_ORIGINAL_10_PLUS_GLOBAL_REALTIME_BETA127; toàn bộ pre-OTA + GitHub Release exact bytes + OTA install/readback + finalizer PASS; OWNER acceptance còn PENDING.

## LIVE / TARGET / CANDIDATE
- LIVE BETA: 0.4.2-beta.127 / versionCode 133 / package vn.pickpack1291.app.beta.publicbeta.
- TARGET: PASS/LIVE, chờ OWNER nghiệm thu đúng checklist của release request.
- CANDIDATE LOCKED: run 33967758178; artifact 9970037896; source 014ea67eb05773d0d61593f705c2171b5ec574ee; SHA256 922dd571c8e8d6cb5e6d8dbe7fd4f3d73433e14a9f35a50a78d97bf64fa9fbf7; size 14461941; signer d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e.
- Fast Check: PASS run 33968559771.
- Service gate: PASS.
- Visual/PDA pre-OTA: PASS run 33967758178, artifact 9970125449.
- Human visual 320x568 / 360x640 / 480x800: PASS.
- Fresh discovery/device: PASS run 33967758178.
- Runtime DoD: PASS run 33968559764.
- Stable/main/signer/authority: unchanged.

## Evidence cốt lõi
- Cài đặt: đổi đúng nhãn Xóa dữ liệu ứng dụng; chỉ reset dữ liệu local, không xóa dữ liệu chuẩn trên Dịch vụ.
- Báo cáo tình hình nhân sự: tiêu đề hiển thị thật; Chi tiết công nhật nằm đúng dưới Thâm niên và trên Pick & Pack, kể cả khi chưa có dữ liệu hỗ trợ.
- Regression: exact-device bắt buộc nhìn thấy các nội dung OWNER yêu cầu và cấm PASS chỉ vì chuỗi tồn tại trong source.
- Giữ nguyên tối ưu Nhân sự, Công nhật, Hàng rớt, PDA, Điểm danh, QR và realtime từ Beta126; khóa đủ contract R2 11 mục.
- GitHub Release asset exact bytes khớp candidate SHA256/size; OTA tải trực tiếp từ GitHub Release: PASS.
- OTA 0.4.2-beta.126 → 0.4.2-beta.127: download/install exact SHA/size/version/package/signer và mở app: PASS.
- Google Drive APK: FORBIDDEN; canonical APK transport = GITHUB_RELEASE_ONLY.

## Checklist OWNER nghiệm thu
1. **Cài đặt**
   - Trong Thông tin ứng dụng có Xóa cache và Xóa dữ liệu ứng dụng.
   - Xóa dữ liệu cho phép cả USER; chỉ cần xác nhận, không yêu cầu mật khẩu; chỉ xóa dữ liệu local và đưa app về trạng thái như mới cài, không xóa dữ liệu Service/server.
   - Sau reset, app đồng bộ lại đúng dữ liệu canonical từ Service.
   - Layout các nhóm cài đặt có màu sắc rõ ràng, dễ phân biệt và vẫn giữ bố cục logic.
2. **Lịch sử**
   - Có nút Xóa toàn bộ cùng hàng với Chọn/Bỏ chọn/Xóa đã chọn; xóa toàn bộ lịch sử của ngày đang chọn theo quyền/xác thực đã chốt.
   - Ô tìm kiếm hiển thị Tìm mã nhân viên, họ tên, nghiệp vụ …
   - Chọn ngày/search/nút có kích thước gọn, đồng bộ toàn app và tăng diện tích hiển thị lịch sử.
   - Chi tiết lịch sử thuần Việt, dễ hiểu, bỏ text hướng dẫn OWNER thừa và hiển thị đủ thông tin chi tiết hữu ích.
3. **Ba ô Mạng / Đồng bộ / Dịch vụ**
   - Dịch vụ hiển thị loại/nguồn đang dùng thực tế như Cloudflare/LAN; chỉ hiện Không hoạt động/OFFLINE khi thực sự không hoạt động.
   - Mạng hiển thị ping cạnh loại mạng.
   - Các mục Đồng bộ/Dịch vụ đang chờ có thao tác xử lý lại từng mục, xử lý lại tất cả/cưỡng ép thử lại theo cơ chế an toàn.
   - ADMIN/SUPERADMIN có thể tự xử lý; chỉ cho xóa hẳn mục đã xác minh terminal/stale/không còn giá trị nghiệp vụ, không làm mất mutation chưa commit.
4. **Nhân sự**
   - Gõ ô search không còn giật/khựng dù danh sách lớn hoặc giới hạn hiển thị đang áp dụng.
   - Không rebuild toàn bộ danh sách đồng bộ theo từng ký tự; kết quả tìm kiếm vẫn đúng.
5. **Hàng rớt**
   - Cột thời gian được căn để không tràn xuống hai dòng.
   - Hiển thị 50 DO mỗi trang; có tiến/lùi trang khi dữ liệu nhiều hơn 50.
   - Đã bỏ text thừa Service / D1 xác nhận ngay ….
6. **Báo cáo tình hình nhân sự**
   - Bỏ text Phạm vi báo cáo; tiêu đề đúng Báo cáo tình hình nhân sự.
   - Select ca có đúng 3 lựa chọn: Ca 1 và HC / C2 / Cả ngày; đi cùng chọn ngày-tháng-năm; kích thước gọn và đồng bộ toàn app.
   - Tiêu đề bảng và Vị trí dùng chữ đậm.
   - Bỏ Tổng nhân sự và Khấu trừ nhân sự; vùng kết quả mang tiêu đề Nhân sự pick & pack thực tế sau khi loại trừ hỗ trợ.
   - Có chi tiết công nhật dưới bảng thâm niên và trên vùng Pick & Pack thực tế: hiển thị vị trí công nhật và số lượng mỗi vị trí với layout hợp lý.
7. **Công nhật**
   - Màn công nhật không còn cảm giác giật/khựng.
   - Tạo/kết thúc nhiều người không load tuần tự gây đơ; trạng thái hoàn thành cập nhật mượt.
   - Bỏ qua cảnh báo Tổ trưởng/Kéo hàng lưu theo từng NLĐ + phiên/ngày; xử lý một người không ẩn cảnh báo người khác; NLĐ mới xuất hiện vẫn có cảnh báo.
   - Có thể chọn riêng/chọn nhiều/chọn tất cả; select không dính nhau và có kích thước hợp lý.
   - Có Sửa nhiều cho giờ bắt đầu, giờ kết thúc và tính/không tính khấu trừ.
8. **Đổi / trả PDA**
   - Hiển thị nguồn PDA.
   - Layout Đổi PDA được thiết kế lại đơn giản, dễ hiểu cho người dùng và không làm sai canonical PDA/session.
9. **Điểm danh**
   - Ô search hiển thị Tìm mã nhân viên / họ tên.
   - Bấm/mở/lọc không còn reload-like, nhấp nháy hoặc giật lag.
10. **Scan QR vào / ra**
   - Sau khi quét có kết quả thì không hiển thị danh sách nhân sự chi tiết; danh sách này chỉ hiển thị khi chưa quét.
   - Layout chi tiết theo ca được đưa ra ngay trong danh sách chi tiết; không phải mở danh sách rồi bấm ca để vào thêm một tầng trang chi tiết.
   - Luồng scan/result/back giữ đúng navigation thực tế và không làm UI chớp/reload.
11. **Realtime UI toàn app**
   - Cảnh báo có dữ liệu local xuất hiện gần như tức thì, không chờ 1–2 giây.
   - Thao tác local/UI phản hồi mục tiêu khoảng <=100 ms theo phương án OWNER đã chốt; không chờ round-trip Service để render.
   - Service xử lý/reconcile nền vào state hiện tại; Service chậm không làm UI khựng, reload hoặc chớp giật.
   - Rà soát toàn app: các màn bị tác động giữ realtime UI update mượt và đúng canonical state.

## Blocker
Không có blocker kỹ thuật. Technical DoD PASS; đang chờ OWNER nghiệm thu đúng checklist phía trên.

## Invariants
- Stable/main/signer/authority không đổi.
- APK Beta release/OTA/rollback = GITHUB_RELEASE_ONLY.
- Google Drive không được dùng cho APK; GSheet/GAS nghiệp vụ không bị xóa/thay authority.
- OWNER silence không phải acceptance; chỉ mục OWNER xác nhận OK mới được khóa ACTIVE_PASS.

## NEXT_ACTION
PUBLISH_EXACT_LOCKED_CANDIDATE_THEN_OTA_READBACK

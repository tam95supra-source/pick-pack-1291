# PICK PACK 1291 — HANDOFF SCHEMA V2

- schema_version: 2
- status: READY
- time_utc: 2026-09-05T12:02:14Z
- corrected_owner_checklist_at_utc: 2026-09-05T12:14:00Z
- owner: Nguyễn Văn Tâm
- branch: release/beta126-owner-scope-20260905
- release_trigger_sha: 9b5393986af87c993b647978ccc176929e2c1ed4
- archive_file: docs/handovers/HANDOVER_20260905-120214_beta126-pass-live.md
- owner_scope: OWNER_20260905_CHAT_ORIGINAL_10_PLUS_GLOBAL_REALTIME_BETA126
- owner_scope_source: Anh chat đầu phiên yêu cầu.docx + OWNER chốt 6 điểm ở cuối tài liệu
- owner_checklist_id: BETA126_OWNER_ACCEPTANCE_20260905_R2
- owner_checklist_revision: 2

## Mục tiêu + DoD
Release 0.4.2-beta.126 Technical PASS/LIVE cho yêu cầu OWNER đầu phiên 05/09: 10 mục từ Cài đặt đến Scan QR vào/ra, cộng yêu cầu realtime UI toàn app và 6 điểm OWNER đã chốt. Toàn bộ gate kỹ thuật/release đã PASS; OWNER acceptance còn PENDING.

## LIVE / CANDIDATE / EVIDENCE
- LIVE BETA: 0.4.2-beta.126 / versionCode 132 / package vn.pickpack1291.app.beta.publicbeta.
- CANDIDATE LOCKED: run 33963619992; artifact 9968783758; source 9bfcad4bb218d5865fe6ae220352c44cd4bd8cf0; SHA256 211229dff3bcabc8151b4753914a3439185b5bbfe69fcad9f3faecbfa4fac4bb; size 14461941; signer d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e.
- Full ACTIVE_PASS regression: PASS run 33964356946.
- Visual/PDA/API36 pre-OTA: PASS run 33963619992, artifact 9968868014; 44 screenshots; 320x568 / 360x640 / 480x800 human-inspected PASS.
- Fresh discovery/device: PASS run 33964502604, artifact 9969005524.
- Runtime DoD: PASS run 33964635091, artifact 9969035647.
- Publish + OTA install/readback + finalize: PASS run 33964725581; publish artifact 9969070202; PDA artifact 9969099501; final artifact 9969103461.
- OTA: Beta125 → Beta126 exact bytes qua GitHub Release; rebuild=false; resign=false.
- Stable/main/signer/authority: unchanged.
- Google Drive APK: FORBIDDEN.

## Checklist OWNER nghiệm thu — R2, bám đúng yêu cầu gốc
1. **Cài đặt**
   - Trong Thông tin ứng dụng có Xóa cache và Xóa dữ liệu ứng dụng.
   - Xóa dữ liệu cho phép cả USER; chỉ cần xác nhận, không yêu cầu mật khẩu; chỉ xóa dữ liệu local, đưa app về như mới cài và không xóa Service/server.
   - Sau reset app đồng bộ lại đúng dữ liệu canonical từ Service.
   - Các nhóm cài đặt có màu sắc rõ ràng, dễ phân biệt và bố cục logic.

2. **Lịch sử**
   - Có Xóa toàn bộ cùng hàng với Chọn/Bỏ chọn/Xóa đã chọn; tác dụng trên ngày đang chọn theo quyền/xác thực đã chốt.
   - Search: `Tìm mã nhân viên, họ tên, nghiệp vụ …`.
   - Chọn ngày/search/nút gọn và đồng bộ kích thước, tăng diện tích hiển thị lịch sử.
   - Chi tiết lịch sử thuần Việt, dễ hiểu, bỏ text hướng dẫn OWNER thừa và có đủ thông tin chi tiết hữu ích.

3. **Ba ô Mạng / Đồng bộ / Dịch vụ**
   - Dịch vụ thể hiện nguồn/loại đang dùng thực tế như Cloudflare/LAN; chỉ hiện Không hoạt động/OFFLINE khi thực sự không hoạt động.
   - Mạng có ping cạnh loại mạng.
   - Dữ liệu chờ có xử lý lại từng mục, xử lý lại tất cả/cưỡng ép thử lại an toàn.
   - ADMIN/SUPERADMIN có thể tự thao tác; chỉ cho xóa hẳn mục terminal/stale/không còn giá trị nghiệp vụ, không làm mất mutation chưa commit.

4. **Nhân sự**
   - Gõ search không còn giật/khựng khi dữ liệu lớn.
   - Không rebuild đồng bộ cả danh sách theo từng ký tự; kết quả tìm vẫn đúng.

5. **Hàng rớt**
   - Cột thời gian không tràn xuống 2 dòng.
   - 50 DO/trang; có tiến/lùi trang khi nhiều hơn 50.
   - Bỏ text `Service / D1 xác nhận ngay …`.

6. **Báo cáo tình hình nhân sự**
   - Bỏ `Phạm vi báo cáo`; tiêu đề đúng `Báo cáo tình hình nhân sự`.
   - Select đúng 3 lựa chọn: `Ca 1 và HC` / `C2` / `Cả ngày`, đi cùng chọn ngày-tháng-năm; kích thước gọn, thống nhất toàn app.
   - Tiêu đề bảng và `Vị trí` dùng chữ đậm.
   - Bỏ `Tổng nhân sự` và `Khấu trừ nhân sự`; vùng kết quả mang tiêu đề `Nhân sự pick & pack thực tế sau khi loại trừ hỗ trợ`.
   - Có chi tiết công nhật dưới bảng thâm niên và trên vùng Pick & Pack thực tế: vị trí công nhật + số lượng mỗi vị trí, layout hợp lý.

7. **Công nhật**
   - Không còn cảm giác giật/khựng.
   - Tạo/kết thúc nhiều người không load tuần tự gây đơ; trạng thái hoàn thành cập nhật mượt.
   - Bỏ qua cảnh báo Tổ trưởng/Kéo hàng lưu theo từng NLĐ + phiên/ngày; xử lý một người không ẩn người khác; NLĐ mới vẫn phải được cảnh báo.
   - Cho xử lý riêng/chọn nhiều/chọn tất cả; select không dính nhau, kích thước hợp lý.
   - Có Sửa nhiều cho giờ bắt đầu, giờ kết thúc và tính/không tính khấu trừ.

8. **Đổi / trả PDA**
   - Có thông tin nguồn PDA.
   - Layout Đổi PDA đơn giản, dễ hiểu và không làm sai canonical PDA/session.

9. **Điểm danh**
   - Search hiển thị `Tìm mã nhân viên / họ tên`.
   - Bấm/mở/lọc không reload-like, không nhấp nháy và không giật lag.

10. **Scan QR vào / ra**
   - Sau khi quét có kết quả thì không hiển thị danh sách nhân sự chi tiết; danh sách chỉ hiện khi chưa quét.
   - Layout chi tiết theo ca được đưa ra ngay ở danh sách chi tiết; không phải vào thêm một tầng trang sau khi bấm ca.
   - Luồng scan/result/back không làm UI chớp/reload và giữ navigation thực tế.

11. **Realtime UI toàn app**
   - Cảnh báo có dữ liệu local xuất hiện gần như tức thì, không chờ 1–2 giây.
   - Thao tác local/UI phản hồi mục tiêu khoảng <=100 ms theo phương án OWNER đã chốt; không đợi round-trip Service để render.
   - Service xử lý/reconcile nền vào state hiện tại; Service chậm không làm UI khựng, reload hoặc chớp giật.
   - Rà soát toàn app: các màn bị tác động giữ realtime UI update mượt và đúng canonical state.

## Sai sót checklist đã sửa
- Finalizer cũ đọc `.scope` trong khi request Beta126 dùng `.owner_scope`, nên sinh `scope null`.
- Template handoff còn hardcode evidence/checklist từ continuity scope Beta116→117, khiến checklist 14 mục trộn yêu cầu cũ với release/QR evidence.
- Yêu cầu OWNER thực tế của Beta126 nằm trong `Anh chat đầu phiên yêu cầu.docx`: 10 mục mới + realtime toàn app và 6 điểm chốt.
- Đã sửa `tools/finalize_beta83.sh` để đọc `.owner_scope` và `owner_checklist` trực tiếp từ release request; nếu thiếu checklist thì báo lỗi thay vì tự sinh checklist cũ.
- Đây là sửa tools/docs/metadata; không thay APK/service/GAS bytes, không rebuild/resign và không làm mất Technical PASS Beta126.

## Blocker
Không có blocker kỹ thuật. Technical DoD PASS; chờ OWNER nghiệm thu checklist R2 mục 1–11.

## Invariants
- Stable/main/signer/authority không đổi.
- APK Beta release/OTA/rollback = GITHUB_RELEASE_ONLY.
- OWNER silence không phải acceptance; chỉ mục OWNER xác nhận OK mới được khóa ACTIVE_PASS.

## NEXT_ACTION
WAIT_FOR_OWNER_ACCEPTANCE_NUMBERED_CHECKLIST_1_TO_11

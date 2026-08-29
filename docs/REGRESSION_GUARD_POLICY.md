# REGRESSION GUARD POLICY — APK PICK PACK 1291

OWNER: Nguyễn Văn Tâm

Mục tiêu: mọi sửa lỗi/tính năng phải giữ nguyên các hành vi đang PASS; cấm sửa A làm hỏng B.

## Quy tắc bắt buộc

0. Mọi phiên phải đọc `docs/STABLE_INVARIANTS.md`. Đây là registry tích lũy các hành vi đã PASS/OWNER-lock; mọi change phải lập impact matrix với các invariant ACTIVE liên quan trước khi sửa.

1. Mỗi hành vi đã được OWNER chốt phải được coi là invariant cho tới khi OWNER trực tiếp thay đổi.
2. Mỗi bug đã từng xảy ra phải có regression test tương ứng; bug chỉ được coi là sửa xong khi test đó PASS trên exact candidate.
3. Mỗi quyết định nghiệp vụ quan trọng chỉ có một authority và một helper/canonical decision path. UI không tự suy đoán lại bằng field/cache/fallback khác.
4. Legacy/fallback chỉ được dùng cho hiển thị hoặc tương thích đọc; không được âm thầm quyết định nghiệp vụ nếu authority hiện tại không xác nhận.
5. Khi sửa một failure domain, phải chạy impact matrix của toàn bộ chức năng liên quan trực tiếp, không chỉ test happy path của lỗi vừa sửa.
6. Release không PASS nếu chỉ case mới PASS; mọi invariant liên quan cũ phải tiếp tục PASS trên cùng exact bytes.
7. Không refactor lan rộng. Sửa nhỏ nhất đúng root cause. Nếu cần thay đổi hành vi đã PASS khác, phải dừng và xin OWNER chốt trước.
8. Regression gate phải có cả positive + negative cases, đặc biệt cho các nhánh dễ bị dữ liệu stale/legacy/cache tác động.
9. Sau mỗi task/DoD PASS, phải cập nhật `docs/STABLE_INVARIANTS.md`: thêm hành vi mới đã PASS hoặc cập nhật evidence/last_verified cho invariant cũ. Đây là bước bắt buộc trước handoff/finalizer.
10. Invariant ACTIVE chỉ được đổi business rule khi OWNER Nguyễn Văn Tâm trực tiếp chốt. Implementation có thể đổi nhưng semantics đã khóa phải giữ nguyên.

## Mẫu áp dụng bắt buộc

Business rule duy nhất → authority duy nhất → helper duy nhất → UI chỉ gọi helper → regression matrix khóa hành vi.

## Invariant PDA / Ra ca

- Chỉ kiểm PDA cuối ca khi đúng session hiện tại thực tế có PDA theo authority của chính session đó.
- Session không có PDA → Ra ca trực tiếp, không hiện kiểm PDA.
- PDA đã trả trong session → không kiểm lại.
- pda_serial/cache/legacy stale không được tự biến thành bằng chứng session đang có PDA.
- Nếu dữ liệu authority chưa đủ để quyết định, phải resolve đúng session từ Service; cấm suy đoán từ scalar/cache cũ.
- Regression matrix tối thiểu: active PDA / no PDA / PDA đã trả / stale pda_serial / thiếu assignment snapshot / phiên cũ có PDA nhưng phiên hiện tại không có.

## Áp dụng cho các chức năng khác

Các nhóm QR nhân sự, Điểm danh, Ra ca, Đổi/Trả PDA, User Pick, User Pack, realtime UI, History role, 3 ô Mạng-Đồng bộ-Dịch vụ, OTA/release đều áp dụng cùng policy này.

Policy này chỉ thay đổi khi OWNER Nguyễn Văn Tâm trực tiếp yêu cầu.


## Registry tích lũy

- Canonical: `docs/STABLE_INVARIANTS.md`.
- ACTIVE_PASS = đã có evidence PASS và phải được bảo vệ trong mọi change liên quan.
- LOCKED_REQUIREMENT_PENDING_FIX = OWNER đã khóa rule nhưng implementation hiện chưa đạt; không được giả vờ coi là PASS.
- SUPERSEDED = chỉ dùng khi OWNER trực tiếp thay rule; giữ lịch sử, không xóa.

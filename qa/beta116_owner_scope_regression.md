# Beta116 OWNER scope regression

Status: TECHNICAL_PASS_AWAITING_OWNER.

Executable contract: `tools/beta116_owner_scope_contract.py`.

## OWNER checklist mapping
1. Biên bản: icon CRUD + chọn/xóa/chọn tất cả ảnh nháp + chú thích từng ảnh/trang.
2. Viewer biên bản: vuốt trang + pinch zoom, giữ grouping canonical.
3. PDA: tự lấy 5 số cuối Seri; không nhập tay/không khoảng trắng.
4. Báo cáo nhân sự: Tổng trước khấu trừ; Khấu trừ công nhật; Picker/Packer thực tế.
5. Nhận hàng rớt: CRUD, DO/Số kiện, danh sách chi tiết, chọn/xóa selected có password.
6. Đổi/Trả PDA + Công nhật: local-first, reconcile nền; exact Service session vẫn là authority.
7. Điểm danh + QR vào/ra: lọc Ca/NCC/Vị trí; tìm MNV/họ tên; scan nổi bật.
8. Công nhật: cảnh báo Tổ trưởng/Kéo hàng/5S; không tự sinh; nút nhanh giữ trọng số.
9. SUPERADMIN: đổi mật khẩu từng user sau privileged re-auth.
10. LAN test toàn cục: Service authority + epoch; test traffic tách production route.
11. Tap feedback: transform-only, không layout animation.

## Release/finalizer regression
- Baseline GitHub Release phải dùng `base_candidate_source_sha`, không dùng service source làm APK tag provenance.
- Finalizer phải rebase/fence trước khi render/commit final state.
- Finalizer phải ghi `technical_pass_status=PASS`, `owner_acceptance=PENDING` và NEXT_ACTION owner checklist.
- Không rerun/rebuild/resign APK khi publish+OTA receipts exact bytes đã PASS.
- Nếu một PUBLISH trùng chạy khi exact target đã active, phải read-only PASS/no-op trước mọi GAS mutation; không được restore baseline cũ. Regression từ incident run 33780103076 đã restore 116 → 115.

## Technical evidence
0.4.2-beta.116 Technical PASS/LIVE; candidate source cf01dab16e1c62091561ca008a355a8f49326581; candidate 33767353642/9898290631; Service 33767353642/9898616640; visual+PDA/API36 33774026289/9901071098 + human PASS 43 screenshots 320x568/360x640/480x800; Beta Auth 33776285435/9902148937; device 33778316587/9902571477; runtime 33778605857/9902663700; domain 33778957345/9902758766; Fast Check 33780103022 PASS; publish 33780057070/9903236359; OTA install/open/readback 33780057070/9903336912; SHA256 a346d4554e07fc37552c9d8876179860677fc93923a3bd42f9b3f97f5e11f235; size 14347253; signer d180450ae47ac6e8daf26840308e62bd602d5f8d6ac12ee0da58e5eb1a44731e; Stable/main/authority unchanged.

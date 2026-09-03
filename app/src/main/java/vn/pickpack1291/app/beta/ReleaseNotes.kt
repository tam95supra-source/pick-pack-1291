package vn.pickpack1291.app.beta

object ReleaseNotes {
    const val VERSION_NAME = "0.4.2-beta.116"

    private val current = listOf(
        "Quản lý biên bản dùng icon gọn, chọn/xóa ảnh trước tải, chọn tất cả, chú thích từng ảnh/trang, xem lớn có vuốt trang và pinch zoom.",
        "Tài nguyên PDA tự lấy 5 số cuối Seri từ mã/tên PDA, không nhập tay và không cho khoảng trắng.",
        "Báo cáo nhân sự giữ Tổng trước khấu trừ, tách Khấu trừ công nhật và hiển thị Picker/Packer thực tế sau khấu trừ.",
        "Nhận hàng rớt dùng icon CRUD, DO/Số kiện cùng dòng, có danh sách chi tiết và xóa một/nhiều bản ghi bằng xác nhận mật khẩu.",
        "Đổi/Trả PDA và Công nhật hiển thị dữ liệu local trước rồi reconcile nền; chi tiết Công nhật vẫn xác minh exact-session từ Service.",
        "Điểm danh có tìm MNV/họ tên cùng dòng ngày, ô quét nổi bật và bộ lọc Ca/NCC/Vị trí.",
        "Công nhật có bộ lọc Ca/NCC/Vị trí, cảnh báo kiểm tra các vị trí cố định và bố cục nút tạo/kết thúc nhanh cân đối hơn.",
        "Danh sách QR vào/ra tách rõ khỏi ô quét và có bộ lọc Ca/NCC/Vị trí.",
        "SUPERADMIN có thể đổi mật khẩu từng tài khoản khác sau xác nhận quyền hiện tại; không hiển thị mật khẩu cũ.",
        "LAN test dùng trạng thái Service toàn cục có epoch; các thiết bị online tự theo trạng thái test, trong khi traffic nghiệp vụ thật vẫn cô lập.",
        "Nút, thẻ và vùng bấm chính có phản hồi nhấn nhẹ, ngắn, không dùng animation layout nặng.",
        "Giữ nguyên toàn bộ invariant Beta115 đã được OWNER nghiệm thu OK."
    )

    fun currentItems():List<String> = current.toList()
    fun currentText():String = current.joinToString("\n") { "• $it" }
}

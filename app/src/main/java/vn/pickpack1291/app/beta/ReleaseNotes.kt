package vn.pickpack1291.app.beta

object ReleaseNotes {
    const val VERSION_NAME = "0.4.2-beta.121"

    private val current = listOf(
        "Làm mới 3 ô Mạng / Đồng bộ / Dịch vụ với biểu tượng dễ nhận biết và nội dung chi tiết thuần Việt.",
        "SUPERADMIN chuyển chế độ trải nghiệm USER / ADMIN / SUPERADMIN ngay trong chi tiết Dịch vụ; mọi quyền còn lại hạ theo chế độ đang chọn.",
        "Cài đặt được chia thành các vùng Tài khoản, Giao diện, Ứng dụng & cập nhật, Hỗ trợ & nhật ký rõ ràng hơn.",
        "Thêm thẻ Bảng công Inhouse ở trạng thái chờ phát triển.",
        "Nhận hàng Rớt hiển thị danh sách dạng bảng có ô kẻ và cân bằng nút Chọn tất cả / Xóa đã chọn.",
        "PDA bổ sung trường Nguồn và truyền qua master data với các giá trị danh mục được OWNER quy định.",
        "Giữ nguyên Stable/main/signer/authority và các invariant ACTIVE_PASS ngoài phạm vi thay đổi."
    )

    fun currentItems():List<String> = current.toList()
    fun currentText():String = current.joinToString("\n") { "• $it" }
}

package vn.pickpack1291.app.beta

object ReleaseNotes {
    const val VERSION_NAME = "0.4.2-beta.118"

    private val current = listOf(
        "Quản lý biên bản gọn hơn: nút thao tác cùng hàng, tự ẩn vùng rỗng/chế độ không cần thiết, hỗ trợ sửa và xóa từng hoặc nhiều ảnh.",
        "Viewer biên bản vuốt xuyên giữa các biên bản, vẫn pan X/Y khi zoom và có chế độ toàn màn hình cho ảnh đã chọn hoặc đã tải.",
        "Danh sách biên bản, hàng rớt, QR/điểm danh, công nhật và danh sách lớn render theo lô; Lịch sử debounce tìm kiếm để giảm giật trên PDA yếu.",
        "Select/Spinner được thu gọn toàn app nhưng vẫn giữ vùng chạm phù hợp PDA; bộ lọc không rebuild adapter khi dữ liệu lựa chọn không đổi.",
        "Nhận hàng rớt hiển thị nhất quán HH:mm dd/MM/yyyy | vị trí | DO | số kiện, mới nhất trước; ADMIN/SUPERADMIN được xóa theo xác thực canonical.",
        "Cảnh báo công nhật vị trí cố định hỗ trợ chọn nhiều/chọn tất cả, áp một khoảng giờ cho nhiều NLĐ và chỉ ẩn đúng người đã xác nhận không tính.",
        "LAN thực tế được tách hoàn toàn khỏi LAN test; chỉ SUPERADMIN bật/tắt và có thể bật ngay cả khi Service không phản hồi, sau đó reconcile an toàn.",
        "Phản hồi nhấn được tăng nhẹ so với Beta116 nhưng vẫn chỉ dùng transform ngắn, không animation layout.",
        "PDA serial và SUPERADMIN reset mật khẩu giữ nguyên semantics Beta116 đã OWNER chốt.",
        "Báo cáo nhân sự và local-first Đổi/Trả PDA + Công nhật vẫn giữ trạng thái chờ OWNER nghiệm thu thực tế; không tự promote.",
        "Giữ toàn bộ ACTIVE_PASS Beta115/Beta116 và không thay đổi Stable/main/signer/authority."
    )

    fun currentItems():List<String> = current.toList()
    fun currentText():String = current.joinToString("\n") { "• $it" }
}

package vn.pickpack1291.app.beta

object ReleaseNotes {
    private val current = listOf(
        "Quản lý biên bản: chụp ảnh hoặc chọn ảnh từ máy, chọn loại và tải lên ngay trong thẻ hiện có.",
        "Ảnh được tối ưu rồi tải thẳng Google Drive; Service/D1 chỉ lưu metadata/hash/audit, không lưu file ảnh.",
        "Nếu mạng hoặc Drive gián đoạn, ảnh được giữ an toàn trong hàng chờ trên máy và tự tải lại sau khi kết nối phục hồi.",
        "Hệ thống chặn ảnh trùng tuyệt đối, cảnh báo ảnh gần giống; ảnh xem lại được cache giới hạn để không tăng dung lượng vô hạn.",
        "Có thể thêm loại biên bản; Sửa/Xóa vẫn khóa an toàn chờ OWNER chốt quy tắc dữ liệu cũ."
    )

    fun currentItems():List<String> = current.toList()
    fun currentText():String = current.joinToString("\n") { "• $it" }
}

package vn.pickpack1291.app.beta

object ReleaseNotes {
    private val current = listOf(
        "Quản lý biên bản đã hoạt động trong thẻ hiện có: chụp ảnh hoặc chọn ảnh từ máy, chọn loại và tải lên.",
        "Ảnh được tối ưu trên thiết bị rồi tải thẳng Google Drive; Service/D1 chỉ lưu metadata, có thể xem lại ảnh ngay trong app khi cần.",
        "Hệ thống chặn ảnh trùng tuyệt đối và cảnh báo ảnh gần giống bằng dấu vân tay hình ảnh trước khi tải.",
        "Có thể thêm loại biên bản; Sửa/Xóa đang khóa an toàn chờ OWNER chốt quy tắc bảo toàn dữ liệu và tên file cũ."
    )

    fun currentItems():List<String> = current.toList()
    fun currentText():String = current.joinToString("\n") { "• $it" }
}

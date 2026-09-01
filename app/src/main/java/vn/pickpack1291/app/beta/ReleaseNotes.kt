package vn.pickpack1291.app.beta

object ReleaseNotes {
    private val current = listOf(
        "Quản lý biên bản: chụp ảnh hoặc chọn ảnh từ máy, chọn loại và tải lên ngay trong thẻ hiện có.",
        "Ảnh được tối ưu rồi tải thẳng Google Drive; Service/D1 chỉ lưu metadata/hash/audit, không lưu file ảnh.",
        "Nếu mạng hoặc Drive gián đoạn, ảnh được giữ an toàn trong hàng chờ trên máy và tự tải lại sau khi kết nối phục hồi.",
        "Hệ thống chặn ảnh trùng tuyệt đối, cảnh báo ảnh gần giống; ảnh xem lại được cache giới hạn để không tăng dung lượng vô hạn.",
        "Sửa loại biên bản sẽ đổi tên toàn bộ dữ liệu và file Drive; Xóa sẽ xóa hẳn ảnh + dữ liệu; cả hai dùng mã xác nhận thời gian hiện tại của app."
    )

    fun currentItems():List<String> = current.toList()
    fun currentText():String = current.joinToString("\n") { "• $it" }
}

package vn.pickpack1291.app.beta

object ReleaseNotes {
    private val current = listOf(
        "Danh sách chi tiết nhân sự theo ca được nhóm theo NCC, có bộ lọc Tất cả / Trong ca / Đã ra ca kèm số lượng ngay trên tiêu đề.",
        "Mỗi nhân sự hiển thị gọn họ tên, MNV, vị trí, giờ vào/ra; bỏ chi tiết PDA, User Pick/Pack và thời lượng trong ca.",
        "Chạm vào nhân sự mở trực tiếp luồng Quét QR nhân sự để xử lý Vào/Ra theo MNV đó.",
        "Cài đặt có QR tải ứng dụng: Beta lấy APK công khai mới nhất; Stable tự xuất hiện khi Stable được OWNER phát hành."
    )

    fun currentItems():List<String> = current.toList()
    fun currentText():String = current.joinToString("\n") { "• $it" }
}

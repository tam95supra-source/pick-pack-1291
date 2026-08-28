package vn.pickpack1291.app.beta

object ReleaseNotes {
    private val current = listOf(
        "Đồng bộ danh sách User Pick, User Pack và Bàn Pack khả dụng trực tiếp từ Service để tránh chọn tài nguyên rồi bị báo unavailable.",
        "Giữ nguyên màn hình và lựa chọn đang thao tác khi dữ liệu phiên hoặc snapshot nền về; không tự dựng lại toàn bộ UI nhân viên.",
        "Cập nhật mục phiên bản: hiển thị bản mới nhất, thay đổi của bản mới khi có và thay đổi của bản đang sử dụng."
    )

    fun currentItems():List<String> = current.toList()
    fun currentText():String = current.joinToString("\n") { "• $it" }
}

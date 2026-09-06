package vn.pickpack1291.app.beta

object ReleaseNotes {
    const val VERSION_NAME = "0.4.2-beta.130"
    private val current = listOf(
        "Realtime: cập nhật theo phần thay đổi, không tải lại toàn bộ màn hình khi dữ liệu nền đồng bộ.",
        "Hiệu năng: diễn biến công việc trong ca chỉ thêm hoặc cập nhật đúng thẻ thay đổi, không dựng lại toàn bộ timeline.",
        "Đồng bộ: dùng revision và delta có chỉ mục, gom yêu cầu trùng và chỉ một bộ điều phối nền trên PDA.",
        "Quota: gom thông báo, batch đồng bộ Google Sheets và giới hạn tác vụ phụ theo ngân sách động để giữ trong mức miễn phí.",
        "An toàn dữ liệu: mutation/outbox canonical, ACK fence và cơ chế retry/khôi phục vẫn được giữ nguyên."
    )
    fun currentItems():List<String> = current.toList()
    fun currentText():String = current.joinToString("\n") { "• $it" }
}

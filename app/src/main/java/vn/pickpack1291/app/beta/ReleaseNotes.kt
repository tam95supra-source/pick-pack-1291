package vn.pickpack1291.app.beta

object ReleaseNotes {
    private val current = listOf(
        "Thiết kế lại Trung tâm kiểm thử resilience: chọn từng kịch bản sự cố, giả lập cô lập và tự kiểm PASS/FAIL/recovery.",
        "Test resilience dùng event kỹ thuật riêng, không chặn mạng hoặc đẩy dữ liệu nghiệp vụ thật sang fallback.",
        "3 ô Mạng / Đồng bộ / Dịch vụ mở thông tin chi tiết; Đồng bộ có nút Đồng bộ ngay.",
        "Log thủ công ghi kịch bản, trạng thái, local durability, Google/GAS capture, LAN ACK và lỗi test gần nhất."
    )

    fun currentItems():List<String> = current.toList()
    fun currentText():String = current.joinToString("\n") { "• $it" }
}

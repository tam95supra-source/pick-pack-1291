package vn.pickpack1291.app.beta

object ReleaseNotes {
    const val VERSION_NAME = "0.4.2-beta.128"
    private val current = listOf(
        "Nhận hàng Rớt: ưu tiên cột thời gian, thu gọn Chọn/Vị trí/Số kiện và giữ thời gian hiển thị đầy đủ.",
        "Bỏ tiêu đề lặp cho Scan QR, DO, Số kiện và làm ô nhập nổi bật, dễ nhận biết hơn.",
        "Công nhật và Điểm danh bỏ render trùng local/Service gây nhấp nháy; phần đầu danh sách được cập nhật ngay trong cùng khung hình.",
        "QR vào/ra chỉ dựng lại timeline khi revision ngày thực sự thay đổi; Service reconcile nền không làm chớp chi tiết đang xem."
    )
    fun currentItems():List<String> = current.toList()
    fun currentText():String = current.joinToString("\n") { "• $it" }
}

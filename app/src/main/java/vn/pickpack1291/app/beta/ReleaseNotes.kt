package vn.pickpack1291.app.beta

object ReleaseNotes {
    const val VERSION_NAME = "0.4.2-beta.127"
    private val current = listOf(
        "Sửa đúng nút Xóa dữ liệu ứng dụng: chỉ xóa dữ liệu cục bộ, không xóa dữ liệu chuẩn trên Dịch vụ.",
        "Báo cáo tình hình nhân sự hiển thị tiêu đề rõ ràng và đặt Chi tiết công nhật đúng vị trí trước kết quả Pick & Pack.",
        "Chi tiết công nhật luôn có trạng thái rõ ràng kể cả khi ngày được chọn chưa có công nhật hỗ trợ.",
        "Tăng regression hành vi để lỗi hiển thị không còn được PASS chỉ vì chuỗi tồn tại trong source.",
        "Giữ nguyên tối ưu Nhân sự, Công nhật, Hàng rớt, PDA, Điểm danh, QR và realtime đã có ở Beta126."
    )
    fun currentItems():List<String> = current.toList()
    fun currentText():String = current.joinToString("\n") { "• $it" }
}

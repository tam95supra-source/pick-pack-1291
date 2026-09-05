package vn.pickpack1291.app.beta

object ReleaseNotes {
    const val VERSION_NAME = "0.4.2-beta.126"
    private val current = listOf(
        "Hoàn thiện các vùng màu Cài đặt để phân biệt rõ từng nhóm mà không thay đổi chức năng đã nghiệm thu.",
        "Tối ưu tìm kiếm Nhân sự bằng debounce; giữ danh sách và thao tác phản hồi ổn định trên PDA yếu.",
        "Sửa Báo cáo tình hình nhân sự theo đúng nội dung đã chốt: bỏ tổng/khấu trừ thừa, thêm vùng công nhật theo vị trí và Pick & Pack thực tế sau hỗ trợ.",
        "Công nhật nhiều người chuyển sang xử lý song song có giới hạn, chỉ làm mới UI một lần và bổ sung sửa hàng loạt BĐ/KT/khấu trừ.",
        "Giữ nguyên các mục đã PASS: Lịch sử, hàng đợi đồng bộ, Nhận hàng rớt, Nguồn PDA, Điểm danh local-first, QR và toàn bộ ACTIVE_PASS liên quan."
    )
    fun currentItems():List<String> = current.toList()
    fun currentText():String = current.joinToString("\n") { "• $it" }
}

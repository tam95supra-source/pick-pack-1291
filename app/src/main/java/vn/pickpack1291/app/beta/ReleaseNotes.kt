package vn.pickpack1291.app.beta

object ReleaseNotes {
    private val current = listOf(
        "Căn đều độ rộng cột giữa các bảng Báo cáo nhân sự và làm đường kẻ mảnh hơn.",
        "Chỉ đối chiếu tình trạng PDA khi phiên đang thực sự giữ PDA; phiên không có PDA ra ca trực tiếp.",
        "Đồng nhất cảnh báo phiên cũ chưa bắn ra bằng một nội dung ngắn gọn."
    )

    fun currentItems():List<String> = current.toList()
    fun currentText():String = current.joinToString("\n") { "• $it" }
}

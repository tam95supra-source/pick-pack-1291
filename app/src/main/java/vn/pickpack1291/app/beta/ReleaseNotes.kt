package vn.pickpack1291.app.beta

object ReleaseNotes {
    private val current = listOf(
        "Sửa lỗi Ra ca gửi thiếu mã phiên: ứng dụng tự xác nhận đúng phiên ACTIVE từ Service trước khi gửi.",
        "Chặn thao tác Ra ca lặp trong lúc đang xác nhận/gửi để không phát sinh nhiều request trùng.",
        "Giữ nguyên Stable, signer và authority; không thay đổi dữ liệu hoặc cấu hình đang hoạt động ổn định."
    )

    fun currentItems():List<String> = current.toList()
    fun currentText():String = current.joinToString("\n") { "• $it" }
}

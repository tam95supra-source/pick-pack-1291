package vn.pickpack1291.app.beta

object ReleaseNotes {
    private val current = listOf(
        "Bổ sung bo viền từng kịch bản resilience để dễ phân biệt và chọn đúng tình huống.",
        "Thêm nút Dừng test / Về bình thường; test dừng an toàn trong isolated scope, không chạm dữ liệu nghiệp vụ.",
        "Lịch sử kiểm thử hiển thị dạng thẻ: kết quả, thời gian, giai đoạn, local/Google/LAN/idempotency và lỗi.",
        "Log thủ công xuất tối đa 20 lượt resilience gần nhất thay vì chỉ giữ kết quả cuối."
    )

    fun currentItems():List<String> = current.toList()
    fun currentText():String = current.joinToString("\n") { "• $it" }
}

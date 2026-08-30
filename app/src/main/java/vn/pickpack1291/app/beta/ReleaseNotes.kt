package vn.pickpack1291.app.beta

object ReleaseNotes {
    private val current = listOf(
        "Sửa Đổi / Trả PDA để không còn bị chặn bởi User Pick cũ hoặc trạng thái tài nguyên không liên quan.",
        "Thêm bài test lỗi Service có probe kỹ thuật, kết quả PASS/FAIL thực tế và tự phục hồi sau 30 phút.",
        "Kiểm chứng Service chết → Emergency Ledger, Google/GAS lỗi → Service trực tiếp, cả hai lỗi → giữ local, phục hồi → tự replay."
    )

    fun currentItems():List<String> = current.toList()
    fun currentText():String = current.joinToString("\n") { "• $it" }
}

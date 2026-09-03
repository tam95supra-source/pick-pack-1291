package vn.pickpack1291.app.beta

object ReleaseNotes {
    const val VERSION_NAME = "0.4.2-beta.115"

    private val current = listOf(
        "Công nhật cho phép chọn trước giờ kết thúc trong tương lai theo giới hạn ca/giờ ra thực tế; giờ bắt đầu vẫn không được ở tương lai.",
        "Bộ chọn giờ công nhật dùng phút 00/15/30/45 và quay vòng liên tục cả giờ lẫn phút.",
        "Khôi phục logic Khấu trừ nhân sự: người được khấu trừ được chuyển khỏi vị trí chính sang nhóm Hỗ trợ đúng MNV/ca, không nhân đôi khi có nhiều khoảng.",
        "Ô quét Mã nhân viên luôn nằm trên cùng cả ở danh sách và khi đang xem/chỉnh công nhật của một nhân sự.",
        "Danh sách công nhật theo ngày gom nhiều khoảng của cùng một nhân sự vào một ô; bấm vào mới xem chi tiết từng khoảng.",
        "Thêm tạo công nhật nhanh và kết thúc công nhật nhanh cho nhiều nhân sự, lọc theo từng người, nhà cung cấp và vị trí; cả hai đều yêu cầu xác nhận mật khẩu.",
        "Chuẩn hóa các ô select theo cùng phân cấp tiêu đề, giá trị đang chọn và danh sách lựa chọn; bao gồm lý do không vào ca.",
        "Lịch dùng để xem dữ liệu luôn cho chọn ngày hôm nay dù chưa có dữ liệu; các ngày trống khác vẫn bị làm mờ và khóa.",
        "Giữ nguyên các chức năng Beta114 đã được OWNER nghiệm thu OK và toàn bộ ReviewAlertUi đã khóa."
    )

    fun currentItems():List<String> = current.toList()
    fun currentText():String = current.joinToString("\n") { "• $it" }
}

package vn.pickpack1291.app.beta

object ReleaseNotes {
    const val VERSION_NAME = "0.4.2-beta.113"

    private val current = listOf(
        "Thông tin thay đổi được khóa theo đúng phiên bản ứng dụng; không còn hiển thị changelog của bản cũ sau khi nâng Beta.",
        "Sửa ghi nhận lịch sử đổi mật khẩu: thao tác đổi mật khẩu và bản ghi kiểm toán dùng đúng luồng đồng bộ.",
        "Quản trị cao nhất có thể xóa lịch sử Service và lịch sử lỗi cục bộ bằng xác nhận bảo mật hiện hành; thao tác nghiệp vụ đang chờ gửi không bị hủy ngầm.",
        "Ô quét Mã nhân viên nổi bật hơn; các ô chọn phân tách rõ tiêu đề và giá trị; rà soát ca chỉ hiển thị nhanh vào/ra và danh sách chưa ra.",
        "Công nhật đặt ô quét phía trên danh sách, hỗ trợ nhiều khoảng công nhật trong một phiên nhưng chỉ một khoảng được mở tại một thời điểm.",
        "Lịch dùng để xem dữ liệu chỉ cho chọn ngày thực sự có dữ liệu; ngày trống được làm mờ. Lịch sửa thời gian/ngày nghiệp vụ không bị giới hạn theo quy tắc này.",
        "Chuẩn hóa bán kính, viền và kích thước nhóm điều khiển chính để giao diện nhất quán hơn."
    )

    fun currentItems():List<String> = current.toList()
    fun currentText():String = current.joinToString("\n") { "• $it" }
}

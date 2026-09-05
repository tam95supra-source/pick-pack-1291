package vn.pickpack1291.app.beta

object ReleaseNotes {
    const val VERSION_NAME = "0.4.2-beta.125"
    private val current = listOf(
        "Sửa lịch sử điều hướng QR: màn đang xác nhận/kết quả nhân sự là cùng một bước, Back một lần quay đúng về màn quét trước đó, không mắc ở trạng thái tải trung gian.",
        "Sau khi quét QR có kết quả chỉ hiển thị đúng nhân sự/phiên vừa quét; danh sách nhân sự trong ca chỉ còn ở màn trước khi quét hoặc luồng danh sách riêng.",
        "Cài đặt bổ sung xóa cache và đặt lại toàn bộ dữ liệu cục bộ sau xác nhận; dữ liệu nghiệp vụ chuẩn được đồng bộ lại từ Dịch vụ.",
        "Lịch sử, Đồng bộ và ba ô trạng thái được làm gọn; thêm xóa lịch sử theo ngày, công cụ xử lý hàng đợi cho quản trị, hiển thị loại Dịch vụ và độ trễ mạng.",
        "Tối ưu tìm kiếm, điểm danh, quét QR và công nhật theo local-first để giảm khựng, chớp và dựng lại màn hình; cảnh báo công nhật được khóa theo đúng từng người/phiên/ngày.",
        "Báo cáo nhân sự, Nhận hàng rớt và Đổi/Trả PDA được chỉnh bố cục, nội dung và thông tin Nguồn PDA theo yêu cầu OWNER.",
        "Giữ nguyên Stable/main/signer/authority và các invariant ACTIVE_PASS ngoài phạm vi sửa."
    )
    fun currentItems():List<String> = current.toList()
    fun currentText():String = current.joinToString("\n") { "• $it" }
}

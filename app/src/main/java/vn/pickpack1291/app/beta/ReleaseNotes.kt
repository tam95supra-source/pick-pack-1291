package vn.pickpack1291.app.beta

object ReleaseNotes {
    const val VERSION_NAME = "0.4.2-beta.119"

    private val current = listOf(
        "Giữ phiên đăng nhập hợp lệ qua cập nhật APK/khởi động lại app; không tự xóa token khi mở app, nhưng đăng xuất/401/revoke vẫn có hiệu lực.",
        "SUPERADMIN có thể dùng chuỗi tối đa 20 ký tự chứa giờ HHmm thực tế trong khoảng ±5 phút, không ràng buộc thiết bị.",
        "Cách thứ hai là mật khẩu một lần 8 chữ số gửi email; mỗi mã chỉ dùng một lần và sau khi dùng thành công hệ thống tự phát sinh/gửi mã kế tiếp.",
        "Đăng nhập bằng giờ không phát sinh email OTP mới; kiểm tra HHmm ±5 phút và giới hạn độ dài được thực hiện lại phía server.",
        "beta/current, checklist OWNER và guard bảo mật được khóa theo trạng thái monotonic để phiên chat cũ không ghi đè Beta/checklist mới.",
        "Không lưu mật khẩu, OTP, session token hoặc Gmail OAuth secret trong GitHub public/log/artifact/handoff.",
        "Giữ nguyên Stable/main/signer/authority và toàn bộ hành vi Beta118 ngoài scope xác thực/control-plane."
    )

    fun currentItems():List<String> = current.toList()
    fun currentText():String = current.joinToString("\n") { "• $it" }
}

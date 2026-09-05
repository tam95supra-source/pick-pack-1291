package vn.pickpack1291.app.beta

object ReleaseNotes {
    const val VERSION_NAME = "0.4.2-beta.122"

    private val current = listOf(
        "Khi SUPERADMIN chuyển sang USER hoặc ADMIN, toàn bộ menu, màn hình và thao tác nghiệp vụ hạ đúng quyền thực tế; chỉ bộ chọn quyền trong chi tiết Dịch vụ vẫn tồn tại để chuyển lại.",
        "PDA hiển thị Nguồn trong thông tin chọn/đang dùng, xác nhận đổi-trả và danh sách PDA ở Tài nguyên; ADMIN có thể chọn Nguồn từ danh mục canonical khi thêm/sửa PDA.",
        "Giữ nguyên hai mục OWNER đã nghiệm thu ở Beta121: ba ô Mạng / Đồng bộ / Dịch vụ và bố cục Cài đặt / Bảng công Inhouse / bảng Nhận hàng Rớt.",
        "Giữ nguyên Stable/main/signer/authority và toàn bộ invariant ACTIVE_PASS ngoài phạm vi sửa."
    )

    fun currentItems():List<String> = current.toList()
    fun currentText():String = current.joinToString("\n") { "• $it" }
}

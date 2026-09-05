from pathlib import Path
import re

def txt(p): return Path(p).read_text(encoding='utf-8')
def fn(src,name):
    start=src.find(f'private fun {name}(')
    assert start>=0,name
    nxt=src.find('\n    private fun ',start+20)
    return src[start:] if nxt<0 else src[start:nxt]

ops=txt('app/src/main/java/vn/pickpack1291/app/beta/OperationsActivity.kt')
drop=txt('app/src/main/java/vn/pickpack1291/app/beta/DropReceiveFeature.kt')
meal=txt('app/src/main/java/vn/pickpack1291/app/beta/PostMealAttendanceFeature.kt')
store=txt('app/src/main/java/vn/pickpack1291/app/beta/OperationalDataStore.kt')
gradle=txt('app/build.gradle.kts')
notes=txt('app/src/main/java/vn/pickpack1291/app/beta/ReleaseNotes.kt')
qa=txt('qa/beta123_owner_scope_regression.md')

# Exact Beta126 identity. Stable remains outside this patch scope.
assert 'versionCode = 132' in gradle
assert 'versionName = "0.4.2-beta.126"' in gradle
assert 'VERSION_NAME = "0.4.2-beta.126"' in notes

# Settings: actual rendered region fill must remain distinct; universal local reset/cache retained.
settings=fn(ops,'settingsScreen')
assert 'setColor(when(title)' in settings
for s in ['Color.rgb(239,248,255)','Color.rgb(242,252,247)','Color.rgb(255,248,237)','XÓA CACHE','ĐẶT LẠI DỮ LIỆU']:
    assert s in settings,(s,'settings')
assert 'clearApplicationUserData' in ops
assert 'không xóa dữ liệu trên Dịch vụ' in ops

# History and sync recovery already passed: guard them against regression.
history=fn(ops,'historyScreen')
assert 'Tìm mã nhân viên, họ tên, nghiệp vụ …' in history
for s in ['XÓA TOÀN BỘ','XÓA ĐÃ CHỌN','BỎ CHỌN','CHỌN']:
    assert s in history,s
assert 'deleteHistoryBulk(all)' in history
for s in ['queueRecoveryItems','retryQueue','deleteTerminalQueue']:
    assert s in store,s
assert "status IN ('REJECTED','REVIEW_REQUIRED','CONFLICT','FAILED','ERROR')" in store
assert 'XỬ LÝ HÀNG ĐỢI' in ops and 'CƯỠNG ÉP THỬ LẠI' in ops

# Header: transport + ping and provider/route retained even when degraded.
assert '• ${ping}ms' in ops
assert 'LanAuthorityPolicy.HealthState.DEGRADED->provider.ifBlank' in ops
assert '"Cloudflare"' in ops and '"Không hoạt động"' in ops

# Staff: debounce required; direct synchronous per-character rebuild forbidden.
staff=fn(ops,'staffScreen')
assert 'staffSearchGeneration' in staff
assert 'postDelayed' in staff and '180L' in staff
assert '{render(v?.toString().orEmpty())}' not in staff

# Drop receive passed scope.
assert 'dropPageSize=50' in drop
assert '50 TRƯỚC' in drop and '50 TIẾP' in drop
assert 'Service/D1 xác nhận ngay' not in drop

# Report exact OWNER semantics.
report=fn(ops,'reportScreen')
assert 'BÁO CÁO TÌNH HÌNH NHÂN SỰ' in report
assert 'spinner(arrayOf("Ca 1 và HC","C2","Cả ngày"))' in report
assert 'NHÂN SỰ PICK & PACK THỰC TẾ SAU KHI LOẠI TRỪ HỖ TRỢ' in report
assert 'CHI TIẾT CÔNG NHẬT' in report
assert 'Công nhật theo vị trí' in report
assert '"Tổng nhân sự" to' not in report
assert '"Khấu trừ công nhật" to' not in report

# Labor: acknowledgement remains employee/session scoped; batch is bounded-parallel, not recursive sequential.
assert 'fun laborAckKey(s:JSONObject)' in ops
assert 'return "$mnv|${sid.ifBlank{enter}}"' in ops
create=fn(ops,'showLaborBatchCreateForm')
finish=fn(ops,'showLaborBatchFinishForm')
assert 'runBoundedLaborBatch(chosen,6' in create
assert 'runBoundedLaborBatch(chosen,6' in finish
assert 'fun next(index:Int,ok:Int)' not in create
assert 'fun next(index:Int,ok:Int)' not in finish
assert 'laborLocalUiRefresh?.invoke()' not in create
assert 'laborLocalUiRefresh?.invoke()' not in finish
assert 'SỬA NHIỀU' in ops
edit=fn(ops,'showLaborBatchEditForm')
for s in ['Áp dụng cùng giờ bắt đầu','Áp dụng cùng giờ kết thúc','Giữ nguyên khấu trừ','Có khấu trừ','Không khấu trừ','correction','deduct_staff']:
    assert s in edit,s
assert 'KEO HANG' in edit and 'TO TRUONG' in edit

# PDA/attendance/QR previously proven behavior must remain.
assert 'Nguồn' in fn(ops,'confirmPdaHandoverCondition')
assert 'Tìm mã nhân viên / họ tên' in meal
assert 'payload=store.load(date.toString());render();remoteLoad()' in meal
scan=fn(ops,'employeeScan')
assert 'preScanStaff.visibility=View.GONE' in scan
active=fn(ops,'renderActive')
assert 'sessionInfoPanel("THÔNG TIN CA"' in active
assert 'sessionInfoPanel("THÔNG TIN CÔNG VIỆC"' in active

# QA must explicitly record the repaired gaps instead of relying on string-presence-only Beta123 checks.
assert '## Beta126 remediation — OWNER DOCX scope audit' in qa
assert 'no recursive per-person `next(index,ok)` chain' in qa

print('BETA126_OWNER_SCOPE_CONTRACT_PASS')

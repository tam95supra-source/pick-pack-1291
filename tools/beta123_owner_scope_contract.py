from pathlib import Path
import re

def txt(p): return Path(p).read_text(encoding='utf-8')
def fn(src,name):
    start=src.find(f'private fun {name}(')
    assert start>=0,name
    nxt=src.find('\n    private fun ',start+20)
    return src[start:] if nxt<0 else src[start:nxt]
def generic_fn(src,signature):
    start=src.find(signature)
    assert start>=0,signature
    nxt=src.find('\n    private fun ',start+len(signature))
    return src[start:] if nxt<0 else src[start:nxt]

ops=txt('app/src/main/java/vn/pickpack1291/app/beta/OperationsActivity.kt')
drop=txt('app/src/main/java/vn/pickpack1291/app/beta/DropReceiveFeature.kt')
meal=txt('app/src/main/java/vn/pickpack1291/app/beta/PostMealAttendanceFeature.kt')
store=txt('app/src/main/java/vn/pickpack1291/app/beta/OperationalDataStore.kt')
gradle=txt('app/build.gradle.kts')
notes=txt('app/src/main/java/vn/pickpack1291/app/beta/ReleaseNotes.kt')
qa=txt('qa/beta123_owner_scope_regression.md')
qa127=txt('qa/beta127_owner_r2_regression.md')

# Current Beta identity must stay internally consistent; do not hardcode a prior Beta.
version_code=re.search(r'versionCode\s*=\s*(\d+)',gradle)
version_name=re.search(r'versionName\s*=\s*"([^"]+)"',gradle)
assert version_code and int(version_code.group(1))>0
assert version_name and re.fullmatch(r'0\.4\.2-beta\.\d+',version_name.group(1))
assert f'VERSION_NAME = "{version_name.group(1)}"' in notes

# 1 Settings: visually distinct groups + user-safe local cache/data reset semantics.
settings=fn(ops,'settingsScreen')
assert 'setColor(when(title)' in settings
for s in ['Color.rgb(239,248,255)','Color.rgb(242,252,247)','Color.rgb(255,248,237)','XÓA CACHE','XÓA DỮ LIỆU ỨNG DỤNG']:
    assert s in settings,(s,'settings')
assert 'clearApplicationUserData' in ops
assert 'không xóa dữ liệu trên Dịch vụ' in ops
assert 'ĐẶT LẠI DỮ LIỆU' not in settings
assert 'Xóa dữ liệu ứng dụng?' in ops

# 2 History: exact search text, compact actions, selected-day delete and canonical destructive path.
history=fn(ops,'historyScreen')
assert 'Tìm mã nhân viên, họ tên, nghiệp vụ …' in history
for s in ['XÓA TOÀN BỘ','XÓA ĐÃ CHỌN','BỎ CHỌN','CHỌN']:
    assert s in history,s
assert 'deleteHistoryBulk(all)' in history

# 3 Network/sync/service: route + ping remain visible and queue recovery cannot delete uncommitted pending mutations.
for s in ['queueRecoveryItems','retryQueue','deleteTerminalQueue']:
    assert s in store,s
assert "status IN ('REJECTED','REVIEW_REQUIRED','CONFLICT','FAILED','ERROR')" in store
assert 'XỬ LÝ HÀNG ĐỢI' in ops and 'CƯỠNG ÉP THỬ LẠI' in ops
assert 'Giữ nguyên Event ID' in ops
assert 'Mục đang chờ gửi không thể bị xóa' in ops
assert '• ${ping}ms' in ops
header=fn(ops,'refreshHeaderConnection')
assert 'LanAuthorityPolicy.HealthState.DEGRADED->serviceProviderFromRuntime().ifBlank' in header
assert '"Cloudflare"' in ops and '"Không hoạt động"' in ops

# 4 Staff: bounded first page/search result + debounce; no synchronous rebuild on every key stroke.
staff=fn(ops,'staffScreen')
assert 'var pageSize=60' in staff
assert 'val limit=if(clean.isBlank())pageSize else 180' in staff
assert 'staffSearchGeneration' in staff
assert 'postDelayed' in staff and '180L' in staff
assert '{render(v?.toString().orEmpty())}' not in staff

# 5 Drop receive: 50/page, chunked render, one-line timestamps, obsolete Service/D1 sentence removed.
assert 'dropPageSize=50' in drop
assert '50 TRƯỚC' in drop and '50 TIẾP' in drop
assert 'dropList.post{addDropChunk(0)}' in drop and 'from+20' in drop
assert 'maxLines=if(header)2 else 1' in drop
assert 'HH:mm dd/MM/yyyy' in drop
assert 'Service/D1 xác nhận ngay' not in drop

# 6 Report: exact OWNER visible structure and ordering.
report=fn(ops,'reportScreen')
assert 'body.addView(txt("BÁO CÁO TÌNH HÌNH NHÂN SỰ"' in report
assert 'spinner(arrayOf("Ca 1 và HC","C2","Cả ngày"))' in report
assert 'NHÂN SỰ PICK & PACK THỰC TẾ SAU KHI LOẠI TRỪ HỖ TRỢ' in report
assert 'CHI TIẾT CÔNG NHẬT' in report
assert 'Công nhật theo vị trí' in report
assert report.index('section("CHI TIẾT CÔNG NHẬT")') < report.index('section("NHÂN SỰ PICK & PACK THỰC TẾ SAU KHI LOẠI TRỪ HỖ TRỢ")')
assert 'Không có công nhật hỗ trợ trong phạm vi đã chọn.' in report
assert '"Tổng nhân sự" to' not in report
assert '"Khấu trừ công nhật" to' not in report

# 7 Labor: per-employee/session acknowledgement + bounded parallel create/finish/edit; bulk fields remain complete.
assert 'fun laborAckKey(s:JSONObject)' in ops
assert 'return "$mnv|${sid.ifBlank{enter}}"' in ops
batch=generic_fn(ops,'private fun <T> runBoundedLaborBatch(')
assert 'maxInFlight:Int=6' in batch and 'running<maxInFlight' in batch
create=fn(ops,'showLaborBatchCreateForm');finish=fn(ops,'showLaborBatchFinishForm')
assert 'runBoundedLaborBatch(chosen,6' in create and 'runBoundedLaborBatch(chosen,6' in finish
assert 'fun next(index:Int,ok:Int)' not in create and 'fun next(index:Int,ok:Int)' not in finish
assert 'laborLocalUiRefresh?.invoke()' not in create and 'laborLocalUiRefresh?.invoke()' not in finish
assert 'SỬA NHIỀU' in ops
edit=fn(ops,'showLaborBatchEditForm')
for s in ['Áp dụng cùng giờ bắt đầu','Áp dụng cùng giờ kết thúc','Giữ nguyên khấu trừ','Có khấu trừ','Không khấu trừ','correction','deduct_staff']:
    assert s in edit,s
assert 'KEO HANG' in edit and 'TO TRUONG' in edit

# 8 PDA exchange: canonical PDA source is rendered in assignment and handover confirmation.
assert 'Nguồn' in fn(ops,'confirmPdaHandoverCondition')
assert 'val source=if(t=="PDA")pdaSourceBySerial(id)' in fn(ops,'resourceListText')
assert '• Nguồn: ${source.ifBlank{"—"}}' in fn(ops,'resourceListText')

# 9 Attendance: exact search, local snapshot first, debounced filter and targeted realtime callback.
assert 'Tìm mã nhân viên / họ tên' in meal
assert 'payload=store.load(date.toString());render();remoteLoad()' in meal
assert 'main.postDelayed(it,140L)' in meal
assert 'if(activeDate==date)activeRefresh?.invoke()' in meal

# 10 QR: post-scan roster hidden; session/work detail is inline in result, not another drill-down layer.
scan=fn(ops,'employeeScan')
assert 'preScanStaff.visibility=View.GONE' in scan
active=fn(ops,'renderActive')
assert 'sessionInfoPanel("THÔNG TIN CA"' in active
assert 'sessionInfoPanel("THÔNG TIN CÔNG VIỆC"' in active

# 11 Realtime: foreground invalidation routes directly to local targeted callbacks; no full-screen refresh/poll wait is introduced.
listener=ops[ops.index('override fun onDayInvalidation'):ops.index('override fun onAuthExpired')]
for s in ['OldSessionWarningFeature.onRealtime()','PostMealAttendanceFeature.onRealtimeFast(date)','laborWarningRealtimeRefresh?.invoke()','laborLocalUiRefresh?.invoke()']:
    assert s in listener,s
assert 'Thread.sleep' not in listener and 'postDelayed' not in listener
assert 'employeeTimelineRealtimeRefresh' in ops and 'businessFastRealtimeRefresh' in ops

# Regression record explicitly documents the false-positive class and exact-device proof requirement.
assert '## Beta126 remediation — OWNER DOCX scope audit' in qa
assert 'no recursive per-person `next(index,ok)` chain' in qa
assert 'Settings rendered `ĐẶT LẠI DỮ LIỆU`' in qa127
assert 'Exact-device instrumentation sees the new Settings label' in qa127

print('BETA127_OWNER_R2_CONTRACT_PASS')

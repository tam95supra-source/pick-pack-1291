from pathlib import Path

def txt(p): return Path(p).read_text(encoding='utf-8')
ops=txt('app/src/main/java/vn/pickpack1291/app/beta/OperationsActivity.kt')
drop=txt('app/src/main/java/vn/pickpack1291/app/beta/DropReceiveFeature.kt')
meal=txt('app/src/main/java/vn/pickpack1291/app/beta/PostMealAttendanceFeature.kt')
store=txt('app/src/main/java/vn/pickpack1291/app/beta/OperationalDataStore.kt')
gradle=txt('app/build.gradle.kts'); notes=txt('app/src/main/java/vn/pickpack1291/app/beta/ReleaseNotes.kt')
need={
 'beta123':['versionCode = 129','versionName = "0.4.2-beta.123"'],
 'notes':['VERSION_NAME = "0.4.2-beta.123"'],
 'settings':['confirmClearCache','confirmResetLocalAppData','clearApplicationUserData','XÓA CACHE','ĐẶT LẠI DỮ LIỆU','không xóa dữ liệu trên Dịch vụ'],
 'history':['Tìm mã nhân viên, họ tên, nghiệp vụ …','XÓA TOÀN BỘ','deleteHistoryBulk(all)','selectedHistoryIds'],
 'status':['Cloudflare','Không hoạt động','ms'],
 'queue':['queueRecoveryItems','retryQueue','deleteTerminalQueue'],
 'queue_ui':['showSyncQueueRecoveryDialog','XỬ LÝ HÀNG ĐỢI','CƯỠNG ÉP THỬ LẠI','XÓA HẲN LỖI ĐÃ DỪNG'],
 'report':['BÁO CÁO TÌNH HÌNH NHÂN SỰ','Ca 1 và HC','C2','Cả ngày'],
 'labor':['laborAckKey'],
 'qr':['preScanStaff.visibility=View.GONE'],
 'attendance':['Tìm mã nhân viên / họ tên'],
 'drop':['dropPageSize=50']
}
for x in need['beta123']: assert x in gradle,x
for x in need['notes']: assert x in notes,x
for k in ['settings','history','status','queue_ui','report','labor','qr']:
 for x in need[k]: assert x in ops,(k,x)
for x in need['queue']: assert x in store,x
for x in need['attendance']: assert x in meal,x
for x in need['drop']: assert x in drop,x
assert 'Service/D1 xác nhận ngay' not in drop
assert 'historyRowsForDate' not in ops
# Queue deletion must be terminal-only and cannot erase a still-pending business mutation.
assert "status IN ('REJECTED','REVIEW_REQUIRED','CONFLICT','FAILED','ERROR')" in store
assert "status!='CONFIRMED'" in store
# Existing role/security/realtime guards must remain.
for x in ['if(!isAdmin())','if(!isSuper())','renderEmployeeIfChanged','SUPERADMIN','deleteHistoryBulk(selectedHistoryIds.toList())']:
 assert x in ops,x
print('BETA123_OWNER_SCOPE_CONTRACT_PASS')

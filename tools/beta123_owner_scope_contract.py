from pathlib import Path
import re

def txt(p): return Path(p).read_text(encoding='utf-8')
ops=txt('app/src/main/java/vn/pickpack1291/app/beta/OperationsActivity.kt')
drop=txt('app/src/main/java/vn/pickpack1291/app/beta/DropReceiveFeature.kt')
meal=txt('app/src/main/java/vn/pickpack1291/app/beta/PostMealAttendanceFeature.kt')
store=txt('app/src/main/java/vn/pickpack1291/app/beta/OperationalDataStore.kt')
gradle=txt('app/build.gradle.kts'); notes=txt('app/src/main/java/vn/pickpack1291/app/beta/ReleaseNotes.kt')
need={
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
# Beta123 is the minimum baseline. Later Betas inherit all scope assertions without pinning
# the exact version number, while ReleaseNotes must still match the current Beta version.
beta_block=gradle[gradle.index('create("beta")'):gradle.index('create("stable")')]
code_match=re.search(r'versionCode = (\d+)',beta_block)
name_match=re.search(r'versionName = "0\.4\.2-beta\.(\d+)"',beta_block)
assert code_match and int(code_match.group(1))>=129, code_match.group(1) if code_match else 'versionCode missing'
assert name_match and int(name_match.group(1))>=123, name_match.group(1) if name_match else 'versionName missing'
current_version=f'0.4.2-beta.{name_match.group(1)}'
assert f'VERSION_NAME = "{current_version}"' in notes,current_version
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
print(f'BETA123_OWNER_SCOPE_CONTRACT_PASS baseline=beta123 current={current_version}')

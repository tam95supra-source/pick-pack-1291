#!/usr/bin/env python3
from pathlib import Path
root=Path(__file__).resolve().parents[1]
read=lambda p:(root/p).read_text(encoding="utf-8")
ops=read("app/src/main/java/vn/pickpack1291/app/beta/OperationsActivity.kt")
old=read("app/src/main/java/vn/pickpack1291/app/beta/OldSessionWarningFeature.kt")
doc=read("app/src/main/java/vn/pickpack1291/app/beta/DocumentManagementFeature.kt")
drop=read("app/src/main/java/vn/pickpack1291/app/beta/DropReceiveFeature.kt")
meal=read("app/src/main/java/vn/pickpack1291/app/beta/PostMealAttendanceFeature.kt")
fg=read("app/src/main/java/vn/pickpack1291/app/beta/ForegroundSyncCoordinator.kt")
service=read("service/src/mobile_hotfix.ts")
gradle=read("app/build.gradle.kts")
notes=read("app/src/main/java/vn/pickpack1291/app/beta/ReleaseNotes.kt")
assert 'versionCode = 124' in gradle and 'versionName = "0.4.2-beta.118"' in gradle
assert 'const val VERSION_NAME = "0.4.2-beta.118"' in notes
assert 'versionCode = 1' in gradle and 'versionName = "0.1.0-stable"' in gradle
for t in ['old_active_sessions_bulk_exit','SUPERADMIN_REQUIRED','HAS_LABOR','pda_auto_confirmed','commitMutation(env.DB,env,auth']:
    assert t in service,t
assert 'verifyTimePasswordOnly' in ops and 'RA CA TẤT CẢ HỢP LỆ' in old
assert 'Mật khẩu thời gian HHmm' in ops and '(-2L..2L)' in ops
assert 'Biên bản • vuốt mọi ảnh / pinch / kéo ảnh' not in doc
assert 'R.drawable.ic_pp_sync,teal,"Làm mới biên bản"' in doc
assert 'Xóa ảnh chưa tải lên?' in doc
assert 'val viewerActions=row()' in doc and 'val save=button("LƯU"' in doc and 'val close=button("ĐÓNG"' in doc
assert 'Xóa toàn bộ' not in drop and 'clearBtn' not in drop
assert 'dropPageSize=50' in drop and '50 TIẾP' in drop
assert 'DO: ${x.optString' not in drop and 'Số kiện: ${x.optInt' not in drop
assert 'text("NHẬN HÀNG RỚT"' not in drop and 'text("ĐIỂM DANH",15f' not in meal
assert 'fun onDayInvalidation' in fg and 'listener.onDayInvalidation' in fg
assert 'businessFastRealtimeRefresh' in ops and 'laborRealtimeRefresh' in ops and 'onRealtimeFast' in meal
assert 'patchLaborCacheOptimistic' in ops
print("beta118_owner_followup_contract=PASS bulk_exit=PASS seed_receipt=EXTERNAL realtime=PASS document=PASS drop=PASS")

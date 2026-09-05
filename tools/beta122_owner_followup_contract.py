#!/usr/bin/env python3
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
ops=(ROOT/'app/src/main/java/vn/pickpack1291/app/beta/OperationsActivity.kt').read_text(encoding='utf-8')
gradle=(ROOT/'app/build.gradle.kts').read_text(encoding='utf-8')
notes=(ROOT/'app/src/main/java/vn/pickpack1291/app/beta/ReleaseNotes.kt').read_text(encoding='utf-8')
drop=(ROOT/'app/src/main/java/vn/pickpack1291/app/beta/DropReceiveFeature.kt').read_text(encoding='utf-8')

assert 'versionCode = 128' in gradle and 'versionName = "0.4.2-beta.122"' in gradle
assert 'const val VERSION_NAME = "0.4.2-beta.122"' in notes

# OWNER item 2: actual SUPERADMIN is only the authority behind the role selector itself.
assert 'private fun isActualSuper() = actualRole == "SUPERADMIN"' in ops
assert ops.count('isActualSuper()') == 3, ops.count('isActualSuper()')
assert 'normalized=="SERVICE"&&isActualSuper()' in ops
assert 'if(!isActualSuper())return@setOnClickListener' in ops
assert 'if(target=="HISTORY"&&!isAdmin())' in ops
assert '"HISTORY"->if(isAdmin())historyScreen() else {module="BUSINESS";businessHome()}' in ops
assert '"ROLE_MODE"->businessHome()' in ops
assert 'private fun rebuildBottomNav()' in ops
assert 'host.removeAllViews()' in ops and 'host.addView(bottomNav(),FrameLayout.LayoutParams(-1,-1))' in ops
assert 'screenBackStack.clear()' in ops and 'tabHistory.clear()' in ops
for forbidden in (
    'if(!isActualSuper()){showError("Chỉ SUPERADMIN được thực hiện thao tác này.")',
    'if(!isActualSuper()){showError("Chỉ SUPERADMIN được bật/tắt LAN thủ công.")',
    'if(!isActualSuper()){showError("Chỉ SUPERADMIN được thay đổi chế độ LAN test toàn cục.")',
    'if(!isActualSuper()){showError("SUPERADMIN_REQUIRED")',
):
    assert forbidden not in ops

# OWNER item 4: source must be visible and editable in Android, not only present in backend/GSheet.
assert 'private fun pdaSourceBySerial(serial:String):String' in ops
assert ' • Nguồn: ${source.ifBlank{"—"}}' in ops
assert 'Serial PDA\\nChưa chọn\\nNguồn\\n—\\nTình trạng PDA' in ops
assert 'Nguồn: ${source.ifBlank{"—"}} • Tình trạng:' in ops
assert '"Nguồn" to source.ifBlank{"—"}' in ops
assert 'private fun resourcePdaSourceValues(catalogs:JSONArray?)' in ops
assert 'val ns="DANH SÁCH PDA_Nguồn"' in ops
assert 'add("Nguồn PDA",sourceSp)' in ops
assert 'showError("Chọn Nguồn PDA.")' in ops
assert '.put("Nguồn",source)' in ops
assert '"Nguồn: ${dash(meta.optString("Nguồn").ifBlank{x.optString("source")})}"' in ops

# Preserve OWNER-accepted Beta121 item 1 semantics.
for label in ('Mạng','Đồng bộ','Dịch vụ'):
    assert label in ops
for kind in ('"NETWORK"','"SYNC"','"SERVICE"'):
    assert kind in ops
assert '"Thông tin mạng"' in ops and '"Thông tin đồng bộ"' in ops and '"Thông tin dịch vụ"' in ops
assert 'setNeutralButton("ĐỒNG BỘ NGAY")' in ops and 'manualRefreshFromHeader(syncStatusText?:host)' in ops

# Preserve OWNER-accepted Beta121 item 3 semantics.
for label in ('TÀI KHOẢN & QUYỀN','GIAO DIỆN','ỨNG DỤNG & CẬP NHẬT','HỖ TRỢ & NHẬT KÝ'):
    assert label in ops
assert 'businessCard(R.drawable.ic_pp_task,"Bảng công Inhouse","Chờ phát triển",false)' in ops
assert 'addTableHeader()' in drop and 'setStroke(dp(1),border)' in drop
assert drop.count('LinearLayout.LayoutParams(0,dp(44),.95f)') >= 2

print('BETA122_OWNER_FOLLOWUP_CONTRACT_PASS')

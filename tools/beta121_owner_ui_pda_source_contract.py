#!/usr/bin/env python3
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
ops=(ROOT/"app/src/main/java/vn/pickpack1291/app/beta/OperationsActivity.kt").read_text(encoding="utf-8")
drop=(ROOT/"app/src/main/java/vn/pickpack1291/app/beta/DropReceiveFeature.kt").read_text(encoding="utf-8")
gradle=(ROOT/"app/build.gradle.kts").read_text(encoding="utf-8")
notes=(ROOT/"app/src/main/java/vn/pickpack1291/app/beta/ReleaseNotes.kt").read_text(encoding="utf-8")
gas=(ROOT/"google-apps-script/PICK_PACK_API.gs").read_text(encoding="utf-8")
service=(ROOT/"service/src/mobile_hotfix.ts").read_text(encoding="utf-8")

assert 'versionCode = 127' in gradle and 'versionName = "0.4.2-beta.121"' in gradle
assert 'const val VERSION_NAME = "0.4.2-beta.121"' in notes

for label in ("Mạng","Đồng bộ","Dịch vụ"):
    assert label in ops
for kind in ('"NETWORK"','"SYNC"','"SERVICE"'):
    assert kind in ops
assert "Thông tin mạng" in ops and "Thông tin đồng bộ" in ops and "Thông tin dịch vụ" in ops

assert 'Triple(R.drawable.ic_pp_account,"Quyền","ROLE_MODE")' not in ops
assert 'normalized=="SERVICE"&&isActualSuper()' in ops
assert 'private lateinit var actualRole: String' in ops
assert 'private fun isActualSuper() = actualRole == "SUPERADMIN"' in ops
assert 'role=value' in ops and 'effectiveRole=value' in ops
assert 'listOf("USER" to "USER","ADMIN" to "ADMIN","SUPERADMIN" to "SUPERADMIN")' in ops

for label in ("TÀI KHOẢN & QUYỀN","GIAO DIỆN","ỨNG DỤNG & CẬP NHẬT","HỖ TRỢ & NHẬT KÝ"):
    assert label in ops
assert 'background=GradientDrawable().apply{setColor(Color.rgb(248,250,252))' in ops
assert ops.count('addVersionChangelog(appRegion,') >= 2
assert 'addVersionChangelog(body,"THAY ĐỔI BẢN HIỆN TẠI"' not in ops

assert 'businessCard(R.drawable.ic_pp_task,"Bảng công Inhouse","Chờ phát triển",false)' in ops

assert 'LinearLayout.LayoutParams(0,dp(44),.95f)' in drop
assert drop.count('LinearLayout.LayoutParams(0,dp(44),.95f)') >= 2
for header in ('"Thời gian"','"Vị trí"','"DO"','"Số kiện"'):
    assert header in drop
assert 'setStroke(dp(1),border)' in drop and 'addTableHeader()' in drop

assert "source:r['Nguồn']||''" in gas
assert 'source:String(m["Nguồn"]||m["source"]||"")' in service

for name in ("ic_pp_network.xml","ic_pp_sync.xml","ic_pp_service.xml"):
    x=(ROOT/"app/src/main/res/drawable"/name).read_text(encoding="utf-8")
    assert "<vector" in x and x.count("<path") >= 2

print("BETA121_OWNER_UI_PDA_SOURCE_CONTRACT_PASS")

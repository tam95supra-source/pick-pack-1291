#!/usr/bin/env python3
from pathlib import Path


def read(p): return Path(p).read_text(encoding='utf-8')
def write(p,s): Path(p).write_text(s,encoding='utf-8')
def replace_once(s,old,new,label):
    n=s.count(old)
    if n!=1: raise SystemExit(f'{label}: expected exactly 1 match, got {n}')
    return s.replace(old,new,1)

# Exact Beta127 identity.
p='app/build.gradle.kts';s=read(p)
s=replace_once(s,'versionCode = 132\n            versionName = "0.4.2-beta.126"','versionCode = 133\n            versionName = "0.4.2-beta.127"','beta identity')
marker='// Beta125: employee loading/result/error are one logical navigation frame; Back from scanned employee returns directly to the actual QR scan screen. Preserves Beta124 post-scan roster suppression. Stable unchanged.'
s=replace_once(s,marker,'// Beta127: closes OWNER R2 visual false-pass gaps: exact local-data delete wording, visible manpower report title, labor-detail ordering/empty state, and behavioral regression gates. Stable unchanged.\n'+marker,'beta127 note')
write(p,s)

p='app/src/main/java/vn/pickpack1291/app/beta/ReleaseNotes.kt';s=read(p)
s=replace_once(s,'const val VERSION_NAME = "0.4.2-beta.126"','const val VERSION_NAME = "0.4.2-beta.127"','release version')
start=s.index('    private val current = listOf(')
end=s.index('\n    )',start)+len('\n    )')
new='''    private val current = listOf(\n        "Sửa đúng nút Xóa dữ liệu ứng dụng: chỉ xóa dữ liệu cục bộ, không xóa dữ liệu chuẩn trên Dịch vụ.",\n        "Báo cáo tình hình nhân sự hiển thị tiêu đề rõ ràng và đặt Chi tiết công nhật đúng vị trí trước kết quả Pick & Pack.",\n        "Chi tiết công nhật luôn có trạng thái rõ ràng kể cả khi ngày được chọn chưa có công nhật hỗ trợ.",\n        "Tăng regression hành vi để lỗi hiển thị không còn được PASS chỉ vì chuỗi tồn tại trong source.",\n        "Giữ nguyên tối ưu Nhân sự, Công nhật, Hàng rớt, PDA, Điểm danh, QR và realtime đã có ở Beta126."\n    )'''
s=s[:start]+new+s[end:];write(p,s)

# App remediation.
p='app/src/main/java/vn/pickpack1291/app/beta/OperationsActivity.kt';s=read(p)
s=replace_once(s,'val clearData=primary("ĐẶT LẠI DỮ LIỆU",red){confirmResetLocalAppData()}.apply{textSize=9.5f}','val clearData=primary("XÓA DỮ LIỆU ỨNG DỤNG",red){confirmResetLocalAppData()}.apply{textSize=8.8f}','settings delete label')
s=replace_once(s,'AlertDialog.Builder(this).setTitle("Đặt lại dữ liệu ứng dụng?").setMessage("Ứng dụng sẽ trở về trạng thái như mới cài. Dữ liệu chỉ có trên thiết bị và chưa đồng bộ có thể mất; dữ liệu chuẩn trên Dịch vụ không bị xóa và sẽ được tải lại sau khi mở ứng dụng.").setNegativeButton("Hủy",null).setPositiveButton("ĐẶT LẠI")','AlertDialog.Builder(this).setTitle("Xóa dữ liệu ứng dụng?").setMessage("Ứng dụng sẽ trở về trạng thái như mới cài. Dữ liệu chỉ có trên thiết bị và chưa đồng bộ có thể mất; dữ liệu chuẩn trên Dịch vụ không bị xóa và sẽ được tải lại sau khi mở ứng dụng.").setNegativeButton("Hủy",null).setPositiveButton("XÓA DỮ LIỆU")','settings delete dialog')
s=replace_once(s,'val root=baseRoot("BÁO CÁO TÌNH HÌNH NHÂN SỰ");val body=column(bg).apply{setPadding(dp(3),dp(6),dp(3),dp(42))}','val root=baseRoot("BÁO CÁO TÌNH HÌNH NHÂN SỰ");val body=column(bg).apply{setPadding(dp(3),dp(6),dp(3),dp(42))};body.addView(txt("BÁO CÁO TÌNH HÌNH NHÂN SỰ",13f,navy,true).apply{setPadding(dp(4),dp(2),dp(4),dp(6))})','report visible title')
old='''            box.addView(gap(6))\n            box.addView(section("NHÂN SỰ PICK & PACK THỰC TẾ SAU KHI LOẠI TRỪ HỖ TRỢ"))\n            box.addView(details(listOf(\n                "Picker" to (pickerBase-pickerDeduct).coerceAtLeast(0).toString(),\n                "Packer" to (packerBase-packerDeduct).coerceAtLeast(0).toString()\n            )))\n            if(support.isNotEmpty()){\n                box.addView(gap(6));box.addView(section("CHI TIẾT CÔNG NHẬT"))\n                box.addView(s34ReportGrid("",supportGrid(support),"Công nhật theo vị trí","position"))\n            }'''
new='''            box.addView(gap(6));box.addView(section("CHI TIẾT CÔNG NHẬT"))\n            if(support.isNotEmpty()) box.addView(s34ReportGrid("",supportGrid(support),"Công nhật theo vị trí","position"))\n            else box.addView(info("Không có công nhật hỗ trợ trong phạm vi đã chọn."))\n            box.addView(gap(6))\n            box.addView(section("NHÂN SỰ PICK & PACK THỰC TẾ SAU KHI LOẠI TRỪ HỖ TRỢ"))\n            box.addView(details(listOf(\n                "Picker" to (pickerBase-pickerDeduct).coerceAtLeast(0).toString(),\n                "Packer" to (packerBase-packerDeduct).coerceAtLeast(0).toString()\n            )))'''
s=replace_once(s,old,new,'report labor ordering');write(p,s)

# Static contract locks exact requirement semantics.
p='tools/beta123_owner_scope_contract.py';s=read(p)
s=replace_once(s,"assert 'versionCode = 132' in gradle\nassert 'versionName = \"0.4.2-beta.126\"' in gradle\nassert 'VERSION_NAME = \"0.4.2-beta.126\"' in notes","assert 'versionCode = 133' in gradle\nassert 'versionName = \"0.4.2-beta.127\"' in gradle\nassert 'VERSION_NAME = \"0.4.2-beta.127\"' in notes",'contract identity')
s=replace_once(s,"for s in ['Color.rgb(239,248,255)','Color.rgb(242,252,247)','Color.rgb(255,248,237)','XÓA CACHE','ĐẶT LẠI DỮ LIỆU']:","for s in ['Color.rgb(239,248,255)','Color.rgb(242,252,247)','Color.rgb(255,248,237)','XÓA CACHE','XÓA DỮ LIỆU ỨNG DỤNG']:",'contract settings label')
anchor="assert 'clearApplicationUserData' in ops\nassert 'không xóa dữ liệu trên Dịch vụ' in ops"
s=replace_once(s,anchor,anchor+"\nassert 'ĐẶT LẠI DỮ LIỆU' not in settings\nassert 'Xóa dữ liệu ứng dụng?' in ops",'contract settings negatives')
anchor="assert 'BÁO CÁO TÌNH HÌNH NHÂN SỰ' in report\nassert 'spinner(arrayOf(\"Ca 1 và HC\",\"C2\",\"Cả ngày\"))' in report"
s=replace_once(s,anchor,"assert 'body.addView(txt(\"BÁO CÁO TÌNH HÌNH NHÂN SỰ\"' in report\nassert 'spinner(arrayOf(\"Ca 1 và HC\",\"C2\",\"Cả ngày\"))' in report",'contract report visible title')
anchor="assert 'CHI TIẾT CÔNG NHẬT' in report\nassert 'Công nhật theo vị trí' in report"
s=replace_once(s,anchor,anchor+"\nassert report.index('section(\"CHI TIẾT CÔNG NHẬT\")') < report.index('section(\"NHÂN SỰ PICK & PACK THỰC TẾ SAU KHI LOẠI TRỪ HỖ TRỢ\")')\nassert 'Không có công nhật hỗ trợ trong phạm vi đã chọn.' in report",'contract report ordering')
write(p,s)

# Exact-device harness: patch generated Java after existing Beta126 injection.
p='tools/build_beta83_verify_harness.sh';s=read(p)
anchor="s=s.replace(needle,repl)\n# Beta126: labor home must expose bulk edit in addition to create/finish."
extra='''s=s.replace(needle,repl)\n# Beta127: visual assertions must prove required text is actually rendered.\nreport_anchor='    waitText("Thâm niên",true,false,12000L);\\n    waitText("NHÂN SỰ PICK & PACK THỰC TẾ SAU KHI LOẠI TRỪ HỖ TRỢ",true,false,12000L);'\nreport_repl='    waitText("BÁO CÁO TÌNH HÌNH NHÂN SỰ",true,false,12000L);\\n    waitText("Thâm niên",true,false,12000L);\\n    waitText("CHI TIẾT CÔNG NHẬT",true,false,12000L);\\n    waitText("NHÂN SỰ PICK & PACK THỰC TẾ SAU KHI LOẠI TRỪ HỖ TRỢ",true,false,12000L);'\nif report_anchor not in s: raise SystemExit('BETA127_REPORT_VISIBLE_ANCHOR_NOT_FOUND')\ns=s.replace(report_anchor,report_repl,1)\nsettings_anchor='    waitText("THÔNG TIN ỨNG DỤNG",true,false,10000L);\\n'\nif settings_anchor not in s: raise SystemExit('BETA127_SETTINGS_VISIBLE_ANCHOR_NOT_FOUND')\ns=s.replace(settings_anchor,settings_anchor+'    waitText("XÓA DỮ LIỆU ỨNG DỤNG",true,false,10000L);\\n    require(findText("ĐẶT LẠI DỮ LIỆU",true,false)==null,"BETA127_OLD_RESET_LABEL_VISIBLE");\\n',1)\n# Beta126: labor home must expose bulk edit in addition to create/finish.'''
s=replace_once(s,anchor,extra,'harness behavioral injection')
anchor="grep -Fq 'BETA126_REPORT_DEDUCTION_SUMMARY_MUST_BE_REMOVED' \"$W/src/vn/pickpack1291/verify/Beta83UiChecksInstrumentation.java\""
checks=anchor+"\ngrep -Fq 'waitText(\"BÁO CÁO TÌNH HÌNH NHÂN SỰ\"' \"$W/src/vn/pickpack1291/verify/Beta83UiChecksInstrumentation.java\"\ngrep -Fq 'waitText(\"CHI TIẾT CÔNG NHẬT\"' \"$W/src/vn/pickpack1291/verify/Beta83UiChecksInstrumentation.java\"\ngrep -Fq 'waitText(\"XÓA DỮ LIỆU ỨNG DỤNG\"' \"$W/src/vn/pickpack1291/verify/Beta83UiChecksInstrumentation.java\"\ngrep -Fq 'BETA127_OLD_RESET_LABEL_VISIBLE' \"$W/src/vn/pickpack1291/verify/Beta83UiChecksInstrumentation.java\""
s=replace_once(s,anchor,checks,'harness self checks');write(p,s)

Path('qa/beta127_owner_r2_regression.md').write_text('''# Beta127 OWNER R2 regression\n\nStatus: LOCKED_REQUIREMENT_PENDING_FIX until exact Beta127 candidate completes all pre-OTA gates.\n\n## Bugs caught after Beta126 false-positive PASS\n1. Settings rendered `ĐẶT LẠI DỮ LIỆU` instead of OWNER-required `XÓA DỮ LIỆU ỨNG DỤNG`.\n2. Report passed source grep while `BÁO CÁO TÌNH HÌNH NHÂN SỰ` was not visible because `appBar(title)` does not render title text.\n3. `CHI TIẾT CÔNG NHẬT` was after Pick & Pack and vanished when support data was empty.\n\n## Mandatory evidence\n- Exact-device instrumentation sees the new Settings label and rejects the old label.\n- Exact-device instrumentation sees report title, `CHI TIẾT CÔNG NHẬT`, and Pick & Pack result title.\n- Static contract locks report ordering and empty-support state.\n- Existing full functional/visual/API36/service/runtime/OTA gates remain mandatory; ACTIVE_PASS semantics are unchanged.\n''',encoding='utf-8')
print('BETA127_OWNER_R2_REMEDIATION_V2_APPLIED')

#!/usr/bin/env python3
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]
OPS=ROOT/'app/src/main/java/vn/pickpack1291/app/beta/OperationsActivity.kt'
GRADLE=ROOT/'app/build.gradle.kts'
NOTES=ROOT/'app/src/main/java/vn/pickpack1291/app/beta/ReleaseNotes.kt'


def once(text, old, new, label):
    n=text.count(old)
    if n!=1:
        raise SystemExit(f'{label}: expected 1 occurrence, got {n}')
    return text.replace(old,new,1)

# Version + owner-facing changelog. Stable identity is intentionally untouched.
g=GRADLE.read_text(encoding='utf-8')
g=once(g,'versionCode = 127','versionCode = 128','beta versionCode')
g=once(g,'versionName = "0.4.2-beta.121"','versionName = "0.4.2-beta.122"','beta versionName')
g=once(g,'// Beta121: owner UI status/service role switch, grouped Settings, pending Inhouse attendance card, bordered dropped-receiving table, and PDA source master metadata. Stable unchanged.',
'''// Beta122: effective USER/ADMIN role lowering is enforced on navigation/actions while only the Service role selector keeps actual SUPERADMIN authority; PDA source is visible/editable throughout Android PDA UI. Stable unchanged.\n// Beta121: owner UI status/service role switch, grouped Settings, pending Inhouse attendance card, bordered dropped-receiving table, and PDA source master metadata. Stable unchanged.''','gradle beta122 note')
GRADLE.write_text(g,encoding='utf-8')

n=NOTES.read_text(encoding='utf-8')
n=once(n,'const val VERSION_NAME = "0.4.2-beta.121"','const val VERSION_NAME = "0.4.2-beta.122"','notes version')
start=n.index('    private val current = listOf(')
end=n.index('\n    )',start)+6
new_current='''    private val current = listOf(\n        "Khi SUPERADMIN chuyển sang USER hoặc ADMIN, toàn bộ menu, màn hình và thao tác nghiệp vụ hạ đúng quyền thực tế; chỉ bộ chọn quyền trong chi tiết Dịch vụ vẫn tồn tại để chuyển lại.",\n        "PDA hiển thị Nguồn trong thông tin chọn/đang dùng, xác nhận đổi-trả và danh sách PDA ở Tài nguyên; ADMIN có thể chọn Nguồn từ danh mục canonical khi thêm/sửa PDA.",\n        "Giữ nguyên hai mục OWNER đã nghiệm thu ở Beta121: ba ô Mạng / Đồng bộ / Dịch vụ và bố cục Cài đặt / Bảng công Inhouse / bảng Nhận hàng Rớt.",\n        "Giữ nguyên Stable/main/signer/authority và toàn bộ invariant ACTIVE_PASS ngoài phạm vi sửa."\n    )'''
n=n[:start]+new_current+n[end:]
NOTES.write_text(n,encoding='utf-8')

s=OPS.read_text(encoding='utf-8')

# Effective-role authority: only the Service detail selector may consult actualRole.
replacements={
'if(!isActualSuper()){showError("Chỉ SUPERADMIN được thực hiện thao tác này.");return}':'if(!isSuper()){showError("Chỉ SUPERADMIN được thực hiện thao tác này.");return}',
'if(!isActualSuper()){showError("Mật khẩu xác nhận không đúng.");return@setOnClickListener}':'if(!isSuper()){showError("Mật khẩu xác nhận không đúng.");return@setOnClickListener}',
'if(!isActualSuper()){showError("Chỉ SUPERADMIN được bật/tắt LAN thủ công.");return}':'if(!isSuper()){showError("Chỉ SUPERADMIN được bật/tắt LAN thủ công.");return}',
'if(!isActualSuper()){showError("Chỉ SUPERADMIN được thay đổi chế độ LAN test toàn cục.");onDone(false);return}':'if(!isSuper()){showError("Chỉ SUPERADMIN được thay đổi chế độ LAN test toàn cục.");onDone(false);return}',
'if(!isActualSuper()){showError("SUPERADMIN_REQUIRED");return}':'if(!isSuper()){showError("SUPERADMIN_REQUIRED");return}',
'"ROLE_MODE"->if(isActualSuper())roleModeScreen() else businessHome()':'"ROLE_MODE"->businessHome()',
'if(!isActualSuper()){module="BUSINESS";businessHome();return}\n        module="ROLE_MODE";screenState="ROLE_MODE"':'if(!isSuper()){module="BUSINESS";businessHome();return}\n        module="ROLE_MODE";screenState="ROLE_MODE"',
}
for old,new in replacements.items():
    if old not in s:
        raise SystemExit('missing effective-role pattern: '+old[:80])
    s=s.replace(old,new,1)

# Direct route must fail closed for USER, not only bottom-navigation taps.
s=once(s,'            "HISTORY"->historyScreen()\n            "SYNC"->syncScreen()',
'''            "HISTORY"->if(isAdmin())historyScreen() else {module="BUSINESS";businessHome()}\n            "SYNC"->syncScreen()''','direct history route')

# Rebuild bottom navigation after effective-role changes so privileged tabs disappear immediately.
refresh='''    private fun refreshBottomNav(){val active=activeTab();navRefs.forEach{(key,ref)->val chosen=key==active;ref.cell.background=if(chosen)round(ThemeManager.soft(this@OperationsActivity),10)else null;ref.icon.imageTintList=ColorStateList.valueOf(if(chosen)teal else muted);ref.label.setTextColor(if(chosen)teal else muted);ref.label.typeface=if(chosen)Typeface.DEFAULT_BOLD else Typeface.DEFAULT}}'''
rebuild=refresh+'''\n    private fun rebuildBottomNav(){\n        val host=navHost?:return\n        host.removeAllViews()\n        host.addView(bottomNav(),FrameLayout.LayoutParams(-1,-1))\n        refreshBottomNav()\n    }'''
s=once(s,refresh,rebuild,'bottom nav rebuild helper')

role_pat=re.compile(r'''                        role=value\n                        effectiveRole=value\n                        dialog\?\.dismiss\(\)\n                        TopNotice\.show\(this@OperationsActivity,"Đã chuyển sang chế độ \$\{roleText\(value\)\}\."\,TopNotice\.Kind\.SUCCESS\)\n                        when\(module\)\{\n                            "SETTINGS"->settingsScreen\(\)\n                            "STAFF"->staffScreen\(\)\n                            "HISTORY"->if\(isAdmin\(\)\)historyScreen\(\) else businessHome\(\)\n                            else->businessHome\(\)\n                        \}''')
role_new='''                        role=value\n                        effectiveRole=value\n                        screenBackStack.clear()\n                        tabHistory.clear()\n                        dialog?.dismiss()\n                        TopNotice.show(this@OperationsActivity,"Đã chuyển sang chế độ ${roleText(value)}.",TopNotice.Kind.SUCCESS)\n                        when(module){\n                            "SETTINGS"->settingsScreen()\n                            "STAFF"->staffScreen()\n                            "HISTORY"->if(isAdmin())historyScreen() else {module="BUSINESS";businessHome()}\n                            else->businessHome()\n                        }\n                        rebuildBottomNav()'''
s,nsub=role_pat.subn(role_new,s,count=1)
if nsub!=1:
    raise SystemExit(f'role switch patch expected 1 got {nsub}')

# Canonical PDA source lookup from cached master snapshot.
old_resource='''    private fun resourceListText(s:JSONObject):List<Pair<String,String>>{\n        val rows=mutableListOf<Pair<String,String>>();for(t in listOf("PDA","USER_PICK","PACK_TABLE","USER_PACK")){for(x in visibleAssignments(s,t)){val state=if(x.optString("state").equals("ACTIVE",true))"Đang dùng" else "Đã dùng";rows.add(resourceLabel(t) to "${x.optString("resource_id")} • $state")}};return rows\n    }'''
new_resource='''    private fun pdaSourceBySerial(serial:String):String{\n        val key=serial.trim();if(key.isBlank())return ""\n        val pdas=MasterDataCache.resourceOptions(this).optJSONArray("pdas")?:JSONArray()\n        for(i in 0 until pdas.length()){\n            val p=pdas.optJSONObject(i)?:continue\n            if(p.optString("serial").trim()==key)return p.optString("source").trim().ifBlank{p.optString("Nguồn").trim()}\n        }\n        return ""\n    }\n    private fun resourceListText(s:JSONObject):List<Pair<String,String>>{\n        val rows=mutableListOf<Pair<String,String>>()\n        for(t in listOf("PDA","USER_PICK","PACK_TABLE","USER_PACK")){for(x in visibleAssignments(s,t)){\n            val state=if(x.optString("state").equals("ACTIVE",true))"Đang dùng" else "Đã dùng"\n            val id=x.optString("resource_id")\n            val source=if(t=="PDA")pdaSourceBySerial(id) else ""\n            val suffix=if(t=="PDA")" • Nguồn: ${source.ifBlank{"—"}}" else ""\n            rows.add(resourceLabel(t) to "$id$suffix • $state")\n        }}\n        return rows\n    }'''
s=once(s,old_resource,new_resource,'PDA source in session resource info')

# Selected PDA panel: make source visible before status.
panel_pat=re.compile(r'''    private fun pdaSelectedPanel\(pdas:JSONArray,field:AutoCompleteTextView\):TextView\{.*?\n    \}\n    private fun pdaInput''',re.S)
panel_new='''    private fun pdaSelectedPanel(pdas:JSONArray,field:AutoCompleteTextView):TextView{\n        val panel=txt("Serial PDA\\nChưa chọn\\nNguồn\\n—\\nTình trạng PDA\\n—",11.2f,navy,false).apply{setPadding(dp(10),dp(8),dp(10),dp(8));background=ColorDrawable(Color.rgb(239,246,255))}\n        fun update(){\n            val p=(field.tag as? JSONObject)?:resolvePdaObject(pdas,field.text?.toString().orEmpty())\n            val serial=p?.optString("serial").orEmpty()\n            val source=p?.optString("source").orEmpty().ifBlank{p?.optString("Nguồn").orEmpty()}\n            val status=p?.optString("status").orEmpty()\n            panel.text="Serial PDA\\n${serial.ifBlank{"Chưa chọn"}}\\nNguồn\\n${source.ifBlank{"—"}}\\nTình trạng PDA\\n${status.ifBlank{"—"}}"\n        }\n        field.addTextChangedListener(object:TextWatcher{override fun beforeTextChanged(s:CharSequence?,st:Int,c:Int,a:Int)=Unit;override fun onTextChanged(s:CharSequence?,st:Int,b:Int,c:Int)=Unit;override fun afterTextChanged(e:Editable?){update()}})\n        field.post{update()}\n        return panel\n    }\n    private fun pdaInput'''
s,nsub=panel_pat.subn(panel_new,s,count=1)
if nsub!=1:
    raise SystemExit(f'pdaSelectedPanel patch expected 1 got {nsub}')

# Autocomplete labels show source alongside serial/status.
old_labels='''            val status=p.optString("status").trim()\n            if(serial.isNotBlank()&&last5.isNotBlank())labels.add("$last5 • $serial • Tình trạng: ${status.ifBlank{"—"}}")'''
new_labels='''            val status=p.optString("status").trim()\n            val source=p.optString("source").trim().ifBlank{p.optString("Nguồn").trim()}\n            if(serial.isNotBlank()&&last5.isNotBlank())labels.add("$last5 • $serial • Nguồn: ${source.ifBlank{"—"}} • Tình trạng: ${status.ifBlank{"—"}}")'''
s=once(s,old_labels,new_labels,'PDA autocomplete source')

# Handover confirmation also surfaces source.
old_handover='''        val sp=spinner(statuses.toTypedArray());val pos=statuses.indexOf(expected);if(pos>=0)sp.setSelection(pos);val note=input("Ghi chú tình trạng (tùy chọn)",false)\n        val box=column(surface).apply{setPadding(dp(12),dp(4),dp(12),dp(8));addView(details(listOf("Seri PDA" to serial,"Tình trạng khi nhận" to expected.ifBlank{"—"},"Thao tác" to operation)));addView(gap(7));addView(labelled("Tình trạng PDA hiện tại",sp));addView(gap(7));addView(note,matchWrap())}'''
new_handover='''        val sp=spinner(statuses.toTypedArray());val pos=statuses.indexOf(expected);if(pos>=0)sp.setSelection(pos);val note=input("Ghi chú tình trạng (tùy chọn)",false)\n        val source=pdaSourceBySerial(serial)\n        val box=column(surface).apply{setPadding(dp(12),dp(4),dp(12),dp(8));addView(details(listOf("Seri PDA" to serial,"Nguồn" to source.ifBlank{"—"},"Tình trạng khi nhận" to expected.ifBlank{"—"},"Thao tác" to operation)));addView(gap(7));addView(labelled("Tình trạng PDA hiện tại",sp));addView(gap(7));addView(note,matchWrap())}'''
s=once(s,old_handover,new_handover,'PDA handover source')

# Source master catalog follows the same namespace mechanism as PDA status.
anchor='''    private fun resourceEditDialog(type:String,existing:JSONObject?,catalogs:JSONArray?,all:JSONArray?,verified:Boolean=false){'''
helper='''    private fun resourcePdaSourceValues(catalogs:JSONArray?):MutableList<String>{\n        val ns="DANH SÁCH PDA_Nguồn"\n        val out=mutableListOf<String>()\n        if(catalogs!=null)for(i in 0 until catalogs.length()){val x=catalogs.optJSONObject(i)?:continue;if(x.optString("namespace")==ns&&x.optString("value").isNotBlank())out.add(x.optString("value"))}\n        if(out.isEmpty())out.addAll(catalogValues(ns))\n        return out.distinct().toMutableList()\n    }\n\n'''+anchor
s=once(s,anchor,helper,'PDA source catalog helper')

# Add source dropdown to PDA resource editor.
old_status='''        val statuses=resourceStatusValues(type,catalogs);val statusSp=spinner((if(statuses.isEmpty())listOf("Hoạt động")else statuses).toTypedArray());selectByValue(statusSp,statuses,existing?.optString("status_label").orEmpty())'''
new_status='''        val statuses=resourceStatusValues(type,catalogs);val statusSp=spinner((if(statuses.isEmpty())listOf("Hoạt động")else statuses).toTypedArray());selectByValue(statusSp,statuses,existing?.optString("status_label").orEmpty())\n        val sourceOptions=mutableListOf("—").apply{addAll(resourcePdaSourceValues(catalogs))}\n        val sourceSp=if(type=="PDA")spinner(sourceOptions.toTypedArray()) else null\n        val existingSource=meta.optString("Nguồn").ifBlank{existing?.optString("source").orEmpty()}\n        if(sourceSp!=null){val at=sourceOptions.indexOf(existingSource);if(at>=0)sourceSp.setSelection(at)}'''
s=once(s,old_status,new_status,'PDA source editor spinner')

old_add='''        add("Mã / tên tài nguyên",id);add("Tình trạng",statusSp);if(type=="PDA")add("5 số cuối Seri (tự động)",extra1) else if(type!="PACK_TABLE")add(extra1.hint?.toString().orEmpty(),extra1);if(type=="USER_PACK")add(extra2.hint?.toString().orEmpty(),extra2);add("Ghi chú",note)'''
new_add='''        add("Mã / tên tài nguyên",id);add("Tình trạng",statusSp);if(type=="PDA"&&sourceSp!=null)add("Nguồn PDA",sourceSp);if(type=="PDA")add("5 số cuối Seri (tự động)",extra1) else if(type!="PACK_TABLE")add(extra1.hint?.toString().orEmpty(),extra1);if(type=="USER_PACK")add(extra2.hint?.toString().orEmpty(),extra2);add("Ghi chú",note)'''
s=once(s,old_add,new_add,'PDA source editor field')

old_save='''            if(type=="PDA"&&key.any{it.isWhitespace()}){showError("Mã / tên PDA không được có khoảng trống.");return@setPositiveButton}\n            val m=JSONObject().put("Ghi chú",note.text.toString().trim())\n            when(type){"PDA"->{val last=key.takeLast(5);if(last.length!=5||!last.all{it.isDigit()}){showError("5 ký tự cuối Mã / tên PDA phải là 5 chữ số Seri.");return@setPositiveButton};m.put("Seri PDA",key).put("5 số cuối Seri",last)};'''
new_save='''            if(type=="PDA"&&key.any{it.isWhitespace()}){showError("Mã / tên PDA không được có khoảng trống.");return@setPositiveButton}\n            val source=if(type=="PDA")sourceSp?.selectedItem?.toString().orEmpty() else ""\n            if(type=="PDA"&&(source.isBlank()||source=="—")){showError("Chọn Nguồn PDA.");return@setPositiveButton}\n            val m=JSONObject().put("Ghi chú",note.text.toString().trim())\n            when(type){"PDA"->{val last=key.takeLast(5);if(last.length!=5||!last.all{it.isDigit()}){showError("5 ký tự cuối Mã / tên PDA phải là 5 chữ số Seri.");return@setPositiveButton};m.put("Seri PDA",key).put("5 số cuối Seri",last).put("Nguồn",source)};'''
s=once(s,old_save,new_save,'PDA source save')

# Resource PDA list: display source from metadata, with top-level service fallback.
old_list='''"PDA"->listOf("5 số cuối Seri: ${dash(meta.optString("5 số cuối Seri"))}","Tình trạng: ${x.optString("status_label").ifBlank{"—"}}","Ghi chú: ${dash(meta.optString("Ghi chú"))}")'''
new_list='''"PDA"->listOf("5 số cuối Seri: ${dash(meta.optString("5 số cuối Seri"))}","Nguồn: ${dash(meta.optString("Nguồn").ifBlank{x.optString("source")})}","Tình trạng: ${x.optString("status_label").ifBlank{"—"}}","Ghi chú: ${dash(meta.optString("Ghi chú"))}")'''
s=once(s,old_list,new_list,'PDA resource list source')

OPS.write_text(s,encoding='utf-8')
print('BETA122_EFFECTIVE_ROLE_PDA_SOURCE_UI_PATCH_APPLIED')

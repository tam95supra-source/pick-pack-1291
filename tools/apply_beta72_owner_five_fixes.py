#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OPS = ROOT / 'app/src/main/java/vn/pickpack1291/app/beta/OperationsActivity.kt'
GRADLE = ROOT / 'app/build.gradle.kts'


def replace_fun(text: str, marker: str, replacement: str) -> str:
    i = text.find(marker)
    if i < 0:
        raise SystemExit(f'missing function marker: {marker}')
    brace = text.find('{', i)
    if brace < 0:
        raise SystemExit(f'missing function brace: {marker}')
    depth = 0
    quote = None
    escaped = False
    pos = brace
    while pos < len(text):
        ch = text[pos]
        if quote:
            if escaped:
                escaped = False
            elif ch == '\\':
                escaped = True
            elif ch == quote:
                quote = None
            pos += 1
            continue
        if ch in ('"', "'"):
            quote = ch
        elif ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                return text[:i] + replacement + text[pos + 1:]
        pos += 1
    raise SystemExit(f'unclosed function: {marker}')


g = GRADLE.read_text(encoding='utf-8')
old_version = 'versionCode = 77\n            versionName = "0.4.2-beta.71"'
new_version = 'versionCode = 78\n            versionName = "0.4.2-beta.72"'
if old_version in g:
    g = g.replace(old_version, new_version, 1)
elif 'versionCode = 78' not in g or 'versionName = "0.4.2-beta.72"' not in g:
    raise SystemExit('Beta72 version anchor drift')
GRADLE.write_text(g, encoding='utf-8')

o = OPS.read_text(encoding='utf-8')
helper_anchor = '    private fun resourceStateRows(s:JSONObject):List<Pair<String,String>> = resourceListText(s)\n'
helpers = r'''    private fun resourceStateRows(s:JSONObject):List<Pair<String,String>> = resourceListText(s)
    private fun shiftResourceValue(s:JSONObject,type:String,ended:Boolean):String{
        val rows=if(ended)visibleAssignments(s,type) else activeAssignments(s,type)
        val value=rows.map{it.optString("resource_id").trim()}.filter{it.isNotBlank()}.distinct().joinToString(" • ")
        return if(value.isNotBlank())value else if(type=="USER_PICK")"Dùng user cố định theo số điện thoại / họ tên." else "—"
    }
    private fun shiftSummaryRows(s:JSONObject,ended:Boolean):List<Pair<String,String>>{
        val out=mutableListOf<Pair<String,String>>()
        out.add("Ca" to dash(s.optString("shift")))
        out.add("Vào lúc" to formatIso(s.optString("enter_at")))
        if(ended)out.add("Ra lúc" to formatIso(s.optString("exit_at")))
        val positions=if(ended)allPositionLabels(s) else activePositionLabels(s)
        if(positions.isEmpty())out.add("Vị trí trong ca" to "Không")
        positions.forEach{label->
            out.add("Vị trí trong ca" to label)
            when{
                label.equals("Pick",true)->{
                    out.add("User pick" to shiftResourceValue(s,"USER_PICK",ended))
                    out.add("PDA" to shiftResourceValue(s,"PDA",ended))
                }
                label.equals("Pack",true)->{
                    out.add("Bàn pack" to shiftResourceValue(s,"PACK_TABLE",ended))
                    out.add("User pack" to shiftResourceValue(s,"USER_PACK",ended))
                }
            }
        }
        return out
    }
    private fun shiftDetails(items:List<Pair<String,String>>)=column(surface).apply{
        setPadding(dp(9),dp(6),dp(9),dp(6));background=outlineBg(surface,10)
        items.forEach{(key,raw)->
            val value=raw.ifBlank{"—"}
            val r=row(surface).apply{gravity=Gravity.TOP;setPadding(0,dp(3),0,dp(3))}
            r.addView(txt("$key:",9.7f,muted,true),LinearLayout.LayoutParams(-2,-2))
            r.addView(txt(value,9.9f,ink,true).apply{maxLines=6;ellipsize=null},LinearLayout.LayoutParams(0,-2,1f).apply{marginStart=dp(4)})
            addView(r,matchWrap())
        }
    }
'''
if 'private fun shiftSummaryRows(' not in o:
    if helper_anchor not in o:
        raise SystemExit('shift helper anchor drift')
    o = o.replace(helper_anchor, helpers, 1)

render_active = r'''    private fun renderActive(body:LinearLayout,ctx:JSONObject){
        val s=ctx.optJSONObject("session")?:JSONObject();val mnv=s.optString("mnv")
        body.addView(section("THỜI GIAN & VỊ TRÍ TRONG CA"));body.addView(shiftDetails(shiftSummaryRows(s,false)));body.addView(gap(7))
        val exit=smallButton("Ra ca",red);fun doExit(status:String){val gen=employeeLookupGeneration;exit.isEnabled=false;api.call("session_exit_v2",JSONObject().put("session_id",s.optString("session_id")).put("mnv",mnv).put("expected_version",s.optInt("version")).put("pda_exit_status",status).put("idempotency_key",UUID.randomUUID().toString())){r->runOnUiThread{exit.isEnabled=true;if(!r.ok){if(r.error=="SESSION_CHANGED")loadEmployee(mnv)else showError(r.error?:"RA_CA_FAILED");return@runOnUiThread};TopNotice.show(this,"Đã ghi nhận ra ca.",TopNotice.Kind.SUCCESS);foregroundSync.requestSync();if(gen==employeeLookupGeneration&&liveEmployeeMnv==mnv)scheduleAttendanceAutoReset(mnv,gen)}}}
        exit.setOnClickListener{if(ctx.optJSONObject("active_labor")!=null){showError("Còn công nhật đang làm. Hoàn thành công nhật trước khi ra ca.");return@setOnClickListener};val pda=activeAssignments(s,"PDA").firstOrNull();if(pda==null){doExit("");return@setOnClickListener};val expected=s.optString("pda_enter_status");val arr=MasterDataCache.resourceOptions(this).optJSONArray("pda_statuses")?:JSONArray();val statuses=mutableListOf<String>();for(i in 0 until arr.length()){val v=arr.optString(i).trim();if(v.isNotBlank()&&!statuses.contains(v))statuses.add(v)};if(expected.isNotBlank()&&!statuses.contains(expected))statuses.add(0,expected);val sp=spinner(statuses.toTypedArray());val wrap=column(surface).apply{setPadding(dp(12),dp(6),dp(12),dp(5));addView(txt("PDA ${pda.optString("resource_id")}",12f,navy,true));addView(labelled("Tình trạng PDA hiện tại",sp))};AlertDialog.Builder(this).setTitle("Đối chiếu PDA trước khi RA CA").setView(wrap).setNegativeButton("Hủy",null).setPositiveButton("KIỂM TRA & RA CA"){_,_->doExit(sp.selectedItem?.toString().orEmpty())}.show()}
        val actions=row(bg);actions.addView(smallButton("Thêm",teal).apply{setOnClickListener{sessionWorkEditor(ctx,"ADD")}},LinearLayout.LayoutParams(0,dp(40),1f).apply{marginEnd=dp(2)});actions.addView(smallButton("Sửa",navy).apply{setOnClickListener{sessionWorkEditor(ctx,"EDIT")}},LinearLayout.LayoutParams(0,dp(40),1f).apply{marginStart=dp(2);marginEnd=dp(2)});actions.addView(smallButton("Xóa",orange).apply{setOnClickListener{deleteSessionWork(ctx)}},LinearLayout.LayoutParams(0,dp(40),1f).apply{marginStart=dp(2)});body.addView(actions,matchWrap());body.addView(gap(5));body.addView(exit,matchWrap());body.addView(gap(8));addSessionTimeline(body,mnv,s)
    }
'''
o = replace_fun(o, '    private fun renderActive(body:LinearLayout,ctx:JSONObject){', render_active)

render_ended = r'''    private fun renderEnded(body:LinearLayout,ctx:JSONObject){
        val s=ctx.optJSONObject("session")?:JSONObject();val mnv=s.optString("mnv")
        body.addView(section("PHIÊN ĐÃ HOÀN THÀNH"));body.addView(shiftDetails(shiftSummaryRows(s,true)));body.addView(gap(7));addSessionTimeline(body,mnv,s);body.addView(gap(8))
        if(isAdmin()){val act=row(bg);act.addView(smallButton("Sửa giờ vào",navy).apply{setOnClickListener{editAttendanceTime(ctx,"enter_at")}},LinearLayout.LayoutParams(0,dp(40),1f).apply{marginEnd=dp(2)});act.addView(smallButton("Sửa giờ ra",teal).apply{setOnClickListener{editAttendanceTime(ctx,"exit_at")}},LinearLayout.LayoutParams(0,dp(40),1f).apply{marginStart=dp(2)});body.addView(act,matchWrap());body.addView(gap(5));body.addView(primary("XÓA GHI NHẬN RA CA",red){deleteExitRecord(ctx)},matchWrap())}
        body.addView(gap(5));body.addView(primary("XÓA TOÀN BỘ PHIÊN",red){deleteSessionWork(ctx)},matchWrap())
    }
'''
o = replace_fun(o, '    private fun renderEnded(body:LinearLayout,ctx:JSONObject){', render_ended)

render_enter = r'''    private fun renderEnter(body:LinearLayout,ctx:JSONObject,masters:JSONObject){
        val e=ctx.optJSONObject("employee")?:JSONObject();val mnv=e.optString("mnv");val main=e.optString("main_position").trim();body.addView(section("PHÂN CÔNG TRONG CA"))
        val now=java.time.LocalTime.now(ZoneId.of("Asia/Ho_Chi_Minh"));var shiftValue=when{now.isBefore(java.time.LocalTime.of(8,0))->"Ca 1";now.isBefore(java.time.LocalTime.of(10,0))->"Ca HC";else->"Ca 2"}
        val mainPick=main.equals("Pick",true);val mainPack=main.equals("Pack",true);val third=if(mainPick||mainPack)"Không" else main.ifBlank{"Không"};val thirdKey=if(third=="Không")"NONE" else foldLocal(third).ifBlank{third.uppercase()};val positionChoices=listOf("Pick" to "PICK","Pack" to "PACK",third to thirdKey)
        var posKey=when{mainPick->"PICK";mainPack->"PACK";else->thirdKey};var posLabel=positionChoices.firstOrNull{it.second==posKey}?.first?:third
        val shiftBox=column(bg);shiftBox.addView(segmentedChoice(listOf("Ca 1" to "Ca 1","Ca HC" to "Ca HC","Ca 2" to "Ca 2"),shiftValue){shiftValue=it},matchWrap());body.addView(labelled("Ca",shiftBox));body.addView(gap(7))
        val resource=column(bg);var pdaField:AutoCompleteTextView?=null;var selectedPda:JSONObject?=null
        var pickSpin:Spinner?=null;var pickChoices=mutableListOf<Pair<String,Boolean>>();var allowPickReissue=false
        var tableSpin:Spinner?=null;var packSelection:JSONObject?=null;var allowPackReissue=false;var preferredPackTable=""
        val pdas=masters.optJSONArray("pdas")?:JSONArray();val picks=masters.optJSONArray("user_picks")?:JSONArray();val pickUsed=masters.optJSONArray("user_picks_reissue")?:JSONArray();val packRows=masters.optJSONArray("pack_tables")?:JSONArray();val packUsedRows=masters.optJSONArray("pack_tables_reissue")?:JSONArray()
        fun addPackMappings(src:JSONArray,duplicate:Boolean,out:MutableList<JSONObject>){
            for(i in 0 until src.length()){
                val q=src.optJSONObject(i)?:continue;val table=q.optString("table").ifBlank{q.optString("pack_table")}.trim();val user=q.optString("user_pack").ifBlank{q.optString("id").ifBlank{q.optString("resource_id")}}.trim();if(table.isBlank()||user.isBlank())continue
                val at=out.indexOfFirst{it.optString("table")==table&&it.optString("user_pack")==user};if(at>=0){if(!duplicate)out[at].put("duplicate_user",false)}else out.add(JSONObject(q.toString()).put("table",table).put("user_pack",user).put("duplicate_user",duplicate))
            }
        }
        fun rebuildResources(){
            resource.removeAllViews();pdaField=null;selectedPda=null;pickSpin=null;pickChoices.clear();tableSpin=null;packSelection=null
            if(posKey=="PICK"){
                pdaField=pdaInput(pdas,onSelected={selectedPda=it});resource.addView(labelled("PDA — bắt buộc, gõ 5 số cuối",pdaField!!));resource.addView(gap(5))
                val labels=mutableListOf("Dùng user cố định theo số điện thoại / họ tên.");pickChoices.add("" to false)
                val normal=mutableListOf<String>();for(i in 0 until picks.length()){val v=picks.optString(i).trim();if(v.isNotBlank()&&!normal.contains(v))normal.add(v)};normal.sortWith(Comparator{a,b->naturalUserCompare(a,b)});normal.forEach{pickChoices.add(it to false);labels.add(it)}
                if(allowPickReissue){optionIds(pickUsed).filter{it !in normal}.forEach{pickChoices.add(it to true);labels.add("⚠ $it • ĐÃ DÙNG HÔM NAY")}}
                pickSpin=spinner(labels.toTypedArray())
                val userRow=row(bg).apply{gravity=Gravity.CENTER_VERTICAL};userRow.addView(pickSpin!!,LinearLayout.LayoutParams(0,dp(50),1.35f).apply{marginEnd=dp(5)});userRow.addView(compactReissueButton("Phát lại",pickUsed.length()>0&&!allowPickReissue){allowPickReissue=true;rebuildResources()},LinearLayout.LayoutParams(0,dp(46),.85f));resource.addView(labelled("User Pick",userRow))
            }else if(posKey=="PACK"){
                val mappings=mutableListOf<JSONObject>();addPackMappings(packRows,false,mappings);if(allowPackReissue)addPackMappings(packUsedRows,true,mappings)
                val tables=mappings.map{it.optString("table")}.filter{it.isNotBlank()}.distinct().sortedWith(Comparator{a,b->naturalUserCompare(a,b)})
                tableSpin=spinner((if(tables.isEmpty())listOf("Không có Bàn Pack khả dụng")else tables).toTypedArray());if(preferredPackTable.isNotBlank()){val at=tables.indexOf(preferredPackTable);if(at>=0)tableSpin?.setSelection(at)};resource.addView(labelled("Bàn Pack — bắt buộc",tableSpin!!));resource.addView(gap(5))
                val userHost=column(bg);resource.addView(userHost,matchWrap())
                fun renderUsers(){
                    userHost.removeAllViews();packSelection=null
                    if(tables.isEmpty()){userHost.addView(info("Không có User Pack theo Bàn Pack khả dụng."));return}
                    val table=tables.getOrNull(tableSpin?.selectedItemPosition?:0).orEmpty();preferredPackTable=table
                    val mapped=mappings.filter{it.optString("table")==table}.sortedWith(Comparator{a,b->naturalUserCompare(a.optString("user_pack"),b.optString("user_pack"))})
                    val labels=mapped.map{if(it.optBoolean("duplicate_user"))"⚠ ${it.optString("user_pack")} • ĐÃ DÙNG HÔM NAY" else it.optString("user_pack")};val userSp=spinner((if(labels.isEmpty())listOf("Không có User Pack")else labels).toTypedArray());packSelection=mapped.getOrNull(0)
                    userSp.onItemSelectedListener=object:android.widget.AdapterView.OnItemSelectedListener{override fun onItemSelected(p:android.widget.AdapterView<*>?,v:View?,i:Int,id:Long){packSelection=mapped.getOrNull(i)};override fun onNothingSelected(p:android.widget.AdapterView<*>?)=Unit}
                    val userRow=row(bg).apply{gravity=Gravity.CENTER_VERTICAL};userRow.addView(userSp,LinearLayout.LayoutParams(0,dp(50),1.35f).apply{marginEnd=dp(5)});userRow.addView(compactReissueButton("Phát lại",packUsedRows.length()>0&&!allowPackReissue){preferredPackTable=table;allowPackReissue=true;rebuildResources()},LinearLayout.LayoutParams(0,dp(46),.85f));userHost.addView(labelled("User Pack theo Bàn Pack",userRow))
                }
                tableSpin?.onItemSelectedListener=object:android.widget.AdapterView.OnItemSelectedListener{override fun onItemSelected(p:android.widget.AdapterView<*>?,v:View?,i:Int,id:Long){preferredPackTable=tables.getOrNull(i).orEmpty();renderUsers()};override fun onNothingSelected(p:android.widget.AdapterView<*>?)=Unit};renderUsers()
            }else resource.addView(info("Vị trí trong ca: $posLabel"))
        }
        val posBox=column(bg);posBox.addView(segmentedChoice(positionChoices,posKey){k->posKey=k;posLabel=positionChoices.firstOrNull{it.second==k}?.first?:k;rebuildResources()},matchWrap());body.addView(labelled("Vị trí trong ca",posBox));body.addView(gap(7));body.addView(resource,matchWrap());rebuildResources()
        val enter=primary("VÀO CA",teal){};enter.setOnClickListener{
            val positions=JSONArray();if(posKey!="NONE")positions.put(JSONObject().put("position_key",posKey).put("position_label",posLabel));val resources=JSONArray()
            if(posKey=="PICK"){
                val typed=pdaField?.text?.toString()?.trim().orEmpty();val p=selectedPda;val expected=p?.optString("last5").orEmpty().ifBlank{p?.optString("serial").orEmpty().takeLast(5)}
                if(p==null||typed!=expected){showError("Vị trí Pick bắt buộc phải chọn PDA: gõ đúng 5 số cuối và chọn PDA trong danh sách gợi ý.");return@setOnClickListener}
                resources.put(JSONObject().put("resource_type","PDA").put("resource_id",p.optString("serial")).put("pda_enter_status",p.optString("status")))
                val choice=pickChoices.getOrNull(pickSpin?.selectedItemPosition?:0)?:("" to false);if(choice.first.isNotBlank())resources.put(JSONObject().put("resource_type","USER_PICK").put("resource_id",choice.first).put("duplicate_user",choice.second))
            }
            if(posKey=="PACK"){
                val selected=packSelection;val table=selected?.optString("table").orEmpty().trim();val user=selected?.optString("user_pack").orEmpty().trim();if(selected==null||table.isBlank()||user.isBlank()){showError("Vị trí Pack bắt buộc phải chọn Bàn Pack và User Pack đúng theo bàn.");return@setOnClickListener}
                resources.put(JSONObject().put("resource_type","PACK_TABLE").put("resource_id",table));resources.put(JSONObject().put("resource_type","USER_PACK").put("resource_id",user).put("duplicate_user",selected.optBoolean("duplicate_user")))
            }
            val gen=employeeLookupGeneration;enter.isEnabled=false;enter.text="ĐANG VÀO CA...";api.call("attendance_enter_v2",JSONObject().put("mnv",mnv).put("shift",shiftValue).put("positions",positions).put("resources",resources).put("idempotency_key",UUID.randomUUID().toString())){r->runOnUiThread{enter.isEnabled=true;enter.text="VÀO CA";if(!r.ok){showError(r.error?:"VÀO CA thất bại");return@runOnUiThread};TopNotice.show(this,"Đã ghi nhận vào ca.",TopNotice.Kind.SUCCESS);foregroundSync.requestSync();if(gen==employeeLookupGeneration&&liveEmployeeMnv==mnv)scheduleAttendanceAutoReset(mnv,gen)}}
        };body.addView(gap(8));body.addView(enter,matchWrap())
    }
'''
o = replace_fun(o, '    private fun renderEnter(body:LinearLayout,ctx:JSONObject,masters:JSONObject){', render_enter)

required = [
    'Dùng user cố định theo số điện thoại / họ tên.',
    'PDA — bắt buộc, gõ 5 số cuối',
    'User Pack theo Bàn Pack',
    'Vị trí Pick bắt buộc phải chọn PDA',
    'Vị trí Pack bắt buộc phải chọn Bàn Pack và User Pack đúng theo bàn.',
    'shiftDetails(shiftSummaryRows(s,false))',
]
for needle in required:
    if needle not in o:
        raise SystemExit(f'missing Beta72 owner invariant: {needle}')
for forbidden in ['PDA (tùy chọn)', 'User Pack — độc lập với bàn', 'Không dùng User Pick']:
    if forbidden in o:
        raise SystemExit(f'forbidden stale Beta71 UI remains: {forbidden}')
OPS.write_text(o, encoding='utf-8')
print('Beta72 owner five fixes materialized')

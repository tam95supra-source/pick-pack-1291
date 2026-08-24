#!/usr/bin/env python3
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OPS=ROOT/'app/src/main/java/vn/pickpack1291/app/beta/OperationsActivity.kt'
FULL=ROOT/'app/src/main/java/vn/pickpack1291/app/beta/FullBetaActivity.kt'

def replace_fun(text,marker,replacement):
    i=text.find(marker)
    if i<0:raise SystemExit(f'missing {marker}')
    b=text.find('{',i);depth=0;quote=None;esc=False
    for p in range(b,len(text)):
        c=text[p]
        if quote:
            if esc:esc=False
            elif c=='\\':esc=True
            elif c==quote:quote=None
            continue
        if c in ('"',"'"):quote=c
        elif c=='{':depth+=1
        elif c=='}':
            depth-=1
            if depth==0:return text[:i]+replacement+text[p+1:]
    raise SystemExit('unclosed '+marker)

f=FULL.read_text().replace('The whole frame is aspect-fitted and centered, never CENTER_CROP/FIT_XY stretched.','The whole frame is aspect-fitted and centered, never cropped or non-uniformly stretched.')
f=f.replace('background=ColorDrawable(Color.rgb(247,238,214))','background=android.graphics.drawable.ColorDrawable(Color.rgb(247,238,214))')
FULL.write_text(f)

o=OPS.read_text()
o=o.replace('data class AddCtl(val type:String,val check:CheckBox,val spin:Spinner,val normal:List<String>,var used:String="")','class AddCtl(val type:String,val check:CheckBox,val spin:Spinner,val normal:List<String>){var used:String=""}')
o=o.replace('data class E(val a:JSONObject,val check:CheckBox,val action:Spinner,val next:Spinner,val normal:List<String>,val used:JSONArray?,val disp:Spinner,val reason:EditText,var usedId:String="")','class E(val a:JSONObject,val check:CheckBox,val action:Spinner,val next:Spinner,val normal:List<String>,val used:JSONArray?,val disp:Spinner,val reason:EditText){var usedId:String=""}')
o=o.replace('data class D(val a:JSONObject,val check:CheckBox,val disp:Spinner,val reason:EditText)','class D(val a:JSONObject,val check:CheckBox,val disp:Spinner,val reason:EditText)')

ENTER=r'''    private fun renderEnter(body:LinearLayout,ctx:JSONObject,masters:JSONObject){
        val e=ctx.optJSONObject("employee")?:JSONObject();val mnv=e.optString("mnv");val main=e.optString("main_position").trim();body.addView(section("PHÂN CÔNG TRONG CA"))
        val now=java.time.LocalTime.now(ZoneId.of("Asia/Ho_Chi_Minh"));var shiftValue=when{now.isBefore(java.time.LocalTime.of(8,0))->"Ca 1";now.isBefore(java.time.LocalTime.of(10,0))->"Ca HC";else->"Ca 2"}
        val mainPick=main.equals("Pick",true);val mainPack=main.equals("Pack",true);val third=if(mainPick||mainPack)"Không" else main.ifBlank{"Không"};val thirdKey=if(third=="Không")"NONE" else foldLocal(third).ifBlank{third.uppercase()};val positionChoices=listOf("Pick" to "PICK","Pack" to "PACK",third to thirdKey)
        var posKey=when{mainPick->"PICK";mainPack->"PACK";else->thirdKey};var posLabel=positionChoices.firstOrNull{it.second==posKey}?.first?:third
        val shiftBox=column(bg);shiftBox.addView(segmentedChoice(listOf("Ca 1" to "Ca 1","Ca HC" to "Ca HC","Ca 2" to "Ca 2"),shiftValue){shiftValue=it},matchWrap());body.addView(labelled("Ca",shiftBox));body.addView(gap(7))
        val resource=column(bg);var pdaField:AutoCompleteTextView?=null;var selectedPda:JSONObject?=null;var pickSpin:Spinner?=null;var pickNormal=mutableListOf<String>();var selectedPickUsed="";var tableSpin:Spinner?=null;var tableNormal=mutableListOf<String>();var packSpin:Spinner?=null;var packNormal=mutableListOf<String>();var selectedPackUsed=""
        val pdas=masters.optJSONArray("pdas")?:JSONArray();val picks=masters.optJSONArray("user_picks")?:JSONArray();val pickUsed=masters.optJSONArray("user_picks_reissue")?:JSONArray();val packRows=masters.optJSONArray("pack_tables")?:JSONArray();val packUsedRows=masters.optJSONArray("pack_tables_reissue")?:JSONArray()
        fun distinctPackUsers(a:JSONArray):MutableList<String>{val x=mutableListOf<String>();for(i in 0 until a.length()){val q=a.optJSONObject(i);val v=(q?.optString("user_pack")?:a.optString(i)).trim();if(v.isNotBlank()&&!x.contains(v))x.add(v)};x.sortWith(Comparator{a,b->naturalUserCompare(a,b)});return x}
        fun distinctTables(a:JSONArray):MutableList<String>{val x=mutableListOf<String>();for(i in 0 until a.length()){val v=a.optJSONObject(i)?.optString("table").orEmpty().trim();if(v.isNotBlank()&&!x.contains(v))x.add(v)};x.sortWith(Comparator{a,b->naturalUserCompare(a,b)});return x}
        fun rebuildResources(){
            resource.removeAllViews();pdaField=null;selectedPda=null;pickSpin=null;pickNormal.clear();selectedPickUsed="";tableSpin=null;tableNormal.clear();packSpin=null;packNormal.clear();selectedPackUsed=""
            if(posKey=="PICK"){
                pdaField=pdaInput(pdas,onSelected={selectedPda=it});resource.addView(labelled("PDA (tùy chọn) — gõ 5 số cuối",pdaField!!));resource.addView(gap(5))
                for(i in 0 until picks.length()){val v=picks.optString(i).trim();if(v.isNotBlank()&&!pickNormal.contains(v))pickNormal.add(v)};pickNormal.sortWith(Comparator{a,b->naturalUserCompare(a,b)});pickSpin=spinner((listOf("Không dùng User Pick")+pickNormal).toTypedArray());pickSpin?.onItemSelectedListener=object:android.widget.AdapterView.OnItemSelectedListener{override fun onItemSelected(p:android.widget.AdapterView<*>?,v:View?,i:Int,id:Long){if(i>0)selectedPickUsed=""};override fun onNothingSelected(p:android.widget.AdapterView<*>?)=Unit};resource.addView(labelled("User Pick",pickSpin!!));resource.addView(compactReissueButton("Chọn User Pick đã dùng",pickUsed.length()>0){chooseUsed("Chọn User Pick đã dùng",pickUsed){selectedPickUsed=it;pickSpin?.setSelection(0);TopNotice.show(this,"Phát lại User Pick $it",TopNotice.Kind.INFO)}},matchWrap())
            }else if(posKey=="PACK"){
                tableNormal=distinctTables(packRows);packNormal=distinctPackUsers(packRows);tableSpin=spinner((listOf("Không chọn Bàn Pack")+tableNormal).toTypedArray());packSpin=spinner((listOf("Không dùng User Pack")+packNormal).toTypedArray());packSpin?.onItemSelectedListener=object:android.widget.AdapterView.OnItemSelectedListener{override fun onItemSelected(p:android.widget.AdapterView<*>?,v:View?,i:Int,id:Long){if(i>0)selectedPackUsed=""};override fun onNothingSelected(p:android.widget.AdapterView<*>?)=Unit};resource.addView(labelled("Bàn Pack",tableSpin!!));resource.addView(gap(5));resource.addView(labelled("User Pack — độc lập với bàn",packSpin!!));resource.addView(compactReissueButton("Chọn User Pack đã dùng",packUsedRows.length()>0){chooseUsed("Chọn User Pack đã dùng",packUsedRows){selectedPackUsed=it;packSpin?.setSelection(0);TopNotice.show(this,"Phát lại User Pack $it",TopNotice.Kind.INFO)}},matchWrap())
            }else resource.addView(info("Vị trí trong ca: $posLabel"))
        }
        val posBox=column(bg);posBox.addView(segmentedChoice(positionChoices,posKey){k->posKey=k;posLabel=positionChoices.firstOrNull{it.second==k}?.first?:k;rebuildResources()},matchWrap());body.addView(labelled("Vị trí trong ca",posBox));body.addView(gap(7));body.addView(resource,matchWrap());rebuildResources()
        val enter=primary("VÀO CA",teal){};enter.setOnClickListener{
            val positions=JSONArray();if(posKey!="NONE")positions.put(JSONObject().put("position_key",posKey).put("position_label",posLabel));val resources=JSONArray()
            if(posKey=="PICK"){
                val typed=pdaField?.text?.toString()?.trim().orEmpty();val p=selectedPda;if(typed.isNotBlank()){if(p==null||typed!=p.optString("last5").ifBlank{p.optString("serial").takeLast(5)}){showError("Nếu nhập PDA, hãy gõ 5 số cuối và chọn đúng PDA trong gợi ý.");return@setOnClickListener};resources.put(JSONObject().put("resource_type","PDA").put("resource_id",p.optString("serial")).put("pda_enter_status",p.optString("status")))}
                val normal=pickNormal.getOrNull((pickSpin?.selectedItemPosition?:0)-1).orEmpty();val u=selectedPickUsed.ifBlank{normal};if(u.isNotBlank())resources.put(JSONObject().put("resource_type","USER_PICK").put("resource_id",u).put("duplicate_user",selectedPickUsed.isNotBlank()))
            }
            if(posKey=="PACK"){
                val t=tableNormal.getOrNull((tableSpin?.selectedItemPosition?:0)-1).orEmpty();if(t.isNotBlank())resources.put(JSONObject().put("resource_type","PACK_TABLE").put("resource_id",t));val normal=packNormal.getOrNull((packSpin?.selectedItemPosition?:0)-1).orEmpty();val u=selectedPackUsed.ifBlank{normal};if(u.isNotBlank())resources.put(JSONObject().put("resource_type","USER_PACK").put("resource_id",u).put("duplicate_user",selectedPackUsed.isNotBlank()))
            }
            val gen=employeeLookupGeneration;enter.isEnabled=false;enter.text="ĐANG VÀO CA...";api.call("attendance_enter_v2",JSONObject().put("mnv",mnv).put("shift",shiftValue).put("positions",positions).put("resources",resources).put("idempotency_key",UUID.randomUUID().toString())){r->runOnUiThread{enter.isEnabled=true;enter.text="VÀO CA";if(!r.ok){showError(r.error?:"VÀO CA thất bại");return@runOnUiThread};TopNotice.show(this,"Đã ghi nhận vào ca.",TopNotice.Kind.SUCCESS);foregroundSync.requestSync();if(gen==employeeLookupGeneration&&liveEmployeeMnv==mnv)scheduleAttendanceAutoReset(mnv,gen)}}
        };body.addView(gap(8));body.addView(enter,matchWrap())
    }
'''
o=replace_fun(o,'    private fun renderEnter(body:LinearLayout,ctx:JSONObject,masters:JSONObject){',ENTER)
OPS.write_text(o)
assert 'CENTER_CROP/FIT_XY' not in FULL.read_text()
assert 'data class AddCtl' not in OPS.read_text()
assert 'rebuildResources()' in OPS.read_text()
print('BETA65_BEHAVIOR_COMPILE_FIX_PASS')

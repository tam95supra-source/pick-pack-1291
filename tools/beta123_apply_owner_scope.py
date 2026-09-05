from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]
OPS=ROOT/'app/src/main/java/vn/pickpack1291/app/beta/OperationsActivity.kt'
DROP=ROOT/'app/src/main/java/vn/pickpack1291/app/beta/DropReceiveFeature.kt'
MEAL=ROOT/'app/src/main/java/vn/pickpack1291/app/beta/PostMealAttendanceFeature.kt'
GRADLE=ROOT/'app/build.gradle.kts'
NOTES=ROOT/'app/src/main/java/vn/pickpack1291/app/beta/ReleaseNotes.kt'
QA=ROOT/'qa/beta123_owner_scope_regression.md'

def read(p): return p.read_text(encoding='utf-8')
def write(p,s): p.write_text(s,encoding='utf-8')
def require(cond,msg):
    if not cond: raise SystemExit(msg)
def replace_once(s,old,new,label):
    require(old in s,f'{label}: anchor missing')
    return s.replace(old,new,1)

def function_span(src,name):
    start=src.find(f'private fun {name}(')
    require(start>=0,f'{name}: function missing')
    brace=src.find('{',start)
    require(brace>=0,f'{name}: body missing')
    i=brace; depth=0; quote=None; line_comment=False; block_comment=False; esc=False
    while i < len(src):
        c=src[i]; n=src[i+1] if i+1<len(src) else ''
        if line_comment:
            if c=='\n': line_comment=False
            i+=1; continue
        if block_comment:
            if c=='*' and n=='/': block_comment=False; i+=2; continue
            i+=1; continue
        if quote:
            if esc: esc=False
            elif c=='\\': esc=True
            elif c==quote: quote=None
            i+=1; continue
        if c=='/' and n=='/': line_comment=True; i+=2; continue
        if c=='/' and n=='*': block_comment=True; i+=2; continue
        if c in ('\"',"'"): quote=c; i+=1; continue
        if c=='{': depth+=1
        elif c=='}':
            depth-=1
            if depth==0: return start,i+1
        i+=1
    raise SystemExit(f'{name}: unmatched body')

def replace_function(src,name,new_text):
    a,b=function_span(src,name)
    return src[:a]+new_text+src[b:]

# Beta126 identity. Stable block remains untouched.
g=read(GRADLE)
g=replace_once(g,'versionCode = 131','versionCode = 132','beta versionCode')
g=replace_once(g,'versionName = "0.4.2-beta.125"','versionName = "0.4.2-beta.126"','beta versionName')
write(GRADLE,g)
write(NOTES,'''package vn.pickpack1291.app.beta

object ReleaseNotes {
    const val VERSION_NAME = "0.4.2-beta.126"
    private val current = listOf(
        "Hoàn thiện các vùng màu Cài đặt để phân biệt rõ từng nhóm mà không thay đổi chức năng đã nghiệm thu.",
        "Tối ưu tìm kiếm Nhân sự bằng debounce; giữ danh sách và thao tác phản hồi ổn định trên PDA yếu.",
        "Sửa Báo cáo tình hình nhân sự theo đúng nội dung đã chốt: bỏ tổng/khấu trừ thừa, thêm vùng công nhật theo vị trí và Pick & Pack thực tế sau hỗ trợ.",
        "Công nhật nhiều người chuyển sang xử lý song song có giới hạn, chỉ làm mới UI một lần và bổ sung sửa hàng loạt BĐ/KT/khấu trừ.",
        "Giữ nguyên các mục đã PASS: Lịch sử, hàng đợi đồng bộ, Nhận hàng rớt, Nguồn PDA, Điểm danh local-first, QR và toàn bộ ACTIVE_PASS liên quan."
    )
    fun currentItems():List<String> = current.toList()
    fun currentText():String = current.joinToString("\\n") { "• $it" }
}
''')

ops=read(OPS)

# 1) Settings: the region background previously overwrote the per-region color with one common fill.
settings_at=ops.find('private fun settingsScreen(){')
require(settings_at>=0,'settingsScreen missing')
head,tail=ops[:settings_at],ops[settings_at:]
old='background=GradientDrawable().apply{setColor(Color.rgb(248,250,252));cornerRadius=dp(14).toFloat()}'
new='background=GradientDrawable().apply{setColor(when(title){"TÀI KHOẢN & QUYỀN"->Color.rgb(239,248,255);"GIAO DIỆN"->Color.rgb(242,252,247);"ỨNG DỤNG & CẬP NHẬT"->Color.rgb(255,248,237);else->Color.rgb(248,245,255)});cornerRadius=dp(14).toFloat()}'
tail=replace_once(tail,old,new,'settings distinct region fill')
ops=head+tail

# 2) Staff: never rebuild synchronously for every keystroke.
old='q.addTextChangedListener(object:TextWatcher{override fun beforeTextChanged(v:CharSequence?,st:Int,c:Int,a:Int)=Unit;override fun onTextChanged(v:CharSequence?,st:Int,b:Int,c:Int){render(v?.toString().orEmpty())};override fun afterTextChanged(v:Editable?)=Unit})'
new='var staffSearchGeneration=0L\n        q.addTextChangedListener(object:TextWatcher{override fun beforeTextChanged(v:CharSequence?,st:Int,c:Int,a:Int)=Unit;override fun onTextChanged(v:CharSequence?,st:Int,b:Int,c:Int){val value=v?.toString().orEmpty();val generation=++staffSearchGeneration;q.postDelayed({if(generation==staffSearchGeneration&&screenState=="STAFF")render(value)},180L)};override fun afterTextChanged(v:Editable?)=Unit})'
ops=replace_once(ops,old,new,'staff debounce')

# 3) Status: retain the actual route/provider even when health is degraded.
ops=replace_once(ops,'LanAuthorityPolicy.HealthState.DEGRADED->"Suy giảm"','LanAuthorityPolicy.HealthState.DEGRADED->provider.ifBlank{"Đang xác định"}+" • Suy giảm"','service degraded provider')

# 4) Report: remove the rows OWNER explicitly rejected and add the requested sections.
report_a,report_b=function_span(ops,'reportScreen')
report=ops[report_a:report_b]
pat=re.compile(r'''\s*box\.addView\(gap\(4\)\)\s*box\.addView\(details\(listOf\(\s*"Tổng nhân sự" to main\.distinctBy\{[^\n]+\}\.size\.toString\(\),\s*"Khấu trừ công nhật" to support\.size\.toString\(\),\s*"Picker thực tế" to "\$\{\(pickerBase-pickerDeduct\)\.coerceAtLeast\(0\)\} / \$pickerBase",\s*"Packer thực tế" to "\$\{\(packerBase-packerDeduct\)\.coerceAtLeast\(0\)\} / \$packerBase"\s*\)\)\)\s*if\(support\.isNotEmpty\(\)\)\{box\.addView\(gap\(4\)\);box\.addView\(s34ReportGrid\("",supportGrid\(support\),"Khấu trừ công nhật","position"\)\)\}''',re.S)
replacement='''
            box.addView(gap(6))
            box.addView(section("NHÂN SỰ PICK & PACK THỰC TẾ SAU KHI LOẠI TRỪ HỖ TRỢ"))
            box.addView(details(listOf(
                "Picker" to (pickerBase-pickerDeduct).coerceAtLeast(0).toString(),
                "Packer" to (packerBase-packerDeduct).coerceAtLeast(0).toString()
            )))
            if(support.isNotEmpty()){
                box.addView(gap(6));box.addView(section("CHI TIẾT CÔNG NHẬT"))
                box.addView(s34ReportGrid("",supportGrid(support),"Công nhật theo vị trí","position"))
            }'''
report2,n=pat.subn(replacement,report,count=1)
require(n==1,'report owner block not replaced')
ops=ops[:report_a]+report2+ops[report_b:]

# 5) Labor bounded parallel runner. UI refresh happens once in laborBatchResult.
runner='''    private fun <T> runBoundedLaborBatch(items:List<T>,maxInFlight:Int=6,worker:(T,(Boolean,String)->Unit)->Unit,done:(Int,List<String>)->Unit){
        if(items.isEmpty()){done(0,emptyList());return}
        val queue=java.util.ArrayDeque<T>();items.forEach{queue.addLast(it)}
        val failures=mutableListOf<String>();var running=0;var success=0;var finished=false
        lateinit var pump:()->Unit
        pump={
            if(finished)return@pump
            while(running<maxInFlight&&queue.isNotEmpty()){
                val item=queue.removeFirst();running++
                worker(item){ok,error->runOnUiThread{
                    running--
                    if(ok)success++ else if(error.isNotBlank())failures.add(error)
                    if(queue.isEmpty()&&running==0){finished=true;done(success,failures.toList())}else pump()
                }}
            }
        }
        pump()
    }

'''
anchor='    private fun showLaborBatchCreate(){'
require(anchor in ops,'labor create anchor missing')
ops=ops.replace(anchor,runner+anchor,1)

create_fn='''    private fun showLaborBatchCreateForm(chosen:List<JSONObject>){
        val masters=MasterDataCache.snapshot(this)?:JSONObject()
        val types=catalogValues("CÔNG NHẬT_Thông tin công nhật",jsonStrings(masters.optJSONArray("labor_types"))).ifEmpty{mutableListOf("Khác")}
        val box=column(surface).apply{setPadding(dp(10),dp(5),dp(10),dp(8))}
        box.addView(txt("Đã chọn ${chosen.size} nhân sự",10.2f,navy,true));box.addView(gap(6))
        val typeSpinner=spinner(types.toTypedArray());box.addView(labelled("Thông tin công nhật",typeSpinner));box.addView(gap(7))
        var startIso=Instant.now().toString();var endIso:String?=null
        fun timeButton(label:String)=Button(this).apply{text=label;textSize=11.5f;isAllCaps=false;setTextColor(navy);background=outlineBg(surface,11)}
        val startBtn=timeButton(compactAttendanceTime(startIso));val endBtn=timeButton("Chưa chọn")
        box.addView(labelled("Bắt đầu",startBtn));box.addView(gap(6));box.addView(labelled("Kết thúc (không bắt buộc)",endBtn));box.addView(gap(5))
        startBtn.setOnClickListener{laborWheelPick(startIso){picked->startIso=picked;startBtn.text=compactAttendanceTime(picked)}}
        endBtn.setOnClickListener{laborWheelPick(endIso?:Instant.now().toString(),true){picked->endIso=picked;endBtn.text=compactAttendanceTime(picked)}}
        val deduct=CheckBox(this).apply{text="Khấu trừ nhân sự";textSize=11f;setTextColor(ink)}
        box.addView(deduct,matchWrap());box.addView(gap(5))
        val note=input("Ghi chú",false);box.addView(note,matchWrap())
        val dialog=AlertDialog.Builder(this).setTitle("Tạo công nhật cho ${chosen.size} NLĐ").setView(ScrollView(this).apply{addView(box)}).setNegativeButton("Hủy",null).setPositiveButton("XÁC NHẬN",null).create()
        dialog.setOnShowListener{dialog.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener{
            val type=typeSpinner.selectedItem?.toString().orEmpty();if(type.isBlank())return@setOnClickListener
            val end=endIso;if(end!=null&&runCatching{Instant.parse(end).isBefore(Instant.parse(startIso))}.getOrDefault(true)){TopNotice.show(this,"Giờ kết thúc phải sau giờ bắt đầu.",TopNotice.Kind.WARNING);return@setOnClickListener}
            val noteText=note.text.toString();val deductRequested=deduct.isChecked;dialog.dismiss()
            verifyActionPassword("tạo công nhật nhanh cho ${chosen.size} nhân sự"){
                runBoundedLaborBatch(chosen,6,{row,complete->
                    val mnv=row.optString("mnv");val sid=row.optString("session_id")
                    api.call("employee_context",JSONObject().put("mnv",mnv).put("session_id",sid).put("include_labor",true).put("include_options",false)){fresh->runOnUiThread{
                        val json=fresh.json;val session=json?.optJSONObject("session")
                        if(!fresh.ok||json?.optString("state")!="ACTIVE"||json.optJSONObject("active_labor")!=null||session==null){complete(false,"$mnv: phiên/công nhật đã thay đổi");return@runOnUiThread}
                        val laborId=UUID.randomUUID().toString();val startEvent=UUID.randomUUID().toString()
                        val fixedMain=foldLocal(row.optString("position")).let{it.contains("KEO HANG")||it.contains("TO TRUONG")}
                        val fixedLabor=foldLocal(type).let{it.contains("KEO HANG")||it.contains("TO TRUONG")}
                        val deductValue=deductRequested&&!fixedMain&&!fixedLabor
                        val payload=JSONObject().put("event_id",startEvent).put("labor_id",laborId).put("mnv",mnv).put("business_date",session.optString("business_date"))
                            .put("session_id",session.optString("session_id")).put("shift",session.optString("shift")).put("labor_type",type).put("start_at",startIso).put("deduct_staff",deductValue).put("note",noteText)
                        api.call("labor_start",payload){started->runOnUiThread{
                            if(!started.ok){complete(false,"$mnv: ${started.error?:"không tạo được"}");return@runOnUiThread}
                            val optimistic=JSONObject().put("labor_id",laborId).put("mnv",mnv).put("business_date",session.optString("business_date")).put("shift",session.optString("shift")).put("labor_type",type).put("state","OPEN").put("start_at",startIso).put("end_at",JSONObject.NULL).put("note",noteText).put("deduct_staff",deductValue).put("attendance_session_id",session.optString("session_id")).put("full_name",row.optString("full_name")).put("supplier",row.optString("supplier")).put("position",row.optString("position"))
                            patchLaborCacheOptimistic(optimistic)
                            if(end==null){complete(true,"");return@runOnUiThread}
                            api.call("labor_finish",JSONObject().put("event_id",UUID.randomUUID().toString()).put("depends_on_event_id",startEvent).put("labor_id",laborId).put("mnv",mnv).put("business_date",session.optString("business_date")).put("session_id",session.optString("session_id")).put("start_at",startIso).put("end_at",end).put("note",noteText)){done->runOnUiThread{
                                if(!done.ok)complete(false,"$mnv: đã tạo nhưng chưa kết thúc — ${done.error?:"lỗi"}")
                                else{patchLaborCacheOptimistic(JSONObject(optimistic.toString()).put("state","COMPLETED").put("end_at",end));complete(true,"")}
                            }}
                        }}
                    }}
                },{ok,failures->laborBatchResult("Tạo công nhật nhanh",ok,failures)})
            }
        }}
        dialog.show()
    }'''
ops=replace_function(ops,'showLaborBatchCreateForm',create_fn)

finish_fn='''    private fun showLaborBatchFinishForm(chosen:List<JSONObject>){
        val box=column(surface).apply{setPadding(dp(10),dp(5),dp(10),dp(8))}
        box.addView(txt("Đã chọn ${chosen.size} nhân sự đang làm công nhật",10.2f,navy,true));box.addView(gap(6))
        var endIso=Instant.now().toString()
        val endBtn=Button(this).apply{text=compactAttendanceTime(endIso);textSize=11.5f;isAllCaps=false;setTextColor(navy);background=outlineBg(surface,11)}
        box.addView(labelled("Giờ kết thúc",endBtn));box.addView(gap(5));endBtn.setOnClickListener{laborWheelPick(endIso,true){picked->endIso=picked;endBtn.text=compactAttendanceTime(picked)}}
        val note=input("Ghi chú",false);box.addView(note,matchWrap())
        val dialog=AlertDialog.Builder(this).setTitle("Kết thúc công nhật ${chosen.size} NLĐ").setView(box).setNegativeButton("Hủy",null).setPositiveButton("XÁC NHẬN",null).create()
        dialog.setOnShowListener{dialog.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener{
            val noteText=note.text.toString();dialog.dismiss()
            verifyActionPassword("kết thúc công nhật nhanh cho ${chosen.size} nhân sự"){
                runBoundedLaborBatch(chosen,6,{row,complete->
                    val mnv=row.optString("mnv");val sid=row.optString("attendance_session_id");val laborId=row.optString("labor_id")
                    api.call("employee_context",JSONObject().put("mnv",mnv).put("session_id",sid).put("include_labor",true).put("include_options",false)){fresh->runOnUiThread{
                        val active=fresh.json?.optJSONObject("active_labor")
                        if(!fresh.ok||active?.optString("labor_id")!=laborId){complete(false,"$mnv: công nhật đã thay đổi");return@runOnUiThread}
                        api.call("labor_finish",JSONObject().put("event_id",UUID.randomUUID().toString()).put("labor_id",laborId).put("mnv",mnv).put("business_date",row.optString("business_date")).put("session_id",sid).put("start_at",active.optString("start_at")).put("end_at",endIso).put("note",noteText)){done->runOnUiThread{
                            if(!done.ok)complete(false,"$mnv: ${done.error?:"không kết thúc được"}")
                            else{patchLaborCacheOptimistic(JSONObject(row.toString()).put("state","COMPLETED").put("end_at",endIso));complete(true,"")}
                        }}
                    }}
                },{ok,failures->laborBatchResult("Kết thúc công nhật nhanh",ok,failures)})
            }
        }};dialog.show()
    }'''
ops=replace_function(ops,'showLaborBatchFinishForm',finish_fn)

# Bulk correction for completed labor intervals: optional shared start/end + tri-state deduction.
edit_code='''
    private fun showLaborBatchEdit(){
        val date=operationalStore.businessDate()
        api.call("labor_list",JSONObject().put("business_date",date)){r->runOnUiThread{
            if(handleAuth(r))return@runOnUiThread;if(!r.ok){showError(r.error?:"Không tải được công nhật");return@runOnUiThread}
            val a=r.json?.optJSONArray("items")?:JSONArray();val candidates=mutableListOf<JSONObject>()
            for(i in 0 until a.length()){
                val x=a.optJSONObject(i)?:continue
                if(x.optString("state").equals("OPEN",true)||x.optString("labor_id").isBlank()||x.optString("end_at").isBlank())continue
                val emp=MasterDataCache.employee(this,x.optString("mnv"))
                candidates.add(JSONObject(x.toString()).put("position",emp?.optString("main_position").orEmpty()).put("supplier",x.optString("supplier").ifBlank{emp?.optString("supplier").orEmpty()}).put("full_name",x.optString("full_name").ifBlank{emp?.optString("full_name").orEmpty()}))
            }
            showLaborBatchSelector("Sửa nhiều công nhật",candidates){chosen->showLaborBatchEditForm(chosen)}
        }}
    }

    private fun showLaborBatchEditForm(chosen:List<JSONObject>){
        val box=column(surface).apply{setPadding(dp(10),dp(5),dp(10),dp(8))}
        box.addView(txt("Đã chọn ${chosen.size} khoảng công nhật đã hoàn thành",10.2f,navy,true));box.addView(gap(7))
        val applyStart=CheckBox(this).apply{text="Áp dụng cùng giờ bắt đầu";setTextColor(ink)};var startIso=chosen.first().optString("start_at")
        val startBtn=Button(this).apply{text=compactAttendanceTime(startIso);isAllCaps=false;background=outlineBg(surface,11);setTextColor(navy);isEnabled=false;alpha=.55f}
        applyStart.setOnCheckedChangeListener{_,on->startBtn.isEnabled=on;startBtn.alpha=if(on)1f else .55f};startBtn.setOnClickListener{laborWheelPick(startIso){startIso=it;startBtn.text=compactAttendanceTime(it)}}
        box.addView(applyStart);box.addView(startBtn,LinearLayout.LayoutParams(-1,dp(40)));box.addView(gap(6))
        val applyEnd=CheckBox(this).apply{text="Áp dụng cùng giờ kết thúc";setTextColor(ink)};var endIso=chosen.first().optString("end_at")
        val endBtn=Button(this).apply{text=compactAttendanceTime(endIso);isAllCaps=false;background=outlineBg(surface,11);setTextColor(navy);isEnabled=false;alpha=.55f}
        applyEnd.setOnCheckedChangeListener{_,on->endBtn.isEnabled=on;endBtn.alpha=if(on)1f else .55f};endBtn.setOnClickListener{laborWheelPick(endIso,true){endIso=it;endBtn.text=compactAttendanceTime(it)}}
        box.addView(applyEnd);box.addView(endBtn,LinearLayout.LayoutParams(-1,dp(40)));box.addView(gap(7))
        val deductMode=spinner(arrayOf("Giữ nguyên khấu trừ","Có khấu trừ","Không khấu trừ"));box.addView(labelled("Khấu trừ nhân sự",deductMode));box.addView(gap(5))
        val dialog=AlertDialog.Builder(this).setTitle("Sửa nhiều công nhật").setView(ScrollView(this).apply{addView(box)}).setNegativeButton("Hủy",null).setPositiveButton("LƯU",null).create()
        dialog.setOnShowListener{dialog.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener{
            if(!applyStart.isChecked&&!applyEnd.isChecked&&deductMode.selectedItemPosition==0){TopNotice.show(this,"Chọn ít nhất một nội dung cần sửa.",TopNotice.Kind.WARNING);return@setOnClickListener}
            dialog.dismiss();verifyActionPassword("sửa nhiều công nhật"){
                runBoundedLaborBatch(chosen,6,{row,complete->
                    val mnv=row.optString("mnv");val start=if(applyStart.isChecked)startIso else row.optString("start_at");val end=if(applyEnd.isChecked)endIso else row.optString("end_at")
                    val sm=runCatching{Instant.parse(start).toEpochMilli()}.getOrDefault(0L);val em=runCatching{Instant.parse(end).toEpochMilli()}.getOrDefault(0L)
                    if(sm<=0||em<sm){complete(false,"$mnv: giờ BĐ/KT không hợp lệ");return@runBoundedLaborBatch}
                    val payload=JSONObject().put("event_id",UUID.randomUUID().toString()).put("labor_id",row.optString("labor_id")).put("mnv",mnv).put("business_date",row.optString("business_date")).put("session_id",row.optString("attendance_session_id")).put("start_at",start).put("end_at",end).put("correction",true).put("note",row.optString("note"))
                    if(deductMode.selectedItemPosition>0){
                        val requested=deductMode.selectedItemPosition==1;val fixedMain=foldLocal(row.optString("position")).let{it.contains("KEO HANG")||it.contains("TO TRUONG")};val fixedLabor=foldLocal(row.optString("labor_type")).let{it.contains("KEO HANG")||it.contains("TO TRUONG")}
                        payload.put("deduct_staff",requested&&!fixedMain&&!fixedLabor)
                    }
                    api.call("labor_finish",payload){r->runOnUiThread{
                        if(!r.ok)complete(false,"$mnv: ${r.error?:"không sửa được"}")
                        else{val optimistic=JSONObject(row.toString()).put("start_at",start).put("end_at",end);if(payload.has("deduct_staff"))optimistic.put("deduct_staff",payload.optBoolean("deduct_staff"));patchLaborCacheOptimistic(optimistic);complete(true,"")}
                    }}
                },{ok,failures->laborBatchResult("Sửa nhiều công nhật",ok,failures)})
            }
        }};dialog.show()
    }
'''
ops=replace_once(ops,'    private fun laborHome(){',edit_code+'\n    private fun laborHome(){','labor bulk edit insertion')

# Add the third batch action in labor home and keep compact widths.
old='''        val batchRow=row(bg).apply{gravity=Gravity.CENTER_VERTICAL}
        val batchCreate=smallButton("TẠO NHANH NHIỀU NLĐ",green)
        val batchFinish=smallButton("KẾT THÚC NHANH NHIỀU NLĐ",red)
        batchRow.addView(batchCreate,LinearLayout.LayoutParams(0,dp(42),.88f).apply{marginEnd=dp(3)})
        batchRow.addView(batchFinish,LinearLayout.LayoutParams(0,dp(42),1.12f).apply{marginStart=dp(3)})
        body.addView(batchRow,matchWrap());body.addView(gap(7))'''
new='''        val batchRow=row(bg).apply{gravity=Gravity.CENTER_VERTICAL}
        val batchCreate=smallButton("TẠO NHIỀU",green)
        val batchFinish=smallButton("KẾT THÚC NHIỀU",red)
        val batchEdit=smallButton("SỬA NHIỀU",navy)
        batchRow.addView(batchCreate,LinearLayout.LayoutParams(0,dp(42),1f).apply{marginEnd=dp(2)})
        batchRow.addView(batchFinish,LinearLayout.LayoutParams(0,dp(42),1f).apply{marginStart=dp(2);marginEnd=dp(2)})
        batchRow.addView(batchEdit,LinearLayout.LayoutParams(0,dp(42),1f).apply{marginStart=dp(2)})
        body.addView(batchRow,matchWrap());body.addView(gap(7))'''
ops=replace_once(ops,old,new,'labor batch action row')
ops=replace_once(ops,'batchCreate.setOnClickListener{showLaborBatchCreate()};batchFinish.setOnClickListener{showLaborBatchFinish()}','batchCreate.setOnClickListener{showLaborBatchCreate()};batchFinish.setOnClickListener{showLaborBatchFinish()};batchEdit.setOnClickListener{showLaborBatchEdit()}','labor edit listener')

write(OPS,ops)

# QA addendum: explicit guards for the gaps that Beta123 contract previously missed.
qa=read(QA)
add='''

## Beta126 remediation — OWNER DOCX scope audit
Status: LOCKED_REQUIREMENT_PENDING_FIX until exact Beta126 candidate passes all gates; then TECHNICAL_PASS_AWAITING_OWNER.

New mandatory regression checks:
- Settings region fills are actually distinct at rendered background level; cache/reset semantics retained for every role.
- Staff search is debounce-driven and cannot synchronously rebuild on every character.
- Report contains `BÁO CÁO TÌNH HÌNH NHÂN SỰ`, `Ca 1 và HC / C2 / Cả ngày`, has `CHI TIẾT CÔNG NHẬT` and `NHÂN SỰ PICK & PACK THỰC TẾ SAU KHI LOẠI TRỪ HỖ TRỢ`, and contains no `Tổng nhân sự` / `Khấu trừ công nhật` summary rows.
- Labor batch create/finish uses bounded concurrency and one UI refresh at completion; no recursive per-person `next(index,ok)` chain.
- Labor bulk edit supports shared BĐ, shared KT and tri-state deduction while preserving fixed-position deduction guards.
- Header Service keeps actual provider/route visible when degraded.
- Previously proven History/queue recovery/Drop/PDA source/Meal local-first/QR roster-hide behavior must remain unchanged.
- Exact candidate visual matrix: 320x568, 360x640, 480x800 with human inspection; PDA functional must exercise Staff search, Report, Labor batch selector/edit, Settings and QR navigation.
'''
if '## Beta126 remediation — OWNER DOCX scope audit' not in qa: qa+=add
write(QA,qa)

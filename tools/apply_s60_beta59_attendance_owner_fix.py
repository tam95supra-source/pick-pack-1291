from pathlib import Path

p = Path("app/src/main/java/vn/pickpack1291/app/beta/OperationsActivity.kt")
s = p.read_text()


def between(text: str, start: str, end: str, new: str) -> str:
    i = text.index(start)
    j = text.index(end, i)
    return text[:i] + new.rstrip() + "\n\n    " + text[j:]


if "S60_BETA59_OWNER_ATTENDANCE_UI" in s:
    raise SystemExit("S60 already applied")

s = between(s, "private fun businessHome(){", "// S59_BETA58_SHIFT_RECONCILIATION_HOME:", r'''private fun businessHome(){
        module="BUSINESS";screenState="BUSINESS"
        val root=baseRoot("NGHIỆP VỤ");val body=body()
        addBusinessShiftReconciliation(body)
        val cards=listOf(
            businessCard(R.drawable.ic_pp_scan,"Quét QR nhân sự","",true){employeeScan()},
            businessCard(R.drawable.ic_pp_pda_exchange,"Đổi / trả PDA","",true){pdaExchangeScreen()},
            businessCard(R.drawable.ic_pp_drop_receive,"Nhận hàng Rớt","",true){TopNotice.show(this,"Nhận hàng Rớt đang được chuẩn bị.",TopNotice.Kind.INFO)},
            businessCard(R.drawable.ic_pp_report,"Báo cáo nhân sự","",isAdmin()){reportScreen()},
            businessCard(R.drawable.ic_pp_task,"Công nhật","",isAdmin()){laborHome()},
            businessCard(R.drawable.ic_pp_resource,"Tài nguyên","",isAdmin()){resourceHome()},
            businessCard(R.drawable.ic_pp_ccdc,"Quản lý CCDC","",isAdmin()){TopNotice.show(this,"Quản lý CCDC đang được chuẩn bị.",TopNotice.Kind.INFO)},
            businessCard(R.drawable.ic_pp_document,"Quản lý biên bản","",isAdmin()){TopNotice.show(this,"Quản lý biên bản đang chờ xây dựng.",TopNotice.Kind.INFO)}
        )
        body.addView(businessRow(cards[0],cards[1]));body.addView(gap(7))
        body.addView(businessRow(cards[2],cards[3]));body.addView(gap(7))
        body.addView(businessRow(cards[4],cards[5]));body.addView(gap(7))
        body.addView(businessRow(cards[6],cards[7]))
        attach(root,body)
    }''')

s = between(s, "// S59_BETA58_SHIFT_RECONCILIATION_HOME:", "private fun employeeScan()", r'''// S60_BETA59_SHIFT_RECONCILIATION_EXACT: only real enter_at / exit_at timestamps count.
    private fun addBusinessShiftReconciliation(body:LinearLayout){
        val day=operationalStore.loadDay(operationalStore.businessDate())?:return
        val sessions=day.optJSONArray("sessions")?:JSONArray()
        val byShift=linkedMapOf<String,MutableList<JSONObject>>("Ca 1" to mutableListOf(),"Ca HC" to mutableListOf(),"Ca 2" to mutableListOf())
        for(i in 0 until sessions.length()){
            val ses=sessions.optJSONObject(i)?:continue;val shift=ses.optString("shift").trim()
            if(shift in byShift.keys)byShift.getValue(shift).add(JSONObject(ses.toString()))
        }
        val bar=row(bg).apply{gravity=Gravity.CENTER_VERTICAL}
        byShift.forEach{(shift,raw)->
            val rows=raw.distinctBy{it.optString("session_id").ifBlank{"${it.optString("mnv")}|${it.optString("enter_at")}"}}
            val entered=rows.filter{dash(it.optString("enter_at"))!="—"}
            val exited=entered.filter{dash(it.optString("exit_at"))!="—"}
            val pending=entered.filter{dash(it.optString("exit_at"))=="—"}
            val button=reconciliationButton("$shift ${entered.size}/${exited.size}",entered.size==exited.size)
            button.setOnClickListener{
                if(pending.isEmpty())TopNotice.show(this,"$shift: ${entered.size}/${exited.size} • đã đối soát đủ.",TopNotice.Kind.SUCCESS)
                else{
                    val labels=pending.map{ses->val mnv=ses.optString("mnv").trim();val emp=MasterDataCache.employee(this,mnv);val display=emp?.optString("full_name").orEmpty().ifBlank{ses.optJSONObject("employee_snapshot")?.optString("full_name").orEmpty()};"$mnv • ${display.ifBlank{"—"}}"}
                    AlertDialog.Builder(this).setTitle("$shift • ${pending.size} nhân sự chưa ra").setItems(labels.toTypedArray()){_,which->pending.getOrNull(which)?.optString("mnv")?.takeIf{it.isNotBlank()}?.let(::loadEmployee)}.setNegativeButton("Đóng",null).show()
                }
            }
            bar.addView(button,LinearLayout.LayoutParams(0,dp(40),1f).apply{marginStart=dp(2);marginEnd=dp(2)})
        }
        body.addView(bar,matchWrap());body.addView(gap(5))
    }''')

s = between(s, "private fun addPdaIdentity(body:LinearLayout,ses:JSONObject){", "private fun addSessionTimeline(body:LinearLayout,mnv:String){", r'''private data class ShiftResourceUsage(val pdas:LinkedHashMap<String,String>,val userPicks:LinkedHashSet<String>,val userPacks:LinkedHashSet<String>)
    private fun shiftResourceUsage(mnv:String,ses:JSONObject):ShiftResourceUsage{
        val pdas=linkedMapOf<String,String>();val picks=linkedSetOf<String>();val packs=linkedSetOf<String>()
        fun clean(v:String)=v.trim().takeUnless{it.isBlank()||it.equals("null",true)||it=="—"}.orEmpty()
        fun addSnapshot(x:JSONObject){
            val serial=clean(x.optString("pda_serial"));val status=clean(x.optString("pda_enter_status")).ifBlank{clean(x.optString("pda_status_at_enter"))}
            if(serial.isNotBlank()&&!pdas.containsKey(serial))pdas[serial]=status else if(serial.isNotBlank()&&pdas[serial].isNullOrBlank()&&status.isNotBlank())pdas[serial]=status
            clean(x.optString("user_pick")).takeIf{it.isNotBlank()}?.let{picks.add(it)};clean(x.optString("user_pack")).takeIf{it.isNotBlank()}?.let{packs.add(it)}
        }
        sessionTimelineItems(mnv).forEach{e->val raw=e.optString("payload_json");val payload=if(raw.isNotBlank())runCatching{JSONObject(raw)}.getOrDefault(JSONObject()) else e.optJSONObject("payload")?:JSONObject();addSnapshot(payload);payload.optJSONObject("before")?.let(::addSnapshot);payload.optJSONObject("after")?.let(::addSnapshot)}
        addSnapshot(ses);return ShiftResourceUsage(LinkedHashMap(pdas),LinkedHashSet(picks),LinkedHashSet(packs))
    }
    private fun addPdaUsage(body:LinearLayout,mnv:String,ses:JSONObject){
        body.addView(section("PDA SỬ DỤNG TRONG CA"));val usage=shiftResourceUsage(mnv,ses)
        if(usage.pdas.isEmpty()){body.addView(txt("—",10.5f,muted,true).apply{setPadding(dp(10),dp(5),dp(10),dp(5))});return}
        usage.pdas.forEach{(serial,status)->body.addView(column(surface).apply{setPadding(dp(14),dp(10),dp(14),dp(10));background=outlineBg(surface,14);addView(txt("Seri PDA",9.5f,muted,true));addView(txt(serial,16.5f,navy,true));addView(gap(5));addView(txt("Tình trạng ghi nhận ban đầu",9.5f,muted,true));addView(txt(dash(status),11.2f,ink,true))},matchWrap());body.addView(gap(5))}
    }''')

s = s.replace('''        body.addView(info("Mỗi lần đổi vị trí / Pick / Pack được giữ thành một mốc riêng. Mốc mới không ghi đè lịch sử cũ."));body.addView(gap(7))
        val items=sessionTimelineItems(mnv)
        if(items.isEmpty()){body.addView(info("Chưa có mốc công việc trong bộ nhớ PDA. Hệ thống sẽ bổ sung khi snapshot đồng bộ về."));return}''','''        val items=sessionTimelineItems(mnv)
        if(items.isEmpty()){body.addView(txt("—",10.5f,muted,true).apply{setPadding(dp(10),dp(5),dp(10),dp(5))});return}''')

s = s.replace('''            if(type=="RESOURCE_CHANGE"){val after=p.optJSONObject("after");if(after!=null)return sessionWorkDetail(after)}''','''            if(type=="RESOURCE_CHANGE"){val before=p.optJSONObject("before")?:JSONObject();val after=p.optJSONObject("after")?:JSONObject();val kind=p.optString("mutation_kind").uppercase();val verb=when(kind){"ADD"->"Thêm";"DELETE"->"Xóa";else->"Sửa"};return "$verb • Trước: ${sessionWorkDetail(before).ifBlank{"—"}} • Sau: ${sessionWorkDetail(after).ifBlank{"—"}}"}''')

s = s.replace('private fun sessionWorkEditor(ctx:JSONObject){\n        val ses=ctx.optJSONObject("session")?:return;val mnv=ses.optString("mnv")','private fun sessionWorkEditor(ctx:JSONObject,mode:String){\n        val ses=ctx.optJSONObject("session")?:return;val mnv=ses.optString("mnv");val editMode=if(mode.uppercase()=="ADD")"ADD" else "EDIT"',1)
s = s.replace('        dialogBody.addView(info("PICK và PACK là hai phần độc lập. Có thể giữ đồng thời cả hai; lưu mới chỉ cập nhật trạng thái hiện tại, lịch sử các lần trước vẫn giữ nguyên."));dialogBody.addView(gap(8))','        dialogBody.addView(gap(2))',1)
s = s.replace('AlertDialog.Builder(this).setTitle("Thêm / sửa công việc trong ca")','AlertDialog.Builder(this).setTitle(if(editMode=="ADD")"Thêm công việc / User trong ca" else "Sửa công việc trong ca")',1)
s = s.replace('''            val baseNote=when{pickOn.isChecked&&packOn.isChecked->"PICK + PACK";pickOn.isChecked->"PICK";packOn.isChecked->"PACK";else->"Đã trả tài nguyên"};p.put("work_choice",primary).put("resource_note",if(reissue)"$baseNote • PHÁT LẠI USER" else baseNote)''','''            val baseNote=when{pickOn.isChecked&&packOn.isChecked->"PICK + PACK";pickOn.isChecked->"PICK";packOn.isChecked->"PACK";else->"Không gán công việc"};p.put("work_choice",primary).put("resource_note",ses.optString("resource_note")).put("mutation_kind",editMode).put("audit_note",if(reissue)"$baseNote • PHÁT LẠI USER" else baseNote)''',1)

insert = r'''private fun deleteSessionWork(ctx:JSONObject){
        val ses=ctx.optJSONObject("session")?:return;val mnv=ses.optString("mnv")
        if(ses.optString("state")!="ACTIVE"){showError("Phiên không còn hoạt động.");return}
        val hasPick=ses.optString("pda_serial").isNotBlank()||ses.optString("user_pick").isNotBlank()||ses.optString("work_choice")=="PICK";val hasPack=ses.optString("pack_table").isNotBlank()||ses.optString("user_pack").isNotBlank()||ses.optString("work_choice")=="PACK"
        val labels=mutableListOf<String>();if(hasPick)labels.add("Công việc PICK / PDA / User Pick");if(hasPack)labels.add("Công việc PACK / User Pack")
        if(labels.isEmpty()){TopNotice.show(this,"Không có thông tin công việc đang lưu để xóa.",TopNotice.Kind.INFO);return}
        val checked=BooleanArray(labels.size){true}
        AlertDialog.Builder(this).setTitle("Xóa thông tin công việc trong ca").setMultiChoiceItems(labels.toTypedArray(),checked){_,which,on->checked[which]=on}.setNegativeButton("Hủy",null).setPositiveButton("XÓA"){_,_->
            if(!checked.any{it}){showError("Chọn ít nhất một thông tin cần xóa.");return@setPositiveButton};var idx=0;val deletePick=if(hasPick)checked[idx++] else false;val deletePack=if(hasPack)checked[idx] else false
            val p=JSONObject().put("session_id",ses.optString("session_id")).put("mnv",mnv).put("idempotency_key",UUID.randomUUID().toString()).put("mutation_kind","DELETE").put("audit_note","Xóa thông tin công việc đã chọn").put("resource_note",ses.optString("resource_note"))
            p.put("pda_serial",if(deletePick)"" else ses.optString("pda_serial")).put("user_pick",if(deletePick)"" else ses.optString("user_pick")).put("pack_table",if(deletePack)"" else ses.optString("pack_table")).put("user_pack",if(deletePack)"" else ses.optString("user_pack"))
            val keepPick=!deletePick&&hasPick;val keepPack=!deletePack&&hasPack;p.put("work_choice",when{keepPick->"PICK";keepPack->"PACK";else->"KHONG"})
            api.call("session_work_update",p){r->runOnUiThread{if(handleAuth(r))return@runOnUiThread;if(!r.ok){showError(r.error?:"Không xóa được thông tin công việc");return@runOnUiThread};TopNotice.show(this,"Đã xóa thông tin công việc và lưu lịch sử.",TopNotice.Kind.SUCCESS);foregroundSync.requestSync();val next=returnedSessionContext(ctx,r);if(next!=null)renderEmployee(next,PdaLocalProjection.resourceOptions(this,mnv))else loadEmployee(mnv)}}
        }.show()
    }

    '''
s = s.replace('    private fun editableTime(iso:String):String=', '    ' + insert + 'private fun editableTime(iso:String):String=', 1)

active = r'''private fun renderActive(body: LinearLayout, ctx: JSONObject) {
        val ses=ctx.optJSONObject("session")?:JSONObject();val mnv=ses.optString("mnv");fun clean(v:String)=v.trim().takeUnless{it.equals("null",true)||it=="—"}?:""
        val pda=clean(ses.optString("pda_serial"));val expectedStatus=clean(ses.optString("pda_enter_status"));val activeLabor=ctx.optJSONObject("active_labor");val usage=shiftResourceUsage(mnv,ses);val currentWork=clean(ses.optString("work_choice")).let{if(it.isBlank())"—" else workText(it)}
        body.addView(status("ĐANG TRONG PHIÊN",green,Color.rgb(235,248,239)));body.addView(gap(7));body.addView(section("THỜI GIAN & CÔNG VIỆC HIỆN TẠI"));body.addView(details(listOf("Ca" to dash(ses.optString("shift")),"Vào lúc" to formatIso(ses.optString("enter_at")),"Ra lúc" to "—","Công việc hiện tại" to currentWork,"User Pick trong ca" to usage.userPicks.joinToString(", ").ifBlank{"—"},"User Pack trong ca" to usage.userPacks.joinToString(", ").ifBlank{"—"},"Ghi chú" to dash(ses.optString("resource_note")))));body.addView(gap(7))
        val exit=smallButton("Ra ca",red)
        fun doExit(statusNow:String){exit.isEnabled=false;exit.text="Đang ra...";val eventId=UUID.randomUUID().toString();api.call("exit",JSONObject().put("event_id",eventId).put("mnv",mnv).put("pda_exit_status",statusNow).put("note","RA CA")){r->runOnUiThread{exit.isEnabled=true;exit.text="Ra ca";if(handleAuth(r))return@runOnUiThread;if(!r.ok){showError(r.error?:"RA_CA_FAILED");return@runOnUiThread};TopNotice.show(this,if(r.code==202)"Đã ghi nhận ra ca trên PDA • đang đồng bộ" else "Đã ghi nhận ra ca.",TopNotice.Kind.SUCCESS);foregroundSync.requestSync();scheduleAttendanceAutoReset(mnv,employeeLookupGeneration)}}}
        exit.setOnClickListener{if(activeLabor!=null){showError("Còn công nhật đang làm. Hoàn thành công nhật trước khi ra ca.");return@setOnClickListener};if(pda.isBlank()){AlertDialog.Builder(this).setTitle("Xác nhận RA CA").setMessage("Xác nhận kết thúc phiên?").setNegativeButton("Hủy",null).setPositiveButton("RA CA"){_,_->doExit("")}.show();return@setOnClickListener};val statuses=mutableListOf<String>();val arr=MasterDataCache.resourceOptions(this).optJSONArray("pda_statuses")?:JSONArray();for(i in 0 until arr.length()){val v=clean(arr.optString(i));if(v.isNotBlank()&&!statuses.contains(v))statuses.add(v)};if(expectedStatus.isNotBlank()&&!statuses.contains(expectedStatus))statuses.add(0,expectedStatus);if(statuses.isEmpty()){showError("Không có danh mục tình trạng PDA để đối chiếu.");return@setOnClickListener};val sp=spinner(statuses.toTypedArray());val wrap=column(surface).apply{setPadding(dp(16),dp(6),dp(16),dp(4));addView(txt("Seri PDA: $pda",12f,navy,true));addView(gap(5));addView(txt("Tình trạng khi nhận: ${expectedStatus.ifBlank{"—"}}",10.5f,muted,true));addView(gap(9));addView(labelled("Tình trạng PDA hiện tại",sp))};AlertDialog.Builder(this).setTitle("Đối chiếu PDA trước khi RA CA").setView(wrap).setNegativeButton("Hủy",null).setPositiveButton("KIỂM TRA & RA CA"){_,_->doExit(sp.selectedItem?.toString().orEmpty())}.show()}
        val actions=row(bg).apply{gravity=Gravity.CENTER_VERTICAL};actions.addView(smallButton("Thêm",teal).apply{setOnClickListener{sessionWorkEditor(ctx,"ADD")}},LinearLayout.LayoutParams(0,dp(40),1f).apply{marginEnd=dp(2)});actions.addView(smallButton("Sửa",navy).apply{setOnClickListener{sessionWorkEditor(ctx,"EDIT")}},LinearLayout.LayoutParams(0,dp(40),1f).apply{marginStart=dp(2);marginEnd=dp(2)});actions.addView(smallButton("Xóa",orange).apply{setOnClickListener{deleteSessionWork(ctx)}},LinearLayout.LayoutParams(0,dp(40),1f).apply{marginStart=dp(2);marginEnd=dp(2)});actions.addView(exit,LinearLayout.LayoutParams(0,dp(40),1f).apply{marginStart=dp(2)});body.addView(actions,matchWrap());body.addView(gap(7))
        if(activeLabor!=null){body.addView(status("CÒN CÔNG NHẬT ĐANG LÀM",orange,Color.rgb(255,247,230)));body.addView(gap(5))};addPdaUsage(body,mnv,ses);body.addView(gap(6));addSessionTimeline(body,mnv);if(isAdmin()){body.addView(gap(7));body.addView(smallButton("Sửa giờ vào ca",navy).apply{setOnClickListener{editAttendanceTime(ctx,"enter_at")}},matchWrap())}
    }'''
s = between(s, "private fun renderActive(body: LinearLayout, ctx: JSONObject) {", "private fun renderEnded(body: LinearLayout, ctx: JSONObject) {", active)
s = s.replace("addPdaIdentity(body,ses)", "addPdaUsage(body,mnv,ses)")

panel = r'''private fun pdaSelectedPanel(pdas:JSONArray,field:AutoCompleteTextView):TextView{
        val panel=txt("Seri PDA được chọn\nChưa chọn seri",11.2f,navy,false).apply{setPadding(dp(12),dp(9),dp(12),dp(9));background=outlineBg(Color.rgb(239,246,255),13)}
        fun update(){val serial=resolvePda(pdas,field.text?.toString().orEmpty());val value=serial?.takeIf{it.isNotBlank()}?:"Chưa chọn seri";val full="Seri PDA được chọn\n$value";val styled=android.text.SpannableStringBuilder(full);val start=full.indexOf('\n')+1;styled.setSpan(android.text.style.StyleSpan(Typeface.BOLD),start,full.length,android.text.Spanned.SPAN_EXCLUSIVE_EXCLUSIVE);styled.setSpan(android.text.style.RelativeSizeSpan(1.10f),start,full.length,android.text.Spanned.SPAN_EXCLUSIVE_EXCLUSIVE);panel.text=styled;panel.setTextColor(if(serial.isNullOrBlank())muted else navy)}
        field.addTextChangedListener(object:TextWatcher{override fun beforeTextChanged(v:CharSequence?,start:Int,count:Int,after:Int)=Unit;override fun onTextChanged(v:CharSequence?,start:Int,before:Int,count:Int)=update();override fun afterTextChanged(v:Editable?)=Unit});update();return panel
    }'''
s = between(s, "private fun pdaSelectedPanel(pdas:JSONArray,field:AutoCompleteTextView):TextView{", "private fun naturalUserCompare(aRaw:String,bRaw:String):Int{", panel)

old_metric='private fun metric(title:String,value:String,color:Int)=column(surface).apply{setPadding(dp(8),dp(7),dp(8),dp(7));background=outlineBg(surface,10);addView(txt(title,9.7f,color,true));addView(gap(1));addView(txt(value,11.8f,ink,true))}'
new_metric='private fun metric(title:String,value:String,color:Int)=txt("$title: $value",10.2f,color,true).apply{gravity=Gravity.CENTER;setPadding(dp(6),dp(8),dp(6),dp(8));background=outlineBg(surface,10)}'
if old_metric not in s: raise SystemExit("metric anchor missing")
s=s.replace(old_metric,new_metric,1)
old_update='fun updateMetric(v:View,n:Int){if(v is ViewGroup){for(i in v.childCount-1 downTo 0){val child=v.getChildAt(i);if(child is TextView){child.text=n.toString();break}}}};updateMetric(allBtn,metricRows.size);updateMetric(pendingBtn,pending);updateMetric(failBtn,failed)'
new_update='fun updateMetric(v:View,title:String,n:Int){if(v is TextView)v.text="$title: $n"};updateMetric(allBtn,"Tổng",metricRows.size);updateMetric(pendingBtn,"Chờ",pending);updateMetric(failBtn,"Cần xử lí",failed)'
if old_update not in s: raise SystemExit("metric updater anchor missing")
s=s.replace(old_update,new_update,1)

old_sub='''        addView(gap(6))
        addView(txt(sub,9.8f,muted,false).apply{
            gravity=Gravity.CENTER
            maxLines=3
            ellipsize=android.text.TextUtils.TruncateAt.END
            setAutoSizeTextTypeUniformWithConfiguration(8,10,1,android.util.TypedValue.COMPLEX_UNIT_SP)
        },LinearLayout.LayoutParams(-1,0,1f))'''
new_sub='''        if(sub.isNotBlank()){addView(gap(6));addView(txt(sub,9.8f,muted,false).apply{gravity=Gravity.CENTER;maxLines=3;ellipsize=android.text.TextUtils.TruncateAt.END;setAutoSizeTextTypeUniformWithConfiguration(8,10,1,android.util.TypedValue.COMPLEX_UNIT_SP)},matchWrap())}'''
if old_sub not in s: raise SystemExit("business subtitle anchor missing")
s=s.replace(old_sub,new_sub,1).replace("addView(a,LinearLayout.LayoutParams(0,dp(188),1f)","addView(a,LinearLayout.LayoutParams(0,dp(150),1f)",1).replace("addView(b,LinearLayout.LayoutParams(0,dp(188),1f)","addView(b,LinearLayout.LayoutParams(0,dp(150),1f)",1)

marker='    private fun smallButton(t:String,c:Int)=Button(this).apply{text=t;textSize=9.5f;setTextColor(Color.WHITE);typeface=Typeface.DEFAULT_BOLD;isAllCaps=false;background=round(c,10);setPadding(dp(4),0,dp(4),0)}\n'
helper='''    private fun reconciliationButton(t:String,balanced:Boolean)=Button(this).apply{text=t;textSize=9.4f;typeface=Typeface.DEFAULT_BOLD;isAllCaps=false;setSingleLine(true);setPadding(dp(2),0,dp(2),0);val fg=if(balanced)Color.rgb(30,125,76) else Color.rgb(190,55,65);val fill=if(balanced)Color.rgb(236,248,241) else Color.rgb(254,240,242);setTextColor(fg);background=GradientDrawable().apply{setColor(fill);cornerRadius=dp(10).toFloat();setStroke(dp(1),Color.argb(90,Color.red(fg),Color.green(fg),Color.blue(fg)))}}\n'''
if marker not in s: raise SystemExit("smallButton anchor missing")
s=s.replace(marker,marker+helper,1)
s=s.replace("// S57_BETA54_OWNER_RESILIENCE_FIX","// S60_BETA59_OWNER_ATTENDANCE_UI\n    // S57_BETA54_OWNER_RESILIENCE_FIX",1)
for forbidden in ["SERI PDA ĐÃ CHỌN","PDA ĐANG GIỮ TRONG PHIÊN","THÊM / SỬA CÔNG VIỆC TRONG CA"]:
    if forbidden in s: raise SystemExit("legacy UI remains: "+forbidden)
p.write_text(s)

g=Path("app/build.gradle.kts");b=g.read_text()
if 'versionCode = 64' not in b or 'versionName = "0.4.2-beta.58"' not in b: raise SystemExit("Beta58 metadata anchor missing")
b=b.replace("versionCode = 64","versionCode = 65",1).replace('versionName = "0.4.2-beta.58"','versionName = "0.4.2-beta.59"',1)
b=b.replace("// Beta58: owner fixes for log accounting, fallback provider label, and shift reconciliation placement.","// Beta59: attendance card/session UX, exact shift reconciliation, compact history metrics and audit semantics.\n// Beta58 remains immutable and is the previous public baseline.")
g.write_text(b)

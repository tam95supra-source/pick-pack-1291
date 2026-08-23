from pathlib import Path
import re

OPS = Path('app/src/main/java/vn/pickpack1291/app/beta/OperationsActivity.kt')
API = Path('app/src/main/java/vn/pickpack1291/app/beta/BetaApiClient.kt')
GRADLE = Path('app/build.gradle.kts')

ops = OPS.read_text(encoding='utf-8')
api = API.read_text(encoding='utf-8')
gradle = GRADLE.read_text(encoding='utf-8')


def once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f'{label}: expected exactly 1 match, got {count}')
    return text.replace(old, new, 1)


# ---------------------------------------------------------------------------
# Versioning: Beta60 is immutable. This source change is Beta61 / VC67.
# ---------------------------------------------------------------------------
gradle = once(gradle, 'versionCode = 66', 'versionCode = 67', 'beta versionCode')
gradle = once(gradle, 'versionName = "0.4.2-beta.60"', 'versionName = "0.4.2-beta.61"', 'beta versionName')
gradle = once(
    gradle,
    '// Beta60: owner operations UX, audited session edits/deletes, PDA exchange and live resource details.',
    '// Beta61: restored Staff tab, denser owner UI, active-PDA holder list, attendance editor refinements and direct Service resource admin.\n// Beta60 remains immutable and is the previous public baseline.',
    'beta release comment',
)

# ---------------------------------------------------------------------------
# Resource UNKNOWN root cause: direct Service owner/resource calls were nested
# inside the OPERATIONAL set, but resource_master_list is not OPERATIONAL.
# Route owner/resource actions before that branch and refresh only Service auth.
# ---------------------------------------------------------------------------
call_anchor = '''    fun call(action: String, payload: JSONObject = JSONObject(), callback: (Result) -> Unit) {\n        if(action in M2ServiceTransport.OPERATIONAL){\n            localExecutor.execute {\n                try {      if (action in setOf("resource_master_list","resource_master_upsert","resource_master_delete","history_correction","session_work_update","session_exit_guarded","attendance_time_correct","attendance_exit_delete","attendance_session_delete","service_connections","account_delete","history_delete")) {\n          val result=serviceOwnerCall(action,payload)\n          if(result.code==401) clearSession()\n          if(action in setOf("resource_master_upsert","resource_master_delete","history_correction")) AppHistory.record(appContext,action,result.ok,result.error.orEmpty())\n          callback(result)\n          return@execute\n      }\n\n                    val m2=m2Transport.operational(action,payload)'''
call_replacement = '''    fun call(action: String, payload: JSONObject = JSONObject(), callback: (Result) -> Unit) {\n        val directOwnerActions=setOf("resource_master_list","resource_master_upsert","resource_master_delete","history_correction","session_work_update","session_exit_guarded","attendance_time_correct","attendance_exit_delete","attendance_session_delete","service_connections","account_delete","history_delete")\n        if(action in directOwnerActions){\n            localExecutor.execute {\n                try {\n                    val result=serviceOwnerCall(action,payload)\n                    if(action in setOf("resource_master_upsert","resource_master_delete","history_correction")) AppHistory.record(appContext,action,result.ok,result.error.orEmpty())\n                    callback(result)\n                } catch(t:Throwable){ callback(failure(t)) }\n            }\n            return\n        }\n        if(action in M2ServiceTransport.OPERATIONAL){\n            localExecutor.execute {\n                try {\n                    val m2=m2Transport.operational(action,payload)'''
api = once(api, call_anchor, call_replacement, 'direct owner/resource routing')

owner_start = api.index('    private fun serviceOwnerCall(action:String,payload:JSONObject):Result{')
owner_end = api.index('\n    private fun accountUpsert', owner_start)
owner_impl = '''    private fun serviceOwnerCall(action:String,payload:JSONObject):Result{\n        if(ServiceFaultInjection.cloudflareDisabled(appContext))return Result(false,-1,null,"TEST_CLOUDFLARE_DISABLED")\n        val d=m2Transport.discoverySnapshot()?:return Result(false,503,null,"SERVICE_DISCOVERY_UNAVAILABLE")\n        if(d.optString("authority_mode")!="SERVICE_PRIMARY")return Result(false,409,d,"SERVICE_NOT_WRITE_AUTHORITY")\n        val base=d.optString("service_url").trimEnd('/')\n        if(!base.startsWith("https://"))return Result(false,503,d,"SERVICE_URL_INVALID")\n        val path=when(action){\n            "history_correction"->"/v1/corrections"\n            "session_work_update"->"/v1/session/work"\n            "session_exit_guarded"->"/v1/session/exit"\n            "attendance_time_correct"->"/v1/session/time-correction"\n            "attendance_exit_delete"->"/v1/session/delete-exit"\n            "attendance_session_delete"->"/v1/session/delete-enter"\n            "service_connections"->"/v1/service/connections"\n            "account_delete"->"/v1/admin/accounts/delete"\n            "history_delete"->"/v1/history/delete"\n            else->"/v1/admin/resources"\n        }\n        val method=if(action in setOf("resource_master_list","service_connections"))"GET" else "POST"\n        val body=JSONObject(payload.toString())\n        if(action=="resource_master_upsert")body.put("operation","UPSERT")\n        if(action=="resource_master_delete")body.put("operation","DELETE")\n        fun request(bearer:String):Result{\n            var conn:HttpURLConnection?=null\n            return try{\n                conn=(URL(base+path).openConnection() as HttpURLConnection).apply{\n                    requestMethod=method;connectTimeout=6_000;readTimeout=12_000\n                    setRequestProperty("Accept","application/json")\n                    setRequestProperty("Authorization","Bearer $bearer")\n                    if(method=="POST"){doOutput=true;setRequestProperty("Content-Type","application/json; charset=utf-8")}\n                }\n                if(method=="POST")conn!!.outputStream.use{it.write(body.toString().toByteArray(Charsets.UTF_8))}\n                val http=conn!!.responseCode\n                val stream=if(http in 200..299)conn!!.inputStream else conn!!.errorStream\n                val text=stream?.bufferedReader(Charsets.UTF_8)?.use{it.readText()}.orEmpty()\n                val j=runCatching{if(text.isBlank())JSONObject() else JSONObject(text)}.getOrElse{JSONObject().put("error","HTTP_${http}_INVALID_JSON")}\n                val ok=http in 200..299&&j.optBoolean("ok",false)\n                val error=if(ok)null else (j.optJSONObject("error")?.optString("code")?.takeIf{it.isNotBlank()}?:j.optString("error","HTTP_$http"))\n                Result(ok,http,j,error)\n            }catch(t:Throwable){Result(false,-1,null,t.message?:"SERVICE_OWNER_CALL_FAILED")}finally{conn?.disconnect()}\n        }\n        var bearer=M2ServiceSessionManager.current(appContext).orEmpty()\n        if(bearer.isBlank())bearer=M2ServiceSessionManager.ensure(appContext,base,token,force=true).orEmpty()\n        if(bearer.isBlank())return Result(false,401,null,"SERVICE_SESSION_UNAVAILABLE")\n        var result=request(bearer)\n        if(result.code==401){\n            M2ServiceSessionManager.clearIfSame(appContext,bearer)\n            val fresh=M2ServiceSessionManager.ensure(appContext,base,token,force=true).orEmpty()\n            if(fresh.isNotBlank())result=request(fresh)\n        }\n        return result\n    }\n'''
api = api[:owner_start] + owner_impl + api[owner_end:]

# ---------------------------------------------------------------------------
# Restore Staff bottom tab (screen/navigation already exists in Beta60).
# ---------------------------------------------------------------------------
old_nav = '''        val items=mutableListOf(\n            Triple(R.drawable.ic_pp_business,"Nghiệp vụ","BUSINESS"),\n            Triple(R.drawable.ic_pp_history,"Lịch sử","HISTORY"),\n            Triple(R.drawable.ic_pp_settings,"Cài đặt","SETTINGS")\n        )'''
new_nav = '''        val items=mutableListOf(\n            Triple(R.drawable.ic_pp_business,"Nghiệp vụ","BUSINESS"),\n            Triple(R.drawable.ic_pp_staff,"Nhân sự","STAFF"),\n            Triple(R.drawable.ic_pp_history,"Lịch sử","HISTORY"),\n            Triple(R.drawable.ic_pp_settings,"Cài đặt","SETTINGS")\n        )'''
ops = once(ops, old_nav, new_nav, 'restore Staff tab')

# ---------------------------------------------------------------------------
# Compact header/status cards and business card geometry.
# ---------------------------------------------------------------------------
header_pattern = re.compile(r'    private fun headerStatusChip\(iconRes:Int,label:String,valueView:TextView,click:\(\)->Unit\)=row\(Color\.TRANSPARENT\)\.apply\{.*?\}\n    private fun greetingText', re.S)
header_impl = '''    private fun headerStatusChip(iconRes:Int,label:String,valueView:TextView,click:()->Unit)=row(Color.TRANSPARENT).apply{\n        gravity=Gravity.CENTER_VERTICAL\n        setPadding(dp(5),dp(3),dp(5),dp(3))\n        background=round(Color.argb(32,255,255,255),12)\n        isClickable=true;isFocusable=true;setOnClickListener{click()}\n        addView(ImageView(this@OperationsActivity).apply{setImageResource(iconRes);imageTintList=ColorStateList.valueOf(Color.WHITE);setPadding(dp(1),dp(1),dp(1),dp(1))},size(dp(19),dp(19)))\n        addView(column(Color.TRANSPARENT).apply{\n            addView(txt(label,7f,Color.argb(210,255,255,255),false).apply{maxLines=1;setAutoSizeTextTypeUniformWithConfiguration(6,8,1,android.util.TypedValue.COMPLEX_UNIT_SP)})\n            addView(valueView.apply{maxLines=1;setAutoSizeTextTypeUniformWithConfiguration(6,9,1,android.util.TypedValue.COMPLEX_UNIT_SP)})\n        },LinearLayout.LayoutParams(0,-2,1f).apply{marginStart=dp(3)})\n    }\n    private fun greetingText'''
ops, n = header_pattern.subn(header_impl, ops, count=1)
if n != 1:
    raise RuntimeError(f'compact headerStatusChip: got {n}')

appbar_pattern = re.compile(r'    private fun appBar\(title:String\)=column\(Color\.TRANSPARENT\)\.apply\{.*?refreshHeaderConnection\(\)\}\n    private fun activeTab', re.S)
appbar_impl = '''    private fun appBar(title:String)=column(Color.TRANSPARENT).apply{\n        setPadding(dp(12),dp(7),dp(12),dp(8));background=gradient(navy,accent,0)\n        val identity=row(Color.TRANSPARENT).apply{gravity=Gravity.CENTER_VERTICAL}\n        if(!isRootScreen())identity.addView(ImageView(this@OperationsActivity).apply{setImageResource(R.drawable.ic_pp_back);imageTintList=ColorStateList.valueOf(Color.WHITE);setPadding(dp(6),dp(6),dp(6),dp(6));setOnClickListener{navigateBack()}},size(dp(32),dp(32)))\n        identity.addView(txt(greetingText(),15.2f,Color.WHITE,true).apply{maxLines=1;ellipsize=android.text.TextUtils.TruncateAt.END},LinearLayout.LayoutParams(0,-2,1f).apply{if(!isRootScreen())marginStart=dp(2)})\n        identity.addView(ImageView(this@OperationsActivity).apply{contentDescription="Làm mới và đồng bộ dữ liệu";setImageResource(R.drawable.ic_pp_refresh_round);imageTintList=ColorStateList.valueOf(Color.WHITE);setPadding(dp(6),dp(6),dp(6),dp(6));setOnClickListener{manualRefreshFromHeader(this)}},size(dp(32),dp(32)))\n        addView(identity,matchWrap());addView(gap(6))\n        val statuses=row(Color.TRANSPARENT).apply{gravity=Gravity.CENTER}\n        val net=txt("—",8.8f,Color.WHITE,true);networkStatusText=net\n        val syn=txt("—",8.8f,Color.WHITE,true);syncStatusText=syn\n        val svc=txt("—",8.8f,Color.WHITE,true);serviceStatusText=svc\n        statuses.addView(headerStatusChip(R.drawable.ic_pp_network,"Mạng",net){showHeaderStatusDetail("NETWORK")},LinearLayout.LayoutParams(0,dp(38),1f).apply{marginEnd=dp(2)})\n        statuses.addView(headerStatusChip(R.drawable.ic_pp_sync,"Đồng bộ",syn){showHeaderStatusDetail("SYNC")},LinearLayout.LayoutParams(0,dp(38),1f).apply{marginStart=dp(1);marginEnd=dp(1)})\n        statuses.addView(headerStatusChip(R.drawable.ic_pp_service,"Dịch vụ",svc){showHeaderStatusDetail("SERVICE")},LinearLayout.LayoutParams(0,dp(38),1f).apply{marginStart=dp(2)})\n        addView(statuses,matchWrap());refreshHeaderConnection()\n    }\n    private fun activeTab'''
ops, n = appbar_pattern.subn(appbar_impl, ops, count=1)
if n != 1:
    raise RuntimeError(f'compact appBar: got {n}')

ops = once(ops, 'val root=baseRoot("NGHIỆP VỤ");val body=body()', 'val root=baseRoot("NGHIỆP VỤ");val body=body().apply{setPadding(dp(8),dp(6),dp(8),dp(76))}', 'business wrapper padding')
ops = once(ops, 'setPadding(dp(9),dp(10),dp(9),dp(9))', 'setPadding(dp(7),dp(7),dp(7),dp(7))', 'business card padding')
ops = once(ops, 'addView(businessIconBubble(iconRes),size(dp(58),dp(58)))', 'addView(businessIconBubble(iconRes),size(dp(52),dp(52)))', 'business icon size')
ops = once(ops, 'addView(gap(9))\n        addView(txt(title,13.5f,ink,true)', 'addView(gap(6))\n        addView(txt(title,13.1f,ink,true)', 'business title spacing')
ops = once(ops, 'addView(gap(5))\n        addView(View(this@OperationsActivity).apply{background=round(teal,2)},size(dp(28),dp(3)))', 'addView(gap(3))\n        addView(View(this@OperationsActivity).apply{background=round(teal,2)},size(dp(26),dp(3)))', 'business underline spacing')
ops = once(ops, 'addView(a,LinearLayout.LayoutParams(0,dp(132),1f).apply{marginEnd=dp(4)})\n        addView(b,LinearLayout.LayoutParams(0,dp(132),1f).apply{marginStart=dp(4)})', 'addView(a,LinearLayout.LayoutParams(0,dp(122),1f).apply{marginEnd=dp(3)})\n        addView(b,LinearLayout.LayoutParams(0,dp(122),1f).apply{marginStart=dp(3)})', 'business row compact')
ops = once(ops, 'body.addView(businessRow(cards[0],cards[1]));body.addView(gap(5))\n        body.addView(businessRow(cards[2],cards[3]));body.addView(gap(5))\n        body.addView(businessRow(cards[4],cards[5]));body.addView(gap(5))', 'body.addView(businessRow(cards[0],cards[1]));body.addView(gap(4))\n        body.addView(businessRow(cards[2],cards[3]));body.addView(gap(4))\n        body.addView(businessRow(cards[4],cards[5]));body.addView(gap(4))', 'business vertical gaps')

# ---------------------------------------------------------------------------
# Attendance editor semantics.
# ---------------------------------------------------------------------------
ops = once(ops, '        if(editMode=="ADD"&&hadPick&&hadPack){TopNotice.show(this,"Đã có đủ Pick & Pack trong ca.",TopNotice.Kind.INFO);return}\n', '', 'remove ADD blocked with Pick+Pack')
old_checks = '''        val pickOn=CheckBox(this).apply{text="Có công việc PICK";isChecked=if(editMode=="ADD")!hadPick else hadPick;isEnabled=editMode=="EDIT"||!hadPick;setTextColor(if(isEnabled)ink else muted)}\n        val packOn=CheckBox(this).apply{text="Có công việc PACK";isChecked=if(editMode=="ADD")!hadPack else hadPack;isEnabled=editMode=="EDIT"||!hadPack;setTextColor(if(isEnabled)ink else muted)}\n        if(editMode=="ADD"&&!hadPick&&!hadPack){pickOn.isChecked=false;packOn.isChecked=false}\n        dialogBody.addView(pickOn,matchWrap());dialogBody.addView(packOn,matchWrap());dialogBody.addView(gap(7));val host=column(surface);dialogBody.addView(host,matchWrap())'''
new_checks = '''        val pickOn=CheckBox(this).apply{text="Có công việc PICK";isChecked=false;isEnabled=true;setTextColor(ink)}\n        val packOn=CheckBox(this).apply{text="Có công việc PACK";isChecked=false;isEnabled=true;setTextColor(ink)}\n        dialogBody.addView(pickOn,matchWrap());val pickHost=column(surface);dialogBody.addView(pickHost,matchWrap());dialogBody.addView(gap(5))\n        dialogBody.addView(packOn,matchWrap());val packHost=column(surface);dialogBody.addView(packHost,matchWrap());dialogBody.addView(gap(7))'''
ops = once(ops, old_checks, new_checks, 'attendance checkbox layout')
ops = once(ops, '            host.removeAllViews();pdaField=null;selectedPda=null;pickSpinner=null;pickChoices.clear();selectedPack=null', '            pickHost.removeAllViews();packHost.removeAllViews();pdaField=null;selectedPda=null;pickSpinner=null;pickChoices.clear();selectedPack=null', 'split edit hosts clear')

editor_start = ops.index('    private fun sessionWorkEditor(ctx:JSONObject,mode:String){')
pick_start = ops.index('            if(pickOn.isChecked){', editor_start)
pack_start = ops.index('            if(packOn.isChecked){', pick_start)
empty_hint = ops.index('            if(!pickOn.isChecked&&!packOn.isChecked)', pack_start)
pick_region = ops[pick_start:pack_start].replace('host.addView', 'pickHost.addView')
pack_region = ops[pack_start:empty_hint].replace('host.addView', 'packHost.addView')
ops = ops[:pick_start] + pick_region + pack_region + ops[empty_hint:]
ops = once(ops, '            if(!pickOn.isChecked&&!packOn.isChecked)host.addView(info("Không gán công việc PICK/PACK. Lưu để trả toàn bộ tài nguyên đang giữ."))\n', '', 'remove clear-resource edit hint')

# For ADD, one new work assignment per action; EDIT may choose one or both.
old_toggles = '''        var addToggleGuard=false\n        pickOn.setOnCheckedChangeListener{_,on->if(editMode=="ADD"&&!hadPick&&!hadPack&&on&&!addToggleGuard){addToggleGuard=true;packOn.isChecked=false;addToggleGuard=false};rebuild()}\n        packOn.setOnCheckedChangeListener{_,on->if(editMode=="ADD"&&!hadPick&&!hadPack&&on&&!addToggleGuard){addToggleGuard=true;pickOn.isChecked=false;addToggleGuard=false};rebuild()}'''
new_toggles = '''        var addToggleGuard=false\n        pickOn.setOnCheckedChangeListener{_,on->if(editMode=="ADD"&&on&&!addToggleGuard){addToggleGuard=true;packOn.isChecked=false;addToggleGuard=false};rebuild()}\n        packOn.setOnCheckedChangeListener{_,on->if(editMode=="ADD"&&on&&!addToggleGuard){addToggleGuard=true;pickOn.isChecked=false;addToggleGuard=false};rebuild()}'''
ops = once(ops, old_toggles, new_toggles, 'ADD toggle behavior')
ops = once(ops, '                val currentPick=ses.optString("user_pick").trim();if(currentPick.isNotBlank()&&!base.contains(currentPick))base.add(currentPick)', '                val currentPick=if(editMode=="EDIT")ses.optString("user_pick").trim() else "";if(currentPick.isNotBlank()&&!base.contains(currentPick))base.add(currentPick)', 'ADD Pick new user default')
ops = once(ops, '                val currentTable=ses.optString("pack_table").trim();val currentUser=ses.optString("user_pack").trim()', '                val currentTable=if(editMode=="EDIT")ses.optString("pack_table").trim() else "";val currentUser=if(editMode=="EDIT")ses.optString("user_pack").trim() else ""', 'ADD Pack new user default')

# Make ADD of another Pick keep the active PDA rather than presenting an ignored PDA edit.
old_pda_editor = '''                pdaField=pdaInput(pdas,ses.optString("pda_serial")){selectedPda=it}\n                pickHost.addView(labelled("PDA (có thể đổi / trả)",pdaField!!));pickHost.addView(gap(4));pickHost.addView(pdaSelectedPanel(pdas,pdaField!!),matchWrap());pickHost.addView(gap(5))\n                pickHost.addView(smallButton("TRẢ PDA",orange).apply{setOnClickListener{selectedPda=null;pdaField?.setText("",false)}},matchWrap());pickHost.addView(gap(7))'''
new_pda_editor = '''                if(editMode=="ADD"&&hadPick){\n                    pickHost.addView(details(listOf("PDA đang dùng" to dash(ses.optString("pda_serial")))))\n                    pickHost.addView(gap(7))\n                }else{\n                    pdaField=pdaInput(pdas,ses.optString("pda_serial")){selectedPda=it}\n                    pickHost.addView(labelled("PDA (có thể đổi / trả)",pdaField!!));pickHost.addView(gap(4));pickHost.addView(pdaSelectedPanel(pdas,pdaField!!),matchWrap());pickHost.addView(gap(5))\n                    pickHost.addView(smallButton("TRẢ PDA",orange).apply{setOnClickListener{selectedPda=null;pdaField?.setText("",false)}},matchWrap());pickHost.addView(gap(7))\n                }'''
ops = once(ops, old_pda_editor, new_pda_editor, 'ADD Pick current PDA display')

old_save = '''            val pickChoice=if(pickOn.isChecked)pickChoices.getOrNull(pickSpinner?.selectedItemPosition?:0) else null;val pick=if(editMode=="ADD"&&hadPick)ses.optString("user_pick") else pickChoice?.first.orEmpty();val pda=if(editMode=="ADD"&&hadPick)ses.optString("pda_serial") else if(pickOn.isChecked)(selectedPda?.optString("serial").orEmpty().ifBlank{resolvePda(pdas,pdaField?.text?.toString().orEmpty()).orEmpty()}) else ""\n            p.put("pda_serial",pda).put("user_pick",pick)\n            var reissue=pickChoice?.second==true\n            if(editMode=="ADD"&&hadPack){p.put("pack_table",ses.optString("pack_table")).put("user_pack",ses.optString("user_pack"))}else if(packOn.isChecked){val row=selectedPack;if(row==null){showError("Chọn Bàn Pack + User Pack hợp lệ.");return@setPositiveButton};p.put("pack_table",row.optString("table")).put("user_pack",row.optString("user_pack"));reissue=reissue||row.optBoolean("duplicate_user")}else p.put("pack_table","").put("user_pack","")\n            if(reissue)p.put("duplicate_user",true)\n            val current=ses.optString("work_choice");val primary=when{pickOn.isChecked&&packOn.isChecked&&current in setOf("PICK","PACK")->current;pickOn.isChecked->"PICK";packOn.isChecked->"PACK";else->"KHONG"}\n            val baseNote=when{pickOn.isChecked&&packOn.isChecked->"PICK + PACK";pickOn.isChecked->"PICK";packOn.isChecked->"PACK";else->"Không gán công việc"};p.put("work_choice",primary).put("resource_note",ses.optString("resource_note")).put("mutation_kind",editMode).put("audit_note",if(reissue)"$baseNote • PHÁT LẠI USER" else baseNote)'''
new_save = '''            val pickChoice=if(pickOn.isChecked)pickChoices.getOrNull(pickSpinner?.selectedItemPosition?:0) else null\n            val pick=if(pickOn.isChecked)pickChoice?.first.orEmpty() else ses.optString("user_pick")\n            val pda=when{\n                !pickOn.isChecked->ses.optString("pda_serial")\n                editMode=="ADD"&&hadPick->ses.optString("pda_serial")\n                else->selectedPda?.optString("serial").orEmpty().ifBlank{resolvePda(pdas,pdaField?.text?.toString().orEmpty()).orEmpty()}\n            }\n            p.put("pda_serial",pda).put("user_pick",pick)\n            var reissue=pickChoice?.second==true\n            if(packOn.isChecked){\n                val row=selectedPack;if(row==null){showError("Chọn Bàn Pack + User Pack hợp lệ.");return@setPositiveButton}\n                p.put("pack_table",row.optString("table")).put("user_pack",row.optString("user_pack"));reissue=reissue||row.optBoolean("duplicate_user")\n            }else{\n                p.put("pack_table",ses.optString("pack_table")).put("user_pack",ses.optString("user_pack"))\n            }\n            if(reissue)p.put("duplicate_user",true)\n            val current=ses.optString("work_choice").uppercase();val primary=if(current in setOf("PICK","PACK"))current else when{pickOn.isChecked->"PICK";packOn.isChecked->"PACK";else->"KHONG"}\n            val baseNote=when{pickOn.isChecked&&packOn.isChecked->"PICK + PACK";pickOn.isChecked->"PICK";packOn.isChecked->"PACK";else->"Điều chỉnh ca / thông tin"};p.put("work_choice",primary).put("resource_note",ses.optString("resource_note")).put("mutation_kind",editMode).put("audit_note",if(reissue)"$baseNote • PHÁT LẠI USER" else baseNote)'''
ops = once(ops, old_save, new_save, 'attendance save preserve-unselected semantics')

# No confirmation prompt when no PDA is held.
old_no_pda = 'if(pda.isBlank()){AlertDialog.Builder(this).setTitle("Xác nhận RA CA").setMessage("Xác nhận kết thúc phiên?").setNegativeButton("Hủy",null).setPositiveButton("RA CA"){_,_->doExit("")}.show();return@setOnClickListener}'
ops = once(ops, old_no_pda, 'if(pda.isBlank()){doExit("");return@setOnClickListener}', 'direct exit when no PDA')

# Two equal timestamp buttons on one row.
old_active_time = 'if(isAdmin()){body.addView(gap(7));body.addView(smallButton("Sửa giờ vào – ra ca",navy).apply{setOnClickListener{editAttendanceTimes(ctx)}},matchWrap())}'
new_active_time = '''if(isAdmin()){body.addView(gap(7));val timeActions=row(bg);val editIn=smallButton("Sửa giờ vào",navy).apply{setOnClickListener{editAttendanceTime(ctx,"enter_at")}};val editOut=smallButton("Sửa giờ ra",teal).apply{isEnabled=ses.optString("exit_at").isNotBlank();alpha=if(isEnabled)1f else .42f;setOnClickListener{if(isEnabled)editAttendanceTime(ctx,"exit_at")}};timeActions.addView(editIn,LinearLayout.LayoutParams(0,dp(40),1f).apply{marginEnd=dp(3)});timeActions.addView(editOut,LinearLayout.LayoutParams(0,dp(40),1f).apply{marginStart=dp(3)});body.addView(timeActions,matchWrap())}'''
ops = once(ops, old_active_time, new_active_time, 'active attendance timestamp buttons')
old_ended_time = 'body.addView(smallButton("SỬA GIỜ VÀO – RA CA",navy).apply{setOnClickListener{editAttendanceTimes(ctx)}},matchWrap());body.addView(gap(6));body.addView(gap(6));body.addView(primary("XÓA GHI NHẬN RA CA",red){deleteExitRecord(ctx)},matchWrap())'
new_ended_time = '''val timeActions=row(bg);timeActions.addView(smallButton("SỬA GIỜ VÀO",navy).apply{setOnClickListener{editAttendanceTime(ctx,"enter_at")}},LinearLayout.LayoutParams(0,dp(40),1f).apply{marginEnd=dp(3)});timeActions.addView(smallButton("SỬA GIỜ RA",teal).apply{setOnClickListener{editAttendanceTime(ctx,"exit_at")}},LinearLayout.LayoutParams(0,dp(40),1f).apply{marginStart=dp(3)});body.addView(timeActions,matchWrap());body.addView(gap(6));body.addView(primary("XÓA GHI NHẬN RA CA",red){deleteExitRecord(ctx)},matchWrap())'''
ops = once(ops, old_ended_time, new_ended_time, 'ended attendance timestamp buttons')

# ---------------------------------------------------------------------------
# Resource PDA list: remove explanatory text. History controls: one row.
# ---------------------------------------------------------------------------
old_resource_note = 'body.addView(info("Danh mục dùng chung. Thay đổi được ghi nhận vào lịch sử; xóa yêu cầu xác thực lại mật khẩu."));body.addView(gap(8))'
new_resource_note = 'if(type!="PDA"){body.addView(info("Danh mục dùng chung. Thay đổi được ghi nhận vào lịch sử; xóa yêu cầu xác thực lại mật khẩu."));body.addView(gap(8))}'
ops = once(ops, old_resource_note, new_resource_note, 'remove PDA list explanatory note')

old_history = '''            val choose=row(bg);val selectPage=smallButton("CHỌN TRANG",navy);val clear=smallButton("BỎ CHỌN",muted)\n            choose.addView(selectPage,LinearLayout.LayoutParams(0,dp(42),1f).apply{marginEnd=dp(3)});choose.addView(clear,LinearLayout.LayoutParams(0,dp(42),1f).apply{marginStart=dp(3)});selectionBox.addView(gap(5));selectionBox.addView(choose,matchWrap())\n            val deleteSelected=smallButton("XÓA ĐÃ CHỌN",red);selectionBox.addView(gap(5));selectionBox.addView(deleteSelected,matchWrap());selectionBox.addView(gap(8))'''
new_history = '''            val choose=row(bg);val selectPage=smallButton("CHỌN TRANG",navy);val clear=smallButton("BỎ CHỌN",muted);val deleteSelected=smallButton("XÓA ĐÃ CHỌN",red)\n            choose.addView(selectPage,LinearLayout.LayoutParams(0,dp(40),1f).apply{marginEnd=dp(2)});choose.addView(clear,LinearLayout.LayoutParams(0,dp(40),1f).apply{marginStart=dp(2);marginEnd=dp(2)});choose.addView(deleteSelected,LinearLayout.LayoutParams(0,dp(40),1f).apply{marginStart=dp(2)});selectionBox.addView(gap(5));selectionBox.addView(choose,matchWrap());selectionBox.addView(gap(8))'''
ops = once(ops, old_history, new_history, 'history bulk action row')

# ---------------------------------------------------------------------------
# PDA exchange/return: show active holders immediately below search; exact
# final-5 filtering; prominent serial; clicking card/serial opens confirm flow.
# ---------------------------------------------------------------------------
pda_start = ops.index('    private fun pdaExchangeScreen(){')
pda_end = ops.index('\n    // S53_BETA47_SHEET_LOGIC_UI', pda_start)
pda_impl = r'''    private fun pdaExchangeScreen(){
        module="PDA_EXCHANGE";screenState="PDA_EXCHANGE"
        val root=baseRoot("ĐỔI / TRẢ PDA");val body=body()
        val serialField=input("Nhập Seri PDA / 5 số cuối",false).apply{setSingleLine(true);imeOptions=EditorInfo.IME_ACTION_SEARCH}
        body.addView(labelled("Seri PDA",serialField));body.addView(gap(6))
        val find=primary("TÌM PDA",navy){};body.addView(find,matchWrap());body.addView(gap(7))
        val listBox=column(bg);body.addView(listBox,matchWrap())
        val changeReasons=arrayOf("PDA lỗi quét / không đọc mã","PDA lỗi mạng / không đồng bộ","PDA yếu pin / hết pin","PDA lỗi phần cứng / hư hỏng","PDA treo / hoạt động không ổn định","Đổi theo điều phối vận hành","Khác")
        val returnReasons=arrayOf("Đi công nhật","Làm xong sớm","Về sớm","Chuyển sang Pack","Điều chuyển sang công việc / vị trí không cần PDA","Tạm dừng Pick theo điều phối","Khác")
        fun chooseReason(title:String,items:Array<String>,done:(String)->Unit){AlertDialog.Builder(this).setTitle(title).setItems(items){_,which->val chosen=items[which];if(chosen!="Khác"){done(chosen);return@setItems};val other=input("Nhập lý do",false);AlertDialog.Builder(this).setTitle("Lý do khác").setView(other).setNegativeButton("Hủy",null).setPositiveButton("XÁC NHẬN"){_,_->val v=other.text.toString().trim();if(v.isBlank())showError("Nhập lý do.")else done(v)}.show()}.setNegativeButton("Hủy",null).show()}
        fun localMnvFor(serial:String):String{val day=operationalStore.loadDay(operationalStore.businessDate())?:return "";val a=day.optJSONArray("sessions")?:return "";for(i in 0 until a.length()){val x=a.optJSONObject(i)?:continue;if(x.optString("state").equals("ACTIVE",true)&&x.optString("pda_serial").equals(serial,true))return x.optString("mnv")};return ""}
        fun matches(serial:String,typed:String):Boolean{val q=typed.trim();if(q.isBlank())return true;return if(q.length==5&&q.all{it.isDigit()})serial.takeLast(5)==q else serial.equals(q,true)}
        fun refreshList(filter:String){
            listBox.removeAllViews();listBox.addView(info("Đang tải PDA đang sử dụng..."))
            api.call("resource_master_list"){rr->runOnUiThread{
                listBox.removeAllViews();if(handleAuth(rr))return@runOnUiThread
                if(!rr.ok){showError(rr.error?:"Không tải được tài nguyên");return@runOnUiThread}
                val resources=rr.json?.optJSONArray("resources")?:JSONArray();val holders=mutableListOf<Pair<String,String>>();val seen=linkedSetOf<String>()
                for(i in 0 until resources.length()){
                    val x=resources.optJSONObject(i)?:continue;if(x.optString("resource_type")!="PDA")continue
                    val serial=x.optString("resource_id").trim();if(serial.isBlank())continue
                    val mnv=x.optString("leased_by_mnv").trim().ifBlank{localMnvFor(serial)}
                    if(mnv.isBlank()||!matches(serial,filter)||!seen.add(serial))continue
                    holders.add(serial to mnv)
                }
                val day=operationalStore.loadDay(operationalStore.businessDate());val sessions=day?.optJSONArray("sessions")?:JSONArray()
                for(i in 0 until sessions.length()){
                    val s=sessions.optJSONObject(i)?:continue;if(!s.optString("state").equals("ACTIVE",true))continue
                    val serial=s.optString("pda_serial").trim();val mnv=s.optString("mnv").trim();if(serial.isBlank()||mnv.isBlank()||!matches(serial,filter)||!seen.add(serial))continue
                    holders.add(serial to mnv)
                }
                holders.sortWith(compareBy<Pair<String,String>>{it.first.takeLast(5)}.thenBy{it.first})
                if(holders.isEmpty()){listBox.addView(info(if(filter.isBlank())"Hiện không có PDA nào đang được sử dụng." else "Không có PDA đang dùng khớp Seri / 5 số cuối đã nhập."));return@runOnUiThread}
                fun openHolder(serial:String,mnv:String){
                    api.call("employee_context",JSONObject().put("mnv",mnv).put("include_options",true)){r->runOnUiThread{
                        if(handleAuth(r))return@runOnUiThread;if(!r.ok){showError(r.error?:"Không tải được phiên");return@runOnUiThread}
                        val ctx=r.json?:JSONObject();val ses=ctx.optJSONObject("session")?:JSONObject();if(!ctx.optString("state").equals("ACTIVE",true)||!ses.optString("pda_serial").equals(serial,true)){showError("PDA đã thay đổi người dùng hoặc phiên. Đồng bộ lại rồi thử lại.");foregroundSync.requestSync();refreshList(serialField.text.toString());return@runOnUiThread}
                        val e=ctx.optJSONObject("employee")?:MasterDataCache.employee(this,mnv)?:JSONObject().put("mnv",mnv)
                        val dialogBody=column(surface).apply{setPadding(dp(10),dp(4),dp(10),dp(8))}
                        dialogBody.addView(txt(serial,16f,navy,true).apply{gravity=Gravity.CENTER_HORIZONTAL});dialogBody.addView(gap(6));dialogBody.addView(employeeCard(e));dialogBody.addView(gap(6));dialogBody.addView(details(listOf("Ca" to dash(ses.optString("shift")),"Công việc trong ca" to workInShiftText(ctx))));dialogBody.addView(gap(7))
                        val pdas=MasterDataCache.resourceOptions(this).optJSONArray("pdas")?:JSONArray();val newPda=pdaInput(pdas,serial);dialogBody.addView(labelled("PDA mới khi đổi",newPda));dialogBody.addView(gap(7))
                        val actions=row(surface);val change=smallButton("ĐỔI PDA",teal);val giveBack=smallButton("TRẢ PDA",orange);actions.addView(change,LinearLayout.LayoutParams(0,dp(44),1f).apply{marginEnd=dp(3)});actions.addView(giveBack,LinearLayout.LayoutParams(0,dp(44),1f).apply{marginStart=dp(3)});dialogBody.addView(actions,matchWrap())
                        val dialog=AlertDialog.Builder(this).setTitle("Xác nhận Đổi / Trả PDA").setView(ScrollView(this).apply{addView(dialogBody)}).setNegativeButton("Đóng",null).create()
                        fun mutate(nextPda:String,kind:String,why:String){val p=JSONObject().put("session_id",ses.optString("session_id")).put("mnv",mnv).put("shift",ses.optString("shift")).put("work_choice",ses.optString("work_choice")).put("pda_serial",nextPda).put("user_pick",ses.optString("user_pick")).put("pack_table",ses.optString("pack_table")).put("user_pack",ses.optString("user_pack")).put("resource_note",ses.optString("resource_note")).put("preserve_work_choice",true).put("mutation_kind","EDIT").put("audit_note","$kind PDA • $why").put("idempotency_key",UUID.randomUUID().toString());api.call("session_work_update",p){x->runOnUiThread{if(handleAuth(x))return@runOnUiThread;if(!x.ok)showError(x.error?:"Không cập nhật được PDA")else{dialog.dismiss();TopNotice.show(this,"Đã ${if(kind=="Đổi")"đổi" else "trả"} PDA và lưu lịch sử.",TopNotice.Kind.SUCCESS);foregroundSync.requestSync();refreshList(serialField.text.toString())}}}}
                        change.setOnClickListener{val next=resolvePda(pdas,newPda.text.toString());if(next==null||next.equals(serial,true)){showError("Chọn PDA mới khác PDA hiện tại.");return@setOnClickListener};chooseReason("Lý do đổi PDA",changeReasons){mutate(next,"Đổi",it)}}
                        giveBack.setOnClickListener{chooseReason("Lý do trả PDA",returnReasons){mutate("","Trả",it)}}
                        dialog.show()
                    }}
                }
                holders.forEach{(serial,mnv)->
                    val e=MasterDataCache.employee(this,mnv)?:JSONObject().put("mnv",mnv)
                    val card=column(surface).apply{setPadding(dp(10),dp(8),dp(10),dp(8));background=outlineBg(surface,12)}
                    val serialView=txt(serial,15f,navy,true).apply{contentDescription="Mở xác nhận đổi hoặc trả PDA $serial";setPadding(0,dp(2),0,dp(4));setOnClickListener{openHolder(serial,mnv)}}
                    card.addView(serialView,matchWrap());card.addView(employeeCard(e));card.setOnClickListener{openHolder(serial,mnv)}
                    listBox.addView(card,matchWrap());listBox.addView(gap(6))
                }
            }}
        }
        find.setOnClickListener{hideSoftKeyboard(serialField);refreshList(serialField.text.toString())};bindScannerEnter(serialField){find.performClick()}
        attach(root,body);refreshList("");serialField.requestFocus()
    }
'''
ops = ops[:pda_start] + pda_impl + ops[pda_end:]

# ---------------------------------------------------------------------------
# Final contract guards before files are written.
# ---------------------------------------------------------------------------
checks_present = [
    ('Beta61 version', 'versionName = "0.4.2-beta.61"', gradle),
    ('Staff tab', 'Triple(R.drawable.ic_pp_staff,"Nhân sự","STAFF")', ops),
    ('direct resource route', 'val directOwnerActions=setOf(', api),
    ('active PDA list', 'Đang tải PDA đang sử dụng...', ops),
    ('exact last5', 'serial.takeLast(5)==q', ops),
    ('history three controls', 'choose.addView(deleteSelected', ops),
    ('split pick host', 'val pickHost=column(surface)', ops),
    ('split pack host', 'val packHost=column(surface)', ops),
    ('direct no-PDA exit', 'if(pda.isBlank()){doExit("");return@setOnClickListener}', ops),
    ('two time buttons', 'val editIn=smallButton("Sửa giờ vào"', ops),
]
for label, needle, text in checks_present:
    if needle not in text:
        raise RuntimeError(f'guard missing: {label}')
if 'Đã có đủ Pick & Pack trong ca.' in ops:
    raise RuntimeError('ADD remains blocked with Pick & Pack')
if 'versionCode = 66' in gradle or 'versionName = "0.4.2-beta.60"' in gradle.split('create("stable")')[0]:
    raise RuntimeError('Beta60 version metadata still active')
if 'versionCode = 1' not in gradle or 'versionName = "0.1.0-stable"' not in gradle:
    raise RuntimeError('Stable identity changed unexpectedly')

OPS.write_text(ops, encoding='utf-8')
API.write_text(api, encoding='utf-8')
GRADLE.write_text(gradle, encoding='utf-8')
print('BETA61_OWNER_PATCH_APPLIED')

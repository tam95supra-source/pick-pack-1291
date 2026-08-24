#!/usr/bin/env python3
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]
GRADLE=ROOT/'app/build.gradle.kts'
API=ROOT/'app/src/main/java/vn/pickpack1291/app/beta/BetaApiClient.kt'
OPS=ROOT/'app/src/main/java/vn/pickpack1291/app/beta/OperationsActivity.kt'
FULL=ROOT/'app/src/main/java/vn/pickpack1291/app/beta/FullBetaActivity.kt'


def replace_fun(text:str, marker:str, replacement:str)->str:
    i=text.find(marker)
    if i<0: raise SystemExit(f'missing function marker: {marker}')
    brace=text.find('{',i)
    if brace<0: raise SystemExit(f'missing function brace: {marker}')
    depth=0; quote=None; escaped=False; pos=brace
    while pos<len(text):
        ch=text[pos]
        if quote:
            if escaped: escaped=False
            elif ch=='\\': escaped=True
            elif ch==quote: quote=None
            pos+=1; continue
        if ch in ('"',"'"): quote=ch
        elif ch=='{': depth+=1
        elif ch=='}':
            depth-=1
            if depth==0:
                return text[:i]+replacement+text[pos+1:]
        pos+=1
    raise SystemExit(f'unclosed function: {marker}')


def replace_between(text:str,start:str,end:str,replacement:str)->str:
    i=text.find(start); j=text.find(end,i if i>=0 else 0)
    if i<0 or j<0: raise SystemExit(f'missing range {start} / {end}')
    return text[:i]+replacement+text[j:]

# Version: Beta64 stays immutable, Beta65 is VC71. Stable untouched.
g=GRADLE.read_text()
g=g.replace('versionCode = 70\n            versionName = "0.4.2-beta.64"','versionCode = 71\n            versionName = "0.4.2-beta.65"',1)
if 'versionName = "0.4.2-beta.65"' not in g: raise SystemExit('Beta65 version bump failed')
g=g.replace('// Beta64: exact-fit Vietnam/Supra login, MNV callback fencing, separate user reissue chooser,','// Beta65: multi-position/multi-resource session ownership + reference-stage login parity.\n// Beta64 remains immutable previous public baseline.\n// Beta64: exact-fit Vietnam/Supra login, MNV callback fencing, separate user reissue chooser,',1)
GRADLE.write_text(g)

# Direct Service routes for the new atomic session model.
a=API.read_text()
old='val directOwnerActions=setOf("resource_master_list","resource_master_upsert","resource_master_delete","history_correction","session_work_update","session_exit_guarded","attendance_time_correct","attendance_exit_delete","attendance_session_delete","service_connections","account_delete","history_delete")'
new='val directOwnerActions=setOf("resource_master_list","resource_master_upsert","resource_master_delete","history_correction","session_work_update","session_exit_guarded","attendance_time_correct","attendance_exit_delete","attendance_session_delete","attendance_enter_v2","session_resource_snapshot","session_resource_mutate","session_exit_v2","service_connections","account_delete","history_delete")'
if old in a:a=a.replace(old,new,1)
elif 'session_resource_mutate' not in a:raise SystemExit('directOwnerActions anchor drift')
oldmap='''            "attendance_session_delete"->"/v1/session/delete-enter"\n            "service_connections"->"/v1/service/connections"'''
newmap='''            "attendance_session_delete"->"/v1/session/delete-enter"\n            "attendance_enter_v2"->"/v1/session/enter-v2"\n            "session_resource_snapshot"->"/v1/session/resources/snapshot"\n            "session_resource_mutate"->"/v1/session/resources/mutate"\n            "session_exit_v2"->"/v1/session/exit-v2"\n            "service_connections"->"/v1/service/connections"'''
if oldmap in a:a=a.replace(oldmap,newmap,1)
elif '"session_resource_mutate"->"/v1/session/resources/mutate"' not in a:raise SystemExit('serviceOwnerCall route anchor drift')
API.write_text(a)

LOGIN=r'''    private fun login() {
        foregroundSync.stop()
        liveEmployeeMnv = ""
        currentScreen = "LOGIN"
        accountLogin = ""; accountName = ""; accountRole = ""; accountPosition = ""; accountEmail = ""
        window.statusBarColor = Color.rgb(218,29,22)
        window.navigationBarColor = Color.rgb(5,45,91)
        @Suppress("DEPRECATION")
        window.decorView.systemUiVisibility = 0

        val user = EditText(this).apply {
            hint="Tài khoản";setSingleLine(true);textSize=14f;background=null
            setTextColor(Color.rgb(28,50,77));setHintTextColor(Color.rgb(145,155,170));setPadding(dp(8),0,dp(4),0);imeOptions=EditorInfo.IME_ACTION_NEXT
        }
        val saved=getPreferences(MODE_PRIVATE).getString("last_login","").orEmpty();if(saved.isNotBlank())user.setText(saved)
        val pass = EditText(this).apply {
            hint="Mật khẩu";setSingleLine(true);textSize=14f;background=null
            setTextColor(Color.rgb(28,50,77));setHintTextColor(Color.rgb(145,155,170));setPadding(dp(8),0,dp(4),0);imeOptions=EditorInfo.IME_ACTION_DONE
            inputType=InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_VARIATION_PASSWORD
        }
        var visible=false
        val eye=ImageButton(this).apply{
            setImageResource(R.drawable.ic_login_eye);setBackgroundColor(Color.TRANSPARENT);contentDescription="Hiện mật khẩu";setPadding(dp(8),dp(8),dp(8),dp(8))
            setOnClickListener{visible=!visible;val p=pass.selectionStart.coerceAtLeast(0);pass.inputType=InputType.TYPE_CLASS_TEXT or if(visible) InputType.TYPE_TEXT_VARIATION_VISIBLE_PASSWORD else InputType.TYPE_TEXT_VARIATION_PASSWORD;pass.setSelection(p.coerceAtMost(pass.text.length));contentDescription=if(visible)"Ẩn mật khẩu" else "Hiện mật khẩu"}
        }
        fun field(icon:Int,input:EditText,trailing:View?=null)=row(Color.WHITE).apply{
            gravity=Gravity.CENTER_VERTICAL;setPadding(dp(12),dp(2),dp(6),dp(2));minimumHeight=dp(49)
            background=GradientDrawable().apply{cornerRadius=dp(13).toFloat();setColor(Color.WHITE);setStroke(dp(1),Color.rgb(191,202,216))}
            addView(ImageView(this@FullBetaActivity).apply{setImageResource(icon);scaleType=ImageView.ScaleType.CENTER_INSIDE},size(dp(26),dp(26)))
            addView(input,LinearLayout.LayoutParams(0,dp(45),1f));if(trailing!=null)addView(trailing,size(dp(42),dp(42)))
        }
        val card=column(Color.WHITE).apply{
            gravity=Gravity.CENTER_HORIZONTAL;setPadding(dp(20),dp(16),dp(20),dp(18))
            background=GradientDrawable().apply{cornerRadius=dp(24).toFloat();setColor(Color.argb(250,255,255,255));setStroke(dp(1),Color.argb(55,73,105,145))}
            elevation=dp(8).toFloat()
        }
        card.addView(ImageView(this).apply{setImageResource(R.drawable.login_supra_logo);adjustViewBounds=true;scaleType=ImageView.ScaleType.FIT_CENTER},size(dp(96),dp(108)))
        card.addView(txt("Supra DC Hưng Yên",17f,Color.rgb(17,75,151),true).center())
        card.addView(gap(12));card.addView(field(R.drawable.ic_login_user,user),matchWrap());card.addView(gap(8));card.addView(field(R.drawable.ic_login_lock,pass,eye),matchWrap())
        val forgot=TextView(this).apply{text="Quên mật khẩu?";textSize=11.5f;setTextColor(Color.rgb(12,72,156));typeface=Typeface.DEFAULT_BOLD;gravity=Gravity.END;setPadding(0,dp(7),0,dp(7));setOnClickListener{val id=user.text.toString().trim();if(id.isBlank()){toast("Nhập tài khoản trước khi chọn Quên mật khẩu.");return@setOnClickListener};isEnabled=false;api.forgotPassword(id){r->runOnUiThread{isEnabled=true;if(!r.ok)showError(r.error?:"Không gửi được yêu cầu đặt lại mật khẩu")else TopNotice.show(this@FullBetaActivity,"Nếu tài khoản hợp lệ, mật khẩu mới đã được gửi tới mail đã cấu hình.",TopNotice.Kind.SUCCESS)}}}}
        card.addView(forgot,matchWrap())
        val loginButton=Button(this).apply{text="Đăng nhập";isAllCaps=false;textSize=15f;setTextColor(Color.WHITE);typeface=Typeface.DEFAULT_BOLD;minimumHeight=dp(50);background=gradient(Color.rgb(17,84,184),Color.rgb(6,57,137),14)}
        fun submit(){val id=user.text.toString().trim();val pw=pass.text.toString();if(id.isBlank()||pw.isBlank()){toast("Nhập tài khoản và mật khẩu.");return};loginButton.isEnabled=false;loginButton.text="Đang xác thực...";api.login(id,pw){r->runOnUiThread{loginButton.isEnabled=true;loginButton.text="Đăng nhập";if(!r.ok){showError(r.error?:"Đăng nhập thất bại");return@runOnUiThread};val x=r.json?.optJSONObject("account")?:JSONObject();accountLogin=x.optString("login_id",id);accountName=x.optString("display_name",accountLogin);accountRole=x.optString("role","USER");accountPosition=x.optString("position","");accountEmail=x.optString("email","");getPreferences(MODE_PRIVATE).edit().putString("last_login",accountLogin).apply();pass.setText("");openMainShell();if(MasterDataCache.revision(this@FullBetaActivity)==0L)refreshMasterCache();LocalLogManager.uploadAutomaticPending(this@FullBetaActivity,api)}}}
        loginButton.setOnClickListener{submit()};user.setOnEditorActionListener{_,id,_->if(id==EditorInfo.IME_ACTION_NEXT){pass.requestFocus();true}else false};pass.setOnEditorActionListener{_,id,_->if(id==EditorInfo.IME_ACTION_DONE){submit();true}else false}
        card.addView(loginButton,matchWrap());card.addView(gap(8));card.addView(Button(this).apply{text="Đăng ký";isAllCaps=false;textSize=13.5f;setTextColor(Color.rgb(13,73,155));typeface=Typeface.DEFAULT_BOLD;minimumHeight=dp(47);background=GradientDrawable().apply{cornerRadius=dp(13).toFloat();setColor(Color.WHITE);setStroke(dp(1),Color.rgb(22,82,168))};setOnClickListener{TopNotice.show(this@FullBetaActivity,"Tính năng đăng ký đang được xây dựng.",TopNotice.Kind.INFO)}},matchWrap())

        // Reference-stage layout: every visual element is positioned inside one 2:3 design frame.
        // The whole frame is aspect-fitted and centered, never CENTER_CROP/FIT_XY stretched.
        val sw=resources.displayMetrics.widthPixels;val sh=resources.displayMetrics.heightPixels
        val designW=minOf(sw,(sh/1.5f).toInt()).coerceAtLeast(1);val designH=(designW*1.5f).toInt()
        val root=FrameLayout(this).apply{setBackgroundColor(Color.rgb(5,45,91))}
        val stage=FrameLayout(this).apply{background=ColorDrawable(Color.rgb(247,238,214));clipChildren=true}
        root.addView(stage,FrameLayout.LayoutParams(designW,designH,Gravity.CENTER))
        stage.addView(ImageView(this).apply{setImageResource(R.drawable.login_vietnam_bg);scaleType=ImageView.ScaleType.CENTER_INSIDE;adjustViewBounds=false},FrameLayout.LayoutParams(-1,-1))
        val cardW=(designW*.76f).toInt().coerceAtLeast(dp(260));val top=(designH*.105f).toInt()
        stage.addView(card,FrameLayout.LayoutParams(cardW,-2,Gravity.TOP or Gravity.CENTER_HORIZONTAL).apply{topMargin=top})
        val copy=TextView(this).apply{text="Copyright 2026 Supra DC Hưng Yên - tamnv2 - Chuyên viên Pick Pack 1291";textSize=9.2f;setTextColor(Color.WHITE);gravity=Gravity.CENTER;typeface=Typeface.DEFAULT_BOLD;setShadowLayer(2f,0f,1f,Color.rgb(0,25,55));setPadding(dp(8),0,dp(8),0)}
        stage.addView(copy,FrameLayout.LayoutParams((designW*.94f).toInt(),dp(36),Gravity.BOTTOM or Gravity.CENTER_HORIZONTAL).apply{bottomMargin=(designH*.018f).toInt()})
        setScreen(root);user.requestFocus()
    }
'''
f=FULL.read_text();f=replace_fun(f,'    private fun login() {',LOGIN);FULL.write_text(f)

# New session UI helpers/editor/delete/enter/exit. These are deliberately Service-authoritative;
# the legacy single-value projection remains only for Beta64 compatibility.
o=OPS.read_text()

DETAIL=r'''    private fun sessionWorkDetail(payload:JSONObject):String{
        val ops=payload.optJSONArray("operations")
        if(ops!=null&&ops.length()>0){
            val out=mutableListOf<String>()
            for(i in 0 until ops.length()){
                val x=ops.optJSONObject(i)?:continue;val op=x.optString("op").uppercase();val t=x.optString("resource_type");val id=x.optString("resource_id");val key=x.optString("position_label").ifBlank{x.optString("position_key")}
                val s=when(op){"ADD_RESOURCE"->"Thêm $t $id";"REMOVE_RESOURCE"->"Xóa $t $id • ${x.optString("reason")}";"ADD_POSITION"->"Thêm vị trí $key";"REMOVE_POSITION"->"Xóa vị trí $key";"UPDATE_SHIFT"->"Sửa ca ${x.optString("shift")}";else->op}
                if(s.isNotBlank())out.add(s)
            }
            if(out.isNotEmpty())return out.joinToString(" • ")
        }
        val parts=mutableListOf<String>();payload.optString("work_choice").trim().takeIf{it.isNotBlank()}?.let{parts.add(it)}
        payload.optString("pda_serial").trim().takeIf{it.isNotBlank()}?.let{parts.add("PDA $it")};payload.optString("user_pick").trim().takeIf{it.isNotBlank()}?.let{parts.add("User Pick $it")};payload.optString("pack_table").trim().takeIf{it.isNotBlank()}?.let{parts.add("Bàn $it")};payload.optString("user_pack").trim().takeIf{it.isNotBlank()}?.let{parts.add("User Pack $it")}
        payload.optString("labor_type").trim().takeIf{it.isNotBlank()}?.let{parts.add("Công nhật: $it")};return parts.joinToString(" • ")
    }
'''
o=replace_fun(o,'    private fun sessionWorkDetail(payload:JSONObject):String{',DETAIL)

RENDER_EMP=r'''    private fun renderEmployee(ctx: JSONObject, masters: JSONObject?) {
        screenState="EMPLOYEE"
        val e=ctx.optJSONObject("employee")?:JSONObject();val state=ctx.optString("state");val currentMnv=e.optString("mnv");liveEmployeeMnv=currentMnv
        val root=column(bg);root.addView(appBar("QUÉT QR NHÂN SỰ"));val body=column(bg).apply{setPadding(dp(12),dp(8),dp(12),dp(58))}
        val scan=mnvInput("Scan / Nhập mã nhân viên").apply{setText("")};body.addView(scan,matchWrap());body.addView(gap(5));body.addView(employeeCard(e,state));body.addView(gap(7))
        var busy=false;fun submit(){val v=scan.text.toString().trim();if(v.isBlank()){TopNotice.show(this,"Nhập hoặc quét mã nhân viên.",TopNotice.Kind.WARNING);return};if(busy)return;busy=true;loadEmployee(v);scan.postDelayed({busy=false},600)};bindScannerEnter(scan){submit()}
        val ses=ctx.optJSONObject("session")
        if((state=="ACTIVE"||state=="ENDED")&&ses!=null&&!ses.has("resource_assignments_v64")){
            body.addView(status("ĐANG ĐỒNG BỘ TÀI NGUYÊN PHIÊN...",blue,Color.rgb(237,244,255)))
            root.addView(ScrollView(this).apply{addView(body)},LinearLayout.LayoutParams(-1,0,1f));setScreen(root);hideKeyboardForResult(root,scan)
            val generation=employeeLookupGeneration;api.call("session_resource_snapshot",JSONObject().put("session_id",ses.optString("session_id")).put("mnv",currentMnv)){r->runOnUiThread{
                if(generation!=employeeLookupGeneration||liveEmployeeMnv!=currentMnv)return@runOnUiThread
                if(!r.ok){showError(r.error?:"Không đọc được tài nguyên phiên");return@runOnUiThread}
                renderEmployee(mergeResourceSnapshot(ctx,r.json?:JSONObject()),masters)
            }};return
        }
        when(state){"ACTIVE"->renderActive(body,ctx);"ENDED"->renderEnded(body,ctx);else->renderEnter(body,ctx,masters?:JSONObject())}
        root.addView(ScrollView(this).apply{addView(body)},LinearLayout.LayoutParams(-1,0,1f));setScreen(root);hideKeyboardForResult(root,scan)
    }
'''
o=replace_fun(o,'    private fun renderEmployee(ctx: JSONObject, masters: JSONObject?) {',RENDER_EMP)

EDITOR_BLOCK=r'''    private fun mergeResourceSnapshot(ctx:JSONObject,snap:JSONObject):JSONObject{
        val out=JSONObject(ctx.toString());val base=snap.optJSONObject("session")?:out.optJSONObject("session")?:JSONObject();val s=JSONObject(base.toString())
        s.put("positions_v64",snap.optJSONArray("positions")?:JSONArray()).put("resource_assignments_v64",snap.optJSONArray("resource_assignments")?:JSONArray()).put("resource_options_v64",snap.optJSONObject("options")?:JSONObject()).put("main_position_v64",snap.optString("main_position"))
        out.put("session",s).put("state",s.optString("state",out.optString("state")));return out
    }
    private fun assignmentArray(s:JSONObject):JSONArray=s.optJSONArray("resource_assignments_v64")?:JSONArray()
    private fun positionArray(s:JSONObject):JSONArray=s.optJSONArray("positions_v64")?:JSONArray()
    private fun activeAssignments(s:JSONObject,type:String=""):List<JSONObject>{val out=mutableListOf<JSONObject>();val a=assignmentArray(s);for(i in 0 until a.length()){val x=a.optJSONObject(i)?:continue;if(!x.optString("state").equals("ACTIVE",true))continue;if(type.isNotBlank()&&!x.optString("resource_type").equals(type,true))continue;out.add(x)};return out}
    private fun visibleAssignments(s:JSONObject,type:String=""):List<JSONObject>{val out=mutableListOf<JSONObject>();val a=assignmentArray(s);for(i in 0 until a.length()){val x=a.optJSONObject(i)?:continue;if(x.optString("state").uppercase() !in setOf("ACTIVE","USED"))continue;if(type.isNotBlank()&&!x.optString("resource_type").equals(type,true))continue;out.add(x)};return out}
    private fun activePositionLabels(s:JSONObject):List<String>{val out=mutableListOf<String>();val a=positionArray(s);for(i in 0 until a.length()){val x=a.optJSONObject(i)?:continue;if(x.optString("state").equals("ACTIVE",true)){val v=x.optString("position_label").ifBlank{x.optString("position_key")};if(v.isNotBlank()&&!out.contains(v))out.add(v)}};return out}
    private fun allPositionLabels(s:JSONObject):List<String>{val out=mutableListOf<String>();val a=positionArray(s);for(i in 0 until a.length()){val x=a.optJSONObject(i)?:continue;if(x.optString("state").uppercase() !in setOf("ACTIVE","USED"))continue;val v=x.optString("position_label").ifBlank{x.optString("position_key")};if(v.isNotBlank()&&!out.contains(v))out.add(v)};return out}
    private fun optionIds(a:JSONArray?):MutableList<String>{val out=mutableListOf<String>();if(a==null)return out;for(i in 0 until a.length()){val v=when(val x=a.opt(i)){is JSONObject->x.optString("id").ifBlank{x.optString("resource_id")};else->a.optString(i)}.trim();if(v.isNotBlank()&&!out.contains(v))out.add(v)};out.sortWith(Comparator{a,b->naturalUserCompare(a,b)});return out}
    private fun chooseUsed(title:String,a:JSONArray?,onPick:(String)->Unit){val ids=optionIds(a);if(ids.isEmpty()){showError("Không có tài nguyên đã dùng khả dụng.");return};AlertDialog.Builder(this).setTitle(title).setItems(ids.toTypedArray()){_,w->onPick(ids[w])}.setNegativeButton("Hủy",null).show()}
    private fun resourceLabel(t:String)=when(t.uppercase()){"PDA"->"PDA";"USER_PICK"->"User Pick";"PACK_TABLE"->"Bàn Pack";"USER_PACK"->"User Pack";else->t}
    private fun resourceListText(s:JSONObject):List<Pair<String,String>>{
        val rows=mutableListOf<Pair<String,String>>();for(t in listOf("PDA","USER_PICK","PACK_TABLE","USER_PACK")){for(x in visibleAssignments(s,t)){val state=if(x.optString("state").equals("ACTIVE",true))"Đang dùng" else "Đã dùng";rows.add(resourceLabel(t) to "${x.optString("resource_id")} • $state")}};return rows
    }
    private fun submitResourceMutation(ctx:JSONObject,ops:JSONArray,note:String){
        val s=ctx.optJSONObject("session")?:return;val mnv=s.optString("mnv");val generation=employeeLookupGeneration
        val p=JSONObject().put("session_id",s.optString("session_id")).put("mnv",mnv).put("expected_version",s.optInt("version")).put("idempotency_key",UUID.randomUUID().toString()).put("audit_note",note).put("operations",ops)
        api.call("session_resource_mutate",p){r->runOnUiThread{if(handleAuth(r))return@runOnUiThread;if(!r.ok){if(r.error=="SESSION_CHANGED")loadEmployee(mnv) else showError(r.error?:"Không cập nhật được phiên");return@runOnUiThread};TopNotice.show(this,"Đã cập nhật tài nguyên trong ca.",TopNotice.Kind.SUCCESS);foregroundSync.requestSync();if(generation==employeeLookupGeneration&&liveEmployeeMnv==mnv)renderEmployee(mergeResourceSnapshot(ctx,r.json?:JSONObject()),null)}}
    }
    private fun sessionWorkEditor(ctx:JSONObject,mode:String){
        val s=ctx.optJSONObject("session")?:return;if(!s.optString("state").equals("ACTIVE",true)){showError("Phiên không còn hoạt động.");return};val edit=mode.equals("EDIT",true);val options=s.optJSONObject("resource_options_v64")?:JSONObject();val box=column(surface).apply{setPadding(dp(10),dp(5),dp(10),dp(8))};val ops=JSONArray()
        val shifts=listOf("Ca 1","Ca HC","Ca 2");val shift=spinner(shifts.toTypedArray());selectByValue(shift,shifts,s.optString("shift"));if(edit){box.addView(labelled("Ca",shift));box.addView(gap(7))}
        val normalPick=optionIds(options.optJSONArray("user_picks"));val usedPick=options.optJSONArray("user_picks_reissue");val normalPack=optionIds(options.optJSONArray("user_packs"));val usedPack=options.optJSONArray("user_packs_reissue");val pdaIds=optionIds(options.optJSONArray("pdas"));val tableIds=optionIds(options.optJSONArray("pack_tables"))
        data class AddCtl(val type:String,val check:CheckBox,val spin:Spinner,val normal:List<String>,var used:String="")
        val adds=mutableListOf<AddCtl>()
        fun addUser(type:String,title:String,normal:List<String>,used:JSONArray?){val check=CheckBox(this).apply{text="Thêm $title";setTextColor(ink)};val spin=spinner((listOf("Chọn $title")+normal).toTypedArray());val ctl=AddCtl(type,check,spin,normal);adds.add(ctl);box.addView(check);val rr=row(surface).apply{gravity=Gravity.CENTER_VERTICAL;addView(spin,LinearLayout.LayoutParams(0,dp(48),1.3f));addView(compactReissueButton("Chọn đã dùng",(used?.length()?:0)>0){chooseUsed("Chọn $title đã dùng",used){id->ctl.used=id;spin.setSelection(0);TopNotice.show(this,"Đã chọn $title $id để phát lại.",TopNotice.Kind.INFO)}},LinearLayout.LayoutParams(0,dp(44),.8f).apply{marginStart=dp(5)})};box.addView(rr,matchWrap());box.addView(gap(5))}
        if(!edit||true){addUser("USER_PICK","User Pick",normalPick,usedPick);addUser("USER_PACK","User Pack",normalPack,usedPack)}
        if(!edit&&activeAssignments(s,"PDA").isEmpty()){val c=CheckBox(this).apply{text="Thêm PDA";setTextColor(ink)};val sp=spinner((listOf("Chọn PDA")+pdaIds).toTypedArray());adds.add(AddCtl("PDA",c,sp,pdaIds));box.addView(c);box.addView(sp,matchWrap());box.addView(gap(5))}
        if(edit){
            box.addView(section("SỬA / XÓA THÔNG TIN ĐANG CÓ"))
            data class E(val a:JSONObject,val check:CheckBox,val action:Spinner,val next:Spinner,val normal:List<String>,val used:JSONArray?,val disp:Spinner,val reason:EditText,var usedId:String="")
            val edits=mutableListOf<E>()
            for(a in activeAssignments(s)){
                val t=a.optString("resource_type");val normal=when(t){"PDA"->pdaIds;"PACK_TABLE"->tableIds;"USER_PICK"->normalPick;"USER_PACK"->normalPack;else->emptyList()};val used=when(t){"USER_PICK"->usedPick;"USER_PACK"->usedPack;else->null};val chk=CheckBox(this).apply{text="${resourceLabel(t)} ${a.optString("resource_id")}";setTextColor(ink)};val act=spinner(arrayOf("Đổi","Xóa"));val next=spinner((listOf("Chọn tài nguyên mới")+normal).toTypedArray());val disp=spinner(arrayOf("Đã sử dụng / có sản lượng","Cấp nhầm / chưa sử dụng"));val reason=input("Lý do sửa / đổi / xóa",false);val er=E(a,chk,act,next,normal,used,disp,reason);edits.add(er);box.addView(chk);box.addView(act,matchWrap());box.addView(next,matchWrap());if(used!=null){box.addView(compactReissueButton("Chọn ${resourceLabel(t)} đã dùng",used.length()>0){chooseUsed("Chọn ${resourceLabel(t)} đã dùng",used){id->er.usedId=id;next.setSelection(0);TopNotice.show(this,"Đã chọn $id để phát lại.",TopNotice.Kind.INFO)}},matchWrap())};box.addView(disp,matchWrap());box.addView(reason,matchWrap());box.addView(gap(7))
            }
            box.addView(section("VỊ TRÍ TRONG CA"));val removePos=mutableListOf<Pair<JSONObject,CheckBox>>();val pa=positionArray(s);for(i in 0 until pa.length()){val p=pa.optJSONObject(i)?:continue;if(!p.optString("state").equals("ACTIVE",true))continue;val label=p.optString("position_label").ifBlank{p.optString("position_key")};val c=CheckBox(this).apply{text="Xóa vị trí $label";setTextColor(ink)};removePos.add(p to c);box.addView(c)}
            val activeKeys=removePos.map{it.first.optString("position_key").uppercase()}.toSet();val main=s.optString("main_position_v64").trim();val addPositions=mutableListOf<Triple<String,String,CheckBox>>();for((k,l) in listOf("PICK" to "Pick","PACK" to "Pack")+(if(main.isNotBlank()&&!main.equals("Pick",true)&&!main.equals("Pack",true))listOf(foldLocal(main).ifBlank{main.uppercase()} to main)else emptyList()))if(k.uppercase() !in activeKeys){val c=CheckBox(this).apply{text="Thêm vị trí $l";setTextColor(ink)};addPositions.add(Triple(k.uppercase(),l,c));box.addView(c)}
            AlertDialog.Builder(this).setTitle("Sửa thông tin trong ca").setView(ScrollView(this).apply{addView(box)}).setNegativeButton("Hủy",null).setPositiveButton("LƯU"){_,_->
                if(shift.selectedItem.toString()!=s.optString("shift"))ops.put(JSONObject().put("op","UPDATE_SHIFT").put("shift",shift.selectedItem.toString()))
                for(er in edits)if(er.check.isChecked){val reason=er.reason.text.toString().trim();if(reason.length<2){showError("Nhập lý do cho ${resourceLabel(er.a.optString("resource_type"))} ${er.a.optString("resource_id")}");return@setPositiveButton};val disposition=if(er.disp.selectedItemPosition==0)"USED" else "AVAILABLE";if(er.action.selectedItemPosition==1)ops.put(JSONObject().put("op","REMOVE_RESOURCE").put("assignment_id",er.a.optString("assignment_id")).put("reason",reason).put("disposition",disposition))else{val normalId=er.normal.getOrNull(er.next.selectedItemPosition-1).orEmpty();val newId=er.usedId.ifBlank{normalId};if(newId.isBlank()){showError("Chọn tài nguyên mới cho ${er.a.optString("resource_id")}");return@setPositiveButton};ops.put(JSONObject().put("op","REPLACE_RESOURCE").put("assignment_id",er.a.optString("assignment_id")).put("new_resource_id",newId).put("reason",reason).put("disposition",disposition).put("duplicate_user",er.usedId.isNotBlank()))}}
                for(add in adds)if(add.check.isChecked){val normalId=add.normal.getOrNull(add.spin.selectedItemPosition-1).orEmpty();val id=add.used.ifBlank{normalId};if(id.isBlank()){showError("Chọn ${resourceLabel(add.type)} cần thêm");return@setPositiveButton};ops.put(JSONObject().put("op","ADD_RESOURCE").put("resource_type",add.type).put("resource_id",id).put("duplicate_user",add.used.isNotBlank()))}
                for((k,l,c) in addPositions)if(c.isChecked)ops.put(JSONObject().put("op","ADD_POSITION").put("position_key",k).put("position_label",l));for((p,c) in removePos)if(c.isChecked)ops.put(JSONObject().put("op","REMOVE_POSITION").put("position_key",p.optString("position_key")).put("reason","Xóa vị trí theo xác nhận thực tế"))
                if(ops.length()==0){showError("Chưa chọn thông tin cần sửa.");return@setPositiveButton};submitResourceMutation(ctx,ops,"Sửa thông tin trong ca")
            }.show();return
        }
        AlertDialog.Builder(this).setTitle("Thêm tài nguyên trong ca").setView(ScrollView(this).apply{addView(box)}).setNegativeButton("Hủy",null).setPositiveButton("THÊM"){_,_->for(add in adds)if(add.check.isChecked){val normalId=add.normal.getOrNull(add.spin.selectedItemPosition-1).orEmpty();val id=add.used.ifBlank{normalId};if(id.isBlank()){showError("Chọn ${resourceLabel(add.type)} cần thêm");return@setPositiveButton};ops.put(JSONObject().put("op","ADD_RESOURCE").put("resource_type",add.type).put("resource_id",id).put("duplicate_user",add.used.isNotBlank()))};if(ops.length()==0){showError("Chọn ít nhất một User hoặc PDA cần thêm.");return@setPositiveButton};submitResourceMutation(ctx,ops,"Thêm tài nguyên trong ca")}.show()
    }
    private fun deleteSessionWork(ctx:JSONObject){
        val s=ctx.optJSONObject("session")?:return;val box=column(surface).apply{setPadding(dp(10),dp(5),dp(10),dp(8))};box.addView(info("Chọn chính xác từng thông tin cần xóa. Tài nguyên chọn 'Cấp nhầm / chưa sử dụng' sẽ AVAILABLE ngay; tài nguyên đã dùng vẫn được giữ trong lịch sử của MNV."));box.addView(gap(6))
        data class D(val a:JSONObject,val check:CheckBox,val disp:Spinner,val reason:EditText);val rows=mutableListOf<D>()
        for(a in activeAssignments(s)){val c=CheckBox(this).apply{text="${resourceLabel(a.optString("resource_type"))}: ${a.optString("resource_id")}";setTextColor(ink)};val d=spinner(arrayOf("Đã sử dụng / có sản lượng","Cấp nhầm / chưa sử dụng"));val r=input("Lý do xóa",false);rows.add(D(a,c,d,r));box.addView(c);box.addView(d,matchWrap());box.addView(r,matchWrap());box.addView(gap(5))}
        val pos=mutableListOf<Pair<JSONObject,CheckBox>>();val pa=positionArray(s);for(i in 0 until pa.length()){val p=pa.optJSONObject(i)?:continue;if(!p.optString("state").equals("ACTIVE",true))continue;val c=CheckBox(this).apply{text="Vị trí: ${p.optString("position_label").ifBlank{p.optString("position_key")}}";setTextColor(ink)};pos.add(p to c);box.addView(c)}
        box.addView(gap(8));val all=smallButton("XÓA TOÀN BỘ PHIÊN VÀO – RA",red);box.addView(all,matchWrap());var dialog:AlertDialog?=null
        all.setOnClickListener{val reason=input("Lý do xóa toàn bộ phiên",false).apply{setText("Xóa phiên theo xác nhận thực tế")};AlertDialog.Builder(this).setTitle("Xóa toàn bộ phiên?").setView(reason).setNegativeButton("Hủy",null).setPositiveButton("XÁC NHẬN"){_,_->verifyDeletePassword("xóa toàn bộ phiên"){api.call("attendance_session_delete",JSONObject().put("session_id",s.optString("session_id")).put("reason",reason.text.toString().trim()).put("idempotency_key",UUID.randomUUID().toString())){r->runOnUiThread{if(!r.ok){showError(r.error?:"Không xóa được phiên");return@runOnUiThread};dialog?.dismiss();TopNotice.show(this,"Đã xóa phiên; audit chi tiết vẫn được giữ.",TopNotice.Kind.SUCCESS);employeeScan()}}}}.show()}
        dialog=AlertDialog.Builder(this).setTitle("Xóa thông tin cụ thể").setView(ScrollView(this).apply{addView(box)}).setNegativeButton("Hủy",null).setPositiveButton("XÓA ĐÃ CHỌN"){_,_->val ops=JSONArray();for(r in rows)if(r.check.isChecked){val reason=r.reason.text.toString().trim();if(reason.length<2){showError("Nhập lý do xóa ${r.a.optString("resource_id")}");return@setPositiveButton};ops.put(JSONObject().put("op","REMOVE_RESOURCE").put("assignment_id",r.a.optString("assignment_id")).put("reason",reason).put("disposition",if(r.disp.selectedItemPosition==0)"USED" else "AVAILABLE"))};for((p,c) in pos)if(c.isChecked)ops.put(JSONObject().put("op","REMOVE_POSITION").put("position_key",p.optString("position_key")).put("reason","Xóa vị trí theo xác nhận thực tế"));if(ops.length()==0){showError("Chọn chính xác thông tin cần xóa.");return@setPositiveButton};submitResourceMutation(ctx,ops,"Xóa thông tin cụ thể trong ca")}.create();dialog?.show()
    }
'''
o=replace_between(o,'    private fun sessionWorkEditor(ctx:JSONObject,mode:String){','    private fun editableTime(iso:String):String',EDITOR_BLOCK+'\n    private fun editableTime(iso:String):String')

DISPLAY_ENTER=r'''    private fun workInShiftText(ctx:JSONObject):String{val s=ctx.optJSONObject("session")?:JSONObject();return activePositionLabels(s).joinToString(" • ").ifBlank{"Không"}}
    private fun resourceStateRows(s:JSONObject):List<Pair<String,String>> = resourceListText(s)
    private fun renderActive(body:LinearLayout,ctx:JSONObject){
        val s=ctx.optJSONObject("session")?:JSONObject();val mnv=s.optString("mnv");val positions=activePositionLabels(s).joinToString(" • ").ifBlank{"Không"};body.addView(section("THỜI GIAN & VỊ TRÍ TRONG CA"));val rows=mutableListOf("Ca" to dash(s.optString("shift")),"Vào lúc" to formatIso(s.optString("enter_at")),"Vị trí trong ca" to positions);rows.addAll(resourceStateRows(s));body.addView(details(rows));body.addView(gap(7))
        val exit=smallButton("Ra ca",red);fun doExit(status:String){val gen=employeeLookupGeneration;exit.isEnabled=false;api.call("session_exit_v2",JSONObject().put("session_id",s.optString("session_id")).put("mnv",mnv).put("expected_version",s.optInt("version")).put("pda_exit_status",status).put("idempotency_key",UUID.randomUUID().toString())){r->runOnUiThread{exit.isEnabled=true;if(!r.ok){if(r.error=="SESSION_CHANGED")loadEmployee(mnv)else showError(r.error?:"RA_CA_FAILED");return@runOnUiThread};TopNotice.show(this,"Đã ghi nhận ra ca.",TopNotice.Kind.SUCCESS);foregroundSync.requestSync();if(gen==employeeLookupGeneration&&liveEmployeeMnv==mnv)scheduleAttendanceAutoReset(mnv,gen)}}}
        exit.setOnClickListener{if(ctx.optJSONObject("active_labor")!=null){showError("Còn công nhật đang làm. Hoàn thành công nhật trước khi ra ca.");return@setOnClickListener};val pda=activeAssignments(s,"PDA").firstOrNull();if(pda==null){doExit("");return@setOnClickListener};val expected=s.optString("pda_enter_status");val arr=MasterDataCache.resourceOptions(this).optJSONArray("pda_statuses")?:JSONArray();val statuses=mutableListOf<String>();for(i in 0 until arr.length()){val v=arr.optString(i).trim();if(v.isNotBlank()&&!statuses.contains(v))statuses.add(v)};if(expected.isNotBlank()&&!statuses.contains(expected))statuses.add(0,expected);val sp=spinner(statuses.toTypedArray());val wrap=column(surface).apply{setPadding(dp(12),dp(6),dp(12),dp(5));addView(txt("PDA ${pda.optString("resource_id")}",12f,navy,true));addView(labelled("Tình trạng PDA hiện tại",sp))};AlertDialog.Builder(this).setTitle("Đối chiếu PDA trước khi RA CA").setView(wrap).setNegativeButton("Hủy",null).setPositiveButton("KIỂM TRA & RA CA"){_,_->doExit(sp.selectedItem?.toString().orEmpty())}.show()}
        val actions=row(bg);actions.addView(smallButton("Thêm",teal).apply{setOnClickListener{sessionWorkEditor(ctx,"ADD")}},LinearLayout.LayoutParams(0,dp(40),1f).apply{marginEnd=dp(2)});actions.addView(smallButton("Sửa",navy).apply{setOnClickListener{sessionWorkEditor(ctx,"EDIT")}},LinearLayout.LayoutParams(0,dp(40),1f).apply{marginStart=dp(2);marginEnd=dp(2)});actions.addView(smallButton("Xóa",orange).apply{setOnClickListener{deleteSessionWork(ctx)}},LinearLayout.LayoutParams(0,dp(40),1f).apply{marginStart=dp(2)});body.addView(actions,matchWrap());body.addView(gap(5));body.addView(exit,matchWrap());body.addView(gap(8));addSessionTimeline(body,mnv)
    }
    private fun renderEnded(body:LinearLayout,ctx:JSONObject){val s=ctx.optJSONObject("session")?:JSONObject();val mnv=s.optString("mnv");body.addView(section("PHIÊN ĐÃ HOÀN THÀNH"));val rows=mutableListOf("Ca" to dash(s.optString("shift")),"Vào lúc" to formatIso(s.optString("enter_at")),"Ra lúc" to formatIso(s.optString("exit_at")),"Vị trí trong ca" to allPositionLabels(s).joinToString(" • ").ifBlank{"Không"});rows.addAll(resourceStateRows(s));body.addView(details(rows));body.addView(gap(7));addSessionTimeline(body,mnv);body.addView(gap(8));if(isAdmin()){val act=row(bg);act.addView(smallButton("Sửa giờ vào",navy).apply{setOnClickListener{editAttendanceTime(ctx,"enter_at")}},LinearLayout.LayoutParams(0,dp(40),1f).apply{marginEnd=dp(2)});act.addView(smallButton("Sửa giờ ra",teal).apply{setOnClickListener{editAttendanceTime(ctx,"exit_at")}},LinearLayout.LayoutParams(0,dp(40),1f).apply{marginStart=dp(2)});body.addView(act,matchWrap());body.addView(gap(5));body.addView(primary("XÓA GHI NHẬN RA CA",red){deleteExitRecord(ctx)},matchWrap())};body.addView(gap(5));body.addView(primary("XÓA TOÀN BỘ PHIÊN",red){deleteSessionWork(ctx)},matchWrap())}
    private fun renderEnter(body:LinearLayout,ctx:JSONObject,masters:JSONObject){
        val e=ctx.optJSONObject("employee")?:JSONObject();val mnv=e.optString("mnv");val main=e.optString("main_position").trim();body.addView(section("PHÂN CÔNG TRONG CA"));val now=java.time.LocalTime.now(ZoneId.of("Asia/Ho_Chi_Minh"));var shiftValue=when{now.isBefore(java.time.LocalTime.of(8,0))->"Ca 1";now.isBefore(java.time.LocalTime.of(10,0))->"Ca HC";else->"Ca 2"};val mainPick=main.equals("Pick",true);val mainPack=main.equals("Pack",true);val third=if(mainPick||mainPack)"Không" else main.ifBlank{"Không"};var posKey=when{mainPick->"PICK";mainPack->"PACK";else->if(third=="Không")"NONE" else foldLocal(third).ifBlank{third.uppercase()}};var posLabel=when(posKey){"PICK"->"Pick";"PACK"->"Pack";"NONE"->"Không";else->third}
        val shiftBox=column(bg);shiftBox.addView(segmentedChoice(listOf("Ca 1" to "Ca 1","Ca HC" to "Ca HC","Ca 2" to "Ca 2"),shiftValue){shiftValue=it},matchWrap());body.addView(labelled("Ca",shiftBox));body.addView(gap(7));val choices=listOf("Pick" to "PICK","Pack" to "PACK",third to (if(third=="Không")"NONE" else foldLocal(third).ifBlank{third.uppercase()}));val posBox=column(bg);posBox.addView(segmentedChoice(choices,posKey){k->posKey=k;posLabel=choices.firstOrNull{it.second==k}?.first?:k;renderEmployee(ctx,masters)},matchWrap());body.addView(labelled("Vị trí trong ca",posBox));body.addView(gap(7))
        val resource=column(bg);body.addView(resource,matchWrap());val pdas=masters.optJSONArray("pdas")?:JSONArray();val picks=masters.optJSONArray("user_picks")?:JSONArray();val pickUsed=masters.optJSONArray("user_picks_reissue")?:JSONArray();val packRows=masters.optJSONArray("pack_tables")?:JSONArray();val packUsedRows=masters.optJSONArray("pack_tables_reissue")?:JSONArray();var pdaField:AutoCompleteTextView?=null;var selectedPda:JSONObject?=null;var pickSpin:Spinner?=null;var selectedPickUsed="";var tableSpin:Spinner?=null;var packSpin:Spinner?=null;var selectedPackUsed=""
        fun distinctPackUsers(a:JSONArray):MutableList<String>{val x=mutableListOf<String>();for(i in 0 until a.length()){val o=a.optJSONObject(i);val v=(o?.optString("user_pack")?:a.optString(i)).trim();if(v.isNotBlank()&&!x.contains(v))x.add(v)};x.sortWith(Comparator{a,b->naturalUserCompare(a,b)});return x};fun distinctTables(a:JSONArray):MutableList<String>{val x=mutableListOf<String>();for(i in 0 until a.length()){val v=a.optJSONObject(i)?.optString("table").orEmpty().trim();if(v.isNotBlank()&&!x.contains(v))x.add(v)};x.sortWith(Comparator{a,b->naturalUserCompare(a,b)});return x}
        if(posKey=="PICK"){pdaField=pdaInput(pdas,onSelected={selectedPda=it});resource.addView(labelled("PDA — gõ 5 số cuối",pdaField!!));val normal=mutableListOf<String>();for(i in 0 until picks.length()){val v=picks.optString(i).trim();if(v.isNotBlank())normal.add(v)};pickSpin=spinner((listOf("Không dùng User Pick")+normal).toTypedArray());resource.addView(labelled("User Pick",pickSpin!!));resource.addView(compactReissueButton("Chọn User Pick đã dùng",pickUsed.length()>0){chooseUsed("Chọn User Pick đã dùng",pickUsed){selectedPickUsed=it;pickSpin?.setSelection(0)}},matchWrap())}
        if(posKey=="PACK"){val tables=distinctTables(packRows);val users=distinctPackUsers(packRows);tableSpin=spinner((listOf("Không chọn Bàn Pack")+tables).toTypedArray());packSpin=spinner((listOf("Không dùng User Pack")+users).toTypedArray());resource.addView(labelled("Bàn Pack",tableSpin!!));resource.addView(gap(5));resource.addView(labelled("User Pack — độc lập với bàn",packSpin!!));resource.addView(compactReissueButton("Chọn User Pack đã dùng",packUsedRows.length()>0){chooseUsed("Chọn User Pack đã dùng",packUsedRows){selectedPackUsed=it;packSpin?.setSelection(0)}},matchWrap())}
        val enter=primary("VÀO CA",teal){};enter.setOnClickListener{val positions=JSONArray();if(posKey!="NONE")positions.put(JSONObject().put("position_key",posKey).put("position_label",posLabel));val resources=JSONArray();if(posKey=="PICK"){val p=selectedPda;if(p==null||pdaField?.text?.toString()?.trim()!=p.optString("last5").ifBlank{p.optString("serial").takeLast(5)}){showError("Gõ 5 số cuối và chọn PDA hợp lệ.");return@setOnClickListener};resources.put(JSONObject().put("resource_type","PDA").put("resource_id",p.optString("serial")).put("pda_enter_status",p.optString("status")));val normal=pickSpin?.selectedItemPosition?.minus(1)?.let{idx->if(idx>=0)picks.optString(idx) else ""}.orEmpty();val u=selectedPickUsed.ifBlank{normal};if(u.isNotBlank())resources.put(JSONObject().put("resource_type","USER_PICK").put("resource_id",u).put("duplicate_user",selectedPickUsed.isNotBlank()))};if(posKey=="PACK"){val tables=distinctTables(packRows);val users=distinctPackUsers(packRows);val t=tables.getOrNull((tableSpin?.selectedItemPosition?:0)-1).orEmpty();if(t.isNotBlank())resources.put(JSONObject().put("resource_type","PACK_TABLE").put("resource_id",t));val normal=users.getOrNull((packSpin?.selectedItemPosition?:0)-1).orEmpty();val u=selectedPackUsed.ifBlank{normal};if(u.isNotBlank())resources.put(JSONObject().put("resource_type","USER_PACK").put("resource_id",u).put("duplicate_user",selectedPackUsed.isNotBlank()))};val gen=employeeLookupGeneration;enter.isEnabled=false;api.call("attendance_enter_v2",JSONObject().put("mnv",mnv).put("shift",shiftValue).put("positions",positions).put("resources",resources).put("idempotency_key",UUID.randomUUID().toString())){r->runOnUiThread{enter.isEnabled=true;if(!r.ok){showError(r.error?:"VÀO CA thất bại");return@runOnUiThread};TopNotice.show(this,"Đã ghi nhận vào ca.",TopNotice.Kind.SUCCESS);foregroundSync.requestSync();if(gen==employeeLookupGeneration&&liveEmployeeMnv==mnv)scheduleAttendanceAutoReset(mnv,gen)}}};body.addView(gap(8));body.addView(enter,matchWrap())
    }
'''
o=replace_between(o,'    private fun workInShiftText(ctx:JSONObject):String{','    private fun laborHome(){',DISPLAY_ENTER+'\n    private fun laborHome(){')
OPS.write_text(o)

# Static assertions: prevent the exact old business constraints from returning in Beta65 source.
for path,need in [(GRADLE,['0.4.2-beta.65','versionCode = 71']),(API,['session_resource_mutate','/v1/session/resources/mutate']),(OPS,['resource_assignments_v64','User Pack — độc lập với bàn','XÓA TOÀN BỘ PHIÊN','attendance_enter_v2','session_exit_v2']),(FULL,['Reference-stage layout','CENTER_INSIDE'])]:
    t=path.read_text()
    for x in need: assert x in t,(path,x)
assert 'rows.filter{it.optString("table")==table}' not in OPS.read_text()
print('BETA65_SESSION_RESOURCE_LOGIN_PARITY_MATERIALIZE_PASS')

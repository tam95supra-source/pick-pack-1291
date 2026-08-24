#!/usr/bin/env python3
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
FULL=ROOT/'app/src/main/java/vn/pickpack1291/app/beta/FullBetaActivity.kt'
OPS=ROOT/'app/src/main/java/vn/pickpack1291/app/beta/OperationsActivity.kt'


def once(text,old,new,label):
    if new in text: return text
    if old not in text: raise SystemExit(f'missing anchor: {label}')
    return text.replace(old,new,1)

def between(text,start,end,repl,label):
    i=text.find(start); j=text.find(end,i+len(start))
    if i<0 or j<0: raise SystemExit(f'missing range: {label}')
    return text[:i]+repl+text[j:]

LOGIN=r'''    private fun login() {
        foregroundSync.stop(); liveEmployeeMnv=""; currentScreen="LOGIN"
        accountLogin=""; accountName=""; accountRole=""; accountPosition=""; accountEmail=""
        window.statusBarColor=Color.rgb(218,29,22); window.navigationBarColor=Color.rgb(5,45,91)
        window.setSoftInputMode(android.view.WindowManager.LayoutParams.SOFT_INPUT_ADJUST_PAN)
        @Suppress("DEPRECATION") window.decorView.systemUiVisibility=0

        val sw=resources.configuration.screenWidthDp.coerceAtLeast(320)
        val sh=resources.configuration.screenHeightDp.coerceAtLeast(520)
        val designW=minOf(sw.toFloat(),sh*2f/3f)
        val designH=designW*1.5f
        val scale=(designW/360f).coerceIn(.78f,1.18f)
        fun ud(v:Int)=dp((v*scale).toInt().coerceAtLeast(1))
        fun usp(v:Float)=v*scale

        val user=EditText(this).apply{hint="Tài khoản";setSingleLine(true);textSize=usp(14f);setTextColor(Color.rgb(28,50,77));setHintTextColor(Color.rgb(145,155,170));background=null;setPadding(ud(5),0,ud(4),0);imeOptions=EditorInfo.IME_ACTION_NEXT}
        getPreferences(MODE_PRIVATE).getString("last_login","").orEmpty().takeIf{it.isNotBlank()}?.let{user.setText(it)}
        val pass=EditText(this).apply{hint="Mật khẩu";setSingleLine(true);textSize=usp(14f);setTextColor(Color.rgb(28,50,77));setHintTextColor(Color.rgb(145,155,170));background=null;setPadding(ud(5),0,ud(4),0);imeOptions=EditorInfo.IME_ACTION_DONE;inputType=InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_VARIATION_PASSWORD}
        fun field(icon:Int,edit:EditText,trailing:View?=null)=row(Color.WHITE).apply{gravity=Gravity.CENTER_VERTICAL;minimumHeight=ud(48);setPadding(ud(10),ud(2),ud(7),ud(2));background=GradientDrawable().apply{cornerRadius=ud(10).toFloat();setColor(Color.argb(250,255,255,255));setStroke(maxOf(1,ud(1)),Color.rgb(183,195,211))};addView(ImageView(this@FullBetaActivity).apply{setImageResource(icon);scaleType=ImageView.ScaleType.CENTER_INSIDE},size(ud(25),ud(25)));addView(edit,LinearLayout.LayoutParams(0,ud(43),1f));if(trailing!=null)addView(trailing,size(ud(38),ud(38)))}
        var visible=false
        val eye=ImageButton(this).apply{setImageResource(R.drawable.ic_login_eye);setBackgroundColor(Color.TRANSPARENT);contentDescription="Hiện mật khẩu";setPadding(ud(7),ud(7),ud(7),ud(7));alpha=.82f;setOnClickListener{visible=!visible;val c=pass.selectionStart.coerceAtLeast(0);pass.inputType=InputType.TYPE_CLASS_TEXT or if(visible)InputType.TYPE_TEXT_VARIATION_VISIBLE_PASSWORD else InputType.TYPE_TEXT_VARIATION_PASSWORD;pass.setSelection(c.coerceAtMost(pass.text.length));alpha=if(visible)1f else .82f;contentDescription=if(visible)"Ẩn mật khẩu" else "Hiện mật khẩu"}}

        val card=column(Color.WHITE).apply{gravity=Gravity.CENTER_HORIZONTAL;setPadding(ud(18),ud(16),ud(18),ud(18));background=GradientDrawable().apply{cornerRadius=ud(23).toFloat();setColor(Color.argb(250,255,255,255));setStroke(maxOf(1,ud(1)),Color.argb(60,90,115,150))};elevation=ud(8).toFloat()}
        card.addView(ImageView(this).apply{setImageResource(R.drawable.login_supra_logo);adjustViewBounds=true;scaleType=ImageView.ScaleType.FIT_CENTER},size(ud(112),ud(125)))
        card.addView(txt("Supra DC Hưng Yên",usp(17f),Color.rgb(17,75,151),true).center());card.addView(gap((12*scale).toInt()))
        card.addView(field(R.drawable.ic_login_user,user),matchWrap());card.addView(gap((8*scale).toInt()));card.addView(field(R.drawable.ic_login_lock,pass,eye),matchWrap())
        val forgot=TextView(this).apply{text="Quên mật khẩu?";textSize=usp(11.5f);setTextColor(Color.rgb(12,72,156));typeface=Typeface.DEFAULT_BOLD;gravity=Gravity.END;setPadding(ud(4),ud(5),0,ud(6));setOnClickListener{val id=user.text.toString().trim();if(id.isBlank()){toast("Nhập đúng tài khoản trước khi chọn Quên mật khẩu.");return@setOnClickListener};isEnabled=false;text="Đang gửi yêu cầu...";api.forgotPassword(id){r->runOnUiThread{isEnabled=true;text="Quên mật khẩu?";if(!r.ok)showError(r.error?:"Không gửi được yêu cầu đặt lại mật khẩu") else TopNotice.show(this@FullBetaActivity,"Nếu tài khoản hợp lệ, mật khẩu mới đã được gửi tới mail đã cấu hình.",TopNotice.Kind.SUCCESS)}}}}
        card.addView(forgot,matchWrap());card.addView(gap((5*scale).toInt()))
        val loginBtn=Button(this).apply{text="Đăng nhập";textSize=usp(15f);setTextColor(Color.WHITE);typeface=Typeface.DEFAULT_BOLD;isAllCaps=false;minimumHeight=ud(50);background=gradient(Color.rgb(18,84,184),Color.rgb(6,57,137),12)}
        fun submit(){val id=user.text.toString().trim();val pw=pass.text.toString();if(id.isBlank()||pw.isBlank()){toast("Nhập tài khoản và mật khẩu.");return};loginBtn.isEnabled=false;loginBtn.text="Đang xác thực...";api.login(id,pw){r->runOnUiThread{loginBtn.isEnabled=true;loginBtn.text="Đăng nhập";if(!r.ok){showError(r.error?:"Đăng nhập thất bại");return@runOnUiThread};val a=r.json?.optJSONObject("account")?:JSONObject();accountLogin=a.optString("login_id",id);accountName=a.optString("display_name",accountLogin);accountRole=a.optString("role","USER");accountPosition=a.optString("position","");accountEmail=a.optString("email","");getPreferences(MODE_PRIVATE).edit().putString("last_login",accountLogin).apply();pass.setText("");openMainShell();if(MasterDataCache.revision(this@FullBetaActivity)==0L)refreshMasterCache();LocalLogManager.uploadAutomaticPending(this@FullBetaActivity,api)}}}
        loginBtn.setOnClickListener{submit()};user.setOnEditorActionListener{_,a,_->if(a==EditorInfo.IME_ACTION_NEXT){pass.requestFocus();true}else false};pass.setOnEditorActionListener{_,a,_->if(a==EditorInfo.IME_ACTION_DONE){submit();true}else false};card.addView(loginBtn,matchWrap());card.addView(gap((8*scale).toInt()))
        card.addView(Button(this).apply{text="Đăng ký";textSize=usp(13.5f);setTextColor(Color.rgb(13,73,155));typeface=Typeface.DEFAULT_BOLD;isAllCaps=false;minimumHeight=ud(48);background=GradientDrawable().apply{cornerRadius=ud(11).toFloat();setColor(Color.argb(248,255,255,255));setStroke(maxOf(1,ud(1)),Color.rgb(22,82,168))};setOnClickListener{TopNotice.show(this@FullBetaActivity,"Tính năng đăng ký đang được xây dựng.",TopNotice.Kind.INFO)}},matchWrap())

        val canvas=FrameLayout(this).apply{setBackgroundColor(Color.rgb(247,238,214));addView(ImageView(this@FullBetaActivity).apply{setImageResource(R.drawable.login_vietnam_bg);scaleType=ImageView.ScaleType.FIT_XY},FrameLayout.LayoutParams(-1,-1))}
        val cardWidth=dp((designW*.64f).toInt())
        canvas.addView(card,FrameLayout.LayoutParams(cardWidth,-2,Gravity.TOP or Gravity.CENTER_HORIZONTAL).apply{topMargin=dp((designH*.185f).toInt())})
        val copyright="Copyright 2026 Supra DC Hưng Yên  -  tamnv2  -  Chuyên viên Pick Pack 1291"
        val span=android.text.SpannableString(copyright);val s0=copyright.indexOf("Supra DC Hưng Yên");if(s0>=0){span.setSpan(android.text.style.ForegroundColorSpan(Color.rgb(251,191,36)),s0,s0+"Supra DC Hưng Yên".length,android.text.Spannable.SPAN_EXCLUSIVE_EXCLUSIVE);span.setSpan(android.text.style.StyleSpan(Typeface.BOLD),s0,s0+"Supra DC Hưng Yên".length,android.text.Spannable.SPAN_EXCLUSIVE_EXCLUSIVE)}
        canvas.addView(TextView(this).apply{text=span;textSize=usp(8.6f);setTextColor(Color.WHITE);gravity=Gravity.CENTER;maxLines=1;setPadding(ud(5),0,ud(5),ud(3))},FrameLayout.LayoutParams(-1,ud(30),Gravity.BOTTOM))
        val root=FrameLayout(this).apply{setBackgroundColor(Color.rgb(238,230,209));addView(canvas,FrameLayout.LayoutParams(dp(designW.toInt()),dp(designH.toInt()),Gravity.CENTER))}
        setScreen(root);user.requestFocus()
    }

'''

full=FULL.read_text()
if 'val designW=minOf(sw.toFloat(),sh*2f/3f)' not in full:
    full=between(full,'    private fun login() {\n','    private fun openMainShell()',LOGIN,'login')
full=once(full,'        root.addView(txt(FOOTER,8f,Color.rgb(113,122,136),false).apply{gravity=Gravity.CENTER;maxLines=1},FrameLayout.LayoutParams(-1,dp(20),Gravity.BOTTOM))','        if(currentScreen!="LOGIN")root.addView(txt(FOOTER,8f,Color.rgb(113,122,136),false).apply{gravity=Gravity.CENTER;maxLines=1},FrameLayout.LayoutParams(-1,dp(20),Gravity.BOTTOM))','login footer')
FULL.write_text(full)

ops=OPS.read_text()
# 2: fence late callbacks so an older employee cannot reset/overwrite a newer scanned employee.
old='''    private fun scheduleAttendanceAutoReset(mnv:String,generation:Long){\n        val expected=mnv.trim()\n        android.os.Handler(mainLooper).postDelayed({\n            // If another code has already been scanned/rendered, never clear that newer employee.\n            if(screenState=="EMPLOYEE"&&liveEmployeeMnv==expected&&employeeLookupGeneration==generation)employeeScan()\n        },650L)\n    }'''
new='''    private fun sameEmployeeContext(mnv:String,generation:Long):Boolean = screenState=="EMPLOYEE" && liveEmployeeMnv.trim()==mnv.trim() && employeeLookupGeneration==generation\n    private fun scheduleAttendanceAutoReset(mnv:String,generation:Long){\n        val expected=mnv.trim()\n        android.os.Handler(mainLooper).postDelayed({ if(sameEmployeeContext(expected,generation))employeeScan() },650L)\n    }'''
ops=once(ops,old,new,'context fence helper')
ops=once(ops,'fun doExit(statusNow:String){exit.isEnabled=false;exit.text="Đang ra...";val eventId=UUID.randomUUID().toString();api.call("exit"','fun doExit(statusNow:String){val actionGeneration=employeeLookupGeneration;exit.isEnabled=false;exit.text="Đang ra...";val eventId=UUID.randomUUID().toString();api.call("exit"','exit generation capture')
ops=ops.replace('scheduleAttendanceAutoReset(mnv,employeeLookupGeneration)','scheduleAttendanceAutoReset(mnv,actionGeneration)')
# Work editor callback: never render MNV A after user has moved to MNV B.
ops=once(ops,'val ses=ctx.optJSONObject("session")?:return;val mnv=ses.optString("mnv");val editMode=if(mode.uppercase()=="ADD")"ADD" else "EDIT"','val ses=ctx.optJSONObject("session")?:return;val mnv=ses.optString("mnv");val actionGeneration=employeeLookupGeneration;val editMode=if(mode.uppercase()=="ADD")"ADD" else "EDIT"','work editor generation')
ops=once(ops,'foregroundSync.requestSync();val next=returnedSessionContext(ctx,r);if(next!=null)renderEmployee(next,PdaLocalProjection.resourceOptions(this,mnv))else loadEmployee(mnv)','foregroundSync.requestSync();if(sameEmployeeContext(mnv,actionGeneration)){val next=returnedSessionContext(ctx,r);if(next!=null)renderEmployee(next,PdaLocalProjection.resourceOptions(this,mnv))else loadEmployee(mnv)}','work callback fence')
# Delete operations also obey the same employee context.
ops=once(ops,'private fun deleteSessionWork(ctx:JSONObject){\n        val ses=ctx.optJSONObject("session")?:return;val mnv=ses.optString("mnv")','private fun deleteSessionWork(ctx:JSONObject){\n        val ses=ctx.optJSONObject("session")?:return;val mnv=ses.optString("mnv");val actionGeneration=employeeLookupGeneration','delete generation')
ops=ops.replace('foregroundSync.requestSync();employeeScan()','foregroundSync.requestSync();if(sameEmployeeContext(mnv,actionGeneration))employeeScan()',1)
# 6: work summary is based only on actually recorded Pick/Pack resources, never main position or stale work_choice alone.
old_work='''    private fun workInShiftText(ctx:JSONObject):String{\n        val ses=ctx.optJSONObject("session")?:JSONObject();val emp=ctx.optJSONObject("employee")?:JSONObject();val main=foldLocal(emp.optString("main_position"))\n        val mainPick=main.contains("PICK");val mainPack=main.contains("PACK")\n        val extraPick=ses.optString("work_choice").equals("PICK",true)||ses.optString("pda_serial").isNotBlank()||ses.optString("user_pick").isNotBlank()\n        val extraPack=ses.optString("work_choice").equals("PACK",true)||ses.optString("pack_table").isNotBlank()||ses.optString("user_pack").isNotBlank()\n        if(!extraPick&&!extraPack)return "Làm theo vị trí chính"\n        val hasPick=mainPick||extraPick;val hasPack=mainPack||extraPack\n        if(mainPick||mainPack)return when{hasPick&&hasPack->"Pick & Pack";hasPick->"Pick";hasPack->"Pack";else->"Làm theo vị trí chính"}\n        return "Làm theo vị trí chính"+when{extraPick&&extraPack->" & Pick & Pack";extraPick->" & Pick";extraPack->" & Pack";else->""}\n    }'''
new_work='''    private fun workInShiftText(ctx:JSONObject):String{\n        val ses=ctx.optJSONObject("session")?:JSONObject()\n        val hasPick=ses.optString("pda_serial").isNotBlank()||ses.optString("user_pick").isNotBlank()\n        val hasPack=ses.optString("pack_table").isNotBlank()||ses.optString("user_pack").isNotBlank()\n        return when{hasPick&&hasPack->"Làm theo vị trí chính & Pick & Pack";hasPick->"Làm theo vị trí chính & Pick";hasPack->"Làm theo vị trí chính & Pack";else->"Làm theo vị trí chính"}\n    }'''
ops=once(ops,old_work,new_work,'work summary')
# 5: timeline/resource usage must be scoped to the exact attendance session, with time-window fallback for legacy events lacking session_id.
ops=once(ops,'private fun sessionTimelineItems(mnv:String):MutableList<JSONObject>{\n        val merged=LinkedHashMap<String,JSONObject>();val date=operationalStore.businessDate()','private fun sessionTimelineItems(mnv:String,ses:JSONObject):MutableList<JSONObject>{\n        val merged=LinkedHashMap<String,JSONObject>();val date=ses.optString("business_date").ifBlank{operationalStore.businessDate()};val currentSessionId=ses.optString("session_id").trim();val enterMs=runCatching{Instant.parse(ses.optString("enter_at")).toEpochMilli()}.getOrDefault(0L);val exitMs=runCatching{Instant.parse(ses.optString("exit_at")).toEpochMilli()}.getOrDefault(Long.MAX_VALUE)\n        fun sameSession(e:JSONObject,p:JSONObject,localAt:Long=0L):Boolean{val sid=e.optString("session_id").ifBlank{p.optString("session_id")}.trim();if(currentSessionId.isNotBlank()&&sid.isNotBlank())return sid==currentSessionId;val ms=if(localAt>0L)localAt else runCatching{Instant.parse(e.optString("committed_at").ifBlank{e.optString("occurred_at").ifBlank{e.optString("at_iso").ifBlank{e.optString("at")}}}).toEpochMilli()}.getOrDefault(0L);return enterMs>0L&&ms>=enterMs&&ms<=exitMs}','timeline signature')
ops=once(ops,'val e=events.optJSONObject(i)?:continue;val p=payload(e);val who=e.optString("mnv").ifBlank{p.optString("mnv")}.trim();if(who!=mnv)continue\n            val type=e.optString("event_type").uppercase()','val e=events.optJSONObject(i)?:continue;val p=payload(e);val who=e.optString("mnv").ifBlank{p.optString("mnv")}.trim();if(who!=mnv||!sameSession(e,p))continue\n            val type=e.optString("event_type").uppercase()','canonical session filter')
ops=once(ops,'val id=local.optString("event_id").trim();if(id.isBlank())continue;val body=local.optJSONObject("body")?:JSONObject();val p=body.optJSONObject("payload")?:body;if(p.optString("mnv").trim()!=mnv)continue','val id=local.optString("event_id").trim();if(id.isBlank())continue;val body=local.optJSONObject("body")?:JSONObject();val p=body.optJSONObject("payload")?:body;if(p.optString("mnv").trim()!=mnv||!sameSession(body,p,local.optLong("queued_at",0L)))continue','local session filter')
ops=ops.replace('sessionTimelineItems(mnv).forEach','sessionTimelineItems(mnv,ses).forEach')
ops=once(ops,'private fun addSessionTimeline(body:LinearLayout,mnv:String){\n        body.addView(section("DIỄN BIẾN CÔNG VIỆC TRONG CA"))\n        val items=sessionTimelineItems(mnv)','private fun addSessionTimeline(body:LinearLayout,mnv:String,ses:JSONObject){\n        body.addView(section("DIỄN BIẾN CÔNG VIỆC TRONG CA"))\n        val items=sessionTimelineItems(mnv,ses)','timeline renderer signature')
ops=ops.replace('addSessionTimeline(body,mnv);','addSessionTimeline(body,mnv,ses);')
ops=ops.replace('addSessionTimeline(body,mnv)','addSessionTimeline(body,mnv,ses)')
# 3: keep normal unused users separate. Reissue opens its own list and only selected used entry is applied.
helper='''\n    private fun showReissueChooser(title:String,labels:List<String>,onSelected:(Int)->Unit){\n        if(labels.isEmpty()){showError("Không có user đã dùng có thể phát lại.");return}\n        AlertDialog.Builder(this).setTitle(title).setItems(labels.toTypedArray()){_,which->if(which in labels.indices)onSelected(which)}.setNegativeButton("Hủy",null).show()\n    }\n'''
if 'private fun showReissueChooser' not in ops:
    ops=ops.replace('    private fun compactReissueButton(',helper+'\n    private fun compactReissueButton(',1)
# Editor pick: remove merge and use dedicated chooser/selection.
ops=ops.replace('var selectedPack:JSONObject?=null;var allowPickReissue=false;var allowPackReissue=false','var selectedPack:JSONObject?=null;var selectedPickReissue:String?=null;var selectedPackReissue:JSONObject?=null')
ops=ops.replace('''                if(allowPickReissue){\n                    val used=mutableListOf<String>();for(i in 0 until pickReissue.length()){val id=pickReissue.optJSONObject(i)?.optString("id").orEmpty().trim();if(id.isNotBlank()&&!base.contains(id)&&!used.contains(id))used.add(id)}\n                    sortedByNaturalUser(used){it}.forEach{pickChoices.add(it to true);labels.add("⚠ $it • ĐÃ DÙNG HÔM NAY")}\n                }''','')
old_btn='userRow.addView(compactReissueButton("Phát lại user pick",pickReissue.length()>0&&!allowPickReissue){allowPickReissue=true;rebuild()},LinearLayout.LayoutParams(0,dp(46),.85f))'
new_btn='''userRow.addView(compactReissueButton("Phát lại user pick",pickReissue.length()>0){val used=mutableListOf<String>();for(i in 0 until pickReissue.length()){val id=pickReissue.optJSONObject(i)?.optString("id").orEmpty().trim();if(id.isNotBlank()&&!used.contains(id))used.add(id)};val sorted=sortedByNaturalUser(used){it};showReissueChooser("Chọn User Pick đã dùng",sorted){idx->selectedPickReissue=sorted[idx];TopNotice.show(this,"Đã chọn phát lại ${sorted[idx]}",TopNotice.Kind.INFO)}},LinearLayout.LayoutParams(0,dp(46),.85f))'''
ops=once(ops,old_btn,new_btn,'editor pick reissue button')
# Editor Pack rows remain unused-only; button opens separate used list.
ops=ops.replace('addPack(packs,false);if(allowPackReissue)addPack(packReissue,true)','addPack(packs,false)')
old_pack_btn='userRow.addView(compactReissueButton("Phát lại user pack",packReissue.length()>0&&!allowPackReissue){allowPackReissue=true;rebuild()},LinearLayout.LayoutParams(0,dp(46),.85f));userHost.addView(labelled("User Pack",userRow))'
new_pack_btn='''userRow.addView(compactReissueButton("Phát lại user pack",packReissue.length()>0){val used=mutableListOf<JSONObject>();for(i in 0 until packReissue.length()){val o=packReissue.optJSONObject(i)?:continue;if(o.optString("table").isNotBlank()&&o.optString("user_pack").isNotBlank())used.add(JSONObject(o.toString()).put("duplicate_user",true))};val labels=used.map{"${it.optString("table")} • ${it.optString("user_pack")}"};showReissueChooser("Chọn User Pack đã dùng",labels){idx->selectedPackReissue=used[idx];TopNotice.show(this,"Đã chọn phát lại ${labels[idx]}",TopNotice.Kind.INFO)}},LinearLayout.LayoutParams(0,dp(46),.85f));userHost.addView(labelled("User Pack",userRow))'''
ops=once(ops,old_pack_btn,new_pack_btn,'editor pack reissue button')
ops=once(ops,'val pickChoice=if(pickOn.isChecked)pickChoices.getOrNull(pickSpinner?.selectedItemPosition?:0) else null\n            val pick=if(pickOn.isChecked)pickChoice?.first.orEmpty() else ses.optString("user_pick")','val pickChoice=if(pickOn.isChecked)pickChoices.getOrNull(pickSpinner?.selectedItemPosition?:0) else null\n            val pick=if(pickOn.isChecked)selectedPickReissue?:pickChoice?.first.orEmpty() else ses.optString("user_pick")','editor selected reissue pick')
ops=ops.replace('var reissue=pickChoice?.second==true','var reissue=selectedPickReissue!=null||pickChoice?.second==true',1)
ops=once(ops,'val row=selectedPack;if(row==null){showError("Chọn Bàn Pack + User Pack hợp lệ.");return@setPositiveButton}','val row=selectedPackReissue?:selectedPack;if(row==null){showError("Chọn Bàn Pack + User Pack hợp lệ.");return@setPositiveButton}','editor selected reissue pack')
# Enter screen: same dedicated chooser model.
ops=ops.replace('var pdaField:AutoCompleteTextView?=null;var selectedPda:JSONObject?=null;var pickSpinner:Spinner?=null;var pickChoices=mutableListOf<Pair<String,Boolean>>();var packSelection:JSONObject?=null\n        var allowPickReissue=false;var allowPackReissue=false','var pdaField:AutoCompleteTextView?=null;var selectedPda:JSONObject?=null;var pickSpinner:Spinner?=null;var pickChoices=mutableListOf<Pair<String,Boolean>>();var packSelection:JSONObject?=null;var selectedPickReissue:String?=null;var selectedPackReissue:JSONObject?=null')
# Remove one-line merge in enter Pick and Pack.
ops=ops.replace('if(allowPickReissue){val used=mutableListOf<String>();for(i in 0 until pickReissue.length()){val id=pickReissue.optJSONObject(i)?.optString("id").orEmpty().trim();if(id.isNotBlank()&&!base.contains(id)&&!used.contains(id))used.add(id)};sortedByNaturalUser(used){it}.forEach{pickChoices.add(it to true);labels.add("⚠ $it • ĐÃ DÙNG HÔM NAY")}}','')
old_enter_pick='userRow.addView(compactReissueButton("Phát lại user pick",pickReissue.length()>0&&!allowPickReissue){allowPickReissue=true;rebuildResources?.invoke()},LinearLayout.LayoutParams(0,dp(46),.85f))'
new_enter_pick='''userRow.addView(compactReissueButton("Phát lại user pick",pickReissue.length()>0){val used=mutableListOf<String>();for(i in 0 until pickReissue.length()){val id=pickReissue.optJSONObject(i)?.optString("id").orEmpty().trim();if(id.isNotBlank()&&!used.contains(id))used.add(id)};val sorted=sortedByNaturalUser(used){it};showReissueChooser("Chọn User Pick đã dùng",sorted){idx->selectedPickReissue=sorted[idx];TopNotice.show(this,"Đã chọn phát lại ${sorted[idx]}",TopNotice.Kind.INFO)}},LinearLayout.LayoutParams(0,dp(46),.85f))'''
ops=once(ops,old_enter_pick,new_enter_pick,'enter pick reissue button')
ops=ops.replace('addRows(packs,false);if(allowPackReissue)addRows(packReissue,true)','addRows(packs,false)')
old_enter_pack='userRow.addView(compactReissueButton("Phát lại user pack",packReissue.length()>0&&!allowPackReissue){allowPackReissue=true;rebuildResources?.invoke()},LinearLayout.LayoutParams(0,dp(46),.85f));userHost.addView(labelled("User Pack",userRow))'
new_enter_pack='''userRow.addView(compactReissueButton("Phát lại user pack",packReissue.length()>0){val used=mutableListOf<JSONObject>();for(i in 0 until packReissue.length()){val o=packReissue.optJSONObject(i)?:continue;if(o.optString("table").isNotBlank()&&o.optString("user_pack").isNotBlank())used.add(JSONObject(o.toString()).put("duplicate_user",true))};val labels=used.map{"${it.optString("table")} • ${it.optString("user_pack")}"};showReissueChooser("Chọn User Pack đã dùng",labels){idx->selectedPackReissue=used[idx];TopNotice.show(this,"Đã chọn phát lại ${labels[idx]}",TopNotice.Kind.INFO)}},LinearLayout.LayoutParams(0,dp(46),.85f));userHost.addView(labelled("User Pack",userRow))'''
ops=once(ops,old_enter_pack,new_enter_pack,'enter pack reissue button')
ops=once(ops,'val picked=pickChoices.getOrNull(pickSpinner?.selectedItemPosition?:0)?:("" to false);if(picked.first.isNotBlank())payload.put("user_pick",picked.first);if(picked.second)payload.put("duplicate_user",true).put("resource_note","PHÁT LẠI USER")','val picked=pickChoices.getOrNull(pickSpinner?.selectedItemPosition?:0)?:("" to false);val pickedId=selectedPickReissue?:picked.first;if(pickedId.isNotBlank())payload.put("user_pick",pickedId);if(selectedPickReissue!=null||picked.second)payload.put("duplicate_user",true).put("resource_note","PHÁT LẠI USER")','enter payload pick')
ops=once(ops,'val row=packSelection;if(row==null){showError("Chọn Bàn Pack và User Pack hợp lệ.");return@setOnClickListener}','val row=selectedPackReissue?:packSelection;if(row==null){showError("Chọn Bàn Pack và User Pack hợp lệ.");return@setOnClickListener}','enter payload pack')
# 7: app information shows actual machine cache footprint.
cache_helper='''\n    private fun appCacheBytes():Long{\n        fun sizeOf(f:java.io.File?):Long{if(f==null||!f.exists())return 0L;if(f.isFile)return f.length();return f.listFiles()?.sumOf{sizeOf(it)}?:0L}\n        return sizeOf(cacheDir)+runCatching{sizeOf(codeCacheDir)}.getOrDefault(0L)\n    }\n'''
if 'private fun appCacheBytes()' not in ops:
    ops=ops.replace('    private fun humanBytes(',cache_helper+'\n    private fun humanBytes(',1)
ops=once(ops,'"Phiên bản ứng dụng" to BuildConfig.VERSION_NAME,\n            "Mã phiên bản" to BuildConfig.VERSION_CODE.toString()','"Phiên bản ứng dụng" to BuildConfig.VERSION_NAME,\n            "Mã phiên bản" to BuildConfig.VERSION_CODE.toString(),\n            "Dung lượng cache ứng dụng" to humanBytes(appCacheBytes())','app cache info')

OPS.write_text(ops)

checks={
 'full frame login':'ImageView.ScaleType.FIT_XY' in FULL.read_text() and 'designH=designW*1.5f' in FULL.read_text(),
 'no login crop':'login_vietnam_bg);scaleType=ImageView.ScaleType.CENTER_CROP' not in FULL.read_text(),
 'callback fence':'sameEmployeeContext' in OPS.read_text() and 'scheduleAttendanceAutoReset(mnv,actionGeneration)' in OPS.read_text(),
 'reissue chooser':'showReissueChooser("Chọn User Pick đã dùng"' in OPS.read_text() and 'showReissueChooser("Chọn User Pack đã dùng"' in OPS.read_text(),
 'timeline session':'sessionTimelineItems(mnv:String,ses:JSONObject)' in OPS.read_text() and 'sameSession(e,p)' in OPS.read_text(),
 'work truth':'Làm theo vị trí chính & Pick & Pack' in OPS.read_text() and 'val mainPick=' not in OPS.read_text(),
 'cache info':'Dung lượng cache ứng dụng' in OPS.read_text(),
}
fail=[k for k,v in checks.items() if not v]
if fail: raise SystemExit('Beta64 checks failed: '+', '.join(fail))
print('Beta64 owner seven fixes materialization PASS')

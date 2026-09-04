package vn.pickpack1291.app.beta

import android.app.Activity
import android.app.AlertDialog
import android.app.TimePickerDialog
import android.graphics.Color
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.os.Handler
import android.os.Looper
import android.view.Gravity
import android.view.KeyEvent
import android.view.View
import android.view.ViewGroup
import android.view.inputmethod.EditorInfo
import android.widget.*
import org.json.JSONArray
import org.json.JSONObject
import java.time.Instant
import java.time.LocalDate
import java.time.LocalDateTime
import java.time.ZoneId
import java.time.format.DateTimeFormatter
import java.util.UUID

object PostMealAttendanceFeature {
    private const val TZ="Asia/Ho_Chi_Minh"
    @Volatile private var activeDate=""
    @Volatile private var activeRefresh:(()->Unit)?=null
    @Volatile private var homeWarningRefresh:(()->Unit)?=null

    fun onRealtime(changedDates:Set<String>){
        // Foreground websocket already performs the relevant fast refresh. Projection completion
        // must not fire a second Service-backed warning reload.
        if(activeDate.isNotBlank()&&activeDate in changedDates)activeRefresh?.invoke()
    }
    fun onRealtimeFast(date:String){
        if(date.isBlank())return
        if(activeDate==date)activeRefresh?.invoke()
        homeWarningRefresh?.invoke()
    }
    fun leave(){activeDate="";activeRefresh=null}

    fun buildHomeWarning(activity:Activity,api:BetaApiClient,onOpen:()->Unit):View{
        val density=activity.resources.displayMetrics.density
        fun dp(v:Int)=(v*density).toInt()
        fun round(color:Int,r:Int)=GradientDrawable().apply{setColor(color);cornerRadius=dp(r).toFloat()}
        val root=ReviewAlertUi.warningContainer(activity)
        val button=ReviewAlertUi.button(activity,"",ReviewAlertUi.Tone.WARNING)
        root.addView(button,ReviewAlertUi.fixedHeightParams(activity))
        val store=MealAttendanceLocalStore(activity)
        val today=LocalDate.now(ZoneId.of(TZ)).toString()
        fun unresolved(source:JSONObject?):Pair<Int,Boolean>{
            if(source==null)return 0 to false
            val now=java.time.ZonedDateTime.now(ZoneId.of(TZ));val minutes=now.hour*60+now.minute;val nowMs=System.currentTimeMillis()
            val items=source.optJSONArray("items")?:JSONArray();var count=0;var severe=false
            for(i in 0 until items.length()){
                val x=items.optJSONObject(i)?:continue
                val shift=x.optString("shift");val due=(shift in setOf("Ca 1","Ca HC")&&minutes>=12*60)||(shift=="Ca 2"&&minutes>=19*60)
                if(!due)continue
                var status=x.optString("status_view").ifBlank{x.optString("status").ifBlank{"PENDING"}}
                if(status=="LATE_EXPECTED"&&x.optString("actual_return_at").isBlank()){
                    val expected=x.optString("expected_return_at")
                    if(expected.isNotBlank()&&runCatching{Instant.parse(expected).toEpochMilli()<=nowMs}.getOrDefault(false))status="OVERDUE_LATE"
                }
                if(status=="PENDING"||status=="OVERDUE_LATE"){
                    count++
                    if(status=="OVERDUE_LATE"||(shift in setOf("Ca 1","Ca HC")&&minutes>=12*60+30)||(shift=="Ca 2"&&minutes>=19*60+30))severe=true
                }
            }
            return count to severe
        }
        fun apply(source:JSONObject?){
            val (count,severe)=unresolved(source)
            button.clearAnimation()
            if(count<=0){root.visibility=View.GONE;return}
            root.visibility=View.VISIBLE
            button.text="CẢNH BÁO: CÒN $count NHÂN SỰ CHƯA ĐIỂM DANH"
            if(severe)button.startAnimation(android.view.animation.AlphaAnimation(1f,.55f).apply{
                duration=760;repeatMode=android.view.animation.Animation.REVERSE;repeatCount=android.view.animation.Animation.INFINITE
            })
        }
        button.setOnClickListener{onOpen()}
        fun remoteRefresh(){
            api.call("meal_attendance_list",JSONObject().put("business_date",today)){r->activity.runOnUiThread{
                if(r.ok&&r.json!=null){val fresh=JSONObject(r.json.toString());store.save(fresh);apply(fresh)}
            }}
        }
        apply(store.load(today))
        homeWarningRefresh={activity.runOnUiThread{remoteRefresh()}}
        root.addOnAttachStateChangeListener(object:View.OnAttachStateChangeListener{
            override fun onViewAttachedToWindow(v:View)=Unit
            override fun onViewDetachedFromWindow(v:View){homeWarningRefresh=null}
        })
        remoteRefresh()
        return root
    }

    fun build(activity:Activity,api:BetaApiClient,onBack:()->Unit):View{
        val density=activity.resources.displayMetrics.density
        fun dp(v:Int)=(v*density).toInt()
        val teal=ThemeManager.primary(activity);val navy=ThemeManager.primaryDark(activity)
        val ink=Color.rgb(24,44,42);val muted=Color.rgb(100,116,139);val red=Color.rgb(218,45,53)
        val orange=Color.rgb(217,119,6);val green=Color.rgb(36,153,85);val bg=Color.WHITE
        fun drawable(fill:Int=Color.WHITE,stroke:Int=Color.rgb(220,228,226),radius:Int=10)=GradientDrawable().apply{setColor(fill);cornerRadius=dp(radius).toFloat();setStroke(dp(1),stroke)}
        fun text(v:String,size:Float,color:Int=ink,bold:Boolean=false)=TextView(activity).apply{text=v;textSize=size;setTextColor(color);typeface=if(bold)Typeface.DEFAULT_BOLD else Typeface.DEFAULT}
        fun column()=LinearLayout(activity).apply{orientation=LinearLayout.VERTICAL;setBackgroundColor(bg)}
        fun row()=LinearLayout(activity).apply{orientation=LinearLayout.HORIZONTAL;setBackgroundColor(bg);gravity=Gravity.CENTER_VERTICAL}
        fun gap(v:Int)=Space(activity).apply{layoutParams=ViewGroup.LayoutParams(1,dp(v))}
        fun button(label:String,color:Int)=Button(activity).apply{text=label;textSize=10f;setTextColor(Color.WHITE);typeface=Typeface.DEFAULT_BOLD;isAllCaps=false;minHeight=0;minimumHeight=0;background=GradientDrawable().apply{setColor(color);cornerRadius=dp(9).toFloat()}}
        fun input(hintText:String)=EditText(activity).apply{hint=hintText;textSize=13f;setTextColor(ink);setHintTextColor(Color.rgb(148,163,184));setPadding(dp(10),dp(7),dp(10),dp(7));background=drawable();setSingleLine(true);imeOptions=EditorInfo.IME_ACTION_DONE}
        fun selectSpinner(values:List<String>)=Spinner(activity).apply{
            adapter=object:ArrayAdapter<String>(activity,android.R.layout.simple_spinner_item,values){
                override fun getView(position:Int,convertView:View?,parent:ViewGroup):View{
                    val v=super.getView(position,convertView,parent) as TextView
                    v.textSize=11.2f;v.setTextColor(navy);v.typeface=Typeface.DEFAULT_BOLD;v.gravity=Gravity.CENTER_VERTICAL
                    v.setPadding(dp(8),0,dp(24),0);v.minHeight=dp(36);return v
                }
                override fun getDropDownView(position:Int,convertView:View?,parent:ViewGroup):View{
                    val v=super.getDropDownView(position,convertView,parent) as TextView
                    v.textSize=11.2f;v.setTextColor(ink);v.typeface=Typeface.DEFAULT;v.gravity=Gravity.CENTER_VERTICAL
                    v.minHeight=dp(38);v.setPadding(dp(10),dp(5),dp(10),dp(5));return v
                }
            }
            minimumHeight=dp(36);background=drawable(Color.WHITE,Color.rgb(220,228,226),10)
        }
        fun labelledSelect(label:String,spinner:Spinner)=column().apply{
            addView(text(label.uppercase(),9.2f,muted,true).apply{letterSpacing=.025f;setPadding(dp(2),0,dp(2),0)})
            addView(gap(2));addView(spinner,LinearLayout.LayoutParams(-1,dp(36)))
        }
        fun safe(v:String)=v.trim().takeUnless{it.isBlank()||it.equals("null",true)}?:"-"
        fun fmtDate(v:String)=runCatching{LocalDate.parse(v).format(DateTimeFormatter.ofPattern("dd/MM/yyyy"))}.getOrDefault(safe(v))
        fun fmtTime(v:String):String{
            val clean=safe(v);if(clean=="-")return "-"
            return runCatching{Instant.parse(clean).atZone(ZoneId.of(TZ)).format(DateTimeFormatter.ofPattern("HH:mm"))}.getOrElse{Regex("""\b\d{2}:\d{2}\b""").find(clean)?.value?:"-"}
        }
        fun nowIso()=Instant.now().toString()
        fun today()=LocalDate.now(ZoneId.of(TZ))
        fun effectiveStatus(item:JSONObject):String{
            val raw=item.optString("status_view").ifBlank{item.optString("status")}
            if(raw=="OVERDUE_LATE")return raw
            if(raw=="LATE_EXPECTED"&&item.optString("actual_return_at").isBlank()){
                val expected=item.optString("expected_return_at")
                if(expected.isNotBlank()&&runCatching{Instant.parse(expected).toEpochMilli()<=System.currentTimeMillis()}.getOrDefault(false))return "OVERDUE_LATE"
            }
            return raw
        }
        fun statusLabel(item:JSONObject):String{
            return when(effectiveStatus(item)){
                "OVERDUE_LATE"->"QUÁ GIỜ VÀO MUỘN"
                "PENDING"->"Chưa điểm danh"
                "CHECKED_IN"->"Đã điểm danh"
                "NO_RETURN"->"Không vào ca"
                "LATE_EXPECTED"->"Vào muộn — dự kiến ${fmtTime(item.optString("expected_return_at"))}"
                else->item.optString("status").ifBlank{"Chưa điểm danh"}
            }
        }
        fun statusColor(item:JSONObject)=when(effectiveStatus(item)){
            "OVERDUE_LATE"->red;"PENDING"->orange;"CHECKED_IN"->green;"NO_RETURN"->muted;"LATE_EXPECTED"->teal;else->muted
        }

        val store=MealAttendanceLocalStore(activity)
        store.prune()
        val root=column()
        val controls=column().apply{setPadding(dp(10),dp(8),dp(10),dp(6))}
        val dateBtn=button("",navy).apply{textSize=10.5f}
        val search=input("Tìm MNV / họ tên").apply{textSize=11.5f}
        val dateSearch=row()
        dateSearch.addView(dateBtn,LinearLayout.LayoutParams(0,dp(44),.46f).apply{marginEnd=dp(3)})
        dateSearch.addView(search,LinearLayout.LayoutParams(0,dp(44),.54f).apply{marginStart=dp(3)})
        controls.addView(dateSearch,LinearLayout.LayoutParams(-1,dp(44)));controls.addView(gap(7))
        val scanBox=column().apply{setPadding(dp(7),dp(6),dp(7),dp(7));background=drawable(Color.rgb(240,253,250),teal,12)}
        scanBox.addView(text("QUÉT ĐỂ ĐIỂM DANH",10.2f,teal,true));scanBox.addView(gap(3))
        val scan=input("Scan / Nhập mã nhân viên").apply{background=drawable(Color.WHITE,teal,10)}
        scanBox.addView(scan,LinearLayout.LayoutParams(-1,dp(46)))
        controls.addView(scanBox,LinearLayout.LayoutParams(-1,-2));controls.addView(gap(7))
        val shiftFilter=selectSpinner(listOf("Tất cả ca"))
        val supplierFilter=selectSpinner(listOf("Tất cả NCC"))
        val positionFilter=selectSpinner(listOf("Tất cả vị trí"))
        val filterRow=row()
        filterRow.addView(shiftFilter,LinearLayout.LayoutParams(0,dp(36),1f).apply{marginEnd=dp(2)})
        filterRow.addView(supplierFilter,LinearLayout.LayoutParams(0,dp(36),1f).apply{marginStart=dp(2);marginEnd=dp(2)})
        filterRow.addView(positionFilter,LinearLayout.LayoutParams(0,dp(36),1f).apply{marginStart=dp(2)})
        controls.addView(filterRow,LinearLayout.LayoutParams(-1,dp(36)))
        root.addView(controls,LinearLayout.LayoutParams(-1,-2))

        val contentBox=column().apply{setPadding(dp(10),dp(2),dp(10),dp(78))}
        val scroll=ScrollView(activity).apply{addView(contentBox,ViewGroup.LayoutParams(-1,-2))}
        root.addView(scroll,LinearLayout.LayoutParams(-1,0,1f))

        val main=Handler(Looper.getMainLooper())
        var selected=today()
        var payload:JSONObject?=null
        var loadGeneration=0L
        var availableDates=store.availableDatesWithData()
        var filterSync=false
        var filterSignature=""
        var renderGeneration=0L
        var searchRenderRunnable:Runnable?=null
        lateinit var showReasonDialog:(JSONObject)->Unit

        fun employeePosition(item:JSONObject):String{
            val mnv=item.optString("mnv")
            return MasterDataCache.employee(activity,mnv)?.optString("main_position").orEmpty().ifBlank{item.optString("position_snapshot")}
        }
        fun setFilterValues(sp:Spinner,values:List<String>){
            val old=sp.selectedItem?.toString().orEmpty()
            sp.adapter=object:ArrayAdapter<String>(activity,android.R.layout.simple_spinner_item,values){
                override fun getView(position:Int,convertView:View?,parent:ViewGroup):View{
                    val v=super.getView(position,convertView,parent) as TextView
                    v.textSize=11.2f;v.setTextColor(navy);v.typeface=Typeface.DEFAULT_BOLD;v.gravity=Gravity.CENTER_VERTICAL;v.setPadding(dp(8),0,dp(22),0);v.minHeight=dp(36);return v
                }
                override fun getDropDownView(position:Int,convertView:View?,parent:ViewGroup):View{
                    val v=super.getDropDownView(position,convertView,parent) as TextView
                    v.textSize=11.2f;v.setTextColor(ink);v.gravity=Gravity.CENTER_VERTICAL;v.minHeight=dp(38);v.setPadding(dp(10),dp(5),dp(10),dp(5));return v
                }
            }
            sp.setSelection(values.indexOf(old).takeIf{it>=0}?:0,false)
        }
        fun refreshFilterOptions(rows:List<JSONObject>){
            val shifts=listOf("Tất cả ca")+rows.map{it.optString("shift")}.filter{it.isNotBlank()}.distinct()
            val suppliers=listOf("Tất cả NCC")+rows.map{it.optString("supplier_snapshot")}.filter{it.isNotBlank()}.distinct().sorted()
            val positions=listOf("Tất cả vị trí")+rows.map{employeePosition(it)}.filter{it.isNotBlank()}.distinct().sorted()
            val signature=(shifts+listOf("|") + suppliers+listOf("|")+positions).joinToString("\u001f")
            if(signature==filterSignature)return
            filterSignature=signature;filterSync=true
            setFilterValues(shiftFilter,shifts);setFilterValues(supplierFilter,suppliers);setFilterValues(positionFilter,positions)
            filterSync=false
        }

        fun applyAvailableDates(remote:List<String> = emptyList()){
            availableDates=(remote+store.availableDatesWithData()+today().toString())
                .filter{it.matches(Regex("\\d{4}-\\d{2}-\\d{2}"))}
                .distinct().sortedDescending()
            dateBtn.isEnabled=true
            dateBtn.alpha=1f
        }
        fun refreshAvailableDates(){
            api.call("meal_attendance_dates"){r->activity.runOnUiThread{
                if(!r.ok||r.json==null){applyAvailableDates();return@runOnUiThread}
                val a=r.json.optJSONArray("dates")?:JSONArray()
                val remote=mutableListOf<String>()
                for(i in 0 until a.length())a.optString(i).takeIf{it.isNotBlank()}?.let{remote+=it}
                applyAvailableDates(remote)
            }}
        }

        fun itemList(source:JSONObject?):MutableList<JSONObject>{
            val a=source?.optJSONArray("items")?:JSONArray();val out=mutableListOf<JSONObject>()
            for(i in 0 until a.length())a.optJSONObject(i)?.let{out+=JSONObject(it.toString())}
            return out
        }

        fun localAlert(source:JSONObject):JSONObject{
            val now=java.time.ZonedDateTime.now(ZoneId.of(TZ));val minutes=now.hour*60+now.minute
            val unresolved=mutableListOf<String>();var severe=false
            for(x in itemList(source)){
                val shift=x.optString("shift");val st=effectiveStatus(x)
                val shiftDue=(shift in setOf("Ca 1","Ca HC")&&minutes>=12*60)||(shift=="Ca 2"&&minutes>=19*60)
                if(!shiftDue)continue
                val unresolvedNow=st=="PENDING"||st=="OVERDUE_LATE"||(st=="LATE_EXPECTED"&&x.optString("expected_return_at").let{it.isNotBlank()&&runCatching{Instant.parse(it).toEpochMilli()<=System.currentTimeMillis()}.getOrDefault(false)})
                if(unresolvedNow){unresolved+=x.optString("mnv");if(st=="OVERDUE_LATE"||(shift in setOf("Ca 1","Ca HC")&&minutes>=12*60+30)||(shift=="Ca 2"&&minutes>=19*60+30))severe=true}
            }
            return JSONObject().put("severity",if(unresolved.isEmpty())"NONE" else if(severe)"SEVERE" else "WARNING").put("unresolved_count",unresolved.size).put("unresolved_mnvs",JSONArray(unresolved))
        }

        fun render(){
            val generation=++renderGeneration
            val source=payload
            contentBox.removeAllViews()
            if(source==null){contentBox.addView(text("Đang tải dữ liệu điểm danh…",11f,muted,false));return}
            val alert=localAlert(source);val severity=alert.optString("severity");val unresolved=alert.optInt("unresolved_count",0)
            if(selected==today()&&severity!="NONE"&&unresolved>0){
                val ids=alert.optJSONArray("unresolved_mnvs")?:JSONArray()
                val preview=(0 until minOf(ids.length(),8)).map{ids.optString(it)}.filter{it.isNotBlank()}.joinToString(", ")
                val message=if(severity=="SEVERE")"Cần xử lý ngay: $unresolved nhân sự chưa hoàn tất điểm danh." else "Còn $unresolved nhân sự cần điểm danh."
                val banner=column().apply{setPadding(dp(10),dp(8),dp(10),dp(8));background=drawable(if(severity=="SEVERE")Color.rgb(255,240,240) else Color.rgb(255,248,230),if(severity=="SEVERE")red else orange)}
                banner.addView(text(message,11f,if(severity=="SEVERE")red else orange,true));if(preview.isNotBlank())banner.addView(text(preview,9.5f,ink,false))
                contentBox.addView(banner,LinearLayout.LayoutParams(-1,-2));contentBox.addView(gap(7))
            }
            val allRows=itemList(source);refreshFilterOptions(allRows)
            val q=search.text.toString().trim().lowercase()
            val sf=shiftFilter.selectedItem?.toString().orEmpty();val nf=supplierFilter.selectedItem?.toString().orEmpty();val pf=positionFilter.selectedItem?.toString().orEmpty()
            val rows=allRows.filter{item->
                val mnv=item.optString("mnv");val name=item.optString("full_name_snapshot")
                (q.isBlank()||mnv.lowercase().contains(q)||name.lowercase().contains(q))&&
                (sf=="Tất cả ca"||item.optString("shift")==sf)&&
                (nf=="Tất cả NCC"||item.optString("supplier_snapshot")==nf)&&
                (pf=="Tất cả vị trí"||employeePosition(item)==pf)
            }
            if(rows.isEmpty()){contentBox.addView(text(if(allRows.isEmpty())"Không có nhân sự cần điểm danh trong ngày ${fmtDate(selected.toString())}." else "Không có nhân sự phù hợp bộ lọc.",11f,muted,false));return}
            fun addChunk(startIndex:Int){
                if(generation!=renderGeneration||!contentBox.isAttachedToWindow)return
                val endIndex=minOf(startIndex+24,rows.size)
                for(index in startIndex until endIndex){
                    val item=rows[index]
                    val card=column().apply{setPadding(dp(10),dp(7),dp(10),dp(7));background=drawable()}
                    val titleRow=row()
                    titleRow.addView(text("${safe(item.optString("supplier_snapshot"))} • ${safe(item.optString("mnv"))} • ${safe(item.optString("full_name_snapshot"))}",10.2f,ink,true),LinearLayout.LayoutParams(0,-2,1f))
                    titleRow.addView(text(statusLabel(item),9.2f,statusColor(item),true),LinearLayout.LayoutParams(-2,-2));card.addView(titleRow)
                    val actual=fmtTime(item.optString("actual_return_at").ifBlank{item.optString("checked_at")});val reason=item.optString("reason_code");val details=mutableListOf<String>()
                    if(actual!="-")details+="Thực tế $actual";safe(reason).takeIf{it!="-" }?.let{details+="Lý do: $it"};safe(item.optString("reason_note")).takeIf{it!="-" }?.let{details+="Ghi chú: $it"};safe(item.optString("expected_return_at")).takeIf{it!="-" }?.let{details+="Dự kiến ${fmtTime(it)}"}
                    card.addView(gap(3));card.addView(text("Ca ${safe(item.optString("shift"))} • ${if(details.isEmpty())"-" else details.joinToString(" • ")}",9f,muted,false))
                    if(selected==today()&&item.optString("status")!="CHECKED_IN"){card.addView(gap(5));val act=button(if(item.optString("status")=="LATE_EXPECTED")"CẬP NHẬT / SỬA GIỜ" else "XỬ LÝ",teal);act.setOnClickListener{showReasonDialog(item)};card.addView(act,LinearLayout.LayoutParams(-1,dp(36)))}
                    contentBox.addView(card,LinearLayout.LayoutParams(-1,-2));contentBox.addView(gap(5))
                }
                if(endIndex<rows.size)contentBox.post{addChunk(endIndex)}
            }
            contentBox.post{addChunk(0)}
        }

        fun remoteLoad(){
            val date=selected.toString();val generation=++loadGeneration
            api.call("meal_attendance_list",JSONObject().put("business_date",date)){r->activity.runOnUiThread{
                if(generation!=loadGeneration||selected.toString()!=date)return@runOnUiThread
                if(r.ok&&r.json!=null){payload=JSONObject(r.json.toString());store.save(payload!!);applyAvailableDates(availableDates);render()}
                else if(payload==null){payload=store.load(date);render();TopNotice.show(activity,r.error?:"Chưa tải được dữ liệu điểm danh.",TopNotice.Kind.WARNING)}
            }}
        }

        fun load(date:LocalDate){
            selected=date;activeDate=date.toString();dateBtn.text="Ngày ${fmtDate(date.toString())}"
            val current=date==today();scanBox.visibility=if(current)View.VISIBLE else View.GONE
            payload=store.load(date.toString());render();remoteLoad()
        }

        fun optimisticCheckin(mnvRaw:String){
            val mnv=MasterDataCache.resolveEmployeeMnv(activity,mnvRaw)
            if(mnv.isBlank()){TopNotice.show(activity,"Mã nhân viên không hợp lệ.",TopNotice.Kind.WARNING);return}
            val date=selected.toString()
            if(selected!=today()){TopNotice.show(activity,"Ngày lịch sử chỉ được xem.",TopNotice.Kind.WARNING);return}
            val ctx=PdaLocalProjection.employeeContext(activity,mnv)
            val ses=ctx?.optJSONObject("session")
            val exactCurrentActive=ctx!=null&&ctx.optString("state").equals("ACTIVE",true)&&
                ses!=null&&ses.optString("state").equals("ACTIVE",true)&&ses.optString("business_date")==date
            if(!exactCurrentActive){
                TopNotice.show(activity,"Nhân sự không có phiên đang hoạt động trong ngày.",TopNotice.Kind.WARNING);remoteLoad();return
            }
            var item=itemList(payload).firstOrNull{it.optString("mnv")==mnv}
            if(item==null){
                val emp=ctx!!.optJSONObject("employee")?:JSONObject();val activeSession=ses!!
                item=JSONObject().put("business_date",date).put("mnv",mnv).put("shift",activeSession.optString("shift"))
                    .put("full_name_snapshot",emp.optString("full_name")).put("supplier_snapshot",emp.optString("supplier"))
                    .put("status","PENDING").put("status_view","PENDING")
                store.addProvisional(date,item);payload=store.load(date)
            }
            if(item.optString("status")=="CHECKED_IN"){
                TopNotice.show(activity,"Nhân sự đã điểm danh lúc ${fmtTime(item.optString("actual_return_at").ifBlank{item.optString("checked_at")})}.",TopNotice.Kind.INFO);return
            }
            val at=nowIso()
            store.updateItem(date,mnv){x->x.put("status","CHECKED_IN").put("status_view","CHECKED_IN").put("checked_at",at).put("actual_return_at",at)}
            payload=store.load(date);render();scan.setText("")
            val id=UUID.randomUUID().toString()
            api.call("meal_checkin",JSONObject().put("mnv",mnv).put("event_id",id).put("timestamp",at)){r->activity.runOnUiThread{
                if(!r.ok){
                    remoteLoad()
                    val msg=if(r.error=="MEAL_EMPLOYEE_NOT_ACTIVE")"Nhân sự không còn phiên đang hoạt động trong ngày; trạng thái đã được làm mới."
                        else r.error?:"Chưa ghi được điểm danh; đang làm mới dữ liệu xác nhận."
                    TopNotice.show(activity,msg,TopNotice.Kind.WARNING)
                }else TopNotice.show(activity,"Đã ghi nhận điểm danh.",TopNotice.Kind.SUCCESS)
            }}
        }

        fun applyReason(item:JSONObject,reason:String,note:String,expectedIso:String){
            val mnv=item.optString("mnv");val status=if(reason=="Xin vào muộn")"LATE_EXPECTED" else "NO_RETURN"
            store.updateItem(selected.toString(),mnv){x->
                x.put("status",status).put("status_view",status).put("reason_code",reason).put("reason_note",note)
                if(expectedIso.isNotBlank())x.put("expected_return_at",expectedIso) else x.remove("expected_return_at")
            }
            payload=store.load(selected.toString());render()
            val id=UUID.randomUUID().toString()
            val body=JSONObject().put("mnv",mnv).put("status",status).put("reason_code",reason).put("reason_note",note).put("event_id",id)
            if(expectedIso.isNotBlank())body.put("expected_return_at",expectedIso)
            api.call("meal_status",body){r->activity.runOnUiThread{
                if(!r.ok)TopNotice.show(activity,r.error?:"Chưa ghi được trạng thái; dữ liệu đang chờ đồng bộ.",TopNotice.Kind.WARNING)
                else TopNotice.show(activity,"Đã cập nhật trạng thái.",TopNotice.Kind.SUCCESS)
            }}
        }

        fun askExpected(item:JSONObject,reason:String,note:String){
            val z=java.time.ZonedDateTime.now(ZoneId.of(TZ))
            TimePickerDialog(activity,{_,hour,minute->
                val local=LocalDateTime.of(selected,java.time.LocalTime.of(hour,minute))
                val instant=local.atZone(ZoneId.of(TZ)).toInstant().toString()
                applyReason(item,reason,note,instant)
            },z.hour,z.minute,true).show()
        }

        showReasonDialog={item->
            if(selected!=today()){
                TopNotice.show(activity,"Ngày lịch sử chỉ được xem.",TopNotice.Kind.INFO)
            }else{
                val reasons=listOf("Xin về sớm","Đi hỗ trợ bộ phận/vị trí khác","Xin vào muộn","Nghỉ đột xuất","Có việc cá nhân","Được quản lý điều chuyển","Khác")
                val reasonSpinner=selectSpinner(reasons)
                val box=column().apply{setPadding(dp(10),dp(5),dp(10),dp(8));addView(labelledSelect("Lý do không vào ca",reasonSpinner))}
                val d=AlertDialog.Builder(activity).setTitle("Xử lý ${item.optString("mnv")}").setView(box).setNegativeButton("Hủy",null).setPositiveButton("TIẾP TỤC",null).create()
                d.setOnShowListener{d.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener{
                    val reason=reasonSpinner.selectedItem?.toString().orEmpty();if(reason.isBlank())return@setOnClickListener
                    d.dismiss()
                    if(reason=="Khác"){
                        val note=input("Nhập lý do")
                        val other=AlertDialog.Builder(activity).setTitle("Lý do khác").setView(note).setNegativeButton("Hủy",null).setPositiveButton("LƯU",null).create()
                        other.setOnShowListener{other.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener{
                            val v=note.text.toString().trim();if(v.isBlank()){TopNotice.show(activity,"Phải nhập lý do.",TopNotice.Kind.WARNING);return@setOnClickListener}
                            other.dismiss();applyReason(item,reason,v,"")
                        }};other.show()
                    }else if(reason=="Xin vào muộn")askExpected(item,reason,"")
                    else applyReason(item,reason,"","")
                }};d.show()
            }
        }

        search.addTextChangedListener(object:android.text.TextWatcher{
            override fun beforeTextChanged(s:CharSequence?,start:Int,count:Int,after:Int)=Unit
            override fun onTextChanged(s:CharSequence?,start:Int,before:Int,count:Int){
                searchRenderRunnable?.let{main.removeCallbacks(it)}
                searchRenderRunnable=Runnable{render()}.also{main.postDelayed(it,140L)}
            }
            override fun afterTextChanged(s:android.text.Editable?)=Unit
        })
        val filterListener=object:android.widget.AdapterView.OnItemSelectedListener{
            override fun onItemSelected(p:android.widget.AdapterView<*>?,v:View?,pos:Int,id:Long){if(!filterSync)render()}
            override fun onNothingSelected(p:android.widget.AdapterView<*>?)=Unit
        }
        shiftFilter.onItemSelectedListener=filterListener;supplierFilter.onItemSelectedListener=filterListener;positionFilter.onItemSelectedListener=filterListener

        dateBtn.setOnClickListener{
            DataDatePickerUi.show(activity,availableDates,selected.toString()){chosen->
                runCatching{LocalDate.parse(chosen)}.getOrNull()?.let{load(it)}
            }
        }
        fun submit(){val v=scan.text.toString().trim();if(v.isBlank()){TopNotice.show(activity,"Nhập hoặc quét mã nhân viên.",TopNotice.Kind.WARNING);return};optimisticCheckin(v)}
        scan.setOnEditorActionListener{_,id,_->if(id==EditorInfo.IME_ACTION_DONE||id==EditorInfo.IME_ACTION_GO||id==EditorInfo.IME_ACTION_SEARCH){submit();true}else false}
        scan.setOnKeyListener{_,key,event->if(key==KeyEvent.KEYCODE_ENTER&&event.action==KeyEvent.ACTION_UP){submit();true}else false}

        fun scheduleBoundary(){
            main.removeCallbacksAndMessages(null)
            val z=java.time.ZonedDateTime.now(ZoneId.of(TZ))
            val day=z.toLocalDate()
            val points=mutableListOf<java.time.ZonedDateTime>()
            for(n in listOf(12*60,12*60+30,19*60,19*60+30)){
                val p=day.atTime(n/60,n%60).atZone(ZoneId.of(TZ))
                if(p.isAfter(z))points+=p
            }
            points+=day.plusDays(1).atStartOfDay(ZoneId.of(TZ))
            val next=points.minByOrNull{it.toInstant()}!!
            val delay=java.time.Duration.between(z,next).toMillis().coerceAtLeast(1_000L)
            main.postDelayed({
                val nowDay=today()
                if(selected.isBefore(nowDay))load(nowDay) else {render();remoteLoad()}
                scheduleBoundary()
            },delay)
        }

        activeRefresh={activity.runOnUiThread{if(activeDate==selected.toString())remoteLoad()}}
        applyAvailableDates();load(selected);refreshAvailableDates();scheduleBoundary()
        root.addOnAttachStateChangeListener(object:View.OnAttachStateChangeListener{
            override fun onViewAttachedToWindow(v:View)=Unit
            override fun onViewDetachedFromWindow(v:View){main.removeCallbacksAndMessages(null);if(activeDate==selected.toString())leave()}
        })
        return root
    }
}

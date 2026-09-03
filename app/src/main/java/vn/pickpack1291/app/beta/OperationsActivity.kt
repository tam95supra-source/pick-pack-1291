package vn.pickpack1291.app.beta

// S11_COMPACT_REPORT_PATCH: compact inner screens and bordered shift reports.

// S10_GENERATED_UI_PATCH: PDA visual/UX corrections for Beta 0.4.2-beta.10.

import android.app.Activity
import android.app.AlertDialog
import android.content.res.ColorStateList
import android.content.Intent
import android.graphics.Bitmap
import android.graphics.Color
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.graphics.drawable.ColorDrawable
import android.net.Uri
import android.provider.MediaStore
import android.os.Build
import android.os.Bundle
import android.text.InputType
import android.text.Editable
import android.text.TextWatcher
import android.text.method.DigitsKeyListener
import android.view.KeyEvent
import android.view.Gravity
import android.view.View
import android.view.ViewGroup
import android.view.WindowInsets
import android.view.inputmethod.EditorInfo
import android.widget.*
import com.google.zxing.BarcodeFormat
import com.google.zxing.qrcode.QRCodeWriter
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.time.Instant
import java.time.ZoneId
import java.time.format.DateTimeFormatter
import java.util.UUID

class OperationsActivity : Activity() {
    // S61_BETA60_OWNER_OPS_RESOURCE_FIX
    // S60_BETA59_OWNER_ATTENDANCE_UI
    // S57_BETA54_OWNER_RESILIENCE_FIX
    // S56_BETA53_OWNER_UI_STATUS_FIX
    // S55_BETA51_OWNER_REFRESH_HISTORY_FIX
    // S54_BETA48_OWNER_10_FIXES
    // S31_SERVICE_FIRST_HOTPATH
    // S29_OWNER_LOCALFIRST_HISTORY
    // S25_CACHE_FIRST_FALLBACK_SYNC
    // S22_PDA_LOCAL_FIRST_OBSERVABILITY
    private val navy:Int get()=ThemeManager.primaryDark(this)
    private val blue:Int get()=ThemeManager.primary(this)
    private val red = Color.rgb(218,45,53)
    private val green = Color.rgb(36,153,85)
    private val orange = Color.rgb(217,119,6)
    private val teal:Int get()=ThemeManager.primary(this)
    private val accent:Int get()=ThemeManager.accent(this)
    private val bg:Int get()=Color.WHITE
    private val surface = Color.WHITE
    private val ink = Color.rgb(24,44,42)
    private val muted = Color.rgb(100,116,139)
    private val line:Int get()=Color.argb(72,Color.red(teal),Color.green(teal),Color.blue(teal))
    private val api by lazy { BetaApiClient(applicationContext) }
    private val syncApi by lazy { BetaApiClient(applicationContext) }
    private val cacheApi by lazy { BetaApiClient(applicationContext) }
    private val operationalStore by lazy { OperationalDataStore(applicationContext) }
    private val operationalSync by lazy {
        OperationalSyncEngine(this, cacheApi, operationalStore) { changedDates ->
            runOnUiThread {
                if (changedDates.isEmpty()) return@runOnUiThread
                when (screenState) {
                    "BUSINESS" -> businessRealtimeRefresh?.invoke(changedDates)
                    "REPORT" -> reportRealtimeRefresh?.invoke(changedDates)
                    "HISTORY" -> historyRealtimeRefresh?.invoke(changedDates)
                    "EMPLOYEE" -> employeeTimelineRealtimeRefresh?.invoke(changedDates) // Timeline only; never rebuild the interactive employee form.
                    "MEAL_ATTENDANCE" -> PostMealAttendanceFeature.onRealtime(changedDates)
                    "EMPLOYEE_LOADING", "PDA_EXCHANGE" -> Unit
                }
            }
        }
    }
    private lateinit var module: String
    private lateinit var login: String
    private lateinit var name: String
    private lateinit var role: String
    private var effectiveRole = "" // S47_BETA41_OWNER_FIVE_FIXES
    // S47B_BETA41_COMPILE_HOTFIX
    private var position = ""
    private var email = ""
    private var initialMnv = ""
    private var screenState = "ROOT"
    private var networkStatusText: TextView? = null
    private var syncStatusText: TextView? = null
    private var serviceStatusText: TextView? = null
    private var lastConnected: Boolean? = null
    private var lastSyncLatencyMs: Long? = null // S33_OWNER_UI_SYNC_RESOURCES
    private var lastProjectionPending: Int = 0
    private var lastReplicationState:String = ""
    private var lastReplicationPending:Int = 0
    private var lastReplicationSuccessAt:String = ""
    private var historySyncInFlight=false // S35_OWNER_UI_HISTORY_CONSISTENCY
    private var historyLastCanonicalRefreshAt=0L
    private var manualRefreshInFlight=false
    private var resilienceTestInFlight=false
    private var resilienceTestStopping=false
    private var lastLatencyMs: Long? = null
    private var lastSyncE2eMs: Long? = null
    private var serviceProviderCache = "—"
    private var historyDetailMnv = ""
    private var historyDetailName = ""
    // Beta86: keep realtime event-driven and update only the data region that changed.
    private var businessRealtimeRefresh: ((Set<String>) -> Unit)? = null
    private var listsRealtimeRefresh: (() -> Unit)? = null
    private var reportRealtimeRefresh: ((Set<String>) -> Unit)? = null
    private var historyRealtimeRefresh: ((Set<String>) -> Unit)? = null
    private var employeeTimelineRealtimeRefresh: ((Set<String>) -> Unit)? = null
    private var lastPingMs: Long? = null
    private var lastStatusUpdateAt: Long = 0L
    private var lanSevereWarningShown=false
    private val lanStateListener=LanCoordinator.StateListener { state ->
        runOnUiThread {
            refreshHeaderConnection()
            if(state==LanAuthorityPolicy.HealthState.NORMAL)lanSevereWarningShown=false
            if((state==LanAuthorityPolicy.HealthState.SERVICE_UNAVAILABLE||state==LanAuthorityPolicy.HealthState.LAN_AVAILABLE)&&!lanSevereWarningShown){
                lanSevereWarningShown=true
                TopNotice.show(this,"Dịch vụ đã gián đoạn trên 5 phút. ADMIN/SUPERADMIN cần kiểm tra và kích hoạt LAN dự phòng nếu vận hành vẫn tiếp tục.",TopNotice.Kind.ERROR)
            }
        }
    }
    private var contentHost: FrameLayout? = null
    private var navHost: FrameLayout? = null
    private data class NavRefs(val cell:LinearLayout,val icon:ImageView,val label:TextView)
    private val navRefs=mutableMapOf<String,NavRefs>()
    private val tabHistory=java.util.ArrayDeque<String>()
    private data class ScreenSnapshot(val view:View,val module:String,val screenState:String,val initialMnv:String,val liveEmployeeMnv:String)
    private val screenBackStack=java.util.ArrayDeque<ScreenSnapshot>()
    private var displayedScreenState=""
    private var displayedModule=""
    private var displayedInitialMnv=""
    private var displayedLiveEmployeeMnv=""
    private var liveEmployeeMnv=""
    private var documentController:DocumentManagementFeature.Controller?=null
    private var documentCameraUri:Uri?=null
    private var documentCameraFile:File?=null
    private val documentCameraRequestCode=7101
    private val documentGalleryRequestCode=7102
    private var employeeLookupGeneration=0L // S39_EMPLOYEE_SESSION_HISTORY
    private val exitInFlightMnvs=mutableSetOf<String>() // Beta93: one exit flow per employee across rerenders/resolution.
    private var lastEmployeeRenderSignature="" // Beta74: suppress identical employee full-tree rebuilds.
    private val foregroundSync by lazy {
        ForegroundSyncCoordinator(this, syncApi, object : ForegroundSyncCoordinator.Listener {
            override fun onStatus(status: ForegroundSyncCoordinator.Status) {
                lastConnected = status.connected
                lastSyncLatencyMs = status.latencyMs
                lastProjectionPending = status.projectionPending.coerceAtLeast(0)
                lastReplicationState = status.replicationState
                lastReplicationPending = status.replicationPending.coerceAtLeast(0)
                lastReplicationSuccessAt = status.replicationLastSuccessAt
                lastLatencyMs = status.latencyMs
                lastSyncE2eMs = status.syncE2eMs
                serviceProviderCache = serviceProviderFromRuntime()
                lastPingMs = status.latencyMs
                lastStatusUpdateAt = System.currentTimeMillis()
                refreshHeaderConnection()
                if(status.connected && status.businessDate.isNotBlank()) {
                    val localFloor=status.retentionFloor.ifBlank{
                        runCatching{java.time.LocalDate.parse(status.businessDate).minusDays(44).toString()}.getOrDefault("")
                    }
                    if(localFloor.isNotBlank()) operationalSync.reconcile(status.businessDate,localFloor,status.retentionEpoch,status.dayRevisions)
                }
                if(status.masterChanged || status.masterRevision != MasterDataCache.revision(this@OperationsActivity)) refreshMasterCache()
                if (!status.connected || !status.changed) return
                if (screenState=="HISTORY") { historyLastCanonicalRefreshAt=0L; refreshHistoryCanonical() }
                if (module=="BUSINESS" && liveEmployeeMnv.isNotBlank()) return
                // Service-backed list can refresh its result box immediately. Local-projection screens
                // wait for OperationalSyncEngine to commit the new revision, then update in place.
                if (screenState=="LISTS") listsRealtimeRefresh?.invoke()
            }

            override fun onAuthExpired() { api.clearSession(); finishAffinity() }
        })
    }

    override fun onCreate(state: Bundle?) {
        super.onCreate(state)
        window.statusBarColor = ThemeManager.primaryDark(this)
        window.navigationBarColor = Color.WHITE
        @Suppress("DEPRECATION")
        window.decorView.systemUiVisibility = View.SYSTEM_UI_FLAG_LIGHT_NAVIGATION_BAR
        module = intent.getStringExtra("module") ?: "BUSINESS"
        login = intent.getStringExtra("login") ?: ""
        name = intent.getStringExtra("name") ?: login
        role = intent.getStringExtra("role") ?: "USER"
        effectiveRole = role
        position = intent.getStringExtra("position") ?: ""
        email = intent.getStringExtra("email") ?: api.restoredAccount()?.optString("email").orEmpty()
        initialMnv = intent.getStringExtra("mnv") ?: ""
        if (api.token == null) { finish(); return }
        installSystemBackHandler()
        when(module){
            "BUSINESS"->businessHome()
            "LABOR"->{module="BUSINESS";laborHome()}
            "RESOURCES"->{module="BUSINESS";resourceHome()}
            "REPORT"->{module="BUSINESS";reportScreen()}
            "LISTS"->{module="BUSINESS";listsScreen()}
            "SETTINGS"->settingsScreen()
            "STAFF"->staffScreen()
            "HISTORY"->historyScreen()
            "SYNC"->syncScreen()
            "PDA_EXCHANGE"->pdaExchangeScreen()
            else->{module="BUSINESS";businessHome()}
        }
    }

    override fun onStart() {
        super.onStart()
        UpdateManager.checkAutomatic(this)
        PpForegroundGate.enter()
        LanCoordinator.get(this).addStateListener(lanStateListener)
        if (api.token != null) {
            // S43_FOREGROUND_OUTBOX_WAKE: old unresolved events are flushed immediately on a
            // background executor after the activity becomes visible. No polling and no UI wait.
            if (runCatching { OperationalDataStore(this).pendingMutationCount() }.getOrDefault(0) > 0) {
                M2ImmediateOutbox.kick(this)
            }
            foregroundSync.start()
        }
    }

    override fun onStop() {
        LanCoordinator.get(this).removeStateListener(lanStateListener)
        PpForegroundGate.leave()
        foregroundSync.stop()
        super.onStop()
    }

    private fun isAdmin() = effectiveRole == "ADMIN" || effectiveRole == "SUPERADMIN"

    private fun isSuper() = effectiveRole == "SUPERADMIN"
    private fun isActualSuper() = role == "SUPERADMIN"

    private fun businessHome(){
        documentController?.dispose();documentController=null
        PostMealAttendanceFeature.leave()
        module="BUSINESS";screenState="BUSINESS"
        val root=baseRoot("NGHIỆP VỤ");val body=body().apply{setPadding(dp(8),dp(6),dp(8),dp(76))}
        val dynamic=column(bg)
        fun renderDynamic(){
            dynamic.suppressLayout(true)
            try {
                dynamic.removeAllViews()
                dynamic.addView(OldSessionWarningFeature.build(this,api){raw->openHistoricalSession(raw)},matchWrap())
                dynamic.addView(PostMealAttendanceFeature.buildHomeWarning(this,api){postMealAttendanceScreen()},matchWrap())
                if(isAdmin())dynamic.addView(laborOpenWarning(),matchWrap())
                addBusinessShiftReconciliation(dynamic)
            } finally { dynamic.suppressLayout(false) }
        }
        body.addView(dynamic,matchWrap())
        businessRealtimeRefresh={dates->
            val current=operationalStore.businessDate()
            if(screenState=="BUSINESS"&&(current.isBlank()||current in dates))renderDynamic()
        }
        renderDynamic()
        val cards=listOf(
            businessCard(R.drawable.ic_pp_scan,"Quét QR nhân sự","",true){employeeScan()},
            businessCard(R.drawable.ic_pp_attendance,"Điểm danh nhân sự","",true){postMealAttendanceScreen()},
            businessCard(R.drawable.ic_pp_pda_exchange,"Đổi / trả PDA","",true){pdaExchangeScreen()},
            businessCard(R.drawable.ic_pp_drop_receive,"Nhận hàng Rớt","",true){dropReceiveScreen()},
            businessCard(R.drawable.ic_pp_report,"Báo cáo nhân sự","",isAdmin()){reportScreen()},
            businessCard(R.drawable.ic_pp_task,"Công nhật","",isAdmin()){laborHome()},
            businessCard(R.drawable.ic_pp_resource,"Tài nguyên","",isAdmin()){resourceHome()},
            businessCard(R.drawable.ic_pp_ccdc,"Quản lý CCDC","",isAdmin()){TopNotice.show(this,"Quản lý CCDC đang được chuẩn bị.",TopNotice.Kind.INFO)},
            businessCard(R.drawable.ic_pp_document,"Quản lý biên bản","",isAdmin()){documentManagementScreen()}
        )
        body.addView(businessRow(cards[0],cards[1]));body.addView(gap(4))
        body.addView(businessRow(cards[2],cards[3]));body.addView(gap(4))
        body.addView(businessRow(cards[4],cards[5]));body.addView(gap(4))
        body.addView(businessRow(cards[6],cards[7]));body.addView(gap(4))
        body.addView(businessSingleRow(cards[8]))
        attach(root,body)
    }


    private fun laborOpenWarning():View{
        val host=ReviewAlertUi.warningContainer(this)
        val open=reconciliationButton("",false).apply{visibility=View.GONE;setOnClickListener{laborHome()}}
        host.addView(open,ReviewAlertUi.fixedHeightParams(this))
        api.call("labor_list",JSONObject().put("business_date",operationalStore.businessDate())){r->runOnUiThread{
            if(!r.ok)return@runOnUiThread
            val items=r.json?.optJSONArray("items")?:JSONArray();var count=0
            for(i in 0 until items.length())if(items.optJSONObject(i)?.optString("state")?.equals("OPEN",true)==true)count++
            if(count>0){open.text="CẢNH BÁO: $count CÔNG NHẬT CHƯA HOÀN THÀNH";open.visibility=View.VISIBLE;host.visibility=View.VISIBLE}
        }}
        return host
    }
    private fun postMealAttendanceScreen(){
        module="BUSINESS"
        screenState="MEAL_ATTENDANCE"
        val root=baseRoot("ĐIỂM DANH NHÂN SỰ")
        root.addView(PostMealAttendanceFeature.build(this,api){businessHome()},LinearLayout.LayoutParams(-1,0,1f))
        setScreen(root)
    }

    private fun dropReceiveScreen(){
        module="BUSINESS"
        screenState="DROP_RECEIVE"
        val root=baseRoot("NHẬN HÀNG RỚT")
        root.addView(DropReceiveFeature.build(this,api,login,name,role){businessHome()},LinearLayout.LayoutParams(-1,0,1f))
        setScreen(root)
    }

    private fun documentManagementScreen(){
        module="BUSINESS"
        screenState="DOCUMENT_MANAGEMENT"
        documentController?.dispose()
        val root=baseRoot("QUẢN LÝ BIÊN BẢN")
        documentController=DocumentManagementFeature.Controller(
            activity=this,
            api=api,
            login=login,
            displayName=name,
            actualRole=role,
            onCamera={launchDocumentCamera()},
            onGallery={launchDocumentGallery()},
            confirmAction={label,after->verifyActionPassword(label,after)}
        )
        root.addView(documentController!!.build(),LinearLayout.LayoutParams(-1,0,1f))
        setScreen(root)
    }

    private fun launchDocumentCamera(){
        if(screenState!="DOCUMENT_MANAGEMENT")return
        val dir=File(cacheDir,"document-capture").apply{mkdirs()}
        dir.listFiles()?.filter{System.currentTimeMillis()-it.lastModified()>24*60*60*1000L}?.forEach{runCatching{it.delete()}}
        val file=File(dir,"capture_${UUID.randomUUID()}.jpg")
        val uri=runCatching{androidx.core.content.FileProvider.getUriForFile(this,"${packageName}.fileprovider",file)}.getOrElse{
            showError("Không chuẩn bị được camera: ${it.message}");return
        }
        val intent=Intent(MediaStore.ACTION_IMAGE_CAPTURE).apply{
            putExtra(MediaStore.EXTRA_OUTPUT,uri)
            addFlags(Intent.FLAG_GRANT_WRITE_URI_PERMISSION or Intent.FLAG_GRANT_READ_URI_PERMISSION)
        }
        if(intent.resolveActivity(packageManager)==null){showError("Thiết bị không có ứng dụng camera phù hợp.");return}
        documentCameraUri=uri;documentCameraFile=file
        @Suppress("DEPRECATION")
        startActivityForResult(intent,documentCameraRequestCode)
    }

    private fun launchDocumentGallery(){
        if(screenState!="DOCUMENT_MANAGEMENT")return
        val intent=Intent(Intent.ACTION_OPEN_DOCUMENT).apply{
            addCategory(Intent.CATEGORY_OPENABLE)
            type="image/*"
            putExtra(Intent.EXTRA_ALLOW_MULTIPLE,true)
        }
        @Suppress("DEPRECATION")
        startActivityForResult(intent,documentGalleryRequestCode)
    }

    @Deprecated("Deprecated in Android framework; retained for API29-compatible document picker/camera flow.")
    override fun onActivityResult(requestCode:Int,resultCode:Int,data:Intent?){
        super.onActivityResult(requestCode,resultCode,data)
        if(resultCode!=Activity.RESULT_OK)return
        when(requestCode){
            documentCameraRequestCode->{
                val uri=documentCameraUri
                if(uri!=null)documentController?.onImageSelected(uri,"CAMERA")
                documentCameraUri=null;documentCameraFile=null
            }
            documentGalleryRequestCode->{
                val uris=mutableListOf<Uri>()
                data?.clipData?.let{clip->for(i in 0 until clip.itemCount)clip.getItemAt(i).uri?.let{uris.add(it)}}
                data?.data?.let{if(it !in uris)uris.add(it)}
                if(uris.isNotEmpty())documentController?.onImagesSelected(uris,"GALLERY")
            }
        }
    }

    // Current-day reconciliation: counts and list are always scoped to the real Asia/Ho_Chi_Minh calendar date.
    private fun businessDateVi(v:String):String=runCatching{java.time.LocalDate.parse(v.take(10)).format(DateTimeFormatter.ofPattern("dd/MM/yyyy"))}.getOrDefault(v.ifBlank{"-"})
    private fun compactAttendanceTime(v:String):String{
        val clean=dash(v)
        if(clean=="-")return "-"
        return runCatching{Instant.parse(v).atZone(ZoneId.of("Asia/Ho_Chi_Minh")).format(DateTimeFormatter.ofPattern("HH:mm"))}.getOrElse{
            Regex("""\b\d{2}:\d{2}\b""").find(v)?.value?:clean
        }
    }

    private data class ShiftStaffIdentity(
        val supplier:String,
        val mnv:String,
        val fullName:String,
        val position:String
    )
    private fun shiftStaffIdentity(ses:JSONObject):ShiftStaffIdentity{
        val mnv=ses.optString("mnv").trim()
        val emp=MasterDataCache.employee(this,mnv)
        val snap=ses.optJSONObject("employee_snapshot")
        fun cleanMasterText(v:String)=v.trim().takeUnless{it.equals("null",true)}.orEmpty()
        val supplier=cleanMasterText(emp?.optString("supplier").orEmpty()).ifBlank{cleanMasterText(snap?.optString("supplier").orEmpty())}
        val fullName=cleanMasterText(emp?.optString("full_name").orEmpty()).ifBlank{cleanMasterText(snap?.optString("full_name").orEmpty())}
        val position=cleanMasterText(emp?.optString("main_position").orEmpty()).ifBlank{cleanMasterText(snap?.optString("main_position").orEmpty())}
        return ShiftStaffIdentity(supplier,mnv,fullName,position)
    }
    private fun shiftStaffEnded(ses:JSONObject)=ses.optString("state").equals("ENDED",true)&&dash(ses.optString("exit_at"))!="-"
    private fun staffInitials(fullName:String,mnv:String):String{
        val words=fullName.trim().split(Regex("\\s+")).filter{it.isNotBlank()}
        val raw=when{
            words.size>=2->"${words.first().first()}${words.last().first()}"
            words.size==1->words.first().take(2)
            else->mnv.takeLast(2)
        }
        return raw.uppercase().ifBlank{"--"}
    }
    private fun shiftStaffOrdered(rows:List<JSONObject>):List<JSONObject>{
        val unique=rows.distinctBy{it.optString("session_id").ifBlank{"${it.optString("mnv")}|${it.optString("enter_at")}"}}
            .filter{dash(it.optString("enter_at"))!="-" }
        fun foldedOrLast(v:String)=foldLocal(v).ifBlank{"\uFFFF"}
        return unique.sortedWith(Comparator{a,b->
            val x=shiftStaffIdentity(a);val y=shiftStaffIdentity(b)
            val supplierCmp=foldedOrLast(x.supplier).compareTo(foldedOrLast(y.supplier))
            if(supplierCmp!=0)return@Comparator supplierCmp
            val mnvCmp=naturalUserCompare(x.mnv,y.mnv)
            if(mnvCmp!=0)return@Comparator mnvCmp
            foldedOrLast(x.fullName).compareTo(foldedOrLast(y.fullName))
        })
    }
    private fun showCurrentDayShiftStaff(date:String,shift:String,rows:List<JSONObject>,filter:String="ALL"){
        screenState="SHIFT_STAFF_LIST"
        val root=baseRoot("DANH SÁCH NHÂN SỰ THEO CA")
        val body=body()
        val clean=shiftStaffOrdered(rows)
        val endedCount=clean.count{shiftStaffEnded(it)}
        val activeCount=(clean.size-endedCount).coerceAtLeast(0)

        body.addView(txt("$shift • ${businessDateVi(date)}",11f,navy,true).apply{setPadding(dp(2),dp(2),dp(2),dp(7))})
        val filters=row(bg).apply{gravity=Gravity.CENTER_VERTICAL}
        fun chip(label:String,count:Int,key:String):TextView{
            val selected=filter==key
            return txt("$label ($count)",9.3f,if(selected)Color.WHITE else navy,true).apply{
                gravity=Gravity.CENTER
                setPadding(dp(4),0,dp(4),0)
                background=if(selected)round(teal,12) else outlineBg(surface,12)
                isClickable=true;isFocusable=true
                setOnClickListener{if(filter!=key)showCurrentDayShiftStaff(date,shift,rows,key)}
            }
        }
        listOf(Triple("Tất cả",clean.size,"ALL"),Triple("Trong ca",activeCount,"ACTIVE"),Triple("Đã ra ca",endedCount,"ENDED")).forEachIndexed{i,(label,count,key)->
            filters.addView(chip(label,count,key),LinearLayout.LayoutParams(0,dp(40),1f).apply{
                if(i>0)marginStart=dp(3)
                if(i<2)marginEnd=dp(3)
            })
        }
        body.addView(filters,matchWrap());body.addView(gap(8))

        val visible=when(filter){
            "ACTIVE"->clean.filterNot{shiftStaffEnded(it)}
            "ENDED"->clean.filter{shiftStaffEnded(it)}
            else->clean
        }
        if(visible.isEmpty()){
            body.addView(info("Không có nhân sự phù hợp bộ lọc trong $shift ngày ${businessDateVi(date)}."))
            attach(root,body);return
        }

        fun supplierKey(ses:JSONObject)=shiftStaffIdentity(ses).supplier.ifBlank{"Chưa xác định NCC"}
        val allGroups=clean.groupBy{supplierKey(it)}
        val visibleGroups=visible.groupBy{supplierKey(it)}
        visibleGroups.forEach{(supplier,groupRows)->
            val allGroup=allGroups[supplier].orEmpty()
            val groupEnded=allGroup.count{shiftStaffEnded(it)}
            val groupActive=(allGroup.size-groupEnded).coerceAtLeast(0)
            val box=column(surface).apply{background=outlineBg(surface,10)}
            val header=column(teal).apply{setPadding(dp(10),dp(7),dp(10),dp(7));background=round(teal,10)}
            val headerTop=row(teal).apply{gravity=Gravity.CENTER_VERTICAL}
            headerTop.addView(txt(supplier,12f,Color.WHITE,true),LinearLayout.LayoutParams(0,-2,1f))
            headerTop.addView(txt("${allGroup.size} người",9.4f,Color.WHITE,true))
            header.addView(headerTop,matchWrap())
            header.addView(txt("Trong ca $groupActive  •  Đã ra ca $groupEnded",8.8f,Color.WHITE,false))
            box.addView(header,matchWrap())

            groupRows.forEachIndexed{index,ses->
                val identity=shiftStaffIdentity(ses)
                val ended=shiftStaffEnded(ses)
                val item=row(surface).apply{
                    gravity=Gravity.CENTER_VERTICAL
                    setPadding(dp(8),dp(8),dp(8),dp(8))
                    isClickable=true;isFocusable=true
                    contentDescription="Mở quét QR vào ra ${dash(identity.fullName)}"
                    setOnClickListener{if(identity.mnv.isNotBlank())loadEmployee(identity.mnv)}
                }
                val initials=txt(staffInitials(identity.fullName,identity.mnv),10.5f,teal,true).apply{
                    gravity=Gravity.CENTER
                    background=GradientDrawable().apply{shape=GradientDrawable.OVAL;setColor(Color.rgb(232,247,238))}
                }
                item.addView(initials,LinearLayout.LayoutParams(dp(36),dp(36)).apply{marginEnd=dp(8)})
                val infoCol=column(surface)
                infoCol.addView(txt(dash(identity.fullName),11.4f,ink,true))
                infoCol.addView(txt("MNV: ${dash(identity.mnv)} • ${dash(identity.position)}",9.2f,muted,false))
                infoCol.addView(txt("Vào ${compactAttendanceTime(ses.optString("enter_at"))} • Ra ${if(ended)compactAttendanceTime(ses.optString("exit_at")) else "-"}",9.2f,muted,false))
                item.addView(infoCol,LinearLayout.LayoutParams(0,-2,1f))
                val statusText=if(ended)"Đã ra ca" else "Trong ca"
                val statusFg=if(ended)Color.rgb(82,93,103) else green
                val statusBg=if(ended)Color.rgb(244,246,248) else Color.rgb(235,248,239)
                item.addView(txt(statusText,8.8f,statusFg,true).apply{
                    gravity=Gravity.CENTER
                    setPadding(dp(5),0,dp(5),0)
                    background=round(statusBg,10)
                },LinearLayout.LayoutParams(dp(72),dp(30)).apply{marginStart=dp(6)})
                box.addView(item,matchWrap())
                if(index<groupRows.lastIndex)box.addView(View(this).apply{setBackgroundColor(line)},LinearLayout.LayoutParams(-1,dp(1)).apply{marginStart=dp(52)})
            }
            body.addView(box,matchWrap());body.addView(gap(8))
        }
        attach(root,body)
    }
    private fun addBusinessShiftReconciliation(body:LinearLayout){
        val currentDate=operationalStore.businessDate()
        val day=operationalStore.loadDay(currentDate)
        if(day==null){body.addView(info("Đang đồng bộ dữ liệu ngày ${businessDateVi(currentDate)}…"));body.addView(gap(4));return}
        val sessions=day.optJSONArray("sessions")?:JSONArray()
        val byShift=linkedMapOf<String,MutableList<JSONObject>>("Ca 1" to mutableListOf(),"Ca HC" to mutableListOf(),"Ca 2" to mutableListOf())
        for(i in 0 until sessions.length()){
            val ses=sessions.optJSONObject(i)?:continue
            if(ses.optString("business_date").trim().let{it.isNotBlank()&&it!=currentDate})continue
            val shift=ses.optString("shift").trim()
            if(shift in byShift.keys)byShift.getValue(shift).add(JSONObject(ses.toString()))
        }
        val bar=row(bg).apply{gravity=Gravity.CENTER_VERTICAL}
        byShift.forEach{(shift,raw)->
            val rows=raw.distinctBy{it.optString("session_id").ifBlank{"${it.optString("mnv")}|${it.optString("enter_at")}"}}
            val entered=rows.filter{dash(it.optString("enter_at"))!="-" }
            val exited=entered.filter{it.optString("state").equals("ENDED",true)&&dash(it.optString("exit_at"))!="-" }
            val pending=entered.filterNot{it.optString("state").equals("ENDED",true)&&dash(it.optString("exit_at"))!="-" }
            val button=reconciliationButton("$shift – ${entered.size}/${exited.size}",entered.size==exited.size)
            if(entered.size!=exited.size){
                button.contentDescription="Cảnh báo đối soát $shift chưa khớp: vào ${entered.size}, ra ${exited.size}"
                button.startAnimation(android.view.animation.AlphaAnimation(1f,0.28f).apply{duration=650L;repeatMode=android.view.animation.Animation.REVERSE;repeatCount=android.view.animation.Animation.INFINITE})
            }
            button.setOnClickListener{
                val list=column(surface).apply{setPadding(dp(10),dp(4),dp(10),dp(6))}
                var dialog:AlertDialog?=null
                if(pending.isEmpty()){
                    list.addView(info("Không có nhân sự chờ ra ca trong $shift."))
                }else{
                    shiftStaffOrdered(pending).forEach{ses->
                        val identity=shiftStaffIdentity(ses)
                        val line=row(surface).apply{gravity=Gravity.CENTER_VERTICAL;setPadding(dp(4),dp(3),dp(4),dp(3))}
                        line.addView(txt("${dash(identity.supplier)} • ${dash(identity.mnv)} • ${dash(identity.fullName)}",10.6f,ink,true),LinearLayout.LayoutParams(0,-2,1f))
                        line.addView(smallButton("RA CA",red).apply{setOnClickListener{dialog?.dismiss();if(identity.mnv.isNotBlank())loadEmployee(identity.mnv)}},LinearLayout.LayoutParams(dp(78),dp(38)))
                        list.addView(line,matchWrap());list.addView(gap(3))
                    }
                }
                dialog=AlertDialog.Builder(this).setTitle("$shift • Vào ${entered.size} / Ra ${exited.size}").setView(ScrollView(this).apply{addView(list)}).setNegativeButton("Đóng",null).create()
                dialog.show()
            }
            bar.addView(button,LinearLayout.LayoutParams(0,dp(42),1f).apply{marginStart=dp(2);marginEnd=dp(2)})
        }
        body.addView(bar,matchWrap());body.addView(gap(4))
    }

    private fun addInlineCurrentShiftStaff(body:LinearLayout){
        val currentDate=operationalStore.businessDate()
        val day=operationalStore.loadDay(currentDate)?:return
        val sessions=day.optJSONArray("sessions")?:JSONArray()
        val rows=mutableListOf<JSONObject>()
        for(i in 0 until sessions.length()){
            val x=sessions.optJSONObject(i)?:continue
            val d=x.optString("business_date").trim()
            if(d.isNotBlank()&&d!=currentDate)continue
            if(dash(x.optString("enter_at"))=="-")continue
            rows.add(JSONObject(x.toString()))
        }
        if(rows.isEmpty())return
        body.addView(gap(14))
        body.addView(section("Danh sách QR vào / ra"))

        val shiftValues=listOf("Tất cả ca")+rows.map{it.optString("shift").trim()}.filter{it.isNotBlank()}.distinct()
        val supplierValues=listOf("Tất cả NCC")+rows.map{shiftStaffIdentity(it).supplier}.filter{it.isNotBlank()}.distinct().sortedWith(Comparator{p,q->naturalUserCompare(p,q)})
        val positionValues=listOf("Tất cả vị trí")+rows.map{shiftStaffIdentity(it).position}.filter{it.isNotBlank()}.distinct().sortedWith(Comparator{p,q->naturalUserCompare(p,q)})
        val shiftSp=spinner(shiftValues.toTypedArray())
        val supplierSp=spinner(supplierValues.toTypedArray())
        val positionSp=spinner(positionValues.toTypedArray())
        val filters=row(bg).apply{
            addView(shiftSp,LinearLayout.LayoutParams(0,dp(48),1f).apply{marginEnd=dp(2)})
            addView(supplierSp,LinearLayout.LayoutParams(0,dp(48),1f).apply{marginStart=dp(2);marginEnd=dp(2)})
            addView(positionSp,LinearLayout.LayoutParams(0,dp(48),1f).apply{marginStart=dp(2)})
        }
        body.addView(filters,matchWrap());body.addView(gap(10))
        val host=column(bg);body.addView(host,matchWrap())

        fun render(){
            host.removeAllViews()
            val shift=shiftValues.getOrNull(shiftSp.selectedItemPosition).orEmpty()
            val supplier=supplierValues.getOrNull(supplierSp.selectedItemPosition).orEmpty()
            val position=positionValues.getOrNull(positionSp.selectedItemPosition).orEmpty()
            val visible=rows.filter{x->
                val id=shiftStaffIdentity(x)
                (shift=="Tất cả ca"||x.optString("shift")==shift)&&
                (supplier=="Tất cả NCC"||id.supplier==supplier)&&
                (position=="Tất cả vị trí"||id.position==position)
            }
            if(visible.isEmpty()){host.addView(info("Không có nhân sự phù hợp bộ lọc."));return}
            listOf("Ca 1","Ca HC","Ca 2").forEach{shiftName->
                val group=shiftStaffOrdered(visible.filter{it.optString("shift").trim()==shiftName})
                if(group.isEmpty())return@forEach
                val ended=group.count{shiftStaffEnded(it)}
                val head=row(surface).apply{
                    gravity=Gravity.CENTER_VERTICAL;setPadding(dp(9),dp(7),dp(9),dp(7));background=outlineBg(surface,12)
                    isClickable=true;isFocusable=true;contentDescription="Mở danh sách nhân sự $shiftName"
                    setOnClickListener{tapFeedback(this);showCurrentDayShiftStaff(currentDate,shiftName,group)}
                    addView(txt(shiftName,10.8f,navy,true),LinearLayout.LayoutParams(0,-2,1f))
                    addView(txt("Trong ca ${group.size-ended} • Đã ra $ended",9.2f,muted,true))
                }
                host.addView(head,matchWrap());host.addView(gap(4))
                group.groupBy{shiftStaffIdentity(it).supplier.ifBlank{"Chưa xác định NCC"}}.forEach{(sup,staff)->
                    host.addView(txt("$sup (${staff.size})",9.4f,teal,true).apply{setPadding(dp(4),dp(3),dp(4),dp(2))})
                    staff.forEach{x->
                        val id=shiftStaffIdentity(x);val endedRow=shiftStaffEnded(x)
                        val line=row(bg).apply{
                            gravity=Gravity.CENTER_VERTICAL;setPadding(dp(5),dp(4),dp(5),dp(4))
                            isClickable=true;isFocusable=true;contentDescription="Mở quét QR vào ra ${dash(id.fullName)}"
                            setOnClickListener{if(id.mnv.isNotBlank()){tapFeedback(this);loadEmployee(id.mnv)}}
                            addView(txt("${dash(id.mnv)} • ${dash(id.fullName)}",10.1f,ink,true),LinearLayout.LayoutParams(0,-2,1f))
                            addView(txt(if(endedRow)"ĐÃ RA" else "TRONG CA",8.5f,if(endedRow)muted else green,true))
                        }
                        host.addView(line,matchWrap())
                    }
                }
                host.addView(gap(7))
            }
        }
        val listener=object:android.widget.AdapterView.OnItemSelectedListener{
            override fun onItemSelected(p:android.widget.AdapterView<*>?,v:View?,pos:Int,id:Long)=render()
            override fun onNothingSelected(p:android.widget.AdapterView<*>?)=Unit
        }
        shiftSp.onItemSelectedListener=listener;supplierSp.onItemSelectedListener=listener;positionSp.onItemSelectedListener=listener
        render()
    }

    private fun addScannedOldSessionWarning(body:LinearLayout,ctx:JSONObject){
        val s=ctx.optJSONObject("session")?:return
        val sessionDate=s.optString("business_date").trim()
        val currentDate=operationalStore.businessDate()
        if(!ctx.optString("state").equals("ACTIVE",true)||sessionDate.isBlank()||sessionDate>=currentDate)return
        val warning=reconciliationButton(OldSessionWarningFeature.WARNING_TEXT,false)
        warning.startAnimation(android.view.animation.AlphaAnimation(1f,0.35f).apply{duration=650L;repeatMode=android.view.animation.Animation.REVERSE;repeatCount=android.view.animation.Animation.INFINITE})
        body.addView(warning,ReviewAlertUi.fixedHeightParams(this));body.addView(gap(4))
    }

    private fun employeeScan() {
        screenState = "SCAN"; liveEmployeeMnv = ""
        val root=column(bg);root.addView(appBar("QUÉT QR NHÂN SỰ"))
        val body=column(bg).apply{setPadding(dp(10),dp(8),dp(10),dp(84))}
        body.addView(OldSessionWarningFeature.build(this,api){raw->openHistoricalSession(raw)},matchWrap())
        addBusinessShiftReconciliation(body)
        val mnv=mnvInput("Scan / Nhập mã nhân viên")
        body.addView(mnv,matchWrap());body.addView(gap(4))
        addInlineCurrentShiftStaff(body)
        var busy=false
        fun submit(){val v=mnv.text.toString().trim();if(v.isBlank()){TopNotice.show(this,"Nhập hoặc quét Mã nhân viên.",TopNotice.Kind.WARNING);return};if(busy)return;busy=true;hideSoftKeyboard(mnv);loadEmployee(v);mnv.postDelayed({busy=false},600)}
        bindScannerEnter(mnv){submit()}
        root.addView(ScrollView(this).apply{addView(body)},LinearLayout.LayoutParams(-1,0,1f));setScreen(root);mnv.requestFocus()
    }

    private fun employeeRenderSignature(ctx:JSONObject,masters:JSONObject?):String{
        val e=ctx.optJSONObject("employee")?:JSONObject();val s=ctx.optJSONObject("session");val state=ctx.optString("state")
        val parts=mutableListOf(e.optString("mnv"),e.optString("full_name"),e.optString("phone"),e.optString("start_date"),e.optString("main_position"),e.optString("supplier"),e.optString("department"),e.optString("site"),e.optString("warehouse"),state,ctx.optString("reconciliation_state"))
        if(s!=null)parts.addAll(listOf(s.optString("session_id"),s.optString("state"),s.optString("version"),s.optString("shift"),s.optString("enter_at"),s.optString("exit_at"),s.optString("pda_serial"),s.optString("user_pick"),s.optString("pack_table"),s.optString("user_pack"),(s.optJSONArray("positions_v64")?:JSONArray()).toString(),(s.optJSONArray("resource_assignments_v64")?:JSONArray()).toString()))
        return parts.joinToString("\u001f")
    }
    private fun renderEmployeeIfChanged(ctx:JSONObject,masters:JSONObject?){
        val mnv=ctx.optJSONObject("employee")?.optString("mnv").orEmpty();val signature=employeeRenderSignature(ctx,masters)
        if(screenState=="EMPLOYEE"&&liveEmployeeMnv==mnv&&lastEmployeeRenderSignature==signature)return
        renderEmployee(ctx,masters)
    }

    private fun renderLocalEmployee(mnv:String):Boolean{
        val ctx=PdaLocalProjection.employeeContext(this,mnv) ?: return false
        if(!ctx.optBoolean("session_known",true)){
            liveEmployeeMnv=mnv
            renderCachedEmployee(ctx.optJSONObject("employee")?:JSONObject())
            TopNotice.show(this,"Đã đọc nhân sự từ PDA • đang đối chiếu phiên nền",TopNotice.Kind.INFO)
            return true
        }
        val masters=if(ctx.optString("state")=="NOT_ENTERED")PdaLocalProjection.resourceOptions(this,mnv) else null
        renderEmployeeIfChanged(ctx,masters)
        return true
    }

    private fun historicalEmployeeContext(raw:JSONObject):JSONObject?{
        val identity=raw.optJSONObject("identity")?:JSONObject()
        val sourceSession=raw.optJSONObject("session")?:return null
        val sourceEmployee=raw.optJSONObject("employee")?:JSONObject()
        val session=JSONObject(sourceSession.toString())
        val sid=identity.optString("session_id").ifBlank{session.optString("session_id")}.trim()
        val mnv=identity.optString("mnv").ifBlank{session.optString("mnv")}.trim()
        val date=identity.optString("business_date").ifBlank{session.optString("business_date")}.trim()
        if(sid.isBlank()||mnv.isBlank()||date.isBlank())return null
        session.put("session_id",sid).put("mnv",mnv).put("business_date",date)
        val employee=JSONObject(sourceEmployee.toString()).apply{if(optString("mnv").isBlank())put("mnv",mnv)}
        val state=session.optString("state").ifBlank{"ACTIVE"}.uppercase()
        val ctx=JSONObject().put("business_date",date).put("employee",employee).put("session",session).put("state",state).put("historical_session",true)
        val labor=raw.optJSONArray("labor")?:JSONArray()
        for(i in 0 until labor.length()){val x=labor.optJSONObject(i)?:continue;if(x.optString("state").equals("OPEN",true)){ctx.put("active_labor",JSONObject(x.toString()));break}}
        return ctx
    }

    private fun openHistoricalSession(raw:JSONObject){
        val ctx=historicalEmployeeContext(raw)
        if(ctx==null){showError("Không dựng được đúng phiên cũ đã chọn.");return}
        val s=ctx.optJSONObject("session")?:return
        val mnv=s.optString("mnv").trim()
        employeeLookupGeneration++
        liveEmployeeMnv=mnv
        lastEmployeeRenderSignature=""
        renderEmployee(ctx,null)
    }

    // S38_ATTENDANCE_UI: render staff identity immediately, then use current Service session/resource options.
    // S39_EMPLOYEE_SESSION_HISTORY: normalized master-backed MNV + stale callback fence.
    // S40_OWNER_LOCAL_FIRST_REPAIR: owner lock = SQLite/PDA first, Service reconcile later.
    // S45_BETA40_OWNER_FIXES: never let an N-1 Service response replace current N local context.
    private fun loadEmployee(mnv: String, button: Button? = null, forceRefresh:Boolean=false) {
        val qrStarted=android.os.SystemClock.elapsedRealtime()
        val resolved=MasterDataCache.resolveEmployeeMnv(this,mnv)
        val resolvedAt=android.os.SystemClock.elapsedRealtime()
        if(resolved.isBlank()){button?.isEnabled=true;showError("MNV_REQUIRED");return}
        val generation=++employeeLookupGeneration
        val currentDate=operationalStore.businessDate()
        val localNow=PdaLocalProjection.employeeContext(this,resolved)
        val localOptions=PdaLocalProjection.resourceOptions(this,resolved)
        val cached=MasterDataCache.employee(this,resolved)
        val projectedAt=android.os.SystemClock.elapsedRealtime()
        val localInteractive=localNow!=null&&localNow.optBoolean("session_known",true)
        val renderStarted=android.os.SystemClock.elapsedRealtime()
        when{
            localInteractive->renderEmployeeIfChanged(localNow!!,localOptions)
            localNow!=null->renderCachedEmployee(localNow.optJSONObject("employee")?:cached?:JSONObject().put("mnv",resolved))
            cached!=null->renderCachedEmployee(cached)
        }
        val localRenderedAt=android.os.SystemClock.elapsedRealtime()
        QrPerformanceDiagnostics.recordLocal(
            this,resolved,resolvedAt-qrStarted,projectedAt-resolvedAt,localRenderedAt-renderStarted,
            localNow?.optString("state").orEmpty(),localNow?.optString("source").orEmpty()
        )
        val serviceStarted=android.os.SystemClock.elapsedRealtime()
        api.call("employee_context",JSONObject().put("mnv",resolved).put("include_options",true).put("include_labor",true)){result->runOnUiThread{
            val serviceTotal=android.os.SystemClock.elapsedRealtime()-serviceStarted
            val serviceRtt=result.json?.optLong("_service_rtt_ms",-1L)?.takeIf{it>=0L}
            QrPerformanceDiagnostics.recordService(this@OperationsActivity,resolved,serviceTotal,serviceRtt,forceRefresh||!localInteractive,result.code)
            if(generation!=employeeLookupGeneration)return@runOnUiThread
            button?.isEnabled=true
            val overlay=PdaLocalProjection.employeeContext(this@OperationsActivity,resolved)
            val refreshedOptions=PdaLocalProjection.resourceOptions(this@OperationsActivity,resolved)
            if(!result.ok){
                if(overlay!=null){
                    if(forceRefresh||!localInteractive)renderEmployeeIfChanged(overlay,refreshedOptions)
                    TopNotice.show(this@OperationsActivity,"Service chưa xác nhận được; đang giữ dữ liệu PDA hiện có.",TopNotice.Kind.WARNING)
                }else if(result.code==401)sessionExpired()
                else showError(result.error?:"Không kiểm tra được mã nhân viên")
                return@runOnUiThread
            }
            if(overlay!=null&&overlay.optString("reconciliation_state")=="LOCAL_PENDING"){
                if(forceRefresh||!localInteractive)renderEmployeeIfChanged(overlay,refreshedOptions)
                return@runOnUiThread
            }
            val ctx=result.json?:JSONObject()
            val remoteDate=ctx.optString("business_date").trim()
            if(remoteDate.isNotBlank()&&remoteDate!=currentDate){
                if(forceRefresh||!localInteractive){
                    if(overlay!=null)renderEmployeeIfChanged(overlay,refreshedOptions)else if(cached!=null)renderCachedEmployee(cached)
                }
                return@runOnUiThread
            }
            val options=ctx.optJSONObject("options")?:refreshedOptions
            // Beta92: a background Service response for the employee already on screen must not
            // rebuild the interactive tree and erase selections. Explicit forceRefresh remains available
            // for conflict recovery; realtime changes update only their dedicated regions.
            if(!forceRefresh&&localInteractive&&screenState=="EMPLOYEE"&&liveEmployeeMnv==resolved)return@runOnUiThread
            renderEmployeeIfChanged(ctx,options)
        }}
    }

    private fun renderCachedEmployee(e: JSONObject) {
        screenState="EMPLOYEE_LOADING";val cachedMnv=e.optString("mnv")
        val root=column(bg);root.addView(appBar("QUÉT QR NHÂN SỰ"));val body=column(bg).apply{setPadding(dp(16),dp(12),dp(16),dp(58))}
        val scan=mnvInput("Scan / Nhập mã nhân viên").apply{setText("")};body.addView(labelled("Mã nhân viên",scan));body.addView(gap(9));body.addView(employeeCard(e));body.addView(gap(9));body.addView(status("ĐANG XÁC NHẬN TRẠNG THÁI PHIÊN...",blue,Color.rgb(237,244,255)))
        var busy=false;fun submit(){val v=scan.text.toString();if(v.isBlank()){TopNotice.show(this,"Nhập hoặc quét mã nhân viên.",TopNotice.Kind.WARNING);return};if(busy)return;busy=true;loadEmployee(v);scan.postDelayed({busy=false},500)};bindScannerEnter(scan){submit()}
        root.addView(ScrollView(this).apply{addView(body)},LinearLayout.LayoutParams(-1,0,1f));setScreen(root);hideKeyboardForResult(root,scan)
        liveEmployeeMnv=cachedMnv
    }

    private fun renderEmployeeLookupRetry(e: JSONObject, mnv: String, reason: String) {
        screenState="EMPLOYEE_LOOKUP_ERROR";liveEmployeeMnv=mnv
        val root=column(bg);root.addView(appBar("QUÉT QR NHÂN SỰ"));val body=column(bg).apply{setPadding(dp(16),dp(12),dp(16),dp(58))}
        val scan=mnvInput("Scan / Nhập mã nhân viên").apply{setText("")};body.addView(labelled("Mã nhân viên",scan));body.addView(gap(9));body.addView(employeeCard(e));body.addView(gap(9))
        body.addView(status("CHƯA XÁC NHẬN ĐƯỢC PHIÊN",orange,Color.rgb(255,251,235)));body.addView(gap(6));body.addView(info("Dữ liệu nhân sự đã có trên PDA nhưng Service chưa trả được trạng thái phiên. Mã lỗi: ${reason.take(100)}"));body.addView(gap(8))
        body.addView(primary("THỬ XÁC NHẬN LẠI",navy){loadEmployee(mnv)},matchWrap())
        var busy=false;fun submit(){val v=scan.text.toString();if(v.isBlank()){TopNotice.show(this,"Nhập hoặc quét mã nhân viên.",TopNotice.Kind.WARNING);return};if(busy)return;busy=true;loadEmployee(v);scan.postDelayed({busy=false},500)};bindScannerEnter(scan){submit()}
        root.addView(ScrollView(this).apply{addView(body)},LinearLayout.LayoutParams(-1,0,1f));setScreen(root);hideKeyboardForResult(root,scan)
    }

    private fun renderEmployee(ctx: JSONObject, masters: JSONObject?) {
        employeeTimelineRealtimeRefresh=null
        screenState="EMPLOYEE"
        val e=ctx.optJSONObject("employee")?:JSONObject();val state=ctx.optString("state");val currentMnv=e.optString("mnv");liveEmployeeMnv=currentMnv;lastEmployeeRenderSignature=employeeRenderSignature(ctx,masters)
        val root=column(bg);root.addView(appBar("QUÉT QR NHÂN SỰ"));val body=column(bg).apply{setPadding(dp(12),dp(8),dp(12),dp(58))}
        addScannedOldSessionWarning(body,ctx)
        addBusinessShiftReconciliation(body)
        val scan=mnvInput("Scan / Nhập mã nhân viên").apply{setText("")};body.addView(scan,matchWrap());body.addView(gap(5));body.addView(employeeCard(e,state));body.addView(gap(7))
        var busy=false;fun submit(){val v=scan.text.toString().trim();if(v.isBlank()){TopNotice.show(this,"Nhập hoặc quét mã nhân viên.",TopNotice.Kind.WARNING);return};if(busy)return;busy=true;loadEmployee(v);scan.postDelayed({busy=false},600)};bindScannerEnter(scan){submit()}
        val ses=ctx.optJSONObject("session");val sessionId=ses?.optString("session_id").orEmpty().trim()
        if((state=="ACTIVE"||state=="ENDED")&&ses!=null&&!ses.has("resource_assignments_v64")&&sessionId.isNotBlank()){
            // Beta77: keep the already rendered employee view while the resource snapshot arrives; never attach an intermediate full tree.
            val generation=employeeLookupGeneration;api.call("session_resource_snapshot",JSONObject().put("session_id",sessionId).put("mnv",currentMnv)){r->runOnUiThread{
                if(generation!=employeeLookupGeneration||liveEmployeeMnv!=currentMnv)return@runOnUiThread
                if(!r.ok){showError(r.error?:"Không đọc được tài nguyên phiên");return@runOnUiThread}
                renderEmployee(mergeResourceSnapshot(ctx,r.json?:JSONObject()),masters)
            }};return
        }
        when(state){"ACTIVE"->renderActive(body,ctx);"ENDED"->renderEnded(body,ctx);else->renderEnter(body,ctx,masters?:JSONObject())}
        addInlineCurrentShiftStaff(body)
        root.addView(ScrollView(this).apply{addView(body)},LinearLayout.LayoutParams(-1,0,1f));setScreen(root);hideKeyboardForResult(root,scan)
    }


    private fun sameEmployeeContext(mnv:String,generation:Long):Boolean = screenState=="EMPLOYEE" && liveEmployeeMnv.trim()==mnv.trim() && employeeLookupGeneration==generation
    private fun scheduleAttendanceAutoReset(mnv:String,generation:Long){
        val expected=mnv.trim()
        android.os.Handler(mainLooper).postDelayed({ if(sameEmployeeContext(expected,generation))employeeScan() },650L)
    }

    // S48_BETA42_SHIFT_WORK_SUMMARY: local-first shift timeline + explicit PDA identity.
    private fun sessionWorkDetail(payload:JSONObject):String{
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


    private fun sessionWorkChangeDetail(payload:JSONObject):String{
        val before=payload.optJSONObject("before")?:JSONObject();val after=payload.optJSONObject("after")?:JSONObject()
        fun assignments(x:JSONObject):JSONArray=x.optJSONArray("resource_assignments_v64")?:x.optJSONArray("resource_assignments")?:x.optJSONArray("assignments")?:JSONArray()
        fun positions(x:JSONObject):JSONArray=x.optJSONArray("positions_v64")?:x.optJSONArray("positions")?:JSONArray()
        fun label(t:String)=when(t.uppercase()){ "PDA"->"PDA";"USER_PICK"->"User Pick";"PACK_TABLE"->"Bàn Pack";"USER_PACK"->"User Pack";else->t.ifBlank{"Tài nguyên"} }
        fun directKey(t:String)=when(t.uppercase()){ "PDA"->"pda_serial";"USER_PICK"->"user_pick";"PACK_TABLE"->"pack_table";"USER_PACK"->"user_pack";else->"" }
        fun currentResource(x:JSONObject,t:String):String{
            val snapshot=x.optJSONArray("resource_assignments_v64")?:x.optJSONArray("resource_assignments")?:x.optJSONArray("assignments")
            if(snapshot!=null){
                val out=mutableListOf<String>()
                for(i in 0 until snapshot.length()){
                    val q=snapshot.optJSONObject(i)?:continue
                    if(!q.optString("resource_type").equals(t,true))continue
                    if(q.optString("state").uppercase() !in setOf("","ACTIVE"))continue
                    val id=q.optString("resource_id").trim()
                    if(id.isNotBlank())out.add(id)
                }
                val projected=out.distinct().joinToString(" • ")
                if(projected.isNotBlank())return projected
            }
            return directKey(t).takeIf{it.isNotBlank()}?.let{x.optString(it).trim().takeUnless{v->v.equals("null",true)}.orEmpty()}.orEmpty()
        }
        fun assignmentById(x:JSONObject,id:String):JSONObject?{val a=assignments(x);for(i in 0 until a.length()){val q=a.optJSONObject(i)?:continue;if(q.optString("assignment_id")==id)return q};return null}
        fun workText(x:JSONObject):String{
            val a=positions(x);val p=mutableListOf<String>();for(i in 0 until a.length()){val q=a.optJSONObject(i)?:continue;if(q.optString("state").uppercase() !in setOf("","ACTIVE"))continue;val v=q.optString("position_label").ifBlank{q.optString("position_key")}.trim();if(v.isNotBlank())p.add(v)}
            if(p.isNotEmpty())return p.distinct().joinToString(" & ")
            return when(x.optString("work_choice").uppercase()){"PICK"->"Pick";"PACK"->"Pack";"BOTH","PICK_PACK"->"Pick & Pack";"KHONG","NONE","NO"->"Không";else->x.optString("work_choice").ifBlank{"—"}}
        }
        val changes=mutableListOf<String>();val ops=payload.optJSONArray("operations")
        if(ops!=null){for(i in 0 until ops.length()){
            val q=ops.optJSONObject(i)?:continue;val op=q.optString("op").uppercase();val t=q.optString("resource_type")
            when(op){
                "ADD_RESOURCE"->{val id=q.optString("resource_id").trim();if(id.isNotBlank())changes.add("${label(t)}: — → $id")}
                "REMOVE_RESOURCE"->{val old=assignmentById(before,q.optString("assignment_id"));val rt=old?.optString("resource_type").orEmpty().ifBlank{t};val id=old?.optString("resource_id").orEmpty().ifBlank{q.optString("resource_id")}.ifBlank{currentResource(before,rt)}.ifBlank{"—"};changes.add("${label(rt)}: $id → —${q.optString("reason").takeIf{it.isNotBlank()}?.let{" • Lý do: $it"}.orEmpty()}")}
                "REPLACE_RESOURCE"->{val old=assignmentById(before,q.optString("assignment_id"));val rt=old?.optString("resource_type").orEmpty().ifBlank{t};val oldId=old?.optString("resource_id").orEmpty().ifBlank{currentResource(before,rt)}.ifBlank{"—"};val newId=q.optString("new_resource_id").ifBlank{currentResource(after,rt)}.ifBlank{"—"};changes.add("${label(rt)}: $oldId → $newId${q.optString("reason").takeIf{it.isNotBlank()}?.let{" • Lý do: $it"}.orEmpty()}")}
                "UPDATE_SHIFT"->{val old=before.optString("shift").ifBlank{"—"};val next=q.optString("shift").ifBlank{after.optString("shift")}.ifBlank{"—"};changes.add("Ca: $old → $next")}
            }
        }}
        if(before.length()>0||after.length()>0){
            val bw=workText(before);val aw=workText(after);if(bw!=aw&&bw!="—"&&aw!="—"&&changes.none{it.startsWith("Công việc trong ca:")})changes.add("Công việc trong ca: $bw → $aw")
            for(t in listOf("PDA","USER_PICK","PACK_TABLE","USER_PACK")){val b=currentResource(before,t).ifBlank{"—"};val a=currentResource(after,t).ifBlank{"—"};if(b!=a&&changes.none{it.startsWith("${label(t)}:")})changes.add("${label(t)}: $b → $a")}
            val bs=before.optString("shift");val asv=after.optString("shift");if(bs.isNotBlank()&&asv.isNotBlank()&&bs!=asv&&changes.none{it.startsWith("Ca:")})changes.add("Ca: $bs → $asv")
        }
        return changes.joinToString(" • ")
    }
    private fun auditWorkRows(s:JSONObject):List<Pair<String,String>>{
        fun directOrAssignment(key:String,type:String):String{
            val snapshot=s.optJSONArray("resource_assignments_v64")?:s.optJSONArray("resource_assignments")?:s.optJSONArray("assignments")
            if(snapshot!=null){
                val values=mutableListOf<String>()
                for(i in 0 until snapshot.length()){
                    val x=snapshot.optJSONObject(i)?:continue
                    if(!x.optString("resource_type").equals(type,true))continue
                    if(x.optString("state").uppercase() !in setOf("","ACTIVE"))continue
                    val id=x.optString("resource_id").trim()
                    if(id.isNotBlank())values.add(id)
                }
                val projected=values.distinct().joinToString(" • ")
                if(projected.isNotBlank())return projected
            }
            return s.optString(key).trim().takeUnless{it.equals("null",true)}.orEmpty().ifBlank{"—"}
        }
        val pa=s.optJSONArray("positions_v64")?:s.optJSONArray("positions")?:JSONArray();val pos=mutableListOf<String>()
        for(i in 0 until pa.length()){val x=pa.optJSONObject(i)?:continue;if(x.optString("state").uppercase() !in setOf("","ACTIVE"))continue;val v=x.optString("position_label").ifBlank{x.optString("position_key")}.trim();if(v.isNotBlank())pos.add(v)}
        val position=pos.distinct().joinToString(" & ").ifBlank{s.optString("work_choice").ifBlank{"—"}}
        return listOf("Vị trí trong ca" to position,"User Pick" to directOrAssignment("user_pick","USER_PICK"),"PDA" to directOrAssignment("pda_serial","PDA"),"Bàn Pack" to directOrAssignment("pack_table","PACK_TABLE"),"User Pack" to directOrAssignment("user_pack","USER_PACK"))
    }
    private fun auditWorkBlock(title:String,s:JSONObject):String=buildString{
        append(title).append(":\n")
        auditWorkRows(s).forEach{(k,v)->append("• ").append(k).append(": ").append(v).append('\n')}
    }.trimEnd()

    private fun sessionWorkSnapshotDetail(s:JSONObject):String{
        if(s.length()==0)return ""
        fun directOrAssignment(key:String,type:String):String{
            val snapshot=s.optJSONArray("resource_assignments_v64")?:s.optJSONArray("resource_assignments")?:s.optJSONArray("assignments")
            if(snapshot!=null){
                val values=mutableListOf<String>()
                for(i in 0 until snapshot.length()){
                    val x=snapshot.optJSONObject(i)?:continue
                    if(!x.optString("resource_type").equals(type,true))continue
                    if(x.optString("state").uppercase() !in setOf("","ACTIVE"))continue
                    val id=x.optString("resource_id").trim()
                    if(id.isNotBlank())values.add(id)
                }
                val projected=values.distinct().joinToString(" • ")
                if(projected.isNotBlank())return projected
            }
            return s.optString(key).trim().takeUnless{it.equals("null",true)}.orEmpty()
        }
        val pa=s.optJSONArray("positions_v64")?:s.optJSONArray("positions")?:JSONArray();val positions=mutableListOf<String>()
        for(i in 0 until pa.length()){val x=pa.optJSONObject(i)?:continue;if(x.optString("state").uppercase() !in setOf("","ACTIVE"))continue;val v=x.optString("position_label").ifBlank{x.optString("position_key")}.trim();if(v.isNotBlank())positions.add(v)}
        val directWork=when(s.optString("work_choice").trim().uppercase()){"PICK"->"Pick";"PACK"->"Pack";"BOTH","PICK_PACK"->"Pick & Pack";"KHONG","NONE","NO"->"Làm theo vị trí chính";else->s.optString("work_choice").trim()}
        val position=positions.distinct().joinToString(" & ").ifBlank{directWork}.ifBlank{"—"}
        val rows=listOf(
            "Vị trí" to position,
            "User Pick" to directOrAssignment("user_pick","USER_PICK").ifBlank{"—"},
            "PDA" to directOrAssignment("pda_serial","PDA").ifBlank{"—"},
            "Bàn Pack" to directOrAssignment("pack_table","PACK_TABLE").ifBlank{"—"},
            "User Pack" to directOrAssignment("user_pack","USER_PACK").ifBlank{"—"}
        )
        return rows.joinToString(" • "){"${it.first}: ${it.second}"}
    }
    private fun sessionTimelineItems(mnv:String,ses:JSONObject):MutableList<JSONObject>{
        val merged=LinkedHashMap<String,JSONObject>();val date=ses.optString("business_date").ifBlank{operationalStore.businessDate()};val currentSessionId=ses.optString("session_id").trim();val enterMs=runCatching{Instant.parse(ses.optString("enter_at")).toEpochMilli()}.getOrDefault(0L);val exitMs=runCatching{Instant.parse(ses.optString("exit_at")).toEpochMilli()}.getOrDefault(Long.MAX_VALUE)
        fun sameSession(e:JSONObject,p:JSONObject,localAt:Long=0L):Boolean{val sid=e.optString("session_id").ifBlank{p.optString("session_id")}.trim();if(currentSessionId.isNotBlank()&&sid.isNotBlank())return sid==currentSessionId;val ms=if(localAt>0L)localAt else runCatching{Instant.parse(e.optString("committed_at").ifBlank{e.optString("occurred_at").ifBlank{e.optString("at_iso").ifBlank{e.optString("at")}}}).toEpochMilli()}.getOrDefault(0L);return enterMs>0L&&ms>=enterMs&&ms<=exitMs}
        val allowed=setOf("ATTENDANCE_ENTER","ENTER","RESOURCE_CHANGE","RESOURCE","LABOR_START","LABOR_FINISH","ATTENDANCE_EXIT","EXIT","ATTENDANCE_TIME_CORRECTED","ATTENDANCE_EXIT_DELETED")
        fun payload(e:JSONObject):JSONObject{
            fun parsed(raw:Any?):JSONObject?=when(raw){
                is JSONObject->raw
                is String->raw.trim().takeIf{it.isNotBlank()}?.let{runCatching{JSONObject(it)}.getOrNull()}
                else->null
            }
            val out=JSONObject()
            fun merge(src:JSONObject?){
                if(src==null)return
                val keys=src.keys()
                while(keys.hasNext()){
                    val k=keys.next();val v=src.opt(k)
                    if(v==null||v===JSONObject.NULL)continue
                    val existing=out.opt(k)
                    val missing=!out.has(k)||existing==null||existing===JSONObject.NULL||(existing is String&&existing.isBlank())
                    if(missing)out.put(k,v)
                }
            }
            // Service can expose a small parsed payload and keep the complete audit snapshot in payload_json.
            // Read the complete JSON first, then fill missing fields from alternate shapes.
            merge(parsed(e.opt("payload_json")))
            merge(parsed(e.opt("payload")))
            merge(e.optJSONObject("data"))
            for(k in listOf("before","after","operations","session_id","mnv","mutation_kind","work_choice","pda_serial","user_pick","pack_table","user_pack","positions_v64","resource_assignments_v64")){
                if(!out.has(k)&&e.has(k)){val v=e.opt(k);if(v!=null&&v!==JSONObject.NULL)out.put(k,v)}
            }
            fun normalizeObject(target:String,vararg aliases:String){
                if(out.optJSONObject(target)!=null)return
                for(alias in aliases){val x=parsed(out.opt(alias));if(x!=null){out.put(target,x);return}}
            }
            normalizeObject("before","before_json","before_snapshot","snapshot_before")
            normalizeObject("after","after_json","after_snapshot","snapshot_after")
            return out
        }
        fun detail(type:String,e:JSONObject,p:JSONObject):String{
            if(type=="ATTENDANCE_TIME_CORRECTED"){val field=if(p.optString("field")=="enter_at")"Giờ vào" else "Giờ ra";return "$field: ${formatIso(p.optString("before_value"))} → ${formatIso(p.optString("after_value"))} • Lý do: ${p.optString("reason").ifBlank{"—"}}"}
            if(type=="ATTENDANCE_EXIT_DELETED")return "Xóa mốc ra ca ${formatIso(p.optString("before_exit_at"))} • Lý do: ${p.optString("reason").ifBlank{"—"}}"
            if(type=="RESOURCE_CHANGE"){
                val delta=sessionWorkChangeDetail(p);val before=p.optJSONObject("before");val after=p.optJSONObject("after")
                if(before!=null||after!=null)return delta
                val current=sessionWorkSnapshotDetail(p).ifBlank{sessionWorkDetail(p)}
                return listOfNotNull(if(delta.isNotBlank())"Thay đổi: $delta" else null,if(current.isNotBlank())"Sau cập nhật: $current" else null,e.optString("detail").takeIf{it.isNotBlank()}).distinct().joinToString("\n").ifBlank{"Không có chi tiết thay đổi trong bản ghi cũ."}
            }
            return e.optString("detail").ifBlank{sessionWorkDetail(p)}
        }
        val day=operationalStore.loadDay(date);val events=day?.optJSONArray("events")?:JSONArray()
        for(i in 0 until events.length()){
            val e=events.optJSONObject(i)?:continue;val p=payload(e);val who=e.optString("mnv").ifBlank{p.optString("mnv")}.trim();if(who!=mnv||!sameSession(e,p))continue
            val type=e.optString("event_type").uppercase();if(type !in allowed)continue
            if(type=="RESOURCE_CHANGE"&&(p.optJSONObject("before")!=null||p.optJSONObject("after")!=null)&&sessionWorkChangeDetail(p).isBlank())continue
            val copy=JSONObject(e.toString()).put("timeline_source","CANONICAL").put("mnv",mnv).put("detail",detail(type,e,p)).put("actor",e.optString("actor").ifBlank{e.optString("actor_id")})
            if(copy.optString("at_iso").isBlank())copy.put("at_iso",e.optString("committed_at").ifBlank{e.optString("occurred_at")})
            val id=copy.optString("event_id").ifBlank{"canonical:$date:$i:${copy.optString("at_iso")}"};merged[id]=copy
        }
        for(local in operationalStore.localHistoryAll()){
            val id=local.optString("event_id").trim();if(id.isBlank())continue;val body=local.optJSONObject("body")?:JSONObject();val p=body.optJSONObject("payload")?:body;val who=body.optString("mnv").ifBlank{p.optString("mnv")}.trim();if(who!=mnv)continue
            val sid=body.optString("session_id").ifBlank{p.optString("session_id")}.trim();if(currentSessionId.isNotBlank()&&sid.isNotBlank()&&sid!=currentSessionId)continue
            val eventIso=body.optString("created_at").ifBlank{body.optString("updated_at").ifBlank{body.optString("at_iso").ifBlank{p.optString("created_at")}}};val queuedAt=local.optLong("queued_at",0L);val eventMs=runCatching{Instant.parse(eventIso).toEpochMilli()}.getOrDefault(queuedAt)
            if(sid.isBlank()&&enterMs>0L&&eventMs>0L&&(eventMs<enterMs||eventMs>exitMs))continue
            val action=body.optString("action").trim().lowercase();val explicit=body.optString("event_type").trim().uppercase();val type=when(explicit){"ENTER"->"ATTENDANCE_ENTER";"RESOURCE"->"RESOURCE_CHANGE";"EXIT"->"ATTENDANCE_EXIT";in allowed->explicit;else->when(action){"enter"->"ATTENDANCE_ENTER";"resource_change"->"RESOURCE_CHANGE";"labor_start"->"LABOR_START";"labor_finish"->"LABOR_FINISH";"exit"->"ATTENDANCE_EXIT";else->""}};if(type.isBlank())continue
            if(type=="RESOURCE_CHANGE"&&(p.optJSONObject("before")!=null||p.optJSONObject("after")!=null)&&sessionWorkChangeDetail(p).isBlank())continue
            val localError=local.optString("error").ifBlank{local.optString("last_error")};val existing=merged[id];if(existing!=null){existing.put("local_status",local.optString("status")).put("local_error",localError).put("local_queued_at",queuedAt);continue}
            val label=body.optString("label").ifBlank{when(type){"ATTENDANCE_ENTER"->"Vào ca";"RESOURCE_CHANGE"->"Cập nhật công việc";"LABOR_START"->"Bắt đầu công nhật";"LABOR_FINISH"->"Hoàn thành công nhật";"ATTENDANCE_EXIT"->"Ra ca";else->action}}
            val actor=body.optString("actor_name").ifBlank{body.optString("actor").ifBlank{body.optString("actor_id").ifBlank{"Thiết bị này"}}}
            merged[id]=JSONObject().put("event_id",id).put("event_type",type).put("label",label).put("mnv",mnv).put("actor",actor).put("detail",detail(type,body,p)).put("at_iso",eventIso).put("timeline_source","LOCAL_PDA").put("local_status",local.optString("status")).put("local_error",localError).put("local_queued_at",queuedAt)
        }
        val out=merged.values.toMutableList();fun atMillis(e:JSONObject):Long{val q=e.optLong("local_queued_at",0L);if(q>0L)return q;return runCatching{Instant.parse(e.optString("at_iso").ifBlank{e.optString("at")}).toEpochMilli()}.getOrDefault(0L)};out.sortByDescending{atMillis(it)};return out
    }

    private fun sessionEventTitle(typeRaw:String,label:String):String=when(typeRaw.uppercase()){
        "ATTENDANCE_ENTER","ENTER"->"VÀO CA";"RESOURCE_CHANGE","RESOURCE"->"CẬP NHẬT CÔNG VIỆC";"LABOR_START"->"BẮT ĐẦU CÔNG NHẬT";"LABOR_FINISH"->"HOÀN THÀNH CÔNG NHẬT";"ATTENDANCE_EXIT","EXIT"->"RA CA";"ATTENDANCE_TIME_CORRECTED"->"SỬA THỜI GIAN VÀO / RA";"ATTENDANCE_EXIT_DELETED"->"XÓA GHI NHẬN RA CA";else->label.ifBlank{"THAO TÁC"}.uppercase()
    }

    private fun sessionEventTime(e:JSONObject):String{
        val local=e.optLong("local_queued_at",0L)
        if(local>0L)return Instant.ofEpochMilli(local).atZone(ZoneId.of("Asia/Ho_Chi_Minh")).format(DateTimeFormatter.ofPattern("HH:mm:ss"))
        return formatIso(e.optString("at_iso").ifBlank{e.optString("at")})
    }

    private data class ShiftResourceUsage(val pdas:LinkedHashMap<String,String>,val userPicks:LinkedHashSet<String>,val userPacks:LinkedHashSet<String>)
    private fun shiftResourceUsage(mnv:String,ses:JSONObject):ShiftResourceUsage{
        val pdas=linkedMapOf<String,String>();val picks=linkedSetOf<String>();val packs=linkedSetOf<String>()
        fun clean(v:String)=v.trim().takeUnless{it.isBlank()||it.equals("null",true)||it=="—"}.orEmpty()
        fun addSnapshot(x:JSONObject){
            val serial=clean(x.optString("pda_serial"));val status=clean(x.optString("pda_enter_status")).ifBlank{clean(x.optString("pda_status_at_enter"))}
            if(serial.isNotBlank()&&!pdas.containsKey(serial))pdas[serial]=status else if(serial.isNotBlank()&&pdas[serial].isNullOrBlank()&&status.isNotBlank())pdas[serial]=status
            clean(x.optString("user_pick")).takeIf{it.isNotBlank()}?.let{picks.add(it)};clean(x.optString("user_pack")).takeIf{it.isNotBlank()}?.let{packs.add(it)}
        }
        sessionTimelineItems(mnv,ses).forEach{e->val raw=e.optString("payload_json");val payload=if(raw.isNotBlank())runCatching{JSONObject(raw)}.getOrDefault(JSONObject()) else e.optJSONObject("payload")?:JSONObject();addSnapshot(payload);payload.optJSONObject("before")?.let(::addSnapshot);payload.optJSONObject("after")?.let(::addSnapshot)}
        addSnapshot(ses);return ShiftResourceUsage(LinkedHashMap(pdas),LinkedHashSet(picks),LinkedHashSet(packs))
    }
    private fun addPdaUsage(body:LinearLayout,mnv:String,ses:JSONObject){
        body.addView(section("PDA SỬ DỤNG TRONG CA"));val usage=shiftResourceUsage(mnv,ses)
        if(usage.pdas.isEmpty()){body.addView(txt("—",10.5f,muted,true).apply{setPadding(dp(10),dp(5),dp(10),dp(5))});return}
        usage.pdas.forEach{(serial,status)->body.addView(column(surface).apply{setPadding(dp(14),dp(10),dp(14),dp(10));background=outlineBg(surface,14);addView(txt("Seri PDA",9.5f,muted,true));addView(txt(serial,16.5f,navy,true));addView(gap(5));addView(txt("Tình trạng ghi nhận ban đầu",9.5f,muted,true));addView(txt(dash(status),11.2f,ink,true))},matchWrap());body.addView(gap(5))}
    }

    private fun addSessionTimeline(body:LinearLayout,mnv:String,ses:JSONObject){
        body.addView(section("DIỄN BIẾN CÔNG VIỆC TRONG CA"))
        val items=sessionTimelineItems(mnv,ses)
        if(items.isEmpty()){body.addView(txt("—",10.5f,muted,true).apply{setPadding(dp(10),dp(5),dp(10),dp(5))});return}
        for(e in items){
            val title=sessionEventTitle(e.optString("event_type"),e.optString("label"));val detail=e.optString("detail").trim();val actor=e.optString("actor").ifBlank{"Hệ thống"};val localStatus=e.optString("local_status")
            val card=column(surface).apply{
                setPadding(dp(9),dp(6),dp(9),dp(6));background=outlineBg(surface,12)
                val top=row(surface).apply{gravity=Gravity.CENTER_VERTICAL;addView(txt(title,10.7f,navy,true),LinearLayout.LayoutParams(0,-2,1f));addView(txt(sessionEventTime(e),9.4f,muted,true))};addView(top,matchWrap())
                if(detail.isNotBlank()){addView(gap(2));addView(txt(detail,10f,ink,false))}
                addView(gap(2));val statusText=when(localStatus){"LOCAL_PENDING","PENDING","OFFLINE_PROVISIONAL"->" • Chờ đồng bộ";"RETRY"->" • Chờ gửi lại";"REVIEW_REQUIRED","CONFLICT"->" • Cần kiểm tra";"REJECTED"->" • Bị từ chối";else->""};addView(txt("Người thực hiện: $actor$statusText",9.2f,muted,false))
            }
            body.addView(card,matchWrap());body.addView(gap(3))
        }
    }

    private fun addRealtimeSessionTimeline(body:LinearLayout,mnv:String,ses:JSONObject){
        val host=column(bg)
        val date=ses.optString("business_date").ifBlank{operationalStore.businessDate()}
        fun renderTimeline(){
            host.suppressLayout(true)
            try{host.removeAllViews();addSessionTimeline(host,mnv,ses)}finally{host.suppressLayout(false)}
        }
        employeeTimelineRealtimeRefresh={dates->
            if(screenState=="EMPLOYEE"&&liveEmployeeMnv==mnv&&(date.isBlank()||date in dates))renderTimeline()
        }
        renderTimeline()
        body.addView(host,matchWrap())
    }

    // S49_BETA43_SESSION_ADMIN_CORRECTIONS
    // S49B_BETA43_KOTLIN_QUOTE_HOTFIX
    // S49C_BETA43_KOTLIN_SYNTAX_HOTFIX
    private fun pickSummary(s:JSONObject):String{val x=mutableListOf<String>();s.optString("pda_serial").trim().takeIf{it.isNotBlank()}?.let{x.add("PDA $it")};s.optString("user_pick").trim().takeIf{it.isNotBlank()}?.let{x.add("User $it")};return if(x.isEmpty())"Không" else x.joinToString(" • ")}
    private fun packSummary(s:JSONObject):String{val x=mutableListOf<String>();s.optString("pack_table").trim().takeIf{it.isNotBlank()}?.let{x.add("Bàn $it")};s.optString("user_pack").trim().takeIf{it.isNotBlank()}?.let{x.add("User $it")};return if(x.isEmpty())"Không" else x.joinToString(" • ")}
    private fun returnedSessionContext(ctx:JSONObject,r:BetaApiClient.Result):JSONObject?{val ss=r.json?.optJSONObject("session")?:return null;return JSONObject(ctx.toString()).put("session",ss).put("state",ss.optString("state"))}

    // S50_BETA44_OWNER_USER_PROJECTION_ADMIN_BULK_SYNC_VI
    // Beta84 OWNER confirmation policy: Vietnam HHmm with an inclusive ±2 minute tolerance.
    // The actual SUPERADMIN may alternatively authenticate with the fixed account password.
    private fun validActionTimePassword(value:String):Boolean{
        if(!Regex("""\d{4}""").matches(value))return false
        val now=java.time.ZonedDateTime.now(ZoneId.of("Asia/Ho_Chi_Minh"))
        val formatter=DateTimeFormatter.ofPattern("HHmm")
        return (-2L..2L).any{delta->now.plusMinutes(delta).format(formatter)==value}
    }
    private fun verifyActionPassword(actionLabel:String,after:()->Unit){
        val pw=input("Mật khẩu xác nhận",true)
        val dialog=AlertDialog.Builder(this).setTitle("Xác thực $actionLabel").setView(pw).setNegativeButton("Hủy",null).setPositiveButton("XÁC THỰC",null).create()
        dialog.setOnShowListener{val btn=dialog.getButton(AlertDialog.BUTTON_POSITIVE);btn.setOnClickListener{
            val value=pw.text.toString().trim()
            if(value.isBlank()){showError("Nhập mật khẩu xác nhận.");return@setOnClickListener}
            if(validActionTimePassword(value)){dialog.dismiss();after();return@setOnClickListener}
            if(!isActualSuper()){showError("Mật khẩu xác nhận không đúng.");return@setOnClickListener}
            btn.isEnabled=false;btn.text="ĐANG XÁC THỰC..."
            api.login(login,value){r->runOnUiThread{btn.isEnabled=true;btn.text="XÁC THỰC";if(!r.ok){showError("Mật khẩu xác nhận không đúng.");return@runOnUiThread};dialog.dismiss();after()}}
        }}
        dialog.show();pw.requestFocus()
    }
    private fun verifyDeletePassword(actionLabel:String,after:()->Unit)=verifyActionPassword(actionLabel,after)

    private fun mergeResourceSnapshot(ctx:JSONObject,snap:JSONObject):JSONObject{
        val out=JSONObject(ctx.toString());val base=snap.optJSONObject("session")?:out.optJSONObject("session")?:JSONObject();val s=JSONObject(base.toString())
        s.put("positions_v64",snap.optJSONArray("positions")?:JSONArray()).put("resource_assignments_v64",snap.optJSONArray("resource_assignments")?:JSONArray()).put("resource_options_v64",snap.optJSONObject("options")?:JSONObject()).put("main_position_v64",snap.optString("main_position"))
        out.put("session",s).put("state",s.optString("state",out.optString("state")));return out
    }
    private fun assignmentArray(s:JSONObject):JSONArray=s.optJSONArray("resource_assignments_v64")?:JSONArray()
    private fun positionArray(s:JSONObject):JSONArray=s.optJSONArray("positions_v64")?:JSONArray()
    private fun activePositions(s:JSONObject):List<JSONObject>{val out=mutableListOf<JSONObject>();val a=positionArray(s);for(i in 0 until a.length()){val x=a.optJSONObject(i)?:continue;if(x.optString("state").equals("ACTIVE",true))out.add(x)};return out}
    private fun activeAssignments(s:JSONObject,type:String=""):List<JSONObject>{val out=mutableListOf<JSONObject>();val a=assignmentArray(s);for(i in 0 until a.length()){val x=a.optJSONObject(i)?:continue;if(!x.optString("state").equals("ACTIVE",true))continue;if(type.isNotBlank()&&!x.optString("resource_type").equals(type,true))continue;out.add(x)};return out}
    // PDA-EXIT-001: only the exact current-session authoritative assignment snapshot may require a PDA exit check.
    // Legacy employee/profile/session scalar pda_serial is never evidence for the current session.
    private fun exitPdaDecision(s:JSONObject):SessionPdaAuthority.Decision=
        SessionPdaAuthority.decide(
            authoritativeAssignmentsPresent=s.has("resource_assignments_v64"),
            activePdaIds=activeAssignments(s,"PDA").map{it.optString("resource_id").trim()}.filter{it.isNotBlank()},
        )
    private fun exitPdaId(s:JSONObject):String=exitPdaDecision(s).activePdaId.orEmpty()
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
        val original=ctx.optJSONObject("session")?:return;val mnv=original.optString("mnv");val sessionId=original.optString("session_id");val generation=employeeLookupGeneration
        fun send(expectedVersion:Int,idem:String,retry:Int){
            if(generation!=employeeLookupGeneration||liveEmployeeMnv!=mnv)return
            val p=JSONObject().put("session_id",sessionId).put("mnv",mnv).put("expected_version",expectedVersion).put("idempotency_key",idem).put("audit_note",note).put("operations",ops)
            api.call("session_resource_mutate",p){r->runOnUiThread{
                if(generation!=employeeLookupGeneration||liveEmployeeMnv!=mnv)return@runOnUiThread
                if(handleAuth(r))return@runOnUiThread
                if(r.ok){TopNotice.show(this,"Đã cập nhật công việc trong ca.",TopNotice.Kind.SUCCESS);foregroundSync.requestSync();renderEmployee(mergeResourceSnapshot(ctx,r.json?:JSONObject()),null);return@runOnUiThread}
                if(r.error!="SESSION_CHANGED"){showError(r.error?:"Không cập nhật được phiên");return@runOnUiThread}
                val historical=ctx.optBoolean("historical_session")||original.optString("business_date").let{it.isNotBlank()&&it!=operationalStore.businessDate()}
                val refreshAction=if(historical)"historical_session_detail" else "employee_context"
                val refreshPayload=if(historical)JSONObject().put("session_id",sessionId).put("mnv",mnv).put("business_date",original.optString("business_date")) else JSONObject().put("mnv",mnv).put("include_options",false).put("include_labor",true)
                api.call(refreshAction,refreshPayload){fresh->runOnUiThread{
                    if(generation!=employeeLookupGeneration||liveEmployeeMnv!=mnv)return@runOnUiThread
                    if(handleAuth(fresh))return@runOnUiThread
                    if(!fresh.ok){showError("Không đối chiếu được đúng phiên mới nhất từ Service.");return@runOnUiThread}
                    val fc=if(historical)historicalEmployeeContext(fresh.json?:JSONObject()) else fresh.json
                    val fs=fc?.optJSONObject("session");val freshId=fs?.optString("session_id").orEmpty();val freshState=fc?.optString("state").orEmpty()
                    if(freshId!=sessionId||freshState!="ACTIVE"){showError("Đúng phiên đã chọn thực sự đã thay đổi trên Service. Mở lại phiên trước khi tiếp tục.");return@runOnUiThread}
                    if(retry>=1){showError("Phiên vừa được cập nhật đồng thời. Dữ liệu mới nhất đã được giữ; mở lại thao tác để xác nhận.");return@runOnUiThread}
                    send(fs?.optInt("version",expectedVersion)?:expectedVersion,idem,retry+1)
                }}
            }}
        }
        send(original.optInt("version"),UUID.randomUUID().toString(),0)
    }

    private fun sessionWorkEditor(ctx:JSONObject,mode:String,verified:Boolean=false,authoritativeOptions:JSONObject?=null){
        val s=ctx.optJSONObject("session")?:return;if(!s.optString("state").equals("ACTIVE",true)){showError("Phiên không còn hoạt động.");return}
        val edit=mode.equals("EDIT",true)
        if(edit&&!verified){verifyEditPassword("sửa thông tin trong ca"){sessionWorkEditor(ctx,mode,true,null)};return}
        if(authoritativeOptions==null){
            api.call("master_options",JSONObject().put("mnv",s.optString("mnv"))){r->runOnUiThread{
                if(handleAuth(r))return@runOnUiThread
                if(!r.ok){showError("Không đọc được danh sách tài nguyên khả dụng từ Service. Đồng bộ lại rồi thử lại.");return@runOnUiThread}
                sessionWorkEditor(ctx,mode,verified,r.json?:JSONObject())
            }}
            return
        }
        val server=authoritativeOptions
        fun arr(key:String):JSONArray=server.optJSONArray(key)?:JSONArray()
        fun ids(key:String):MutableList<String>{val out=mutableListOf<String>();val a=arr(key);for(i in 0 until a.length()){val x=a.opt(i);val v=when(x){is JSONObject->x.optString("id").ifBlank{x.optString("resource_id").ifBlank{x.optString("serial")}};else->a.optString(i)}.trim();if(v.isNotBlank()&&!out.contains(v))out.add(v)};out.sortWith(Comparator{a,b->naturalUserCompare(a,b)});return out}
        class PackMap(val table:String,val user:String,val used:Boolean)
        val normalPick=ids("user_picks");val usedPick=optionIds(arr("user_picks_reissue"));val pdaIds=ids("pdas");val normalMaps=mutableListOf<PackMap>();val usedMaps=mutableListOf<PackMap>()
        fun readMaps(a:JSONArray,used:Boolean,out:MutableList<PackMap>){for(i in 0 until a.length()){val x=a.optJSONObject(i)?:continue;val table=x.optString("table").ifBlank{x.optString("pack_table")}.trim();val user=x.optString("user_pack").ifBlank{x.optString("id").ifBlank{x.optString("resource_id")}}.trim();if(table.isNotBlank()&&user.isNotBlank()&&out.none{it.table==table&&it.user==user})out.add(PackMap(table,user,used||x.optBoolean("duplicate_user")))}}
        readMaps(arr("pack_tables"),false,normalMaps);readMaps(arr("pack_tables_reissue"),true,usedMaps)
        val activePda=activeAssignments(s,"PDA").firstOrNull();val activePick=activeAssignments(s,"USER_PICK").firstOrNull();val activeTable=activeAssignments(s,"PACK_TABLE").firstOrNull();val activePack=activeAssignments(s,"USER_PACK").firstOrNull()
        val activePos=activePositions(s);val activeKeys=activePos.map{it.optString("position_key").uppercase()}.toSet();val main=s.optString("main_position_v64").trim();val positionCatalog=(listOf("PICK" to "Pick","PACK" to "Pack")+(if(main.isNotBlank()&&!main.equals("Pick",true)&&!main.equals("Pack",true))listOf(foldLocal(main).ifBlank{main.uppercase()} to main)else emptyList())).distinctBy{it.first.uppercase()}
        val choices=mutableListOf<Pair<String,String>>()
        if(edit){choices.add("Ca" to "SHIFT");if(activePda!=null)choices.add("PDA" to "PDA");if(activePick!=null)choices.add("User Pick" to "PICK");if(activeTable!=null||activePack!=null)choices.add("Bàn Pack / User Pack" to "PACK")}
        else{if(activePda==null)choices.add("PDA" to "PDA");if(activePick==null)choices.add("User Pick" to "PICK");if(activeTable==null&&activePack==null)choices.add("Pack" to "PACK");if(positionCatalog.any{it.first.uppercase() !in activeKeys})choices.add("Vị trí trong ca" to "POSITION")}
        if(choices.isEmpty()){showError(if(edit)"Không có thông tin hiện tại phù hợp để sửa." else "Không còn nội dung phù hợp để thêm.");return}
        val box=column(surface).apply{setPadding(dp(10),dp(5),dp(10),dp(8))};box.addView(info(if(edit)"Chọn đúng nội dung cần sửa. Chỉ control liên quan mới hiển thị." else "Chọn nội dung cần thêm. Chỉ phần cấu hình tương ứng mới mở."));box.addView(gap(7))
        val selector=spinner((listOf(if(edit)"Chọn nội dung cần sửa" else "Chọn nội dung cần thêm")+choices.map{it.first}).toTypedArray());box.addView(selector,matchWrap());box.addView(gap(7));val host=column(surface);box.addView(host,matchWrap())
        var makeOps:(()->JSONArray)?=null;var validationError=""
        fun replaceOrAdd(active:JSONObject?,type:String,id:String,duplicate:Boolean=false):JSONObject?{if(id.isBlank())return null;return if(active==null)JSONObject().put("op","ADD_RESOURCE").put("resource_type",type).put("resource_id",id).put("duplicate_user",duplicate) else if(active.optString("resource_id")!=id)JSONObject().put("op","REPLACE_RESOURCE").put("assignment_id",active.optString("assignment_id")).put("resource_type",type).put("new_resource_id",id).put("reason","Cập nhật ${resourceLabel(type)} trong ca").put("disposition","USED").put("duplicate_user",duplicate) else null}
        fun render(kind:String){
            host.removeAllViews();makeOps=null;validationError=""
            when(kind){
                "SHIFT"->{val values=listOf("Ca 1","Ca HC","Ca 2");val sp=spinner(values.toTypedArray());selectByValue(sp,values,s.optString("shift"));host.addView(labelled("Ca",sp));makeOps={JSONArray().apply{val v=sp.selectedItem?.toString().orEmpty();if(v!=s.optString("shift"))put(JSONObject().put("op","UPDATE_SHIFT").put("shift",v))}}}
                "PDA"->{val values=pdaIds.toMutableList();activePda?.optString("resource_id")?.takeIf{it.isNotBlank()&&it !in values}?.let{values.add(0,it)};val sp=spinner((listOf("Chọn PDA")+values).toTypedArray());activePda?.optString("resource_id")?.let{val at=values.indexOf(it);if(at>=0)sp.setSelection(at+1)};host.addView(labelled(if(edit)"PDA mới" else "PDA",sp));makeOps={val id=values.getOrNull(sp.selectedItemPosition-1).orEmpty();JSONArray().apply{replaceOrAdd(activePda,"PDA",id)?.let{put(it)}}}}
                "PICK"->{var chosenUsed="";var pdaSp:Spinner?=null;var pdaValues=emptyList<String>();val pickSp=spinner((listOf("Chọn User Pick")+normalPick).toTypedArray());activePick?.optString("resource_id")?.let{val at=normalPick.indexOf(it);if(at>=0)pickSp.setSelection(at+1)}
                    fun showPick(id:String){chosenUsed=id;pickSp.adapter=ArrayAdapter(this,android.R.layout.simple_spinner_dropdown_item,arrayOf(id));pickSp.setSelection(0);TopNotice.show(this,"Đã chọn User Pick $id.",TopNotice.Kind.INFO)}
                    val row=row(surface).apply{gravity=Gravity.CENTER_VERTICAL;addView(pickSp,LinearLayout.LayoutParams(0,dp(48),1.25f).apply{marginEnd=dp(5)});addView(compactReissueButton("Phát lại",usedPick.isNotEmpty()){showReissueChooser("Phát lại User Pick",usedPick){i->showPick(usedPick[i])}},LinearLayout.LayoutParams(0,dp(44),.75f))};host.addView(labelled("User Pick",row));if(activePda==null){host.addView(gap(6));pdaValues=pdaIds;val sp=spinner((listOf("Chọn PDA bắt buộc")+pdaValues).toTypedArray());pdaSp=sp;host.addView(labelled("PDA — bắt buộc khi cấp User Pick",sp))}
                    makeOps={val id=chosenUsed.ifBlank{normalPick.getOrNull(pickSp.selectedItemPosition-1).orEmpty()};val out=JSONArray();if(activePda==null){val pda=pdaValues.getOrNull((pdaSp?.selectedItemPosition?:0)-1).orEmpty();replaceOrAdd(null,"PDA",pda)?.let{out.put(it)}};replaceOrAdd(activePick,"USER_PICK",id,chosenUsed.isNotBlank())?.let{out.put(it)};out}}
                "PACK"->{
                    var tableSp:Spinner?=null
                    var userSp:Spinner?=null
                    var currentRows=normalMaps.toList()
                    var duplicate=false
                    fun rebuild(preferredTable:String="",preferredUser:String="",used:Boolean=false){
                        host.removeAllViews()
                        duplicate=used
                        currentRows=if(used){(normalMaps+usedMaps.filter{it.table==preferredTable&&it.user==preferredUser}).distinctBy{it.table+"|"+it.user}}else normalMaps
                        val currentTable=activeTable?.optString("resource_id").orEmpty()
                        val allTables=currentRows.map{it.table}.toMutableList()
                        if(currentTable.isNotBlank()&&currentTable !in allTables)allTables.add(currentTable)
                        val tables=allTables.distinct().sortedWith(Comparator{a,b->naturalUserCompare(a,b)})
                        val t=spinner((listOf("Chọn Bàn Pack")+tables).toTypedArray());tableSp=t
                        val target=preferredTable.ifBlank{currentTable}
                        tables.indexOf(target).takeIf{it>=0}?.let{t.setSelection(it+1)}
                        host.addView(labelled("Bàn Pack",t));host.addView(gap(5))
                        val userHost=column(surface);host.addView(userHost,matchWrap())
                        fun users(pref:String=""){
                            userHost.removeAllViews()
                            val table=tables.getOrNull(t.selectedItemPosition-1).orEmpty()
                            val rows=currentRows.filter{it.table==table}.sortedWith(Comparator{a,b->naturalUserCompare(a.user,b.user)})
                            val u=spinner((listOf("Chọn User Pack")+rows.map{it.user}).toTypedArray());userSp=u
                            val currentUser=activePack?.optString("resource_id").orEmpty()
                            val targetUser=pref.ifBlank{currentUser}
                            rows.indexOfFirst{it.user==targetUser}.takeIf{it>=0}?.let{u.setSelection(it+1)}
                            val rr=row(surface).apply{
                                gravity=Gravity.CENTER_VERTICAL
                                addView(u,LinearLayout.LayoutParams(0,dp(48),1.25f).apply{marginEnd=dp(5)})
                                addView(compactReissueButton("Phát lại",usedMaps.isNotEmpty()){
                                    val labels=usedMaps.map{"${it.table} – ${it.user}"}
                                    showReissueChooser("Phát lại User Pack",labels){i->val m=usedMaps[i];rebuild(m.table,m.user,true)}
                                },LinearLayout.LayoutParams(0,dp(44),.75f))
                            }
                            userHost.addView(labelled("User Pack",rr))
                        }
                        t.onItemSelectedListener=object:android.widget.AdapterView.OnItemSelectedListener{
                            override fun onItemSelected(p:android.widget.AdapterView<*>?,v:View?,i:Int,id:Long){users(if(tables.getOrNull(i-1)==preferredTable)preferredUser else "")}
                            override fun onNothingSelected(p:android.widget.AdapterView<*>?)=Unit
                        }
                        users(preferredUser)
                    }
                    rebuild()
                    makeOps={
                        validationError=""
                        val table=(tableSp?.selectedItem?.toString()?:"").takeIf{it!="Chọn Bàn Pack"}.orEmpty().trim()
                        val user=(userSp?.selectedItem?.toString()?:"").takeIf{it!="Chọn User Pack"}.orEmpty().trim()
                        val valid=currentRows.firstOrNull{it.table==table&&it.user==user}
                        when{
                            table.isBlank()||user.isBlank()->{validationError="Chọn đủ Bàn Pack và User Pack đúng theo cấu hình hiện tại.";JSONArray()}
                            valid==null->{validationError="Bàn Pack / User Pack không còn khớp cấu hình hiện tại. Chọn lại đúng cặp.";JSONArray()}
                            else->JSONArray().apply{
                                replaceOrAdd(activeTable,"PACK_TABLE",table)?.let{put(it)}
                                replaceOrAdd(activePack,"USER_PACK",user,duplicate||valid.used)?.let{put(it)}
                            }
                        }
                    }
                }
                "POSITION"->{val available=positionCatalog.filter{it.first.uppercase() !in activeKeys};val labels=available.map{it.second};val sp=spinner((listOf("Chọn vị trí cần thêm")+labels).toTypedArray());host.addView(labelled("Vị trí trong ca",sp));makeOps={val x=available.getOrNull(sp.selectedItemPosition-1);JSONArray().apply{if(x!=null)put(JSONObject().put("op","ADD_POSITION").put("position_key",x.first.uppercase()).put("position_label",x.second))}}}
            }
        }
        selector.onItemSelectedListener=object:android.widget.AdapterView.OnItemSelectedListener{override fun onItemSelected(p:android.widget.AdapterView<*>?,v:View?,i:Int,id:Long){render(choices.getOrNull(i-1)?.second.orEmpty())};override fun onNothingSelected(p:android.widget.AdapterView<*>?)=Unit}
        val editDialog=AlertDialog.Builder(this).setTitle(if(edit)"Sửa thông tin trong ca" else "Thêm thông tin trong ca").setView(ScrollView(this).apply{addView(box)}).setNegativeButton("Hủy",null).setPositiveButton(if(edit)"LƯU" else "THÊM",null).create()
        editDialog.setOnShowListener{
            editDialog.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener{
                validationError=""
                val ops=makeOps?.invoke()?:JSONArray()
                if(validationError.isNotBlank()){showError(validationError);return@setOnClickListener}
                if(ops.length()==0){showError("Chọn nội dung và giá trị cần ${if(edit)"sửa" else "thêm"}.");return@setOnClickListener}
                if(ops.toString().contains("\"resource_type\":\"USER_PICK\"")&&activePda==null&&!ops.toString().contains("\"resource_type\":\"PDA\"")){showError("User Pick bắt buộc phải có PDA.");return@setOnClickListener}
                editDialog.dismiss()
                submitResourceMutation(ctx,ops,if(edit)"Sửa thông tin trong ca" else "Thêm thông tin trong ca")
            }
        }
        editDialog.show()
    }
    private fun deleteSessionWork(ctx:JSONObject){
        val s=ctx.optJSONObject("session")?:return;val assignments=activeAssignments(s);val positions=activePositions(s)
        class Item(val label:String,val assignment:JSONObject?=null,val position:JSONObject?=null)
        val items=mutableListOf<Item>();for(a in assignments)items.add(Item("${resourceLabel(a.optString("resource_type"))}: ${a.optString("resource_id")}",assignment=a));for(p in positions)items.add(Item("Vị trí: ${p.optString("position_label").ifBlank{p.optString("position_key")}}",position=p))
        if(items.isEmpty()){showError("Phiên không có thông tin công việc có thể xóa.");return}
        val box=column(surface).apply{setPadding(dp(10),dp(5),dp(10),dp(8))};box.addView(info("Chọn đúng một nội dung đang tồn tại. Chỉ phần xác nhận liên quan mới hiển thị."));box.addView(gap(7));val selector=spinner((listOf("Chọn nội dung cần xóa")+items.map{it.label}).toTypedArray());box.addView(selector,matchWrap());box.addView(gap(7));val host=column(surface);box.addView(host,matchWrap())
        var selected:Item?=null;var disposition:Spinner?=null;var reason:EditText?=null
        fun focusReason(r:EditText){
            r.post{
                r.requestFocus();r.setSelection(r.text.length)
                val imm=getSystemService(INPUT_METHOD_SERVICE) as? android.view.inputmethod.InputMethodManager
                imm?.showSoftInput(r,android.view.inputmethod.InputMethodManager.SHOW_IMPLICIT)
            }
        }
        fun render(i:Int){
            host.removeAllViews();selected=items.getOrNull(i-1);disposition=null;reason=null
            val x=selected?:return
            if(x.assignment!=null){
                val d=spinner(arrayOf("Đã sử dụng / có sản lượng","Cấp nhầm / chưa sử dụng"))
                val r=input("Lý do xóa",false);disposition=d;reason=r
                host.addView(labelled("Xử lý tài nguyên sau khi xóa",d));host.addView(gap(6));host.addView(r,matchWrap());focusReason(r)
            }else{
                val r=input("Lý do xóa vị trí",false);reason=r;host.addView(r,matchWrap());focusReason(r)
            }
        }
        selector.onItemSelectedListener=object:android.widget.AdapterView.OnItemSelectedListener{override fun onItemSelected(p:android.widget.AdapterView<*>?,v:View?,i:Int,id:Long){render(i)};override fun onNothingSelected(p:android.widget.AdapterView<*>?)=Unit}
        val full=smallButton("XÓA TOÀN BỘ PHIÊN VÀO – RA",red);box.addView(gap(10));box.addView(full,matchWrap());var dialog:AlertDialog?=null
        full.setOnClickListener{val r=input("Lý do xóa toàn bộ phiên",false).apply{setText("Xóa phiên theo xác nhận thực tế")};AlertDialog.Builder(this).setTitle("Xóa toàn bộ phiên?").setView(r).setNegativeButton("Hủy",null).setPositiveButton("XÁC NHẬN"){_,_->if(r.text.toString().trim().length<3){showError("Nhập lý do xóa phiên.");return@setPositiveButton};verifyDeletePassword("xóa toàn bộ phiên"){api.call("attendance_session_delete",JSONObject().put("session_id",s.optString("session_id")).put("reason",r.text.toString().trim()).put("idempotency_key",UUID.randomUUID().toString())){x->runOnUiThread{if(!x.ok){showError(x.error?:"Không xóa được phiên");return@runOnUiThread};dialog?.dismiss();TopNotice.show(this,"Đã xóa phiên; audit chi tiết vẫn được giữ.",TopNotice.Kind.SUCCESS);employeeScan()}}}}.show()}
        dialog=AlertDialog.Builder(this).setTitle("Xóa thông tin trong ca").setView(ScrollView(this).apply{addView(box)}).setNegativeButton("Hủy",null).setPositiveButton("XÓA",null).create()
        dialog?.setOnShowListener{
            dialog?.getButton(AlertDialog.BUTTON_POSITIVE)?.setOnClickListener{
                val x=selected?:run{showError("Chọn nội dung cần xóa.");return@setOnClickListener}
                val why=reason?.text?.toString()?.trim().orEmpty()
                if(why.length<2){showError("Nhập lý do xóa.");reason?.let(::focusReason);return@setOnClickListener}
                val ops=JSONArray()
                if(x.assignment!=null)ops.put(JSONObject().put("op","REMOVE_RESOURCE").put("assignment_id",x.assignment.optString("assignment_id")).put("resource_type",x.assignment.optString("resource_type")).put("resource_id",x.assignment.optString("resource_id")).put("reason",why).put("disposition",if(disposition?.selectedItemPosition==1)"AVAILABLE" else "USED"))
                else x.position?.let{ops.put(JSONObject().put("op","REMOVE_POSITION").put("position_key",it.optString("position_key")).put("reason",why))}
                dialog?.dismiss()
                verifyDeletePassword("xóa thông tin trong ca"){submitResourceMutation(ctx,ops,"Xóa thông tin trong ca")}
            }
        }
        dialog?.show()
    }
    private fun editableTime(iso:String):String=runCatching{Instant.parse(iso).atZone(ZoneId.of("Asia/Ho_Chi_Minh")).format(DateTimeFormatter.ofPattern("dd/MM/yyyy HH:mm:ss"))}.getOrDefault(iso)
    private fun parseEditableTime(v:String):String?=runCatching{java.time.LocalDateTime.parse(v.trim(),DateTimeFormatter.ofPattern("dd/MM/yyyy HH:mm:ss")).atZone(ZoneId.of("Asia/Ho_Chi_Minh")).toInstant().toString()}.getOrNull()
    private fun editAttendanceTime(ctx:JSONObject,field:String,verified:Boolean=false){
        if(!isAdmin())return;if(!verified){verifyEditPassword("sửa thời gian vào / ra ca"){editAttendanceTime(ctx,field,true)};return};val ses=ctx.optJSONObject("session")?:return;val old=ses.optString(field);if(old.isBlank()){showError("Chưa có mốc thời gian để sửa.");return};val box=column(surface).apply{setPadding(dp(10),dp(4),dp(10),dp(8))};val time=input("dd/MM/yyyy HH:mm:ss",false).apply{setText(editableTime(old))};val reason=input("Lý do điều chỉnh",false).apply{setText("Điều chỉnh theo xác nhận thực tế")};box.addView(info("Giờ ghi nhận ban đầu vẫn được giữ trong lịch sử audit. Sheet RA/VÀO chỉ hiển thị giờ sửa sau cùng."));box.addView(gap(7));box.addView(labelled(if(field=="enter_at")"Giờ vào ca mới" else "Giờ ra ca mới",time));box.addView(gap(7));box.addView(labelled("Lý do",reason));AlertDialog.Builder(this).setTitle(if(field=="enter_at")"Sửa giờ vào ca" else "Sửa giờ ra ca").setView(box).setNegativeButton("Hủy",null).setPositiveButton("LƯU"){_,_->val parsed=parseEditableTime(time.text.toString());if(parsed==null){showError("Thời gian phải đúng định dạng dd/MM/yyyy HH:mm:ss.");return@setPositiveButton};if(reason.text.toString().trim().length<3){showError("Nhập lý do điều chỉnh.");return@setPositiveButton};api.call("attendance_time_correct",JSONObject().put("session_id",ses.optString("session_id")).put("field",field).put("corrected_at",parsed).put("reason",reason.text.toString().trim()).put("idempotency_key",UUID.randomUUID().toString())){r->runOnUiThread{if(handleAuth(r))return@runOnUiThread;if(!r.ok){showError(r.error?:"Không sửa được thời gian");return@runOnUiThread};TopNotice.show(this,"Đã sửa thời gian và lưu audit.",TopNotice.Kind.SUCCESS);foregroundSync.requestSync();val next=returnedSessionContext(ctx,r);if(next!=null)renderEmployee(next,PdaLocalProjection.resourceOptions(this,ses.optString("mnv")))else loadEmployee(ses.optString("mnv"))}}}.show()
    }

    private fun editAttendanceTimes(ctx:JSONObject){
        if(!isAdmin())return;val ses=ctx.optJSONObject("session")?:return;val choices=mutableListOf<Pair<String,String>>();if(ses.optString("enter_at").isNotBlank())choices.add("Giờ vào ca" to "enter_at");if(ses.optString("exit_at").isNotBlank())choices.add("Giờ ra ca" to "exit_at")
        if(choices.isEmpty()){showError("Chưa có mốc thời gian để sửa.");return};if(choices.size==1){editAttendanceTime(ctx,choices[0].second);return}
        AlertDialog.Builder(this).setTitle("Sửa giờ vào – ra ca").setItems(choices.map{it.first}.toTypedArray()){_,which->choices.getOrNull(which)?.second?.let{editAttendanceTime(ctx,it)}}.setNegativeButton("Hủy",null).show()
    }

    private fun deleteExitRecord(ctx:JSONObject){
        if(!isAdmin())return;val ses=ctx.optJSONObject("session")?:return;val mnv=ses.optString("mnv");val reason=input("Lý do xóa ghi nhận ra ca",false).apply{setText("Bắn nhầm ra ca")}
        val box=column(surface).apply{setPadding(dp(10),dp(4),dp(10),dp(8));addView(info("Mốc RA sẽ bị xóa khỏi sheet RA/VÀO và phiên được mở lại. Nhật ký kiểm toán vẫn được giữ."));addView(gap(7));addView(reason,matchWrap())}
        AlertDialog.Builder(this).setTitle("Hủy ghi nhận RA CA?").setView(box).setNegativeButton("Hủy",null).setPositiveButton("TIẾP TỤC"){_,_->if(reason.text.toString().trim().length<3){showError("Nhập lý do xóa.");return@setPositiveButton};verifyDeletePassword("xóa ghi nhận ra ca"){api.call("attendance_exit_delete",JSONObject().put("session_id",ses.optString("session_id")).put("reason",reason.text.toString().trim()).put("idempotency_key",UUID.randomUUID().toString())){r->runOnUiThread{if(handleAuth(r))return@runOnUiThread;if(!r.ok){showError(r.error?:"Không xóa được mốc ra ca");return@runOnUiThread};val conflicts=r.json?.optJSONArray("resource_reacquire_conflicts")?:JSONArray();TopNotice.show(this,if(conflicts.length()>0)"Đã mở lại phiên; một số tài nguyên không thể tự cấp lại." else "Đã xóa mốc ra ca và mở lại phiên.",if(conflicts.length()>0)TopNotice.Kind.WARNING else TopNotice.Kind.SUCCESS);foregroundSync.requestSync();loadEmployee(mnv)}}}}.show()
    }

    private fun workInShiftText(ctx:JSONObject):String{val s=ctx.optJSONObject("session")?:JSONObject();return activePositionLabels(s).joinToString(" • ").ifBlank{"Không"}}
    private fun resourceStateRows(s:JSONObject):List<Pair<String,String>> = resourceListText(s)
    private fun shiftResourceValue(s:JSONObject,type:String,ended:Boolean):String{
        val rows=if(ended)visibleAssignments(s,type) else activeAssignments(s,type)
        val value=rows.map{it.optString("resource_id").trim()}.filter{it.isNotBlank()}.distinct().joinToString(" • ")
        val direct=when(type.uppercase()){ "PDA"->s.optString("pda_serial");"USER_PICK"->s.optString("user_pick");"PACK_TABLE"->s.optString("pack_table");"USER_PACK"->s.optString("user_pack");else->"" }.trim()
        return value.ifBlank{direct}.ifBlank{"—"}
    }
    private fun shiftInfoRows(s:JSONObject,ended:Boolean)=listOf(
        "Ca" to dash(s.optString("shift")),
        "Thời gian vào" to formatIso(s.optString("enter_at")),
        "Thời gian ra" to if(ended)formatIso(s.optString("exit_at")) else "—"
    )
    private fun workInfoRows(s:JSONObject,ended:Boolean,employee:JSONObject?=null):List<Pair<String,String>>{
        val positions=(if(ended)allPositionLabels(s) else activePositionLabels(s)).distinct().toMutableList()
        if(positions.isEmpty()){if(s.optString("pda_serial").isNotBlank()||s.optString("user_pick").isNotBlank())positions.add("Pick");if(s.optString("pack_table").isNotBlank()||s.optString("user_pack").isNotBlank())positions.add("Pack")}
        val rawPick=shiftResourceValue(s,"USER_PICK",ended)
        val hasPick=positions.any{it.equals("Pick",true)}||shiftResourceValue(s,"PDA",ended)!="—"
        val phone=dash(employee?.optString("phone").orEmpty())
        val employeeName=dash(employee?.optString("full_name").orEmpty())
        val pickDisplay=if(hasPick&&rawPick=="—")"Tài khoản $phone / $employeeName" else rawPick
        return listOf("Vị trí trong ca" to if(positions.isEmpty())"Làm theo vị trí chính" else positions.joinToString(" & "),"User Pick" to pickDisplay,"PDA" to shiftResourceValue(s,"PDA",ended),"Bàn Pack" to shiftResourceValue(s,"PACK_TABLE",ended),"User Pack" to shiftResourceValue(s,"USER_PACK",ended))
    }
    private fun sessionInfoPanel(title:String,items:List<Pair<String,String>>,completed:Boolean)=column(surface).apply{
        val fill=if(completed)Color.rgb(236,253,245) else Color.rgb(255,251,235)
        val stroke=if(completed)Color.rgb(74,222,128) else Color.rgb(245,158,11)
        setPadding(dp(11),dp(9),dp(11),dp(9))
        background=GradientDrawable().apply{setColor(fill);cornerRadius=dp(13).toFloat();setStroke(dp(1),stroke)}
        addView(txt(title,11.4f,if(completed)green else orange,true));addView(gap(4))
        items.forEach{(key,raw)->
            val r=row(Color.TRANSPARENT).apply{gravity=Gravity.TOP;setPadding(0,dp(3),0,dp(3))}
            r.addView(txt("$key:",9.5f,muted,true),LinearLayout.LayoutParams(0,-2,.46f))
            r.addView(txt(dash(raw),10f,ink,true).apply{maxLines=5;ellipsize=null},LinearLayout.LayoutParams(0,-2,.54f).apply{marginStart=dp(5)})
            addView(r,matchWrap())
        }
        if(!completed)startAnimation(android.view.animation.AlphaAnimation(1f,.92f).apply{duration=900;repeatMode=android.view.animation.Animation.REVERSE;repeatCount=android.view.animation.Animation.INFINITE})
    }
    private fun usableExitSession(session:JSONObject?,mnvRaw:String):Boolean{
        val s=session?:return false
        val mnv=mnvRaw.trim();val sid=s.optString("session_id").trim();val who=s.optString("mnv").trim()
        return mnv.isNotBlank()&&sid.isNotBlank()&&s.optString("state").equals("ACTIVE",true)&&(who.isBlank()||who==mnv)
    }

    private fun resolveActiveSessionForExit(mnvRaw:String,localSession:JSONObject,done:(JSONObject?,JSONObject?,String?)->Unit){
        val mnv=mnvRaw.trim()
        if(mnv.isBlank()){done(null,null,"MNV_REQUIRED");return}
        val generation=employeeLookupGeneration

        fun finishWithAuthoritativeResources(candidate:JSONObject?,activeLabor:JSONObject?){
            if(!usableExitSession(candidate,mnv)){
                done(null,activeLabor,"SESSION_EXIT_FIELDS_REQUIRED");return
            }
            val session=JSONObject(candidate!!.toString())
            val decision=exitPdaDecision(session)
            if(decision.authoritative){
                done(session,activeLabor,null);return
            }
            val sessionId=session.optString("session_id").trim()
            if(sessionId.isBlank()){done(null,activeLabor,"SESSION_EXIT_FIELDS_REQUIRED");return}
            api.call("session_resource_snapshot",JSONObject().put("session_id",sessionId).put("mnv",mnv)){snap->runOnUiThread{
                if(generation!=employeeLookupGeneration||liveEmployeeMnv.trim()!=mnv){done(null,null,"SESSION_EXIT_CONTEXT_STALE");return@runOnUiThread}
                if(handleAuth(snap)){done(null,null,"UNAUTHORIZED");return@runOnUiThread}
                if(!snap.ok){done(null,activeLabor,snap.error?:"SESSION_RESOURCE_SNAPSHOT_FAILED");return@runOnUiThread}
                val raw=snap.json?:JSONObject()
                val serviceSession=raw.optJSONObject("session")
                if(serviceSession==null||serviceSession.optString("session_id").trim()!=sessionId||serviceSession.optString("mnv").trim()!=mnv||!serviceSession.optString("state").equals("ACTIVE",true)){
                    done(null,activeLabor,"SESSION_RESOURCE_SNAPSHOT_MISMATCH");return@runOnUiThread
                }
                val merged=mergeResourceSnapshot(JSONObject().put("session",serviceSession).put("state","ACTIVE"),raw).optJSONObject("session")
                if(!usableExitSession(merged,mnv)||merged?.has("resource_assignments_v64")!=true){
                    done(null,activeLabor,"SESSION_RESOURCE_AUTHORITY_REQUIRED");return@runOnUiThread
                }
                done(JSONObject(merged.toString()),activeLabor,null)
            }}
        }

        if(usableExitSession(localSession,mnv)){
            finishWithAuthoritativeResources(JSONObject(localSession.toString()),null);return
        }
        api.call("employee_context",JSONObject().put("mnv",mnv).put("include_options",false).put("include_labor",true)){r->runOnUiThread{
            if(generation!=employeeLookupGeneration||liveEmployeeMnv.trim()!=mnv){done(null,null,"SESSION_EXIT_CONTEXT_STALE");return@runOnUiThread}
            if(handleAuth(r)){done(null,null,"UNAUTHORIZED");return@runOnUiThread}
            if(!r.ok){done(null,null,r.error?:"SESSION_EXIT_RESOLVE_FAILED");return@runOnUiThread}
            val remote=r.json?:JSONObject();val resolved=remote.optJSONObject("session")
            if(!usableExitSession(resolved,mnv)){
                val code=if(remote.optString("state").equals("ACTIVE",true))"SESSION_EXIT_FIELDS_REQUIRED" else "SESSION_NOT_ACTIVE"
                done(null,remote.optJSONObject("active_labor"),code);return@runOnUiThread
            }
            finishWithAuthoritativeResources(resolved,remote.optJSONObject("active_labor"))
        }}
    }

    private fun renderActive(body:LinearLayout,ctx:JSONObject){
        val s=ctx.optJSONObject("session")?:JSONObject();val mnv=s.optString("mnv").ifBlank{ctx.optJSONObject("employee")?.optString("mnv").orEmpty()}.trim()
        val exit=smallButton("Ra ca",red)
        fun releaseExitGuard(){exitInFlightMnvs.remove(mnv);exit.isEnabled=true}
        fun doExit(resolved:JSONObject,status:String){
            if(!usableExitSession(resolved,mnv)){releaseExitGuard();showError("SESSION_EXIT_FIELDS_REQUIRED");return}
            val gen=employeeLookupGeneration
            api.call("session_exit_v2",JSONObject().put("session_id",resolved.optString("session_id")).put("mnv",mnv).put("expected_version",resolved.optInt("version")).put("pda_exit_status",status).put("idempotency_key",UUID.randomUUID().toString())){r->runOnUiThread{
                releaseExitGuard()
                if(!r.ok){if(r.error?.contains("OPEN_LABOR_BLOCKS_EXIT")==true)openLaborExact(mnv,resolved.optString("session_id")) else if(r.error=="SESSION_CHANGED"||r.error=="SESSION_EXIT_CONFLICT")loadEmployee(mnv,forceRefresh=true)else showError(r.error?:"RA_CA_FAILED");return@runOnUiThread}
                TopNotice.show(this,"Đã ghi nhận ra ca.",TopNotice.Kind.SUCCESS);foregroundSync.requestSync()
                if(gen==employeeLookupGeneration&&liveEmployeeMnv==mnv)scheduleAttendanceAutoReset(mnv,gen)
            }}
        }
        exit.setOnClickListener{
            if(mnv.isBlank()){showError("MNV_REQUIRED");return@setOnClickListener}
            if(!exitInFlightMnvs.add(mnv))return@setOnClickListener
            exit.isEnabled=false
            resolveActiveSessionForExit(mnv,s){resolved,remoteLabor,error->
                if(error!=null||resolved==null){releaseExitGuard();if(error!="SESSION_EXIT_CONTEXT_STALE"&&error!="UNAUTHORIZED")showError(error?:"SESSION_EXIT_RESOLVE_FAILED");return@resolveActiveSessionForExit}
                if(remoteLabor!=null){releaseExitGuard();openLaborExact(mnv,resolved.optString("session_id"));return@resolveActiveSessionForExit}
                val pdaId=exitPdaId(resolved)
                if(pdaId.isBlank()){doExit(resolved,"");return@resolveActiveSessionForExit}
                val expected=resolved.optString("pda_enter_status");val arr=MasterDataCache.resourceOptions(this).optJSONArray("pda_statuses")?:JSONArray();val statuses=mutableListOf<String>()
                for(i in 0 until arr.length()){val v=arr.optString(i).trim();if(v.isNotBlank()&&!statuses.contains(v))statuses.add(v)}
                if(expected.isNotBlank()&&!statuses.contains(expected))statuses.add(0,expected)
                if(statuses.isEmpty()){releaseExitGuard();showError("PDA_EXIT_STATUS_REQUIRED");return@resolveActiveSessionForExit}
                val sp=spinner(statuses.toTypedArray())
                val wrap=column(surface).apply{setPadding(dp(12),dp(6),dp(12),dp(5));addView(txt("PDA $pdaId",12f,navy,true));addView(labelled("Tình trạng PDA hiện tại",sp))}
                val dialog=AlertDialog.Builder(this).setTitle("Đối chiếu PDA trước khi RA CA").setView(wrap)
                    .setNegativeButton("Hủy"){_,_->releaseExitGuard()}
                    .setPositiveButton("KIỂM TRA & RA CA"){_,_->doExit(resolved,sp.selectedItem?.toString().orEmpty())}.create()
                dialog.setOnCancelListener{releaseExitGuard()}
                dialog.show()
            }
        }
        val actions=row(bg)
        actions.addView(smallButton("Thêm",teal).apply{setOnClickListener{sessionWorkEditor(ctx,"ADD")}},LinearLayout.LayoutParams(0,dp(40),1f).apply{marginEnd=dp(2)})
        actions.addView(smallButton("Sửa",navy).apply{setOnClickListener{sessionWorkEditor(ctx,"EDIT")}},LinearLayout.LayoutParams(0,dp(40),1f).apply{marginStart=dp(2);marginEnd=dp(2)})
        actions.addView(smallButton("Xóa",orange).apply{setOnClickListener{deleteSessionWork(ctx)}},LinearLayout.LayoutParams(0,dp(40),1f).apply{marginStart=dp(2)})
        body.addView(actions,matchWrap());body.addView(gap(5));body.addView(exit,matchWrap());body.addView(gap(8))
        body.addView(sessionInfoPanel("THÔNG TIN CA",shiftInfoRows(s,false),false));body.addView(gap(7))
        body.addView(sessionInfoPanel("THÔNG TIN CÔNG VIỆC",workInfoRows(s,false,ctx.optJSONObject("employee")),false));body.addView(gap(8))
        addRealtimeSessionTimeline(body,mnv,s)
    }


    private fun renderEnded(body:LinearLayout,ctx:JSONObject){
        val s=ctx.optJSONObject("session")?:JSONObject();val mnv=s.optString("mnv")
        body.addView(sessionInfoPanel("THÔNG TIN CA",shiftInfoRows(s,true),true));body.addView(gap(7))
        body.addView(sessionInfoPanel("THÔNG TIN CÔNG VIỆC",workInfoRows(s,true,ctx.optJSONObject("employee")),true));body.addView(gap(8))
        addRealtimeSessionTimeline(body,mnv,s);body.addView(gap(8))
        if(isAdmin()){val act=row(bg);act.addView(smallButton("Sửa giờ vào",navy).apply{setOnClickListener{editAttendanceTime(ctx,"enter_at")}},LinearLayout.LayoutParams(0,dp(40),1f).apply{marginEnd=dp(2)});act.addView(smallButton("Sửa giờ ra",teal).apply{setOnClickListener{editAttendanceTime(ctx,"exit_at")}},LinearLayout.LayoutParams(0,dp(40),1f).apply{marginStart=dp(2)});body.addView(act,matchWrap());body.addView(gap(5));body.addView(primary("XÓA GHI NHẬN RA CA",red){deleteExitRecord(ctx)},matchWrap())}
        body.addView(gap(5));body.addView(primary("XÓA TOÀN BỘ PHIÊN",red){deleteSessionWork(ctx)},matchWrap())
    }


    private fun renderEnter(body:LinearLayout,ctx:JSONObject,masters:JSONObject){
        val e=ctx.optJSONObject("employee")?:JSONObject();val mnv=e.optString("mnv");val main=e.optString("main_position").trim();body.addView(section("PHÂN CÔNG TRONG CA"))
        val now=java.time.LocalTime.now(ZoneId.of("Asia/Ho_Chi_Minh"));var shiftValue=when{now.isBefore(java.time.LocalTime.of(8,0))->"Ca 1";now.isBefore(java.time.LocalTime.of(10,0))->"Ca HC";else->"Ca 2"}
        val mainPick=main.equals("Pick",true);val mainPack=main.equals("Pack",true);val third=if(mainPick||mainPack)"Không" else main.ifBlank{"Không"};val thirdKey=if(third=="Không")"NONE" else foldLocal(third).ifBlank{third.uppercase()};val positionChoices=listOf("Pick" to "PICK","Pack" to "PACK",third to thirdKey)
        var posKey=when{mainPick->"PICK";mainPack->"PACK";else->thirdKey};var posLabel=positionChoices.firstOrNull{it.second==posKey}?.first?:third
        val shiftBox=column(bg);shiftBox.addView(segmentedChoice(listOf("Ca 1" to "Ca 1","Ca HC" to "Ca HC","Ca 2" to "Ca 2"),shiftValue){shiftValue=it},matchWrap());body.addView(labelled("Ca",shiftBox));body.addView(gap(7))
        val resource=column(bg);var pdaField:AutoCompleteTextView?=null;var selectedPda:JSONObject?=null;var pickSpin:Spinner?=null;var pickChoices=mutableListOf<Pair<String,Boolean>>();var preferredPick="";var tableSpin:Spinner?=null;var packSelection:JSONObject?=null;var preferredPackTable="";var preferredPackUser="";var preferredPackUsed=false
        val pdas=masters.optJSONArray("pdas")?:JSONArray();val picks=masters.optJSONArray("user_picks")?:JSONArray();val pickUsed=masters.optJSONArray("user_picks_reissue")?:JSONArray();val packRows=masters.optJSONArray("pack_tables")?:JSONArray();val packUsedRows=masters.optJSONArray("pack_tables_reissue")?:JSONArray()
        fun maps(src:JSONArray,used:Boolean):MutableList<JSONObject>{val out=mutableListOf<JSONObject>();for(i in 0 until src.length()){val q=src.optJSONObject(i)?:continue;val table=q.optString("table").ifBlank{q.optString("pack_table")}.trim();val user=q.optString("user_pack").ifBlank{q.optString("id").ifBlank{q.optString("resource_id")}}.trim();if(table.isNotBlank()&&user.isNotBlank())out.add(JSONObject(q.toString()).put("table",table).put("user_pack",user).put("duplicate_user",used||q.optBoolean("duplicate_user")))};return out}
        val normalPack=maps(packRows,false);val usedPack=maps(packUsedRows,true)
        fun rebuildResources(){
            resource.removeAllViews();pdaField=null;selectedPda=null;pickSpin=null;pickChoices.clear();tableSpin=null;packSelection=null
            if(posKey=="PICK"){
                pdaField=pdaInput(pdas,onSelected={selectedPda=it});resource.addView(labelled("PDA — gõ 5 số cuối",pdaField!!));resource.addView(gap(4));resource.addView(pdaSelectedPanel(pdas,pdaField!!));resource.addView(gap(5))
                val normal=mutableListOf<String>();for(i in 0 until picks.length()){val v=picks.optString(i).trim();if(v.isNotBlank()&&!normal.contains(v))normal.add(v)};normal.sortWith(Comparator{a,b->naturalUserCompare(a,b)})
                val labels=mutableListOf("Không dùng hy1.outbound");pickChoices.add("" to false);normal.forEach{pickChoices.add(it to false);labels.add(it)};if(preferredPick.isNotBlank()&&preferredPick !in normal){pickChoices.add(preferredPick to true);labels.add(preferredPick)}
                pickSpin=spinner(labels.toTypedArray());preferredPick.takeIf{it.isNotBlank()}?.let{v->pickChoices.indexOfFirst{it.first==v}.takeIf{it>=0}?.let{pickSpin?.setSelection(it)}}
                val usedIds=optionIds(pickUsed);val userRow=row(bg).apply{gravity=Gravity.CENTER_VERTICAL;addView(pickSpin!!,LinearLayout.LayoutParams(0,dp(50),1.35f).apply{marginEnd=dp(5)});addView(compactReissueButton("Phát lại",usedIds.isNotEmpty()){showReissueChooser("Phát lại User Pick",usedIds){i->preferredPick=usedIds[i];rebuildResources()}},LinearLayout.LayoutParams(0,dp(46),.85f))};resource.addView(labelled("User Pick",userRow))
            }else if(posKey=="PACK"){
                val chosenUsed=usedPack.filter{it.optString("table")==preferredPackTable&&it.optString("user_pack")==preferredPackUser};val mappings=(normalPack+chosenUsed).distinctBy{it.optString("table")+"|"+it.optString("user_pack")};val tables=mappings.map{it.optString("table")}.filter{it.isNotBlank()}.distinct().sortedWith(Comparator{a,b->naturalUserCompare(a,b)})
                tableSpin=spinner((if(tables.isEmpty())listOf("Không có Bàn Pack khả dụng")else tables).toTypedArray());preferredPackTable.takeIf{it.isNotBlank()}?.let{v->tables.indexOf(v).takeIf{it>=0}?.let{tableSpin?.setSelection(it)}};resource.addView(labelled("Bàn Pack — bắt buộc",tableSpin!!));resource.addView(gap(5));val userHost=column(bg);resource.addView(userHost,matchWrap())
                fun renderUsers(){userHost.removeAllViews();packSelection=null;if(tables.isEmpty()){userHost.addView(info("Không có User Pack theo Bàn Pack khả dụng."));return};val table=tables.getOrNull(tableSpin?.selectedItemPosition?:0).orEmpty();preferredPackTable=table;val rows=mappings.filter{it.optString("table")==table}.sortedWith(Comparator{a,b->naturalUserCompare(a.optString("user_pack"),b.optString("user_pack"))});val u=spinner((if(rows.isEmpty())listOf("Không có User Pack")else rows.map{it.optString("user_pack")}).toTypedArray());val target=preferredPackUser;val at=rows.indexOfFirst{it.optString("user_pack")==target};if(at>=0)u.setSelection(at);packSelection=rows.getOrNull(if(at>=0)at else 0);u.onItemSelectedListener=object:android.widget.AdapterView.OnItemSelectedListener{override fun onItemSelected(p:android.widget.AdapterView<*>?,v:View?,i:Int,id:Long){packSelection=rows.getOrNull(i);preferredPackUser=packSelection?.optString("user_pack").orEmpty();preferredPackUsed=packSelection?.optBoolean("duplicate_user")?:false};override fun onNothingSelected(p:android.widget.AdapterView<*>?)=Unit};val reissueLabels=usedPack.map{"${it.optString("table")} – ${it.optString("user_pack")}"};val row=row(bg).apply{gravity=Gravity.CENTER_VERTICAL;addView(u,LinearLayout.LayoutParams(0,dp(50),1.35f).apply{marginEnd=dp(5)});addView(compactReissueButton("Phát lại",usedPack.isNotEmpty()){showReissueChooser("Phát lại User Pack",reissueLabels){i->val q=usedPack[i];preferredPackTable=q.optString("table");preferredPackUser=q.optString("user_pack");preferredPackUsed=true;rebuildResources()}},LinearLayout.LayoutParams(0,dp(46),.85f))};userHost.addView(labelled("User Pack theo Bàn Pack",row))}
                tableSpin?.onItemSelectedListener=object:android.widget.AdapterView.OnItemSelectedListener{override fun onItemSelected(p:android.widget.AdapterView<*>?,v:View?,i:Int,id:Long){val t=tables.getOrNull(i).orEmpty();if(t!=preferredPackTable){preferredPackTable=t;preferredPackUser="";preferredPackUsed=false};renderUsers()};override fun onNothingSelected(p:android.widget.AdapterView<*>?)=Unit};renderUsers()
            }
        }
        val posBox=column(bg);posBox.addView(segmentedChoice(positionChoices,posKey){k->posKey=k;posLabel=positionChoices.firstOrNull{it.second==k}?.first?:k;preferredPick="";preferredPackTable="";preferredPackUser="";preferredPackUsed=false;rebuildResources()},matchWrap());body.addView(labelled("Vị trí trong ca",posBox));body.addView(gap(7));body.addView(resource,matchWrap());rebuildResources()
        val enter=primary("VÀO CA",teal){};enter.setOnClickListener{val positions=JSONArray();if(posKey!="NONE")positions.put(JSONObject().put("position_key",posKey).put("position_label",posLabel));val resources=JSONArray();if(posKey=="PICK"){val typed=pdaField?.text?.toString()?.trim().orEmpty();val p=selectedPda?:resolvePdaObject(pdas,typed);val expected=p?.optString("last5").orEmpty().ifBlank{p?.optString("serial").orEmpty().takeLast(5)};if(p==null||typed!=expected){showError("Vị trí Pick bắt buộc chọn PDA bằng đúng 5 số cuối.");return@setOnClickListener};resources.put(JSONObject().put("resource_type","PDA").put("resource_id",p.optString("serial")).put("pda_enter_status",p.optString("status")));val choice=pickChoices.getOrNull(pickSpin?.selectedItemPosition?:0)?:("" to false);if(choice.first.isNotBlank())resources.put(JSONObject().put("resource_type","USER_PICK").put("resource_id",choice.first).put("duplicate_user",choice.second))};if(posKey=="PACK"){val q=packSelection;val table=q?.optString("table").orEmpty().trim();val user=q?.optString("user_pack").orEmpty().trim();if(q==null||table.isBlank()||user.isBlank()){showError("Chọn đủ Bàn Pack và User Pack đúng theo bàn.");return@setOnClickListener};resources.put(JSONObject().put("resource_type","PACK_TABLE").put("resource_id",table));resources.put(JSONObject().put("resource_type","USER_PACK").put("resource_id",user).put("duplicate_user",preferredPackUsed||q.optBoolean("duplicate_user")))};val gen=employeeLookupGeneration;enter.isEnabled=false;enter.text="ĐANG VÀO CA...";api.call("attendance_enter_v2",JSONObject().put("mnv",mnv).put("shift",shiftValue).put("positions",positions).put("resources",resources).put("idempotency_key",UUID.randomUUID().toString())){r->runOnUiThread{enter.isEnabled=true;enter.text="VÀO CA";if(!r.ok){showError(r.error?:"VÀO CA thất bại");return@runOnUiThread};TopNotice.show(this,"Đã ghi nhận vào ca.",TopNotice.Kind.SUCCESS);foregroundSync.requestSync();if(gen==employeeLookupGeneration&&liveEmployeeMnv==mnv)scheduleAttendanceAutoReset(mnv,gen)}}};body.addView(gap(8));body.addView(enter,matchWrap())
    }
    private fun laborBatchCandidateFromSession(s:JSONObject):JSONObject{
        val id=shiftStaffIdentity(s)
        return JSONObject()
            .put("mnv",id.mnv).put("full_name",id.fullName).put("supplier",id.supplier).put("position",id.position)
            .put("session_id",s.optString("session_id")).put("business_date",s.optString("business_date"))
            .put("shift",s.optString("shift")).put("state",s.optString("state")).put("enter_at",s.optString("enter_at")).put("exit_at",s.optString("exit_at"))
    }

    private fun showLaborBatchSelector(title:String,candidates:List<JSONObject>,onSelected:(List<JSONObject>)->Unit){
        if(candidates.isEmpty()){TopNotice.show(this,"Không có nhân sự phù hợp.",TopNotice.Kind.INFO);return}
        val selected=linkedSetOf<String>()
        val suppliers=(listOf("Tất cả NCC")+candidates.map{dash(it.optString("supplier"))}.distinct().sortedBy{foldLocal(it)}).toMutableList()
        val positions=(listOf("Tất cả vị trí")+candidates.map{dash(it.optString("position"))}.distinct().sortedBy{foldLocal(it)}).toMutableList()
        val box=column(surface).apply{setPadding(dp(10),dp(4),dp(10),dp(8))}
        val supplier=spinner(suppliers.toTypedArray());val position=spinner(positions.toTypedArray())
        box.addView(labelled("Nhà cung cấp",supplier));box.addView(gap(6));box.addView(labelled("Vị trí",position));box.addView(gap(7))
        val actions=row(surface);val selectVisible=smallButton("CHỌN ĐANG LỌC",teal);val clear=smallButton("BỎ CHỌN",muted)
        actions.addView(selectVisible,LinearLayout.LayoutParams(0,dp(38),1f).apply{marginEnd=dp(3)});actions.addView(clear,LinearLayout.LayoutParams(0,dp(38),1f).apply{marginStart=dp(3)})
        box.addView(actions,matchWrap());box.addView(gap(6))
        val count=txt("Đã chọn 0",9.6f,muted,true);box.addView(count);box.addView(gap(5))
        val list=column(surface);box.addView(list,matchWrap())
        fun visible():List<JSONObject>{
            val sup=supplier.selectedItem?.toString().orEmpty();val posValue=position.selectedItem?.toString().orEmpty()
            return candidates.filter{x->
                (sup=="Tất cả NCC"||dash(x.optString("supplier"))==sup)&&
                (posValue=="Tất cả vị trí"||dash(x.optString("position"))==posValue)
            }
        }
        fun render(){
            list.removeAllViews();val rows=visible()
            if(rows.isEmpty()){list.addView(info("Không có nhân sự theo bộ lọc."));return}
            rows.forEach{x->
                val id=x.optString("mnv");val cb=CheckBox(this).apply{
                    text="${dash(x.optString("supplier"))} • $id • ${dash(x.optString("full_name"))}\n${dash(x.optString("position"))} • ${dash(x.optString("shift"))}"
                    textSize=10.2f;setTextColor(ink);isChecked=id in selected
                    setOnCheckedChangeListener{_,checked->if(checked)selected.add(id)else selected.remove(id);count.text="Đã chọn ${selected.size}"}
                }
                list.addView(cb,matchWrap());list.addView(gap(2))
            }
        }
        val listener=object:android.widget.AdapterView.OnItemSelectedListener{
            override fun onItemSelected(p:android.widget.AdapterView<*>?,v:View?,position:Int,id:Long){render()}
            override fun onNothingSelected(p:android.widget.AdapterView<*>?)=Unit
        }
        supplier.onItemSelectedListener=listener;position.onItemSelectedListener=listener
        selectVisible.setOnClickListener{visible().forEach{selected.add(it.optString("mnv"))};count.text="Đã chọn ${selected.size}";render()}
        clear.setOnClickListener{selected.clear();count.text="Đã chọn 0";render()}
        val dialog=AlertDialog.Builder(this).setTitle(title).setView(ScrollView(this).apply{addView(box)}).setNegativeButton("Hủy",null).setPositiveButton("TIẾP TỤC",null).create()
        dialog.setOnShowListener{dialog.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener{
            if(selected.isEmpty()){TopNotice.show(this,"Chọn ít nhất một nhân sự.",TopNotice.Kind.WARNING);return@setOnClickListener}
            val out=candidates.filter{it.optString("mnv") in selected};dialog.dismiss();onSelected(out)
        }}
        render();dialog.show()
    }

    private fun laborBatchResult(title:String,success:Int,failures:List<String>){
        foregroundSync.requestSync()
        if(failures.isEmpty()){
            TopNotice.show(this,"$title: thành công $success nhân sự.",TopNotice.Kind.SUCCESS);laborHome();return
        }
        AlertDialog.Builder(this).setTitle(title).setMessage("Thành công: $success\nLỗi: ${failures.size}\n\n${failures.take(12).joinToString("\n")}").setPositiveButton("Đóng"){_,_->laborHome()}.show()
    }

    private fun showLaborBatchCreate(){
        val date=operationalStore.businessDate();val day=operationalStore.loadDay(date)
        val sessions=day?.optJSONArray("sessions")?:JSONArray();val base=mutableListOf<JSONObject>()
        for(i in 0 until sessions.length()){
            val s=sessions.optJSONObject(i)?:continue
            if(!s.optString("state").equals("ACTIVE",true)||dash(s.optString("enter_at"))=="-")continue
            base.add(laborBatchCandidateFromSession(s))
        }
        if(base.isEmpty()){TopNotice.show(this,"Không có nhân sự đang trong ca.",TopNotice.Kind.INFO);return}
        api.call("labor_list",JSONObject().put("business_date",date)){r->runOnUiThread{
            if(handleAuth(r))return@runOnUiThread
            val open=mutableSetOf<String>();val items=r.json?.optJSONArray("items")?:JSONArray()
            for(i in 0 until items.length()){val x=items.optJSONObject(i)?:continue;if(x.optString("state").equals("OPEN",true))open.add(x.optString("mnv"))}
            val eligible=base.filter{it.optString("mnv") !in open}
            showLaborBatchSelector("Tạo công nhật nhanh",eligible){chosen->showLaborBatchCreateForm(chosen)}
        }}
    }

    private fun showLaborBatchCreateForm(chosen:List<JSONObject>){
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
            val noteText=note.text.toString();val deductRequested=deduct.isChecked
            dialog.dismiss()
            verifyActionPassword("tạo công nhật nhanh cho ${chosen.size} nhân sự"){
                val failures=mutableListOf<String>()
                fun next(index:Int,ok:Int){
                    if(index>=chosen.size){laborBatchResult("Tạo công nhật nhanh",ok,failures);return}
                    val row=chosen[index];val mnv=row.optString("mnv");val sid=row.optString("session_id")
                    api.call("employee_context",JSONObject().put("mnv",mnv).put("session_id",sid).put("include_labor",true).put("include_options",false)){fresh->runOnUiThread{
                        val json=fresh.json;val session=json?.optJSONObject("session")
                        if(!fresh.ok||json?.optString("state")!="ACTIVE"||json.optJSONObject("active_labor")!=null||session==null){
                            failures.add("$mnv: phiên/công nhật đã thay đổi");next(index+1,ok);return@runOnUiThread
                        }
                        val laborId=UUID.randomUUID().toString();val startEvent=UUID.randomUUID().toString()
                        val fixedMain=foldLocal(row.optString("position")).let{it.contains("KEO HANG")||it.contains("TO TRUONG")}
                        val fixedLabor=foldLocal(type).let{it.contains("KEO HANG")||it.contains("TO TRUONG")}
                        val payload=JSONObject().put("event_id",startEvent).put("labor_id",laborId).put("mnv",mnv).put("business_date",session.optString("business_date"))
                            .put("session_id",session.optString("session_id")).put("shift",session.optString("shift")).put("labor_type",type).put("start_at",startIso)
                            .put("deduct_staff",deductRequested&&!fixedMain&&!fixedLabor).put("note",noteText)
                        api.call("labor_start",payload){started->runOnUiThread{
                            if(!started.ok){failures.add("$mnv: ${started.error?:"không tạo được"}");next(index+1,ok);return@runOnUiThread}
                            if(end==null){next(index+1,ok+1);return@runOnUiThread}
                            api.call("labor_finish",JSONObject().put("event_id",UUID.randomUUID().toString()).put("depends_on_event_id",startEvent).put("labor_id",laborId)
                                .put("mnv",mnv).put("business_date",session.optString("business_date")).put("session_id",session.optString("session_id")).put("start_at",startIso).put("end_at",end).put("note",noteText)){done->runOnUiThread{
                                if(!done.ok){failures.add("$mnv: đã tạo nhưng chưa kết thúc — ${done.error?:"lỗi"}");next(index+1,ok)}
                                else next(index+1,ok+1)
                            }}
                        }}
                    }}
                }
                next(0,0)
            }
        }}
        dialog.show()
    }

    private fun showLaborBatchFinish(){
        val date=operationalStore.businessDate()
        api.call("labor_list",JSONObject().put("business_date",date)){r->runOnUiThread{
            if(handleAuth(r))return@runOnUiThread
            if(!r.ok){showError(r.error?:"Không tải được công nhật đang mở");return@runOnUiThread}
            val items=r.json?.optJSONArray("items")?:JSONArray();val candidates=mutableListOf<JSONObject>()
            for(i in 0 until items.length()){
                val x=items.optJSONObject(i)?:continue;if(!x.optString("state").equals("OPEN",true))continue
                val emp=MasterDataCache.employee(this,x.optString("mnv"))
                candidates.add(JSONObject(x.toString()).put("position",emp?.optString("main_position").orEmpty()).put("supplier",x.optString("supplier").ifBlank{emp?.optString("supplier").orEmpty()}).put("full_name",x.optString("full_name").ifBlank{emp?.optString("full_name").orEmpty()}))
            }
            showLaborBatchSelector("Kết thúc công nhật nhanh",candidates){chosen->showLaborBatchFinishForm(chosen)}
        }}
    }

    private fun showLaborBatchFinishForm(chosen:List<JSONObject>){
        val box=column(surface).apply{setPadding(dp(10),dp(5),dp(10),dp(8))}
        box.addView(txt("Đã chọn ${chosen.size} nhân sự đang làm công nhật",10.2f,navy,true));box.addView(gap(6))
        var endIso=Instant.now().toString()
        val endBtn=Button(this).apply{text=compactAttendanceTime(endIso);textSize=11.5f;isAllCaps=false;setTextColor(navy);background=outlineBg(surface,11)}
        box.addView(labelled("Giờ kết thúc",endBtn));box.addView(gap(5))
        endBtn.setOnClickListener{laborWheelPick(endIso,true){picked->endIso=picked;endBtn.text=compactAttendanceTime(picked)}}
        val note=input("Ghi chú",false);box.addView(note,matchWrap())
        val dialog=AlertDialog.Builder(this).setTitle("Kết thúc công nhật ${chosen.size} NLĐ").setView(box).setNegativeButton("Hủy",null).setPositiveButton("XÁC NHẬN",null).create()
        dialog.setOnShowListener{dialog.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener{
            val noteText=note.text.toString();dialog.dismiss()
            verifyActionPassword("kết thúc công nhật nhanh cho ${chosen.size} nhân sự"){
                val failures=mutableListOf<String>()
                fun next(index:Int,ok:Int){
                    if(index>=chosen.size){laborBatchResult("Kết thúc công nhật nhanh",ok,failures);return}
                    val row=chosen[index];val mnv=row.optString("mnv");val sid=row.optString("attendance_session_id");val laborId=row.optString("labor_id")
                    api.call("employee_context",JSONObject().put("mnv",mnv).put("session_id",sid).put("include_labor",true).put("include_options",false)){fresh->runOnUiThread{
                        val active=fresh.json?.optJSONObject("active_labor")
                        if(!fresh.ok||active?.optString("labor_id")!=laborId){failures.add("$mnv: công nhật đã thay đổi");next(index+1,ok);return@runOnUiThread}
                        api.call("labor_finish",JSONObject().put("event_id",UUID.randomUUID().toString()).put("labor_id",laborId).put("mnv",mnv)
                            .put("business_date",row.optString("business_date")).put("session_id",sid).put("start_at",active.optString("start_at")).put("end_at",endIso).put("note",noteText)){done->runOnUiThread{
                            if(!done.ok){failures.add("$mnv: ${done.error?:"không kết thúc được"}");next(index+1,ok)}
                            else next(index+1,ok+1)
                        }}
                    }}
                }
                next(0,0)
            }
        }}
        dialog.show()
    }

    private fun laborHome(){
        screenState="LABOR_HOME"
        if(!isAdmin()){simpleMessage("CÔNG NHẬT","Không có quyền truy cập.");return}
        val root=baseRoot("CÔNG NHẬT");val body=body()
        val currentDate=operationalStore.businessDate()
        var selectedLaborDate=currentDate
        var laborDates:List<String> = listOf(currentDate).filter{it.isNotBlank()}
        val cache=getSharedPreferences("pp_labor_list_cache_v116",MODE_PRIVATE)
        val reviewPrefs=getSharedPreferences("pp_labor_fixed_review_v116",MODE_PRIVATE)

        body.addView(section("Ghi nhận công nhật"))
        val mnv=mnvInput("Scan / Nhập mã nhân viên").apply{setText(initialMnv)}
        body.addView(labelled("Mã nhân viên",mnv));body.addView(gap(7))

        val batchRow=row(bg).apply{gravity=Gravity.CENTER_VERTICAL}
        val batchCreate=smallButton("TẠO NHANH NHIỀU NLĐ",green)
        val batchFinish=smallButton("KẾT THÚC NHANH NHIỀU NLĐ",red)
        batchRow.addView(batchCreate,LinearLayout.LayoutParams(0,dp(42),.88f).apply{marginEnd=dp(3)})
        batchRow.addView(batchFinish,LinearLayout.LayoutParams(0,dp(42),1.12f).apply{marginStart=dp(3)})
        body.addView(batchRow,matchWrap());body.addView(gap(7))

        val fixedWarningHost=column(bg);body.addView(fixedWarningHost,matchWrap());body.addView(gap(6))
        val dateRow=row(bg);dateRow.addView(section("Chi tiết công nhật theo ngày"),LinearLayout.LayoutParams(0,-2,1f))
        val laborDateButton=Button(this).apply{text=businessDateVi(selectedLaborDate);textSize=10.5f;isAllCaps=false;setTextColor(navy);background=outlineBg(surface,12);isEnabled=true}
        dateRow.addView(laborDateButton,LinearLayout.LayoutParams(dp(112),dp(42)));body.addView(dateRow,matchWrap())

        val shiftSp=spinner(arrayOf("Tất cả ca"))
        val supplierSp=spinner(arrayOf("Tất cả NCC"))
        val positionSp=spinner(arrayOf("Tất cả vị trí"))
        val filterRow=row(bg).apply{
            addView(shiftSp,LinearLayout.LayoutParams(0,dp(48),1f).apply{marginEnd=dp(2)})
            addView(supplierSp,LinearLayout.LayoutParams(0,dp(48),1f).apply{marginStart=dp(2);marginEnd=dp(2)})
            addView(positionSp,LinearLayout.LayoutParams(0,dp(48),1f).apply{marginStart=dp(2)})
        }
        body.addView(filterRow,matchWrap());body.addView(gap(5))
        val laborCount=txt("",9.5f,muted,true);body.addView(laborCount);body.addView(gap(4))
        val openBox=column(bg);body.addView(openBox,matchWrap());body.addView(gap(8))

        var currentRows=emptyList<JSONObject>()
        var filterSync=false
        fun setOptions(sp:Spinner,values:List<String>){
            val old=sp.selectedItem?.toString().orEmpty()
            sp.adapter=ArrayAdapter(this,android.R.layout.simple_spinner_dropdown_item,values)
            sp.setSelection(values.indexOf(old).takeIf{it>=0}?:0)
        }
        fun rowPosition(x:JSONObject)=MasterDataCache.employee(this,x.optString("mnv"))?.optString("main_position").orEmpty().ifBlank{x.optString("position")}
        fun renderRows(rows:List<JSONObject>){
            currentRows=rows
            filterSync=true
            setOptions(shiftSp,listOf("Tất cả ca")+rows.map{it.optString("shift")}.filter{it.isNotBlank()}.distinct())
            setOptions(supplierSp,listOf("Tất cả NCC")+rows.map{it.optString("supplier")}.filter{it.isNotBlank()}.distinct().sortedWith(Comparator{p,q->naturalUserCompare(p,q)}))
            setOptions(positionSp,listOf("Tất cả vị trí")+rows.map{rowPosition(it)}.filter{it.isNotBlank()}.distinct().sortedWith(Comparator{p,q->naturalUserCompare(p,q)}))
            filterSync=false
            val shift=shiftSp.selectedItem?.toString().orEmpty();val sup=supplierSp.selectedItem?.toString().orEmpty();val pos=positionSp.selectedItem?.toString().orEmpty()
            val visible=rows.filter{x->(shift=="Tất cả ca"||x.optString("shift")==shift)&&(sup=="Tất cả NCC"||x.optString("supplier")==sup)&&(pos=="Tất cả vị trí"||rowPosition(x)==pos)}
            openBox.removeAllViews()
            val groups=visible.groupBy{x->"${x.optString("mnv")}|${x.optString("attendance_session_id")}"}
                .values.sortedWith(compareByDescending<List<JSONObject>>{g->g.any{it.optString("state").equals("OPEN",true)}}.thenBy{g->foldLocal(g.firstOrNull()?.optString("supplier").orEmpty())}.thenBy{g->g.firstOrNull()?.optString("mnv").orEmpty()})
            val allGroups=rows.groupBy{x->"${x.optString("mnv")}|${x.optString("attendance_session_id")}"}
            laborCount.text="Nhân sự: ${allGroups.size} • Đang làm: ${allGroups.values.count{g->g.any{it.optString("state").equals("OPEN",true)}}} • Tổng khoảng: ${rows.size}"
            if(groups.isEmpty()){openBox.addView(txt(if(rows.isEmpty())"Chưa có công nhật trong ngày." else "Không có công nhật phù hợp bộ lọc.",9.8f,muted,false));return}
            groups.forEach{intervals->
                val first=intervals.first();val id=first.optString("mnv");val sid=first.optString("attendance_session_id");val anyOpen=intervals.any{it.optString("state").equals("OPEN",true)}
                val fill=if(anyOpen)Color.rgb(255,247,237) else Color.rgb(240,253,250)
                val summaries=intervals.sortedBy{it.optString("start_at")}.map{x->"${compactAttendanceTime(x.optString("start_at"))}–${if(x.optString("state").equals("OPEN",true))"…" else compactAttendanceTime(x.optString("end_at"))}"}
                val card=column(fill).apply{
                    setPadding(dp(9),dp(7),dp(9),dp(7));background=outlineBg(fill,12)
                    val top=row(fill);top.addView(txt("$id • ${dash(first.optString("full_name"))}",10.5f,navy,true),LinearLayout.LayoutParams(0,-2,1f));top.addView(txt(if(anyOpen)"ĐANG LÀM" else "HOÀN THÀNH",8.8f,if(anyOpen)Color.rgb(194,65,12) else green,true));addView(top)
                    addView(txt("${dash(first.optString("supplier"))} • ${dash(rowPosition(first))} • ${intervals.size} khoảng",9.2f,ink,false))
                    addView(txt(summaries.joinToString(" • "),9.2f,muted,false).apply{maxLines=2})
                    setOnClickListener{tapFeedback(this);openLaborExact(id,sid)}
                }
                openBox.addView(card,matchWrap());openBox.addView(gap(5))
            }
        }

        fun localRows(date:String):List<JSONObject>{
            val day=operationalStore.loadDay(date)?:return emptyList()
            val events=day.optJSONArray("events")?:return emptyList()
            val map=linkedMapOf<String,JSONObject>()
            for(i in 0 until events.length()){
                val ev=events.optJSONObject(i)?:continue
                val type=ev.optString("event_type").uppercase();if(type !in setOf("LABOR_START","LABOR_FINISH"))continue
                val p=runCatching{JSONObject(ev.optString("payload_json","{}"))}.getOrDefault(JSONObject());val after=p.optJSONObject("after")?:JSONObject()
                val mnv=ev.optString("mnv").ifBlank{p.optString("mnv")}.ifBlank{after.optString("mnv")};if(mnv.isBlank())continue
                val laborId=ev.optString("labor_id").ifBlank{p.optString("labor_id")}.ifBlank{after.optString("labor_id")}.ifBlank{"local-$mnv-${p.optString("start_at").ifBlank{ev.optString("event_id")}}"}
                val emp=MasterDataCache.employee(this,mnv)
                val row=map.getOrPut(laborId){JSONObject().put("labor_id",laborId).put("mnv",mnv).put("business_date",date).put("shift",ev.optString("shift").ifBlank{p.optString("shift")}.ifBlank{after.optString("shift")}).put("labor_type",p.optString("labor_type").ifBlank{after.optString("labor_type")}).put("start_at",p.optString("start_at").ifBlank{after.optString("start_at")}).put("state","OPEN").put("full_name",emp?.optString("full_name").orEmpty()).put("supplier",emp?.optString("supplier").orEmpty()).put("attendance_session_id",p.optString("session_id").ifBlank{after.optString("attendance_session_id")})}
                if(type=="LABOR_FINISH")row.put("state","COMPLETED").put("end_at",p.optString("end_at").ifBlank{after.optString("end_at")})
            }
            return map.values.toList()
        }

        fun reviewFixed(rows:List<JSONObject>){
            fixedWarningHost.removeAllViews()
            if(selectedLaborDate!=currentDate)return
            val day=operationalStore.loadDay(currentDate)?:return
            val sessions=day.optJSONArray("sessions")?:JSONArray()
            val acknowledged=(reviewPrefs.getStringSet("ack_$currentDate",emptySet())?:emptySet()).toMutableSet()
            val laborSessionIds=rows.map{it.optString("attendance_session_id")}.filter{it.isNotBlank()}.toSet()
            val pending=mutableListOf<JSONObject>()
            for(i in 0 until sessions.length()){
                val ses=sessions.optJSONObject(i)?:continue
                if(!ses.optString("state").equals("ACTIVE",true))continue
                val mnv=ses.optString("mnv");val emp=MasterDataCache.employee(this,mnv)?:JSONObject();val folded=foldLocal(emp.optString("main_position"))
                if(!(folded.contains("TO TRUONG")||folded.contains("KEO HANG")||folded=="5S"||folded.contains(" 5S")))continue
                val sid=ses.optString("session_id");if(sid in laborSessionIds||sid in acknowledged)continue
                pending.add(JSONObject(ses.toString()).put("_position",emp.optString("main_position")).put("_name",emp.optString("full_name")))
            }
            if(pending.isEmpty())return
            val warn=reconciliationButton("KIỂM TRA CÔNG NHẬT CHO CÁC VỊ TRÍ CỐ ĐỊNH (${pending.size})",false)
            warn.setOnClickListener{
                val host=column(surface).apply{setPadding(dp(8),dp(5),dp(8),dp(8))}
                var dialog:AlertDialog?=null
                pending.forEach{x->
                    val sid=x.optString("session_id");val id=x.optString("mnv")
                    val line=column(surface).apply{
                        setPadding(dp(7),dp(5),dp(7),dp(5));background=outlineBg(surface,10)
                        addView(txt("$id • ${dash(x.optString("_name"))}",10.4f,navy,true));addView(txt("${dash(x.optString("_position"))} • ${dash(x.optString("shift"))}",9.2f,muted,false))
                        val acts=row(surface);acts.addView(smallButton("CÔNG NHẬT",green).apply{setOnClickListener{dialog?.dismiss();initialMnv=id;laborHome()}},LinearLayout.LayoutParams(0,dp(38),1f).apply{marginEnd=dp(3)})
                        acts.addView(smallButton("ĐÃ KIỂM TRA - KHÔNG",navy).apply{setOnClickListener{acknowledged.add(sid);reviewPrefs.edit().putStringSet("ack_$currentDate",acknowledged).apply();dialog?.dismiss();reviewFixed(rows)}},LinearLayout.LayoutParams(0,dp(38),1.25f).apply{marginStart=dp(3)});addView(acts,matchWrap())
                    }
                    host.addView(line,matchWrap());host.addView(gap(4))
                }
                dialog=AlertDialog.Builder(this).setTitle("Kiểm tra công nhật vị trí cố định").setView(ScrollView(this).apply{addView(host)}).setNegativeButton("Đóng",null).create();dialog.show()
            }
            fixedWarningHost.addView(warn,ReviewAlertUi.fixedHeightParams(this))
        }

        fun loadOpen(){
            val cached=cache.getString(selectedLaborDate,"").orEmpty()
            val local=if(cached.isNotBlank())runCatching{val a=JSONArray(cached);(0 until a.length()).mapNotNull{a.optJSONObject(it)?.let{j->JSONObject(j.toString())}}}.getOrDefault(emptyList()) else localRows(selectedLaborDate)
            renderRows(local);reviewFixed(local)
            api.call("labor_list",JSONObject().put("business_date",selectedLaborDate)){r->runOnUiThread{
                if(screenState!="LABOR_HOME")return@runOnUiThread
                if(handleAuth(r))return@runOnUiThread
                if(!r.ok){if(local.isEmpty())openBox.addView(txt("Chưa tải được dữ liệu; sẽ tự cập nhật khi Service sẵn sàng.",9.3f,muted,false));return@runOnUiThread}
                val a=r.json?.optJSONArray("items")?:JSONArray();val fresh=(0 until a.length()).mapNotNull{a.optJSONObject(it)?.let{j->JSONObject(j.toString())}}
                cache.edit().putString(selectedLaborDate,a.toString()).apply();renderRows(fresh);reviewFixed(fresh)
            }}
        }

        var busy=false
        fun submit(){
            val v=mnv.text.toString().trim();if(v.isBlank()){TopNotice.show(this,"Nhập Mã nhân viên.",TopNotice.Kind.WARNING);return};if(busy)return
            busy=true
            val local=PdaLocalProjection.employeeContext(this,v)
            if(local!=null&&local.optString("state").equals("ACTIVE",true)){busy=false;showLaborContext(local,MasterDataCache.snapshot(this)?:JSONObject());return}
            api.call("employee_context",JSONObject().put("mnv",v).put("include_labor",true).put("include_options",false)){r->runOnUiThread{
                busy=false;if(handleAuth(r))return@runOnUiThread;if(!r.ok){showError(r.error?:"Không kiểm tra được Mã nhân viên");return@runOnUiThread};showLaborContext(r.json?:JSONObject(),MasterDataCache.snapshot(this@OperationsActivity)?:JSONObject())
            }}
        }
        fun localLaborDates():List<String> = operationalStore.availableDates().filter{date->
            val events=operationalStore.loadDay(date)?.optJSONArray("events")?:return@filter false
            (0 until events.length()).any{i->events.optJSONObject(i)?.optString("event_type")?.uppercase() in setOf("LABOR_START","LABOR_FINISH")}
        }
        fun loadLaborDates(){
            laborDates=(localLaborDates()+listOf(currentDate)).filter{it.isNotBlank()}.distinct().sortedDescending()
            laborDateButton.text=businessDateVi(selectedLaborDate);loadOpen()
            api.call("labor_dates"){r->runOnUiThread{
                if(screenState!="LABOR_HOME"||!r.ok)return@runOnUiThread
                laborDates=(jsonStrings(r.json?.optJSONArray("dates"))+laborDates).filter{it.isNotBlank()}.distinct().sortedDescending()
            }}
        }
        val filterListener=object:android.widget.AdapterView.OnItemSelectedListener{override fun onItemSelected(p:android.widget.AdapterView<*>?,v:View?,pos:Int,id:Long){if(!filterSync)renderRows(currentRows)};override fun onNothingSelected(p:android.widget.AdapterView<*>?)=Unit}
        shiftSp.onItemSelectedListener=filterListener;supplierSp.onItemSelectedListener=filterListener;positionSp.onItemSelectedListener=filterListener
        laborDateButton.setOnClickListener{DataDatePickerUi.show(this,laborDates,selectedLaborDate){chosen->selectedLaborDate=chosen;laborDateButton.text=businessDateVi(chosen);loadOpen()}}
        batchCreate.setOnClickListener{showLaborBatchCreate()};batchFinish.setOnClickListener{showLaborBatchFinish()}
        bindScannerEnter(mnv){submit()};loadLaborDates()
        if(initialMnv.isNotBlank())mnv.post{submit()}
        attach(root,body);mnv.requestFocus()
    }

    private fun laborWheelPick(currentIso:String,allowFuture:Boolean=false,onPick:(String)->Unit){
        val tz=ZoneId.of("Asia/Ho_Chi_Minh")
        val raw=runCatching{Instant.parse(currentIso).atZone(tz)}.getOrDefault(java.time.ZonedDateTime.now(tz))
        val roundedMinutes=((raw.minute+7)/15)*15
        val z=if(roundedMinutes>=60)raw.plusHours(1).withMinute(0).withSecond(0).withNano(0) else raw.withMinute(roundedMinutes).withSecond(0).withNano(0)
        val minuteValues=arrayOf("00","15","30","45")
        val hour=NumberPicker(this).apply{minValue=0;maxValue=23;value=z.hour;wrapSelectorWheel=true;setFormatter{String.format(java.util.Locale.US,"%02d",it)}}
        val minute=NumberPicker(this).apply{minValue=0;maxValue=3;value=(z.minute/15).coerceIn(0,3);displayedValues=minuteValues;wrapSelectorWheel=true}
        val box=row(surface).apply{gravity=Gravity.CENTER;addView(hour,LinearLayout.LayoutParams(0,dp(126),1f));addView(txt(":",18f,navy,true).apply{gravity=Gravity.CENTER},LinearLayout.LayoutParams(dp(24),dp(126)));addView(minute,LinearLayout.LayoutParams(0,dp(126),1f))}
        AlertDialog.Builder(this).setTitle("Chọn giờ và phút").setView(box).setNegativeButton("Hủy",null).setPositiveButton("CHỌN"){_,_->
            val picked=z.toLocalDate().atTime(hour.value,minute.value*15).atZone(tz).toInstant()
            if(!allowFuture&&picked.isAfter(Instant.now().plusSeconds(60)))TopNotice.show(this,"Giờ bắt đầu không được ở tương lai.",TopNotice.Kind.WARNING) else onPick(picked.toString())
        }.show()
    }
    private fun openLaborExact(mnv:String,sessionId:String){
        val p=JSONObject().put("mnv",mnv).put("include_labor",true).put("include_options",false);if(sessionId.isNotBlank())p.put("session_id",sessionId)
        api.call("employee_context",p){r->runOnUiThread{if(handleAuth(r))return@runOnUiThread;if(!r.ok){showError(r.error?:"Không đọc được công nhật");return@runOnUiThread};showLaborContext(r.json?:JSONObject(),MasterDataCache.snapshot(this@OperationsActivity)?:JSONObject())}}
    }
    private fun showCompletedLaborEditor(item:JSONObject,verified:Boolean=false){
        if(!isAdmin())return;if(!verified){verifyEditPassword("sửa công nhật"){showCompletedLaborEditor(item,true)};return}
        screenState="LABOR_CONTEXT";val root=baseRoot("SỬA CÔNG NHẬT");val body=body()
        val mnv=item.optString("mnv");val date=item.optString("business_date");val sid=item.optString("attendance_session_id");val laborId=item.optString("labor_id")
        body.addView(details(listOf("Nhân sự" to "$mnv • ${dash(item.optString("full_name"))}","Ngày" to businessDateVi(date),"Nội dung" to dash(item.optString("labor_type")))));body.addView(gap(7))
        var startIso=item.optString("start_at");var endIso=item.optString("end_at")
        fun timeButton(v:String)=Button(this).apply{text=compactAttendanceTime(v);textSize=11.5f;isAllCaps=false;setTextColor(navy);background=outlineBg(surface,11)}
        val sr=row(bg);sr.addView(txt("Bắt đầu",10.2f,ink,true),LinearLayout.LayoutParams(0,-2,1f));val sb=timeButton(startIso);sr.addView(sb,LinearLayout.LayoutParams(dp(118),dp(42)));body.addView(sr);body.addView(gap(5))
        val er=row(bg);er.addView(txt("Kết thúc",10.2f,ink,true),LinearLayout.LayoutParams(0,-2,1f));val eb=timeButton(endIso);er.addView(eb,LinearLayout.LayoutParams(dp(118),dp(42)));body.addView(er);body.addView(gap(6))
        sb.setOnClickListener{laborWheelPick(startIso){startIso=it;sb.text=compactAttendanceTime(it)}};eb.setOnClickListener{laborWheelPick(endIso,true){endIso=it;eb.text=compactAttendanceTime(it)}}
        val note=input("Ghi chú",false).apply{setText(item.optString("note"))};body.addView(note);body.addView(gap(7));val save=primary("LƯU SỬA",teal){}
        save.setOnClickListener{
            val s=runCatching{Instant.parse(startIso).toEpochMilli()}.getOrDefault(0L);val e=runCatching{Instant.parse(endIso).toEpochMilli()}.getOrDefault(0L);if(s<=0||e<s){TopNotice.show(this,"Kiểm tra lại giờ bắt đầu và kết thúc.",TopNotice.Kind.WARNING);return@setOnClickListener}
            save.isEnabled=false;api.call("labor_finish",JSONObject().put("event_id",UUID.randomUUID().toString()).put("mnv",mnv).put("business_date",date).put("session_id",sid).put("labor_id",laborId).put("start_at",startIso).put("end_at",endIso).put("correction",true).put("note",note.text.toString())){r->runOnUiThread{
                save.isEnabled=true;if(handleAuth(r))return@runOnUiThread;if(!r.ok)showError(r.error?:"Không sửa được công nhật")else{TopNotice.show(this,"Đã ghi nhận sửa công nhật.",TopNotice.Kind.SUCCESS);foregroundSync.requestSync();laborHome()}
            }}
        };body.addView(save,matchWrap());attach(root,body)
    }

    private fun showLaborContext(ctx:JSONObject, masters:JSONObject){
        screenState="LABOR_CONTEXT"
        val e=ctx.optJSONObject("employee")?:JSONObject();val state=ctx.optString("state");val active=ctx.optJSONObject("active_labor")
        val root=baseRoot("CÔNG NHẬT");val body=body()
        val laborScan=mnvInput("Scan / Nhập mã nhân viên")
        body.addView(laborScan,matchWrap());body.addView(gap(7))
        var scanBusy=false
        fun submitLaborScan(){
            val id=laborScan.text.toString().trim();if(id.isBlank()){TopNotice.show(this,"Nhập hoặc quét Mã nhân viên.",TopNotice.Kind.WARNING);return};if(scanBusy)return
            scanBusy=true;hideSoftKeyboard(laborScan)
            api.call("employee_context",JSONObject().put("mnv",id).put("include_labor",true).put("include_options",false)){r->runOnUiThread{
                scanBusy=false;if(handleAuth(r))return@runOnUiThread
                if(!r.ok){showError(r.error?:"Không đọc được công nhật");return@runOnUiThread}
                showLaborContext(r.json?:JSONObject(),MasterDataCache.snapshot(this@OperationsActivity)?:JSONObject())
            }}
        }
        bindScannerEnter(laborScan){submitLaborScan()}
        body.addView(employeeCard(e));body.addView(gap(7))
        if(state!="ACTIVE"){
            body.addView(status(if(state=="ENDED")"ĐÃ HẾT PHIÊN" else "CHƯA VÀO CA",red,Color.rgb(255,238,239)))
            attach(root,body);laborScan.requestFocus();return
        }
        val ses=ctx.optJSONObject("session")?:JSONObject()
        val laborMnv=e.optString("mnv");val laborSessionId=ses.optString("session_id");val laborBusinessDate=ses.optString("business_date").ifBlank{ctx.optString("business_date")}
        body.addView(details(listOf("Ca" to dash(ses.optString("shift")),"Vị trí" to dash(workText(ses.optString("work_choice"))),"Vào lúc" to formatIso(ses.optString("enter_at")))));body.addView(gap(7))
        val intervals=ctx.optJSONArray("labor_intervals")?:JSONArray()
        if(intervals.length()>0){
            body.addView(section("Các khoảng công nhật trong phiên"))
            for(i in 0 until intervals.length()){
                val x=intervals.optJSONObject(i)?:continue
                val open=x.optString("state").equals("OPEN",true)
                val fill=if(open)Color.rgb(255,247,237) else Color.rgb(240,253,250)
                val item=JSONObject(x.toString()).put("attendance_session_id",laborSessionId).put("full_name",e.optString("full_name")).put("supplier",e.optString("supplier"))
                val card=column(fill).apply{
                    setPadding(dp(10),dp(7),dp(10),dp(7));background=outlineBg(fill,12)
                    val top=row(fill).apply{gravity=Gravity.CENTER_VERTICAL}
                    top.addView(txt("Khoảng ${i+1} • ${dash(x.optString("labor_type"))}",10.4f,navy,true),LinearLayout.LayoutParams(0,-2,1f))
                    top.addView(txt(if(open)"ĐANG LÀM" else "HOÀN THÀNH",8.5f,if(open)Color.rgb(194,65,12) else green,true))
                    addView(top,matchWrap())
                    addView(txt("${compactAttendanceTime(x.optString("start_at"))} → ${if(open)"-" else compactAttendanceTime(x.optString("end_at"))}",9.3f,ink,false))
                    val noteText=x.optString("note").trim();if(noteText.isNotBlank())addView(txt("Ghi chú: $noteText",9f,muted,false))
                    if(!open)setOnClickListener{showCompletedLaborEditor(item)}
                }
                body.addView(card,matchWrap());body.addView(gap(5))
            }
            body.addView(gap(3))
        }
        fun pickClock(currentIso:String,onPick:(String)->Unit)=laborWheelPick(currentIso,false,onPick)
        fun timeButton(iso:String):Button=Button(this).apply{
            text=compactAttendanceTime(iso);textSize=12f;isAllCaps=false;setTextColor(navy);background=outlineBg(surface,11);minHeight=0;minimumHeight=0
        }
        if(active!=null){
            body.addView(status("ĐANG LÀM CÔNG NHẬT",green,Color.rgb(235,248,239)));body.addView(gap(6))
            body.addView(details(listOf("Nội dung" to dash(active.optString("labor_type")),"Ghi chú" to dash(active.optString("note")))));body.addView(gap(7))
            var startIso=active.optString("start_at");var endIso:String?=null
            val startRow=row(bg);startRow.addView(txt("Bắt đầu",10.2f,ink,true),LinearLayout.LayoutParams(0,-2,1f));val startTime=timeButton(startIso);startRow.addView(startTime,LinearLayout.LayoutParams(dp(112),dp(42)));body.addView(startRow,matchWrap());body.addView(gap(5))
            val endRow=row(bg);endRow.addView(txt("Kết thúc",10.2f,ink,true),LinearLayout.LayoutParams(0,-2,1f))
            val endTime=Button(this).apply{text="Chưa chọn";textSize=12f;isAllCaps=false;setTextColor(navy);background=outlineBg(surface,11)};endRow.addView(endTime,LinearLayout.LayoutParams(dp(112),dp(42)));body.addView(endRow,matchWrap());body.addView(gap(6))
            startTime.setOnClickListener{pickClock(startIso){picked->startIso=picked;startTime.text=compactAttendanceTime(picked)}}
            endTime.setOnClickListener{laborWheelPick(endIso?:Instant.now().toString(),true){picked->endIso=picked;endTime.text=compactAttendanceTime(picked)}}
            val note=input("Ghi chú",false).apply{setText(active.optString("note"))};body.addView(note,matchWrap());body.addView(gap(7))
            val finish=primary("HOÀN THÀNH",red){}
            finish.setOnClickListener{
                val end=endIso;if(end.isNullOrBlank()){TopNotice.show(this,"Chọn giờ kết thúc.",TopNotice.Kind.WARNING);return@setOnClickListener}
                val startMs=runCatching{Instant.parse(startIso).toEpochMilli()}.getOrDefault(0L);val endMs=runCatching{Instant.parse(end).toEpochMilli()}.getOrDefault(0L)
                if(startMs<=0||endMs<startMs){TopNotice.show(this,"Giờ kết thúc phải sau giờ bắt đầu.",TopNotice.Kind.WARNING);return@setOnClickListener}
                finish.isEnabled=false;finish.text="ĐANG GHI..."
                api.call("employee_context",JSONObject().put("mnv",laborMnv).put("session_id",laborSessionId).put("include_labor",true).put("include_options",false)){fresh->runOnUiThread{
                    if(handleAuth(fresh)){finish.isEnabled=true;return@runOnUiThread};val freshLabor=fresh.json?.optJSONObject("active_labor")
                    if(!fresh.ok||freshLabor?.optString("labor_id")!=active.optString("labor_id")){finish.isEnabled=true;showError("Công nhật trên Service vừa thay đổi. Mở lại dữ liệu mới nhất.");fresh.json?.let{showLaborContext(it,masters)};return@runOnUiThread}
                    api.call("labor_finish",JSONObject().put("event_id",UUID.randomUUID().toString()).put("mnv",laborMnv).put("business_date",laborBusinessDate).put("session_id",laborSessionId).put("labor_id",active.optString("labor_id")).put("start_at",startIso).put("end_at",end).put("note",note.text.toString())){r->runOnUiThread{
                        finish.isEnabled=true;finish.text="HOÀN THÀNH";if(handleAuth(r))return@runOnUiThread;if(!r.ok)showError(r.error?:"Không kết thúc được công nhật")else{TopNotice.show(this,"Đã ghi nhận hoàn thành công nhật.",TopNotice.Kind.SUCCESS);foregroundSync.requestSync();initialMnv="";laborHome()}
                    }}
                }}
            }
            body.addView(finish,matchWrap())
        }else{
            val types=catalogValues("CÔNG NHẬT_Thông tin công nhật",jsonStrings(masters.optJSONArray("labor_types")))
            val typeSpinner=spinner((if(types.isEmpty())listOf("Khác")else types).toTypedArray())
            body.addView(labelled("Thông tin công nhật",typeSpinner));body.addView(gap(7))
            var startIso=Instant.now().toString();var endIso:String?=null
            val startRow=row(bg);startRow.addView(txt("Bắt đầu",10.2f,ink,true),LinearLayout.LayoutParams(0,-2,1f))
            val startTime=timeButton(startIso);startRow.addView(startTime,LinearLayout.LayoutParams(dp(112),dp(42)));body.addView(startRow,matchWrap());body.addView(gap(5))
            val endRow=row(bg);endRow.addView(txt("Kết thúc (không bắt buộc)",10.2f,ink,true),LinearLayout.LayoutParams(0,-2,1f));val endTime=Button(this).apply{text="Chưa chọn";textSize=11.5f;isAllCaps=false;setTextColor(navy);background=outlineBg(surface,11)};endRow.addView(endTime,LinearLayout.LayoutParams(dp(112),dp(42)));body.addView(endRow,matchWrap());body.addView(gap(5))
            val clearEnd=smallButton("BỎ KT",muted).apply{visibility=View.GONE};body.addView(clearEnd,LinearLayout.LayoutParams(dp(86),dp(36)).apply{gravity=Gravity.END})
            startTime.setOnClickListener{pickClock(startIso){picked->startIso=picked;startTime.text=compactAttendanceTime(picked)}}
            endTime.setOnClickListener{laborWheelPick(endIso?:Instant.now().toString(),true){picked->endIso=picked;endTime.text=compactAttendanceTime(picked);clearEnd.visibility=View.VISIBLE}};clearEnd.setOnClickListener{endIso=null;endTime.text="Chưa chọn";clearEnd.visibility=View.GONE}
            val fixedMain=foldLocal(e.optString("main_position")).let{it.contains("KEO HANG")||it.contains("TO TRUONG")}
            val deduct=CheckBox(this).apply{text="Khấu trừ nhân sự";isChecked=false;setTextColor(ink);textSize=11f}
            fun updateDeduct(){val fixedLabor=foldLocal(typeSpinner.selectedItem?.toString().orEmpty()).let{it.contains("KEO HANG")||it.contains("TO TRUONG")};val blocked=fixedMain||fixedLabor;deduct.isEnabled=!blocked;if(blocked)deduct.isChecked=false;deduct.setTextColor(if(blocked)muted else ink)}
            typeSpinner.onItemSelectedListener=object:android.widget.AdapterView.OnItemSelectedListener{override fun onItemSelected(p:android.widget.AdapterView<*>?,v:View?,pos:Int,id:Long){updateDeduct()};override fun onNothingSelected(p:android.widget.AdapterView<*>?)=Unit};updateDeduct()
            body.addView(deduct,matchWrap());body.addView(gap(5))
            val note=input("Ghi chú",false);body.addView(note,matchWrap());body.addView(gap(7))
            val start=primary("LƯU CÔNG NHẬT",green){}
            start.setOnClickListener{
                val selectedEnd=endIso;if(selectedEnd!=null&&runCatching{Instant.parse(selectedEnd).isBefore(Instant.parse(startIso))}.getOrDefault(true)){TopNotice.show(this,"Giờ kết thúc phải sau giờ bắt đầu.",TopNotice.Kind.WARNING);return@setOnClickListener}
                start.isEnabled=false;start.text="ĐANG GHI..."
                api.call("employee_context",JSONObject().put("mnv",laborMnv).put("session_id",laborSessionId).put("include_labor",true).put("include_options",false)){fresh->runOnUiThread{
                    if(handleAuth(fresh)){start.isEnabled=true;return@runOnUiThread};if(!fresh.ok||fresh.json?.optString("state")!="ACTIVE"||fresh.json?.optJSONObject("active_labor")!=null){start.isEnabled=true;showError(if(fresh.json?.optJSONObject("active_labor")!=null)"Nhân sự đã có công nhật đang mở." else "Phiên nhân sự không còn hoạt động.");fresh.json?.let{showLaborContext(it,masters)};return@runOnUiThread}
                    val laborId=UUID.randomUUID().toString();val startEvent=UUID.randomUUID().toString()
                    val payload=JSONObject().put("event_id",startEvent).put("labor_id",laborId).put("mnv",laborMnv).put("business_date",laborBusinessDate).put("session_id",laborSessionId).put("shift",ses.optString("shift")).put("labor_type",typeSpinner.selectedItem.toString()).put("start_at",startIso).put("deduct_staff",deduct.isChecked&&deduct.isEnabled).put("note",note.text.toString())
                    api.call("labor_start",payload){r->runOnUiThread{
                        if(!r.ok){start.isEnabled=true;start.text="LƯU CÔNG NHẬT";showError(r.error?:"Không bắt đầu được công nhật");return@runOnUiThread}
                        if(selectedEnd==null){start.isEnabled=true;TopNotice.show(this,"Đã ghi nhận bắt đầu công nhật.",TopNotice.Kind.SUCCESS);foregroundSync.requestSync();initialMnv="";laborHome();return@runOnUiThread}
                        api.call("labor_finish",JSONObject().put("event_id",UUID.randomUUID().toString()).put("depends_on_event_id",startEvent).put("labor_id",laborId).put("mnv",laborMnv).put("business_date",laborBusinessDate).put("session_id",laborSessionId).put("start_at",startIso).put("end_at",selectedEnd).put("note",note.text.toString())){done->runOnUiThread{
                            start.isEnabled=true;start.text="LƯU CÔNG NHẬT";if(!done.ok)showError(done.error?:"Không ghi được giờ kết thúc công nhật")else{TopNotice.show(this,"Đã ghi nhận đủ thời gian công nhật.",TopNotice.Kind.SUCCESS);foregroundSync.requestSync();initialMnv="";laborHome()}
                        }}
                    }}
                }}
            }
            body.addView(start,matchWrap())
        }
        body.addView(gap(7));attach(root,body)
    }
    private fun resourceHome(){
        screenState="RESOURCE_HOME"
        val root=baseRoot("TÀI NGUYÊN");val body=body()
        val cards=listOf(
            Triple("PDA","PDA","Danh sách PDA"),
            Triple("USER_PICK","USER PICK","Danh sách / tình trạng"),
            Triple("PACK_TABLE","BÀN PACK","Danh sách / tình trạng"),
            Triple("USER_PACK","USER PACK","Danh sách / bàn liên kết")
        )
        cards.chunked(2).forEach{pair->
            val row=businessRow(
                businessCard(R.drawable.ic_pp_resource,pair[0].second,pair[0].third){resourceListScreen(pair[0].first,pair[0].second)},
                if(pair.size>1)businessCard(R.drawable.ic_pp_resource,pair[1].second,pair[1].third){resourceListScreen(pair[1].first,pair[1].second)} else Space(this)
            );body.addView(row);body.addView(gap(10))
        }
        attach(root,body)
    }

    private fun resourceListScreen(type:String,title:String){
        screenState="RESOURCE_LIST"
        val root=baseRoot(title);val body=body();val box=column(bg);val selected=linkedSetOf<String>();val checks=mutableListOf<CheckBox>()
        if(isAdmin()){val actions=row(bg);actions.addView(smallButton("THÊM",teal).apply{setOnClickListener{resourceEditDialog(type,null,null,null)}},LinearLayout.LayoutParams(0,dp(42),1f).apply{marginEnd=dp(3)});actions.addView(smallButton("CHỌN TẤT CẢ",navy).apply{setOnClickListener{checks.forEach{it.isChecked=true}}},LinearLayout.LayoutParams(0,dp(42),1f).apply{marginStart=dp(3);marginEnd=dp(3)});actions.addView(smallButton("XÓA ĐÃ CHỌN",red).apply{setOnClickListener{deleteResourcesBulk(type,selected.toList(),title)}},LinearLayout.LayoutParams(0,dp(42),1f).apply{marginStart=dp(3)});body.addView(actions,matchWrap());body.addView(gap(8))}
        body.addView(box,matchWrap());box.addView(info("Đang tải danh sách..."))
        api.call("resource_master_list"){r->runOnUiThread{
            box.removeAllViews();if(handleAuth(r))return@runOnUiThread;if(!r.ok){box.addView(info(r.error?:"Không tải được tài nguyên"));return@runOnUiThread}
            val all=r.json?.optJSONArray("resources")?:JSONArray();val catalogs=r.json?.optJSONArray("catalogs")?:JSONArray();val rows=mutableListOf<JSONObject>();for(i in 0 until all.length()){val x=all.optJSONObject(i)?:continue;if(x.optString("resource_type")==type)rows.add(x)}
            rows.sortWith(Comparator{a,b->naturalUserCompare(a.optString("resource_id"),b.optString("resource_id"))})
            if(rows.isEmpty())box.addView(info("Chưa có dữ liệu."))
            rows.forEach{x->val id=x.optString("resource_id");val card=column(surface).apply{setPadding(dp(12),dp(10),dp(12),dp(10));background=outlineBg(surface,14);val top=row(surface).apply{gravity=Gravity.CENTER_VERTICAL};if(isAdmin()){val c=CheckBox(this@OperationsActivity).apply{isChecked=id in selected;setOnCheckedChangeListener{_,on->if(on)selected.add(id)else selected.remove(id)}};checks.add(c);top.addView(c,size(dp(42),dp(42)))};val meta=runCatching{JSONObject(x.optString("metadata_json","{}"))}.getOrDefault(JSONObject());top.addView(column(surface).apply{addView(txt(id,13.2f,navy,true));val lines=when(type){"PDA"->listOf("5 số cuối Seri: ${dash(meta.optString("5 số cuối Seri"))}","Tình trạng: ${x.optString("status_label").ifBlank{"—"}}","Ghi chú: ${dash(meta.optString("Ghi chú"))}");"USER_PICK"->listOf("Số User: ${dash(meta.optString("Số User"))}","User Pick: ${dash(meta.optString("User Pick").ifBlank{id})}","Tình trạng: ${x.optString("status_label").ifBlank{"—"}}","Ghi chú: ${dash(meta.optString("Ghi chú"))}");"PACK_TABLE"->listOf("Tên bàn pack: ${dash(meta.optString("Tên bàn pack").ifBlank{id})}","Tình trạng: ${x.optString("status_label").ifBlank{"—"}}");else->listOf("Bàn Pack: ${dash(meta.optString("Tên bàn pack"))}","Nhãn: ${dash(meta.optString("User pack"))}","User Pack: ${dash(meta.optString("User Pack").ifBlank{id})}","Tình trạng: ${x.optString("status_label").ifBlank{"—"}}")};lines.forEach{addView(txt(it,9.8f,if(it.startsWith("Tình trạng"))if(x.optInt("available")!=0)green else muted else muted,it.startsWith("Tình trạng")))}} ,LinearLayout.LayoutParams(0,-2,1f));addView(top,matchWrap());if(isAdmin()){addView(gap(6));val a=row(surface);a.addView(smallButton("SỬA",teal).apply{setOnClickListener{resourceEditDialog(type,x,catalogs,all)}},LinearLayout.LayoutParams(0,dp(38),1f).apply{marginEnd=dp(3)});a.addView(smallButton("XÓA",red).apply{setOnClickListener{confirmDeleteResource(type,id,title)}},LinearLayout.LayoutParams(0,dp(38),1f).apply{marginStart=dp(3)});addView(a,matchWrap())}};box.addView(card,matchWrap());box.addView(gap(7))}
        }}
        attach(root,body)
    }

    private fun resourceStatusValues(type:String,catalogs:JSONArray?):MutableList<String>{
        val ns=when(type){"PDA"->"DANH SÁCH PDA_Tình trạng";"USER_PICK"->"DANH SÁCH USER PICK_Tình trạng";"PACK_TABLE"->"DANH SÁCH BÀN PACK_Tình trạng";else->"DANH SÁCH USER PACK_Tình trạng"}
        val out=mutableListOf<String>();if(catalogs!=null)for(i in 0 until catalogs.length()){val x=catalogs.optJSONObject(i)?:continue;if(x.optString("namespace")==ns&&x.optString("value").isNotBlank())out.add(x.optString("value"))}
        if(out.isEmpty())out.addAll(catalogValues(ns));return out.distinct().toMutableList()
    }

    private fun resourceEditDialog(type:String,existing:JSONObject?,catalogs:JSONArray?,all:JSONArray?,verified:Boolean=false){
        if(!isAdmin())return
        if(existing!=null&&!verified){verifyEditPassword("sửa tài nguyên"){resourceEditDialog(type,existing,catalogs,all,true)};return}
        val meta=runCatching{JSONObject(existing?.optString("metadata_json","{}")?:"{}")}.getOrDefault(JSONObject());val box=column(surface).apply{setPadding(dp(10),dp(4),dp(10),dp(8))}
        val id=input("Mã / tên tài nguyên",false).apply{setText(existing?.optString("resource_id").orEmpty());isEnabled=existing==null}
        val statuses=resourceStatusValues(type,catalogs);val statusSp=spinner((if(statuses.isEmpty())listOf("Hoạt động")else statuses).toTypedArray());selectByValue(statusSp,statuses,existing?.optString("status_label").orEmpty())
        val note=input("Ghi chú",false).apply{setText(meta.optString("Ghi chú").ifBlank{meta.optString("note")})}
        val extra1=input(when(type){"PDA"->"5 số cuối Seri";"USER_PICK"->"Số User";"USER_PACK"->"Tên bàn pack";else->""},false)
        val extra2=input(if(type=="USER_PACK")"Nhãn User pack (ví dụ CA 1-...)" else "",false)
        if(type=="PDA"){
            fun syncLast5(){
                val clean=id.text.toString().replace(Regex("\\s+"),"")
                if(id.text.toString()!=clean){id.setText(clean);id.setSelection(clean.length);return}
                extra1.setText(clean.takeLast(5));extra1.isEnabled=false;extra1.alpha=.72f
            }
            id.addTextChangedListener(object:TextWatcher{override fun beforeTextChanged(v:CharSequence?,a:Int,b:Int,c:Int)=Unit;override fun onTextChanged(v:CharSequence?,a:Int,b:Int,c:Int)=syncLast5();override fun afterTextChanged(v:Editable?)=Unit})
            syncLast5()
        }else if(type=="USER_PICK")extra1.setText(meta.optString("Số User")) else if(type=="USER_PACK"){extra1.setText(meta.optString("Tên bàn pack").ifBlank{meta.optString("pack_table")});extra2.setText(meta.optString("User pack").ifBlank{meta.optString("label")})}
        fun add(l:String,v:View){if(l.isBlank())return;box.addView(txt(l,10.2f,ink,true));box.addView(gap(4));box.addView(v,matchWrap());box.addView(gap(8))}
        add("Mã / tên tài nguyên",id);add("Tình trạng",statusSp);if(type=="PDA")add("5 số cuối Seri (tự động)",extra1) else if(type!="PACK_TABLE")add(extra1.hint?.toString().orEmpty(),extra1);if(type=="USER_PACK")add(extra2.hint?.toString().orEmpty(),extra2);add("Ghi chú",note)
        AlertDialog.Builder(this).setTitle(if(existing==null)"Thêm tài nguyên" else "Sửa tài nguyên").setView(ScrollView(this).apply{addView(box)}).setNegativeButton("Hủy",null).setPositiveButton("LƯU"){_,_->
            val key=id.text.toString().trim();if(key.isBlank()){showError("Mã tài nguyên là bắt buộc.");return@setPositiveButton}
            if(type=="PDA"&&key.any{it.isWhitespace()}){showError("Mã / tên PDA không được có khoảng trống.");return@setPositiveButton}
            val m=JSONObject().put("Ghi chú",note.text.toString().trim())
            when(type){"PDA"->{val last=key.takeLast(5);if(last.length!=5||!last.all{it.isDigit()}){showError("5 ký tự cuối Mã / tên PDA phải là 5 chữ số Seri.");return@setPositiveButton};m.put("Seri PDA",key).put("5 số cuối Seri",last)};"USER_PICK"->m.put("User Pick",key).put("Số User",extra1.text.toString().trim());"USER_PACK"->{val table=extra1.text.toString().trim();if(table.isBlank()){showError("Tên bàn pack là bắt buộc cho User Pack.");return@setPositiveButton};m.put("Tên bàn pack",table).put("User Pack",key).put("User pack",extra2.text.toString().trim())};"PACK_TABLE"->m.put("Tên bàn pack",key)}
            val p=JSONObject().put("operation","UPSERT").put("resource_type",type).put("resource_id",key).put("status_label",statusSp.selectedItem?.toString().orEmpty()).put("metadata",m).put("idempotency_key",UUID.randomUUID().toString())
            api.call("resource_master_upsert",p){r->runOnUiThread{if(handleAuth(r))return@runOnUiThread;if(!r.ok)showError(r.error?:"Không lưu được tài nguyên")else{TopNotice.show(this,"Đã cập nhật tài nguyên.",TopNotice.Kind.SUCCESS);resourceListScreen(type,when(type){"PDA"->"DANH SÁCH PDA";"USER_PICK"->"DANH SÁCH USER PICK";"PACK_TABLE"->"DANH SÁCH BÀN PACK";else->"DANH SÁCH USER PACK"})}}}
        }.show()
    }

    private fun deleteResourcesBulk(type:String,ids:List<String>,title:String){
        if(!isAdmin())return;if(ids.isEmpty()){showError("Chọn ít nhất một mục cần xóa.");return}
        AlertDialog.Builder(this).setTitle("Xóa ${ids.size} mục?").setMessage("Tài nguyên đang được sử dụng sẽ bị hệ thống chặn xóa.").setNegativeButton("Hủy",null).setPositiveButton("TIẾP TỤC"){_,_->verifyDeletePassword("xóa ${ids.size} tài nguyên"){fun next(i:Int){if(i>=ids.size){TopNotice.show(this,"Đã xử lý xóa các mục đã chọn.",TopNotice.Kind.SUCCESS);resourceListScreen(type,title);return};api.call("resource_master_delete",JSONObject().put("operation","DELETE").put("resource_type",type).put("resource_id",ids[i]).put("idempotency_key",UUID.randomUUID().toString())){r->runOnUiThread{if(handleAuth(r))return@runOnUiThread;if(!r.ok){showError("${ids[i]}: ${r.error?:"Không xóa được"}");return@runOnUiThread};next(i+1)}}};next(0)}}.show()
    }

    private fun confirmDeleteResource(type:String,id:String,title:String){
        if(!isAdmin())return
        AlertDialog.Builder(this).setTitle("Xóa tài nguyên?").setMessage("Xóa $id khỏi $title?").setNegativeButton("Hủy",null).setPositiveButton("TIẾP TỤC"){_,_->verifyDeletePassword("xóa tài nguyên $id"){api.call("resource_master_delete",JSONObject().put("operation","DELETE").put("resource_type",type).put("resource_id",id).put("idempotency_key",UUID.randomUUID().toString())){r->runOnUiThread{if(handleAuth(r))return@runOnUiThread;if(!r.ok)showError(r.error?:"Không xóa được tài nguyên")else{TopNotice.show(this,"Đã xóa tài nguyên.",TopNotice.Kind.SUCCESS);resourceListScreen(type,title)}}}}}.show()
    }

    private fun staffScreen(){
        module="STAFF";screenState="STAFF"
        val root=baseRoot("NHÂN SỰ")
        val selected=linkedSetOf<String>();val checks=mutableListOf<CheckBox>()
        val fixed=column(bg).apply{setPadding(dp(10),dp(8),dp(10),dp(4))}
        val searchRow=row(bg).apply{gravity=Gravity.CENTER_VERTICAL}
        val q=input("Tìm mã nhân viên, họ tên hoặc số điện thoại",false).apply{setSingleLine(true);imeOptions=EditorInfo.IME_ACTION_SEARCH;contentDescription="Tìm kiếm nhân sự cố định"}
        searchRow.addView(q,LinearLayout.LayoutParams(0,dp(50),1f))
        if(isAdmin()){searchRow.addView(gap(8));searchRow.addView(iconActionButton(R.drawable.ic_pp_add,teal,"Thêm nhân sự"){staffEditor(null)},size(dp(50),dp(50)))}
        fixed.addView(searchRow,matchWrap())
        if(isSuper()){
            fixed.addView(gap(7))
            val bulk=row(bg)
            bulk.addView(smallButton("CHỌN TẤT CẢ",navy).apply{setOnClickListener{checks.forEach{it.isChecked=true}}},LinearLayout.LayoutParams(0,dp(42),1f).apply{marginEnd=dp(3)})
            bulk.addView(smallButton("XÓA ĐÃ CHỌN",red).apply{setOnClickListener{deleteStaffBulk(selected.toList())}},LinearLayout.LayoutParams(0,dp(42),1f).apply{marginStart=dp(3)})
            fixed.addView(bulk,matchWrap())
        }
        root.addView(fixed,matchWrap())
        val listBody=column(bg).apply{setPadding(dp(10),dp(4),dp(10),dp(76))}
        val box=column(bg);listBody.addView(box,matchWrap());var pageSize=60
        fun render(query:String){
            box.removeAllViews();checks.clear()
            val clean=query.trim();val limit=if(clean.isBlank())pageSize else 180
            val arr=MasterDataCache.searchStaff(this,clean,limit)
            for(i in 0 until arr.length()){
                val e=arr.optJSONObject(i)?:continue;val id=e.optString("mnv")
                val card=column(surface).apply{
                    setPadding(dp(11),dp(9),dp(11),dp(9));background=outlineBg(surface,15)
                    val top=row(surface).apply{gravity=Gravity.CENTER_VERTICAL}
                    if(isSuper()){
                        val c=CheckBox(this@OperationsActivity).apply{isChecked=id in selected;setOnCheckedChangeListener{_,on->if(on)selected.add(id)else selected.remove(id)}}
                        checks.add(c);top.addView(c,size(dp(40),dp(40)))
                    }
                    top.addView(column(surface).apply{
                        addView(txt(dash(e.optString("full_name")),13.5f,ink,true).apply{maxLines=2})
                        addView(txt("$id • ${dash(e.optString("main_position"))}",10.5f,navy,true))
                        addView(txt("SĐT: ${dash(e.optString("phone"))} • Bắt đầu: ${dash(e.optString("start_date"))}",9.6f,teal,true).apply{maxLines=2})
                        addView(txt("${dash(e.optString("supplier"))} • ${dash(e.optString("department"))} • Site ${dash(e.optString("site"))} • Kho ${dash(e.optString("warehouse"))}",9.1f,muted,false).apply{maxLines=3})
                    },LinearLayout.LayoutParams(0,-2,1f))
                    if(isAdmin()){
                        top.addView(iconActionButton(R.drawable.ic_pp_edit,teal,"Sửa"){staffEditor(e)},size(dp(38),dp(38)))
                        if(isSuper()){top.addView(gap(4));top.addView(iconActionButton(R.drawable.ic_pp_delete,red,"Xóa"){confirmDeleteStaff(e)},size(dp(38),dp(38)))}
                    }
                    addView(top,matchWrap())
                }
                box.addView(card,matchWrap());box.addView(gap(6))
            }
            if(arr.length()==0)box.addView(info("Không có nhân sự phù hợp."))
            if(clean.isBlank()&&arr.length()>=pageSize&&pageSize<MasterDataCache.staffCount(this))box.addView(primary("XEM THÊM",teal){pageSize+=60;render("")},matchWrap())
        }
        q.addTextChangedListener(object:TextWatcher{override fun beforeTextChanged(v:CharSequence?,st:Int,c:Int,a:Int)=Unit;override fun onTextChanged(v:CharSequence?,st:Int,b:Int,c:Int){render(v?.toString().orEmpty())};override fun afterTextChanged(v:Editable?)=Unit})
        q.setOnEditorActionListener{_,_,_->render(q.text.toString());true}
        render("")
        root.addView(ScrollView(this).apply{addView(listBody)},LinearLayout.LayoutParams(-1,0,1f))
        setScreen(root)
    }

    private fun staffEditor(existing:JSONObject?){
        if(!isAdmin())return
        if(existing!=null){verifyEditPassword{staffEditorUnlocked(existing)};return}
        staffEditorUnlocked(null)
    }

    private fun verifyEditPassword(actionLabel:String="quyền sửa",after:()->Unit)=verifyActionPassword(actionLabel,after)

    private fun staffEditorUnlocked(existing:JSONObject?){
        val box=column(surface).apply{setPadding(dp(10),dp(4),dp(10),dp(8))};val mnv=mnvInput("Mã nhân viên").apply{setText(existing?.optString("mnv").orEmpty());isEnabled=existing==null};val full=input("Họ và tên",false).apply{setText(existing?.optString("full_name").orEmpty())};val phone=input("Số điện thoại",false).apply{setText(existing?.optString("phone").orEmpty());inputType=InputType.TYPE_CLASS_PHONE;keyListener=DigitsKeyListener.getInstance("0123456789")}
        val pos=catalogSpinner("DANH SÁCH NHÂN SỰ_Vị trí chính",existing?.optString("main_position").orEmpty(),true);val supplier=catalogSpinner("DANH SÁCH NHÂN SỰ_Nhà cung cấp",existing?.optString("supplier").orEmpty(),true);val department=catalogSpinner("DANH SÁCH NHÂN SỰ_Bộ phận",existing?.optString("department").orEmpty(),true);val site=catalogSpinner("DANH SÁCH NHÂN SỰ_Site",existing?.optString("site").orEmpty(),true);val warehouse=catalogSpinner("DANH SÁCH NHÂN SỰ_Kho",existing?.optString("warehouse").orEmpty(),true)
        val startDate=input("Chọn ngày bắt đầu",false).apply{setText(existing?.optString("start_date").orEmpty());isFocusable=false;isClickable=true};startDate.setOnClickListener{val now=java.time.LocalDate.now(ZoneId.of("Asia/Ho_Chi_Minh"));val parts=startDate.text.toString().split("/");val d=parts.getOrNull(0)?.toIntOrNull()?:now.dayOfMonth;val m=(parts.getOrNull(1)?.toIntOrNull()?:now.monthValue)-1;val y=parts.getOrNull(2)?.toIntOrNull()?:now.year;android.app.DatePickerDialog(this,{_,yy,mm,dd->startDate.setText(String.format(java.util.Locale.US,"%02d/%02d/%04d",dd,mm+1,yy))},y,m,d).show()};val note=input("Ghi chú",false).apply{setText(existing?.optString("note").orEmpty())}
        fun addField(label:String,view:View){box.addView(txt(label,10.2f,ink,true));box.addView(gap(4));box.addView(view,matchWrap());box.addView(gap(8))};addField("Mã nhân viên",mnv);addField("Họ và tên",full);addField("Số điện thoại",phone);addField("Vị trí chính",pos);addField("Nhà cung cấp",supplier);addField("Bộ phận",department);addField("Site",site);addField("Kho",warehouse);addField("Ngày bắt đầu làm việc",startDate);addField("Ghi chú",note)
        val dialog=AlertDialog.Builder(this).setTitle(if(existing==null)"Thêm nhân sự" else "Sửa nhân sự").setView(ScrollView(this).apply{addView(box)}).setNegativeButton("Hủy",null).setPositiveButton("LƯU",null).create();dialog.setOnShowListener{dialog.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener{val id=mnv.text.toString().trim();val nm=full.text.toString().trim();val ph=phone.text.toString().trim();val sd=startDate.text.toString().trim();if(id.isBlank()||!id.all{it.isDigit()}){showError("Mã nhân viên là bắt buộc và chỉ gồm chữ số.");return@setOnClickListener};if(nm.isBlank()){showError("Họ và tên là bắt buộc.");return@setOnClickListener};if(!Regex("^0[0-9]{9}$").matches(ph)){showError("Số điện thoại phải gồm 10 chữ số và bắt đầu bằng 0.");return@setOnClickListener};if(!Regex("^(0[1-9]|[12][0-9]|3[01])/(0[1-9]|1[0-2])/([0-9]{4})$").matches(sd)){showError("Ngày bắt đầu làm việc chưa hợp lệ.");return@setOnClickListener};val payload=JSONObject().put("event_id",UUID.randomUUID().toString()).put("mnv",id).put("full_name",nm).put("phone",ph).put("main_position",catalogSelection(pos)).put("supplier",catalogSelection(supplier)).put("department",catalogSelection(department)).put("site",catalogSelection(site)).put("warehouse",catalogSelection(warehouse)).put("start_date",sd).put("note",note.text.toString());api.call("staff_upsert",payload){r->runOnUiThread{if(handleAuth(r))return@runOnUiThread;if(!r.ok)showError(r.error?:"Không lưu được nhân sự")else{dialog.dismiss();reloadMaster{TopNotice.show(this,"Đã lưu nhân sự.",TopNotice.Kind.SUCCESS);staffScreen()}}}}}};dialog.show()
    }

    private fun deleteStaffBulk(ids:List<String>){
        if(!isSuper()){showError("Chỉ Quản trị cao nhất được xóa nhân sự.");return};if(ids.isEmpty()){showError("Chọn ít nhất một nhân sự cần xóa.");return}
        AlertDialog.Builder(this).setTitle("Xóa ${ids.size} nhân sự?").setMessage("Nhân sự đang có phiên hoạt động sẽ bị hệ thống chặn xóa. Lịch sử nghiệp vụ vẫn được giữ.").setNegativeButton("Hủy",null).setPositiveButton("TIẾP TỤC"){_,_->verifyDeletePassword("xóa ${ids.size} nhân sự"){fun next(i:Int){if(i>=ids.size){reloadMaster{TopNotice.show(this,"Đã xử lý xóa các nhân sự đã chọn.",TopNotice.Kind.SUCCESS);staffScreen()};return};api.call("staff_delete",JSONObject().put("event_id",UUID.randomUUID().toString()).put("mnv",ids[i])){r->runOnUiThread{if(handleAuth(r))return@runOnUiThread;if(!r.ok){showError("${ids[i]}: ${r.error?:"Không xóa được"}");return@runOnUiThread};next(i+1)}}};next(0)}}.show()
    }

    private fun confirmDeleteStaff(employee:JSONObject){
        if(!isSuper()){showError("Chỉ Quản trị cao nhất được xóa nhân sự.");return}
        val id=employee.optString("mnv");AlertDialog.Builder(this).setTitle("Xóa nhân sự?").setMessage("Xóa Mã nhân viên $id • ${employee.optString("full_name")}? Lịch sử nghiệp vụ vẫn được giữ.").setNegativeButton("Hủy",null).setPositiveButton("TIẾP TỤC"){_,_->verifyDeletePassword("xóa nhân sự $id"){api.call("staff_delete",JSONObject().put("event_id",UUID.randomUUID().toString()).put("mnv",id)){r->runOnUiThread{if(handleAuth(r))return@runOnUiThread;if(!r.ok)showError(r.error?:"Không xóa được nhân sự")else reloadMaster{TopNotice.show(this,"Đã xóa nhân sự.",TopNotice.Kind.SUCCESS);staffScreen()}}}}}.show()
    }

    private fun reloadMaster(done:()->Unit){
        cacheApi.call("master_snapshot") { result ->
            runOnUiThread {
                if(result.ok && result.json!=null) MasterDataCache.save(this,result.json)
                done()
            }
        }
    }

    private fun listsScreen(){
        screenState = "LISTS"
        val root=baseRoot("DANH SÁCH");val body=body();val q=scanSearchInput("Scan / Nhập mã nhân viên, họ tên để tìm kiếm");body.addView(q,matchWrap());body.addView(gap(8));val buttons=row(bg);val sessions=smallButton("PHIÊN HÔM NAY",blue);val labor=smallButton("CÔNG NHẬT",green);val staff=smallButton("NHÂN SỰ",navy);buttons.addView(sessions,LinearLayout.LayoutParams(0,dp(44),1f).apply{marginEnd=dp(3)});buttons.addView(labor,LinearLayout.LayoutParams(0,dp(44),1f).apply{marginStart=dp(3);marginEnd=dp(3)});buttons.addView(staff,LinearLayout.LayoutParams(0,dp(44),1f).apply{marginStart=dp(3)});body.addView(buttons,matchWrap());body.addView(gap(9));val box=column(bg);body.addView(box,matchWrap())
        var active="SESSIONS"
        fun loadSessions(){box.removeAllViews();box.addView(txt("Đang tải...",10.5f,muted,false));api.call("list_sessions",JSONObject().put("query",q.text.toString())){r->runOnUiThread{if(screenState!="LISTS"||active!="SESSIONS")return@runOnUiThread;box.removeAllViews();if(handleAuth(r))return@runOnUiThread;if(!r.ok){box.addView(info(r.error?:"Lỗi"));return@runOnUiThread};val a=r.json?.optJSONArray("items")?:JSONArray();if(a.length()==0)box.addView(info("Chưa có phiên phù hợp."));for(i in 0 until a.length()){val s=a.optJSONObject(i)?:continue;val e=s.optJSONObject("employee_snapshot")?:JSONObject();box.addView(listCard("${s.optString("mnv")} • ${e.optString("full_name")}","${s.optString("state")} • ${s.optString("shift")} • ${workText(s.optString("work_choice"))}\nPDA ${dash(s.optString("pda_serial"))} • Pick ${dash(s.optString("user_pick"))} • Pack ${dash(s.optString("pack_table"))}"));box.addView(gap(6))}}}}
        fun loadLabor(){box.removeAllViews();if(!isAdmin()){box.addView(info("Công nhật chỉ hiển thị cho ADMIN/SUPERADMIN."));return};api.call("list_labor"){r->runOnUiThread{if(screenState!="LISTS"||active!="LABOR")return@runOnUiThread;box.removeAllViews();if(handleAuth(r))return@runOnUiThread;if(!r.ok){box.addView(info(r.error?:"Lỗi"));return@runOnUiThread};val a=r.json?.optJSONArray("items")?:JSONArray();if(a.length()==0)box.addView(info("Chưa có công nhật hôm nay."));for(i in 0 until a.length()){val l=a.optJSONObject(i)?:continue;val e=l.optJSONObject("employee_snapshot")?:JSONObject();box.addView(listCard("${l.optString("mnv")} • ${e.optString("full_name")}","${l.optString("state")} • ${l.optString("labor_type")}\n${formatIso(l.optString("start_at"))} → ${formatIso(l.optString("end_at"))}"));box.addView(gap(6))}}}}
        fun searchStaff(){val query=q.text.toString().trim();box.removeAllViews();if(query.length<2){box.addView(info("Nhập ít nhất 2 ký tự để tìm nhân sự."));return};val a=MasterDataCache.searchStaff(this,query);for(i in 0 until a.length()){val e=a.optJSONObject(i)?:continue;box.addView(listCard("${e.optString("mnv")} • ${e.optString("full_name")}","${e.optString("main_position")} • ${e.optString("supplier")} • ${e.optString("department")}"));box.addView(gap(6))};if(a.length()==0)box.addView(info("Không tìm thấy nhân sự phù hợp."))}
        fun refreshActive(){when(active){"LABOR"->loadLabor();"STAFF"->searchStaff();else->loadSessions()}}
        listsRealtimeRefresh={if(screenState=="LISTS")refreshActive()}
        sessions.setOnClickListener{active="SESSIONS";loadSessions()};labor.setOnClickListener{active="LABOR";loadLabor()};staff.setOnClickListener{active="STAFF";searchStaff()};q.setOnEditorActionListener{_,_,_->active="STAFF";searchStaff();true};loadSessions();attach(root,body)
    }

    private fun reportDateLabel(iso:String):String=runCatching{
        java.time.LocalDate.parse(iso).format(java.time.format.DateTimeFormatter.ofPattern("dd/MM/yyyy"))
    }.getOrDefault(iso)

    // S34C_SITE1291_LOCAL_REPORT: manpower is derived from the canonical day event snapshot.
    // A person counts on the entry business date as soon as ATTENDANCE_ENTER exists; ATTENDANCE_EXIT is not required.
    // S36_PERF_HISTORY_REPORT_SERVICE: selected-date cached aggregation; no full-day parse on UI thread.
    private fun reportScreen(){
        module="BUSINESS";screenState="REPORT"
        val root=baseRoot("BÁO CÁO NHÂN SỰ");val body=column(bg).apply{setPadding(dp(3),dp(6),dp(3),dp(42))}
        val period=spinner(arrayOf("Ca 1 + Ca HC","Ca 2","Cả ngày"))
        fun availableReportDates():List<String> = operationalStore.availableDates().filter{date->
            val events=operationalStore.loadDay(date)?.optJSONArray("events")
            events!=null&&(0 until events.length()).any{i->events.optJSONObject(i)?.optString("event_type")?.uppercase()=="ATTENDANCE_ENTER"}
        }
        val initialReportDates=availableReportDates()
        var selectedDate=initialReportDates.firstOrNull()?:operationalStore.businessDate()
        val dateButton=Button(this).apply{
            text=runCatching{java.time.LocalDate.parse(selectedDate).format(DateTimeFormatter.ofPattern("dd/MM/yyyy"))}.getOrDefault(selectedDate)
            textSize=12f;isAllCaps=false;background=outlineBg(surface,14);setTextColor(ink);isEnabled=true
        }
        val controls=row(bg).apply{gravity=Gravity.CENTER_VERTICAL;addView(period,LinearLayout.LayoutParams(0,dp(50),1f).apply{marginEnd=dp(5)});addView(dateButton,LinearLayout.LayoutParams(0,dp(50),1f).apply{marginStart=dp(5)})}
        body.addView(section("Phạm vi báo cáo"));body.addView(controls,matchWrap());body.addView(gap(7))
        val box=column(bg);body.addView(box,matchWrap())
        fun fold(v:String)=java.text.Normalizer.normalize(v,java.text.Normalizer.Form.NFD).replace(Regex("\\p{Mn}+"),"").uppercase().trim()
        fun site1291(v:String):Boolean{val x=fold(v);return x=="1291"||x=="SITE 1291"||Regex("(^|[^0-9])1291([^0-9]|$)").containsMatchIn(x)}
        fun shiftBucket(v:String):String{val x=fold(v).replace(Regex("\\s+")," ");return when{x=="CA 1"||x=="CA1"||x=="1"->"CA1";x=="CA HC"||x=="CAHC"||x=="HC"||x.contains("HANH CHINH")->"HC";x=="CA 2"||x=="CA2"||x=="2"->"CA2";else->x}}
        fun supplierCode(raw:String):String{val x=fold(raw);return when{x=="INHOUSE"||x=="IH"->"IH";x=="NGUON LUC VIET"||x=="NLV"->"NLV";x=="VIET WORK"||x=="VW"->"VW";x=="MAN POWER"||x=="MP"->"MP";x=="MEGA LINK"||x=="MGL"->"MGL";x=="HA GIA PHAT"||x=="HGP"->"HGP";x=="HOA ANH DAO"||x=="HAD"->"HAD";else->raw.trim().ifBlank{"Khác"}}}
        fun reportPosition(emp:JSONObject,work:String):String{val p=fold(emp.optString("main_position"));val d=fold(emp.optString("department"));return when{p=="TRUONG NHOM"->"Trưởng nhóm";p=="CHUYEN VIEN"->"Chuyên viên";p=="TO TRUONG"->"Tổ trưởng";p.contains("DIEU PHOI")&&d.contains("PACK")->"Điều phối khu pack";p.contains("DIEU PHOI")&&(d.contains("CHO XUAT")||d.contains("GIAO VAN")||d.contains("OUTBOUND"))->"Điều phối khu chờ xuất";p.contains("KEO HANG")->"Kéo hàng";p=="5S"||p.contains(" 5S")->"5S";p.contains("PHUC LONG")->"Phúc Long";fold(work)=="PICK"||p.contains("PICK")->"Picker";fold(work)=="PACK"||p.contains("PACK")->"Packer";else->emp.optString("main_position").ifBlank{"Khác"}}}
        fun tenureLabel(emp:JSONObject,date:String):String{val raw=emp.optString("start_date").trim();if(raw.isBlank())return "Nhân sự cũ";val started=runCatching{if(raw.matches(Regex("\\d{2}/\\d{2}/\\d{4}")))java.time.LocalDate.parse(raw,DateTimeFormatter.ofPattern("dd/MM/yyyy"))else java.time.LocalDate.parse(raw.take(10))}.getOrNull()?:return "Nhân sự cũ";val target=runCatching{java.time.LocalDate.parse(date)}.getOrNull()?:return "Nhân sự cũ";return if(java.time.temporal.ChronoUnit.DAYS.between(started,target)<=30)"Nhân sự mới" else "Nhân sự cũ"}
        data class Entry(val mnv:String,val shift:String,val work:String,val emp:JSONObject,val deductSupport:Boolean=false)
        var cachedDate="";var cachedEntries:List<Entry> = emptyList();var loadSerial=0
        fun makeGrid(rows:List<Entry>,kind:String,date:String):JSONObject{
            val columns=listOf("IH","NLV","VW","MP","MGL","HGP","HAD").filter{c->rows.any{supplierCode(it.emp.optString("supplier"))==c}}
            val rowOrder=if(kind=="position")listOf("Trưởng nhóm","Chuyên viên","Tổ trưởng","Điều phối khu pack","Điều phối khu chờ xuất","Kéo hàng","5S","Picker","Packer","Phúc Long","Khác") else listOf("Nhân sự mới","Nhân sự cũ")
            val values=LinkedHashMap<String,MutableMap<String,Int>>();rowOrder.forEach{values[it]=LinkedHashMap()}
            rows.forEach{r->val label=if(kind=="position")reportPosition(r.emp,r.work) else tenureLabel(r.emp,date);val key=if(values.containsKey(label))label else if(kind=="position")"Khác" else label;val sup=supplierCode(r.emp.optString("supplier"));values.getOrPut(key){LinkedHashMap()}[sup]=(values[key]?.get(sup)?:0)+1}
            val outRows=JSONArray();rowOrder.forEach{label->val counts=JSONObject();var total=0;columns.forEach{c->val n=values[label]?.get(c)?:0;counts.put(c,n);total+=n};if(total>0||kind!="position")outRows.put(JSONObject().put(if(kind=="position")"position" else "label",label).put("counts",counts).put("total",total))};val totals=JSONObject();var grand=0;columns.forEach{c->val n=rowOrder.sumOf{values[it]?.get(c)?:0};totals.put(c,n);grand+=n};return JSONObject().put("columns",JSONArray(columns)).put("rows",outRows).put("totals",totals).put("total",grand)
        }
        fun supportGrid(rows:List<Entry>):JSONObject{
            val unique=rows.distinctBy{"${it.mnv}|${shiftBucket(it.shift)}"}
            val columns=listOf("IH","NLV","VW","MP","MGL","HGP","HAD").filter{code->unique.any{supplierCode(it.emp.optString("supplier"))==code}}
            val counts=JSONObject();var total=0
            columns.forEach{code->val n=unique.count{supplierCode(it.emp.optString("supplier"))==code};counts.put(code,n);total+=n}
            val row=JSONObject().put("position","Hỗ trợ bộ phận khác").put("counts",counts).put("total",total)
            return JSONObject().put("columns",JSONArray(columns)).put("rows",JSONArray().put(row)).put("totals",JSONObject(counts.toString())).put("total",total)
        }
        fun renderCached(){
            box.removeAllViews();if(cachedDate!=selectedDate){box.addView(info("Đang đọc snapshot $selectedDate từ bộ nhớ PDA…"));return}
            val selected=cachedEntries.filter{when(period.selectedItemPosition){0->shiftBucket(it.shift) in setOf("CA1","HC");1->shiftBucket(it.shift)=="CA2";else->true}}
            val support=selected.filter{it.deductSupport}.distinctBy{"${it.mnv}|${shiftBucket(it.shift)}"}
            // OWNER Beta116: Tổng luôn là nhân sự thực tế trước khấu trừ.
            val main=selected
            box.addView(s34ReportGrid("",makeGrid(main,"position",selectedDate),"Vị trí","position"));box.addView(gap(4));box.addView(s34ReportGrid("",makeGrid(main,"tenure",selectedDate),"Thâm niên","label"))
            val pickerBase=main.count{reportPosition(it.emp,it.work)=="Picker"}
            val packerBase=main.count{reportPosition(it.emp,it.work)=="Packer"}
            val pickerDeduct=support.count{reportPosition(it.emp,it.work)=="Picker"}
            val packerDeduct=support.count{reportPosition(it.emp,it.work)=="Packer"}
            box.addView(gap(4))
            box.addView(details(listOf(
                "Tổng nhân sự" to main.distinctBy{"${it.mnv}|${shiftBucket(it.shift)}"}.size.toString(),
                "Khấu trừ công nhật" to support.size.toString(),
                "Picker thực tế" to "${(pickerBase-pickerDeduct).coerceAtLeast(0)} / $pickerBase",
                "Packer thực tế" to "${(packerBase-packerDeduct).coerceAtLeast(0)} / $packerBase"
            )))
            if(support.isNotEmpty()){box.addView(gap(4));box.addView(s34ReportGrid("",supportGrid(support),"Khấu trừ công nhật","position"))}
            if(cachedEntries.isEmpty())box.addView(info("Chưa có snapshot ngày đã chọn trên PDA. Chọn ngày khác hoặc đồng bộ để tải dữ liệu canonical."))
        }
        fun loadDate(){
            val serial=++loadSerial;cachedDate="";box.removeAllViews();box.addView(info("Đang đọc báo cáo $selectedDate…"))
            Thread{
                val out=LinkedHashMap<String,Entry>();val day=operationalStore.loadDay(selectedDate);val events=day?.optJSONArray("events")?:JSONArray()
                val deducted=mutableSetOf<String>()
                fun deductedFlag(v:Any?):Boolean=when(v){is Boolean->v;is Number->v.toInt()!=0;else->foldLocal(v?.toString().orEmpty()) in setOf("CO","TRUE","1","YES")}
                for(i in 0 until events.length()){
                    val e=events.optJSONObject(i)?:continue;if(e.optString("event_type").uppercase()!="LABOR_START")continue
                    val p=runCatching{JSONObject(e.optString("payload_json","{}"))}.getOrDefault(JSONObject())
                    val after=p.optJSONObject("after");val mnv=e.optString("mnv").ifBlank{p.optString("mnv")}.ifBlank{after?.optString("mnv").orEmpty()}
                    val shift=e.optString("shift").ifBlank{p.optString("shift")}.ifBlank{after?.optString("shift").orEmpty()}
                    val raw=if(p.has("deduct_staff"))p.opt("deduct_staff") else after?.opt("deduct_staff")
                    if(mnv.isNotBlank()&&shift.isNotBlank()&&deductedFlag(raw))deducted.add("$mnv|${shiftBucket(shift)}")
                }
                for(i in 0 until events.length()){
                    val e=events.optJSONObject(i)?:continue;if(e.optString("event_type").uppercase()!="ATTENDANCE_ENTER")continue
                    val p=runCatching{JSONObject(e.optString("payload_json","{}"))}.getOrDefault(JSONObject());val after=p.optJSONObject("after");val snap=p.optJSONObject("employee_snapshot")?:after?.optJSONObject("employee_snapshot")
                    val mnv=e.optString("mnv").ifBlank{p.optString("mnv")}.ifBlank{after?.optString("mnv").orEmpty()}.ifBlank{snap?.optString("mnv").orEmpty()};if(mnv.isBlank())continue
                    val emp=MasterDataCache.employee(this,mnv)?:snap?:JSONObject();if(!site1291(emp.optString("site")))continue
                    val shift=e.optString("shift").ifBlank{p.optString("shift")}.ifBlank{after?.optString("shift").orEmpty()};val work=e.optString("work_choice").ifBlank{p.optString("work_choice")}.ifBlank{after?.optString("work_choice").orEmpty()}
                    val key=e.optString("entity_id").ifBlank{e.optString("session_id")}.ifBlank{e.optString("event_id")}.ifBlank{"$mnv|$shift|$i"}
                    out[key]=Entry(mnv,shift,work,emp,"$mnv|${shiftBucket(shift)}" in deducted)
                }
                runOnUiThread{if(serial==loadSerial&&screenState=="REPORT"){cachedDate=selectedDate;cachedEntries=out.values.toList();renderCached()}}
            }.start()
        }
        dateButton.setOnClickListener{
            val dates=availableReportDates()
            DataDatePickerUi.show(this,dates,selectedDate){chosen->
                selectedDate=chosen;dateButton.text=reportDateLabel(chosen);loadDate()
            }
        }
        period.onItemSelectedListener=object:android.widget.AdapterView.OnItemSelectedListener{override fun onItemSelected(p:android.widget.AdapterView<*>?,v:View?,pos:Int,id:Long){if(cachedDate==selectedDate)renderCached()};override fun onNothingSelected(p:android.widget.AdapterView<*>?)=Unit}
        reportRealtimeRefresh={dates->if(screenState=="REPORT"&&(dates.isEmpty()||selectedDate in dates))loadDate()}
        attach(root,body);loadDate()
    }

    private fun reportTable(title:String,data:JSONObject?,firstTitle:String,rowKey:String,highlightPhuc:Boolean):View{
        val outer=column(surface).apply{setPadding(0,0,0,0);setBackgroundColor(surface)}
        if(title.isNotBlank())outer.addView(txt(title,10.2f,navy,true).apply{setPadding(dp(2),dp(2),0,dp(3))})
        if(data==null){outer.addView(txt("Chưa có dữ liệu",9.4f,muted,false));return outer}
        val columns=jsonStrings(data.optJSONArray("columns"))
        val rows=data.optJSONArray("rows")?:JSONArray()
        val table=TableLayout(this).apply{isStretchAllColumns=false;isShrinkAllColumns=false}
        val header=TableRow(this)
        header.addView(reportFixedCell(firstTitle,true,true,false),TableRow.LayoutParams(dp(126),-2))
        columns.forEach{header.addView(reportFixedCell(reportColumnLabel(it),true,false,false),TableRow.LayoutParams(dp(if(it=="IH")44 else 40),-2))}
        header.addView(reportFixedCell("Tổng",true,false,true),TableRow.LayoutParams(dp(42),-2));table.addView(header)
        for(i in 0 until rows.length()){
            val item=rows.optJSONObject(i)?:continue
            val label=item.optString(rowKey)
            val tr=TableRow(this)
            tr.addView(reportFixedCell(label,false,true,highlightPhuc&&label=="Phúc Long"),TableRow.LayoutParams(dp(126),-2))
            val counts=item.optJSONObject("counts")?:JSONObject()
            columns.forEach{c->tr.addView(reportFixedCell(counts.optInt(c).toString(),false,false,highlightPhuc&&label=="Phúc Long"),TableRow.LayoutParams(dp(if(c=="IH")44 else 40),-1))}
            tr.addView(reportFixedCell(item.optInt("total").toString(),false,false,highlightPhuc&&label=="Phúc Long",true),TableRow.LayoutParams(dp(42),-1));table.addView(tr)
        }
        val totals=data.optJSONObject("totals")
        if(totals!=null){
            val tr=TableRow(this)
            tr.addView(reportFixedCell("Tổng",true,true,false),TableRow.LayoutParams(dp(126),-2))
            columns.forEach{c->tr.addView(reportFixedCell(totals.optInt(c).toString(),true,false,false),TableRow.LayoutParams(dp(if(c=="IH")44 else 40),-1))}
            tr.addView(reportFixedCell(data.optInt("total").toString(),true,false,true),TableRow.LayoutParams(dp(42),-1));table.addView(tr)
        }
        outer.addView(HorizontalScrollView(this).apply{isHorizontalScrollBarEnabled=true;isFillViewport=false;addView(table,ViewGroup.LayoutParams(-2,-2))},matchWrap())
        return outer
    }

    private fun reportColumnLabel(v:String)=if(v=="IH")"Inhouse" else v
    private fun reportFixedCell(v:String,header:Boolean=false,first:Boolean=false,highlight:Boolean=false,total:Boolean=false)=TextView(this).apply{
        text=v;textSize=if(header)8.0f else 8.3f;setTextColor(if(header||total)navy else ink)
        typeface=if(header||first||total)Typeface.DEFAULT_BOLD else Typeface.DEFAULT
        gravity=if(first)Gravity.START or Gravity.CENTER_VERTICAL else Gravity.CENTER
        setPadding(dp(if(first)5 else 2),dp(4),dp(2),dp(4));maxLines=if(first)3 else 2
        background=GradientDrawable().apply{
            setColor(when{highlight->Color.rgb(246,249,82);header||total->Color.rgb(226,238,244);else->Color.WHITE})
            setStroke(dp(1),Color.rgb(105,118,126))
        }
    }

    // S32_LOCAL_HISTORY_FLUSH_FIX: History is local-first and never depends on remote ACK to exist.
    // S34D_COMPILE_FIXES: compact renderer owned by the Site 1291 local report.
    private fun s34ReportGrid(title:String,data:JSONObject?,firstTitle:String,rowKey:String):View{
        val wrap=column(surface).apply{setPadding(dp(1),dp(2),dp(1),dp(2));setBackgroundColor(surface)}
        if(title.isNotBlank())wrap.addView(txt(title,11f,navy,true).apply{gravity=Gravity.CENTER;setPadding(0,0,0,dp(3))})
        if(data==null){wrap.addView(txt("Chưa có dữ liệu",10f,muted,false));return wrap}
        val cols=jsonStrings(data.optJSONArray("columns"));val rows=data.optJSONArray("rows")?:JSONArray()
        // Beta94: every report grid uses the same proportional column geometry so stacked tables align exactly.
        val table=TableLayout(this).apply{isStretchAllColumns=false;isShrinkAllColumns=false}
        val firstWeight=3.4f;val dataWeight=1f;val totalWeight=1.1f
        fun cell(v:String,bold:Boolean=false,header:Boolean=false)=TextView(this).apply{
            text=v;textSize=if(header)8.2f else 8.5f;setTextColor(if(header)navy else ink);typeface=if(bold)Typeface.DEFAULT_BOLD else Typeface.DEFAULT;gravity=Gravity.CENTER;setPadding(dp(1),dp(3),dp(1),dp(3));maxLines=3;background=GradientDrawable().apply{
                setColor(if(header)Color.rgb(232,241,246) else Color.WHITE)
                setStroke(1,Color.rgb(105,118,126))
            }
        }
        fun addCell(row:TableRow,view:View,weight:Float){row.addView(view,TableRow.LayoutParams(0,-2,weight))}
        fun newRow()=TableRow(this).apply{layoutParams=TableLayout.LayoutParams(-1,-2)}
        val hr=newRow();addCell(hr,cell(firstTitle,true,true),firstWeight);cols.forEach{addCell(hr,cell(it,true,true),dataWeight)};addCell(hr,cell("Tổng",true,true),totalWeight);table.addView(hr)
        for(i in 0 until rows.length()){
            val row=rows.optJSONObject(i)?:continue;val tr=newRow();addCell(tr,cell(row.optString(rowKey),true),firstWeight);val counts=row.optJSONObject("counts")?:JSONObject();cols.forEach{c->val n=counts.optInt(c);addCell(tr,cell(if(n==0)"" else n.toString()),dataWeight)};val total=row.optInt("total");addCell(tr,cell(if(total==0)"" else total.toString(),true),totalWeight);table.addView(tr)
        }
        val totals=data.optJSONObject("totals")
        if(totals!=null){val tr=newRow();addCell(tr,cell("Tổng",true,true),firstWeight);cols.forEach{c->val n=totals.optInt(c);addCell(tr,cell(if(n==0)"" else n.toString(),true,true),dataWeight)};val total=data.optInt("total");addCell(tr,cell(if(total==0)"" else total.toString(),true,true),totalWeight);table.addView(tr)}
        wrap.addView(table,matchWrap());return wrap
    }

    // S36_PERF_HISTORY_REPORT_SERVICE: bounded background canonical refresh.
    private fun refreshHistoryCanonical(force:Boolean=false){
        if(historySyncInFlight)return
        val now=System.currentTimeMillis();if(!force&&now-historyLastCanonicalRefreshAt<60_000L)return
        val before=operationalStore.revisions().toString()
        historySyncInFlight=true
        Thread{
            val ok=runCatching{M2BackgroundSync.catchUp(applicationContext)}.getOrDefault(false)
            val changed=ok&&before!=operationalStore.revisions().toString()
            runOnUiThread{
                historySyncInFlight=false;historyLastCanonicalRefreshAt=System.currentTimeMillis()
                if(ok&&screenState=="HISTORY"&&(force||changed))historyRealtimeRefresh?.invoke(emptySet())
            }
        }.start()
    }

    // S36_PERF_HISTORY_REPORT_SERVICE: selected-date history, bounded global search, pagination and Service telemetry.
    // S36B_COMPILE_HOTFIX
    private fun historyScreen(){
        if(!isAdmin()){module="BUSINESS";businessHome();return}
        module="HISTORY";screenState="HISTORY";historyDetailMnv="";historyDetailName=""
        // S52_BETA46_SUPERADMIN_HISTORY_DELETE: SUPERADMIN bulk logical delete with immutable tombstone audit.
        if(isSuper())android.os.Handler(android.os.Looper.getMainLooper()).postDelayed({flushDeferredHistoryDeletes()},500L)
        val root=baseRoot("LỊCH SỬ");val body=body()
        fun canonicalHistoryDates():List<String> = operationalStore.availableDates().filter{date->
            val events=operationalStore.loadDay(date)?.optJSONArray("events")
            events!=null&&events.length()>0
        }
        val initialHistoryDates=canonicalHistoryDates()
        var selectedDate=initialHistoryDates.firstOrNull()?:operationalStore.businessDate();var filter="ALL";val pageSize=100;var pageStart=0;var query=""
        val hiddenHistoryIds=(getSharedPreferences("pp_history_delete_ui",MODE_PRIVATE).getStringSet("hidden_ids",emptySet())?:emptySet()).toMutableSet()
        val selectedHistoryIds=linkedSetOf<String>();val currentPageDeleteIds=linkedSetOf<String>();val pageChecks=mutableListOf<CheckBox>()
        val q=input("Tìm MNV, họ tên, nghiệp vụ, người xử lý",false).apply{setSingleLine(true)};val dateButton=Button(this).apply{text=runCatching{java.time.LocalDate.parse(selectedDate).format(DateTimeFormatter.ofPattern("dd/MM/yyyy"))}.getOrDefault(selectedDate);textSize=11f;isAllCaps=false;background=outlineBg(surface,14);setTextColor(ink)}
        val searchRow=row(bg).apply{addView(q,LinearLayout.LayoutParams(0,dp(50),1f).apply{marginEnd=dp(5)});addView(dateButton,size(dp(112),dp(50)))};body.addView(searchRow,matchWrap());body.addView(gap(7))
        val metrics=row(bg);val allBtn=metric("Tổng","0",navy);val pendingBtn=metric("Chờ","0",Color.rgb(217,119,6));val failBtn=metric("Cần xử lí","0",red);metrics.addView(allBtn,LinearLayout.LayoutParams(0,-2,1f).apply{marginEnd=dp(2)});metrics.addView(pendingBtn,LinearLayout.LayoutParams(0,-2,1f).apply{setMargins(dp(2),0,dp(2),0)});metrics.addView(failBtn,LinearLayout.LayoutParams(0,-2,1f).apply{marginStart=dp(2)});body.addView(metrics,matchWrap());body.addView(gap(7))
        val selectionBox=column(bg)
        val selectionCount=txt("Đã chọn 0 lịch sử",10f,muted,true)
        fun updateSelectedCount(){selectionCount.text="Đã chọn ${selectedHistoryIds.size} lịch sử"}
        if(isSuper()){
            selectionBox.addView(gap(6));selectionBox.addView(selectionCount)
            val choose=row(bg);val selectPage=smallButton("CHỌN TRANG",navy);val clear=smallButton("BỎ CHỌN",muted);val deleteSelected=smallButton("XÓA ĐÃ CHỌN",red)
            choose.addView(selectPage,LinearLayout.LayoutParams(0,dp(40),1f).apply{marginEnd=dp(2)});choose.addView(clear,LinearLayout.LayoutParams(0,dp(40),1f).apply{marginStart=dp(2);marginEnd=dp(2)});choose.addView(deleteSelected,LinearLayout.LayoutParams(0,dp(40),1f).apply{marginStart=dp(2)});selectionBox.addView(gap(5));selectionBox.addView(choose,matchWrap());selectionBox.addView(gap(8))
            selectPage.setOnClickListener{selectedHistoryIds.addAll(currentPageDeleteIds);pageChecks.forEach{it.isChecked=true};updateSelectedCount()}
            clear.setOnClickListener{selectedHistoryIds.clear();pageChecks.forEach{it.isChecked=false};updateSelectedCount()}
            deleteSelected.setOnClickListener{deleteHistoryBulk(selectedHistoryIds.toList())}
            body.addView(selectionBox,matchWrap())
        }
        val box=column(bg);body.addView(box,matchWrap())
        fun friendly(type:String,label:String):String=when(type.uppercase()){ "ATTENDANCE_ENTER","ENTER"->"Vào ca";"ATTENDANCE_EXIT","EXIT"->"Ra ca";"RESOURCE_CHANGE"->"Đổi tài nguyên";"LABOR_START"->"Bắt đầu công nhật";"LABOR_FINISH"->"Hoàn thành công nhật";"DOCUMENT_UPLOAD"->"Tải biên bản";"DOCUMENT_DELETE"->"Xóa biên bản";"DOCUMENT_CATEGORY_CREATE"->"Thêm loại biên bản";"DOCUMENT_CATEGORY_UPDATE"->"Sửa loại biên bản";"DOCUMENT_CATEGORY_DELETE"->"Xóa loại biên bản";"ADMIN_AUDIT"->"Thao tác quản trị";"MASTER_STAFF_UPSERT"->"Cập nhật nhân sự";"MASTER_STAFF_DELETE"->"Xóa nhân sự";"ACCOUNT_UPSERT"->"Tạo / sửa tài khoản";"ACCOUNT_STATUS"->"Đổi trạng thái tài khoản";"ACCOUNT_EMAIL"->"Đổi email tài khoản";"ACCOUNT_PASSWORD"->"Đổi mật khẩu";else->label.ifBlank{type.ifBlank{"Thao tác"}} }
        fun statusOf(e:JSONObject):String{val s=e.optString("local_status").uppercase();return when{s in setOf("REJECTED","REVIEW_REQUIRED","CONFLICT","FAILED","ERROR")->"FAILED";s in setOf("LOCAL_PENDING","PENDING","RETRY","OFFLINE_PROVISIONAL")->"PENDING";else->"SYNCED"}}
        fun eventDate(e:JSONObject,fallback:String):String=e.optString("business_date").ifBlank{e.optString("cache_business_date")}.ifBlank{runCatching{java.time.Instant.parse(e.optString("at_iso").ifBlank{e.optString("at")}).atZone(ZoneId.of("Asia/Ho_Chi_Minh")).toLocalDate().toString()}.getOrDefault(fallback)}
        fun scanDate(date:String,needle:String,remaining:Int,out:MutableList<JSONObject>){
            if(remaining<=0)return;val day=operationalStore.loadDay(date)?:return;val events=day.optJSONArray("events")?:JSONArray();val n=needle.uppercase()
            // First pass: collect tombstones before considering older target events in the same day snapshot.
            for(i in 0 until events.length()){
                val e=events.optJSONObject(i)?:continue;if(e.optString("event_type").uppercase()!="HISTORY_DELETE")continue
                val p=runCatching{JSONObject(e.optString("payload_json","{}"))}.getOrDefault(JSONObject());val ids=p.optJSONArray("target_event_ids")?:JSONArray();for(j in 0 until ids.length()){val id=ids.optString(j);if(id.isNotBlank())hiddenHistoryIds.add(id)}
            }
            for(i in 0 until events.length()){
                if(out.size>=remaining)return;val e=events.optJSONObject(i)?:continue;val type=e.optString("event_type");val realId=e.optString("event_id");if(type.uppercase()!="HISTORY_DELETE"&&realId in hiddenHistoryIds)continue
                var mnv=e.optString("mnv");var full=e.optString("full_name");var actor=e.optString("actor").ifBlank{e.optString("actor_id")};var detail=e.optString("detail");var shift=e.optString("shift")
                var p:JSONObject?=null;if(mnv.isBlank()||full.isBlank()||actor.isBlank()||detail.isBlank()||n.isNotBlank()){p=runCatching{JSONObject(e.optString("payload_json","{}"))}.getOrNull();mnv=mnv.ifBlank{p?.optString("mnv").orEmpty()};full=full.ifBlank{p?.optString("full_name").orEmpty()};actor=actor.ifBlank{p?.optString("actor").orEmpty()};detail=detail.ifBlank{p?.optString("detail").orEmpty().ifBlank{p?.optString("labor_type").orEmpty()}};shift=shift.ifBlank{p?.optString("shift").orEmpty()}}
                if(full.isBlank()&&mnv.isNotBlank())full=MasterDataCache.employee(this,mnv)?.optString("full_name").orEmpty();val label=if(type.uppercase()=="HISTORY_DELETE")"Xóa lịch sử" else friendly(type,e.optString("label"));if(type.uppercase()=="HISTORY_DELETE"&&detail.isBlank()){val hp=p?:runCatching{JSONObject(e.optString("payload_json","{}"))}.getOrNull();detail="Đã xóa ${hp?.optInt("deleted_count",0)?:0} mục; dữ liệu gốc và dấu vết kiểm toán được giữ."};if(n.isNotBlank()&&!listOf(mnv,full,label,actor,detail,shift).any{it.uppercase().contains(n)})continue
                out.add(JSONObject().put("event_id",realId.ifBlank{"$date:$i"}).put("event_type",type).put("entity_type",e.optString("entity_type")).put("entity_id",e.optString("entity_id")).put("payload_json",e.optString("payload_json","{}")).put("label",label).put("mnv",mnv).put("full_name",full).put("actor",actor).put("actor_role",e.optString("actor_role")).put("device_id",e.optString("device_id")).put("origin",e.optString("origin")).put("detail",detail).put("shift",shift).put("at_iso",e.optString("at_iso").ifBlank{e.optString("committed_at")}.ifBlank{e.optString("at")}).put("authority_seq",e.optLong("authority_seq",0L)).put("business_date",date).put("history_source","SERVICE_CANONICAL").put("local_status","CONFIRMED"))
            }
        }
        fun loadRows():MutableList<JSONObject>{
            val out=mutableListOf<JSONObject>();val needle=query.trim();if(needle.isBlank())scanDate(selectedDate,"",Int.MAX_VALUE,out) else for(d in operationalStore.historyWindowDates()){if(out.size>=300)break;scanDate(d,needle,300,out)}
            for(local in operationalStore.localHistoryAll()){
                val bodyJ=local.optJSONObject("body")?:continue;val payload=bodyJ.optJSONObject("payload")?:bodyJ;val d=payload.optString("business_date").ifBlank{bodyJ.optString("business_date")}.ifBlank{runCatching{java.time.Instant.ofEpochMilli(local.optLong("queued_at")).atZone(ZoneId.of("Asia/Ho_Chi_Minh")).toLocalDate().toString()}.getOrDefault(selectedDate)};if(needle.isBlank()&&d!=selectedDate)continue
                val id=local.optString("event_id");if(id in hiddenHistoryIds)continue;val idx=out.indexOfFirst{it.optString("event_id")==id};if(idx>=0){out[idx].put("local_status",local.optString("status")).put("local_error",local.optString("error")).put("local_queued_at",local.optLong("queued_at"));continue}
                val action=bodyJ.optString("action");val mnv=payload.optString("mnv").ifBlank{bodyJ.optString("target_id")};val full=payload.optString("full_name").ifBlank{bodyJ.optString("target_label")}.ifBlank{MasterDataCache.employee(this,mnv)?.optString("full_name").orEmpty()};val actor=payload.optString("actor").ifBlank{payload.optString("login_id")}.ifBlank{"Thiết bị này"};val detail=bodyJ.optString("detail").ifBlank{payload.optString("labor_type")};val label=friendly(action.uppercase(),action)
                if(needle.isNotBlank()&&!listOf(mnv,full,label,actor,detail).any{it.uppercase().contains(needle.uppercase())})continue
                out.add(JSONObject().put("event_id",id).put("event_type",action.uppercase()).put("label",label).put("mnv",mnv).put("full_name",full).put("actor",actor).put("device_id",payload.optString("device_id").ifBlank{payload.optString("_device_id")}).put("detail",detail).put("business_date",d).put("history_source","LOCAL_PDA").put("local_status",local.optString("status")).put("local_error",local.optString("error")).put("local_queued_at",local.optLong("queued_at")))
            }
            out.sortByDescending{e->val qAt=e.optLong("local_queued_at",0L);if(qAt>0)qAt else runCatching{java.time.Instant.parse(e.optString("at_iso")).toEpochMilli()}.getOrDefault(0L)};return out
        }
        fun render(){
            box.removeAllViews();currentPageDeleteIds.clear();pageChecks.clear();val rows=loadRows();val groups=rows.groupBy{e->e.optString("event_id").ifBlank{"${e.optString("mnv")}|${e.optString("at_iso")}|${e.optString("event_type")}"}}.entries.sortedByDescending{entry->entry.value.maxOfOrNull{e->e.optLong("local_queued_at",0L).takeIf{it>0}?:runCatching{java.time.Instant.parse(e.optString("at_iso")).toEpochMilli()}.getOrDefault(0L)}?:0L};val states=groups.map{g->if(g.value.any{statusOf(it)=="FAILED"})"FAILED" else if(g.value.any{statusOf(it)=="PENDING"})"PENDING" else "SYNCED"};val metricRows=if(query.isBlank())rows else run{val savedQuery=query;query="";val allRows=loadRows();query=savedQuery;allRows};val pending=metricRows.count{statusOf(it)=="PENDING"};val failed=metricRows.count{statusOf(it)=="FAILED"}
            fun updateMetric(v:View,title:String,n:Int){if(v is TextView)v.text="$title: $n"};updateMetric(allBtn,"Tổng",metricRows.size);updateMetric(pendingBtn,"Chờ",pending);updateMetric(failBtn,"Cần xử lí",failed)
            val filtered=groups.filterIndexed{idx,_->filter=="ALL"||states[idx]==filter};if(pageStart>=filtered.size&&pageStart>0)pageStart=((filtered.size-1).coerceAtLeast(0)/pageSize)*pageSize;val visible=filtered.drop(pageStart).take(pageSize)

            for(g in visible){
                val items=g.value;val first=items.first();val state=if(items.any{statusOf(it)=="FAILED"})"FAILED" else if(items.any{statusOf(it)=="PENDING"})"PENDING" else "SYNCED";val label=when(state){"FAILED"->"Lỗi đồng bộ";"PENDING"->"Chưa đồng bộ";else->"Đã đồng bộ"};val tint=when(state){"FAILED"->Color.rgb(254,242,242);"PENDING"->Color.rgb(255,251,235);else->Color.rgb(240,253,250)};val mnv=first.optString("mnv");val full=first.optString("full_name");val last=items.first()
                val deletable=items.filter{it.optString("event_type").uppercase()!="HISTORY_DELETE"}.map{it.optString("event_id")}.filter{it.isNotBlank()}.distinct();currentPageDeleteIds.addAll(deletable)
                val card=column(tint).apply{
                    setPadding(dp(13),dp(11),dp(13),dp(11));background=outlineBg(tint,17)
                    val top=row(tint).apply{gravity=Gravity.CENTER_VERTICAL
                        if(isSuper()&&deletable.isNotEmpty()){val c=CheckBox(this@OperationsActivity).apply{isChecked=deletable.all{it in selectedHistoryIds};setOnCheckedChangeListener{_,on->if(on)selectedHistoryIds.addAll(deletable)else selectedHistoryIds.removeAll(deletable.toSet());updateSelectedCount()}};pageChecks.add(c);addView(c,size(dp(42),dp(42)))}
                        addView(txt(friendly(last.optString("event_type"),last.optString("label")),12.5f,ink,true),LinearLayout.LayoutParams(0,-2,1f));addView(txt(label,9f,when(state){"FAILED"->red;"PENDING"->Color.rgb(217,119,6);else->teal},true).apply{setPadding(dp(7),dp(4),dp(7),dp(4));background=round(Color.WHITE,9)})
                    };addView(top,matchWrap());val subject=listOf(mnv,full).filter{it.isNotBlank()}.joinToString(" – ").ifBlank{last.optString("entity_id").ifBlank{"Hệ thống"}};addView(txt(subject,10.2f,navy,true));val actorText=last.optString("actor").ifBlank{"Hệ thống"};val roleText=last.optString("actor_role").ifBlank{"—"};val originText=last.optString("origin").ifBlank{"Service"};addView(txt("Lúc ${formatIso(last.optString("at_iso"))} • Người thực hiện: $actorText${if(roleText!="—")" • Vai trò: $roleText" else ""}",9.7f,muted,false));if(last.optString("detail").isNotBlank())addView(txt("Nội dung: ${last.optString("detail")}",9.7f,ink,false).apply{maxLines=3});setOnClickListener{historyTimeline(items)}
                };box.addView(card,matchWrap());box.addView(gap(6))
            }
            updateSelectedCount()
            if(visible.isEmpty())box.addView(info("Không có lịch sử phù hợp."));if(filtered.isNotEmpty()){val from=pageStart+1;val to=(pageStart+visible.size).coerceAtMost(filtered.size);box.addView(txt("$from–$to / ${filtered.size}",9f,muted,false));val nav=row(bg);if(pageStart>0)nav.addView(smallButton("‹ 100 TRƯỚC",navy).apply{setOnClickListener{pageStart=(pageStart-pageSize).coerceAtLeast(0);render()}},LinearLayout.LayoutParams(0,dp(46),1f).apply{marginEnd=dp(3)});if(pageStart+pageSize<filtered.size)nav.addView(smallButton("100 TIẾP ›",teal).apply{setOnClickListener{pageStart+=pageSize;render()}},LinearLayout.LayoutParams(0,dp(46),1f).apply{marginStart=dp(3)});if(nav.childCount>0)box.addView(nav,matchWrap())}
        }
        allBtn.setOnClickListener{filter="ALL";pageStart=0;render()};pendingBtn.setOnClickListener{filter="PENDING";pageStart=0;render()};failBtn.setOnClickListener{filter="FAILED";pageStart=0;render()}
        q.addTextChangedListener(object:TextWatcher{override fun beforeTextChanged(v:CharSequence?,st:Int,c:Int,a:Int)=Unit;override fun onTextChanged(v:CharSequence?,st:Int,b:Int,c:Int){query=v?.toString().orEmpty();pageStart=0;render()};override fun afterTextChanged(v:Editable?)=Unit})
        dateButton.setOnClickListener{
            val localDates=operationalStore.localHistoryAll().mapNotNull{local->
                val bodyJ=local.optJSONObject("body")?:return@mapNotNull null
                val payload=bodyJ.optJSONObject("payload")?:bodyJ
                payload.optString("business_date").ifBlank{bodyJ.optString("business_date")}.ifBlank{
                    runCatching{java.time.Instant.ofEpochMilli(local.optLong("queued_at")).atZone(ZoneId.of("Asia/Ho_Chi_Minh")).toLocalDate().toString()}.getOrDefault("")
                }.takeIf{it.matches(Regex("\\d{4}-\\d{2}-\\d{2}"))}
            }
            val dates=(canonicalHistoryDates()+localDates).distinct().sortedDescending()
            DataDatePickerUi.show(this,dates,selectedDate){chosen->
                selectedDate=chosen;dateButton.text=java.time.LocalDate.parse(chosen).format(DateTimeFormatter.ofPattern("dd/MM/yyyy"));query="";q.setText("");pageStart=0;render()
            }
        }
        historyRealtimeRefresh={dates->if(screenState=="HISTORY"&&(dates.isEmpty()||query.isNotBlank()||selectedDate in dates))render()}
        attach(root,body);render();refreshHistoryCanonical()
    }

    private fun historyGroupStatus(items:List<JSONObject>):String{
        val states=items.map{it.optString("local_status").trim().uppercase()}
        if(states.any{it in setOf("REJECTED","REVIEW_REQUIRED","CONFLICT","FAILED","ERROR")})return "Lỗi đồng bộ"
        val allSynced=states.all{it.isBlank()||it in setOf("CONFIRMED","SYNCED","ACKED","CANONICAL")}
        return if(allSynced)"Đã đồng bộ" else "Chưa đồng bộ"
    }

    private fun historyEventTime(e:JSONObject):String{val local=e.optLong("local_queued_at");if(local>0)return java.text.SimpleDateFormat("HH:mm:ss dd/MM/yyyy",java.util.Locale("vi","VN")).apply{timeZone=java.util.TimeZone.getTimeZone("Asia/Ho_Chi_Minh")}.format(java.util.Date(local));return formatIso(e.optString("committed_at").ifBlank{e.optString("occurred_at").ifBlank{e.optString("at_iso").ifBlank{e.optString("at")}}})}
    private fun historyCanEdit(e:JSONObject):Boolean{if(!isAdmin())return false;val date=e.optString("business_date").ifBlank{e.optString("cache_business_date")};val ix=operationalStore.availableDates().take(7).indexOf(date);return ix>=0&&ix<=if(isSuper())6 else 1}
    private fun flushDeferredHistoryDeletes(){
        if(!isSuper())return
        val prefs=getSharedPreferences("pp_history_delete_ui",MODE_PRIVATE)
        val queue=(prefs.getStringSet("deferred_ids",emptySet())?:emptySet()).filter{it.isNotBlank()}.toList()
        if(queue.isEmpty())return
        fun next(i:Int){
            if(i>=queue.size)return
            val id=queue[i]
            api.call("history_delete",JSONObject().put("event_ids",JSONArray(listOf(id))).put("idempotency_key","beta47-history-delete-$id").put("reason","SUPERADMIN xóa lịch sử từ PDA")){r->
                if(r.ok||r.error?.contains("HISTORY_DELETE_TARGET_NOT_FOUND")==true){val left=(prefs.getStringSet("deferred_ids",emptySet())?:emptySet()).toMutableSet();left.remove(id);prefs.edit().putStringSet("deferred_ids",left).apply()}
                next(i+1)
            }
        }
        next(0)
    }

    private fun deleteHistoryBulk(ids:List<String>){
        if(!isSuper()){showError("Chỉ Quản trị cao nhất được xóa lịch sử.");return}
        val clean=ids.filter{it.isNotBlank()}.distinct();if(clean.isEmpty()){showError("Chọn ít nhất một lịch sử cần xóa.");return}
        AlertDialog.Builder(this).setTitle("Xóa ${clean.size} lịch sử?").setMessage("Lịch sử Service sẽ được xóa bằng dấu vết kiểm toán. Lịch sử lỗi chỉ có trên PDA sẽ được xóa cục bộ; thao tác đang chờ đồng bộ không bị hủy ngầm.").setNegativeButton("Hủy",null).setPositiveButton("Tiếp tục"){_,_->
            verifyDeletePassword("xóa lịch sử"){
                val wanted=clean.toSet();val canonical=linkedSetOf<String>()
                for(date in operationalStore.availableDates()){
                    val events=operationalStore.loadDay(date)?.optJSONArray("events")?:continue
                    for(i in 0 until events.length()){
                        val e=events.optJSONObject(i)?:continue
                        val id=e.optString("event_id")
                        if(id in wanted&&e.optString("event_type").uppercase()!="HISTORY_DELETE")canonical.add(id)
                    }
                    if(canonical.size==wanted.size)break
                }
                operationalStore.deleteLocalHistory(clean)
                val prefs=getSharedPreferences("pp_history_delete_ui",MODE_PRIVATE)
                val hidden=(prefs.getStringSet("hidden_ids",emptySet())?:emptySet()).toMutableSet().apply{addAll(clean)}
                val deferred=(prefs.getStringSet("deferred_ids",emptySet())?:emptySet()).toMutableSet().apply{addAll(canonical)}
                prefs.edit().putStringSet("hidden_ids",hidden).putStringSet("deferred_ids",deferred).apply()
                TopNotice.show(this,"Đã xóa ${clean.size} lịch sử khỏi màn hình.",TopNotice.Kind.SUCCESS)
                if(canonical.isNotEmpty())flushDeferredHistoryDeletes()
                historyScreen()
            }
        }.show()
    }

    private fun historyActionVi(typeRaw:String):String=when(typeRaw.trim().uppercase()){
        "ATTENDANCE_ENTER","ENTER"->"Vào ca"
        "ATTENDANCE_EXIT","EXIT"->"Ra ca"
        "ATTENDANCE_TIME_CORRECTED"->"Sửa thời gian vào / ra ca"
        "ATTENDANCE_EXIT_DELETED"->"Xóa mốc ra ca"
        "RESOURCE_CHANGE","RESOURCE"->"Thay đổi công việc / tài nguyên"
        "WORK_SESSION_UPDATE"->"Cập nhật công việc trong ca"
        "WORK_SESSION_ADD"->"Thêm công việc trong ca"
        "WORK_SESSION_DELETE"->"Xóa công việc trong ca"
        "LABOR_START"->"Bắt đầu công nhật"
        "LABOR_FINISH"->"Kết thúc công nhật"
        "DOCUMENT_UPLOAD"->"Tải biên bản"
        "DOCUMENT_DELETE"->"Xóa biên bản"
        "DOCUMENT_CATEGORY_CREATE"->"Thêm loại biên bản"
        "DOCUMENT_CATEGORY_UPDATE"->"Sửa loại biên bản"
        "DOCUMENT_CATEGORY_DELETE"->"Xóa loại biên bản"
        "MASTER_STAFF_UPSERT"->"Thêm / sửa nhân sự"
        "MASTER_STAFF_DELETE"->"Xóa nhân sự"
        "ACCOUNT_UPSERT"->"Tạo / sửa tài khoản"
        "ACCOUNT_STATUS"->"Đổi trạng thái tài khoản"
        "ACCOUNT_EMAIL"->"Đổi email tài khoản"
        "ACCOUNT_PASSWORD"->"Đổi mật khẩu tài khoản"
        "HISTORICAL_CORRECTION"->"Sửa lịch sử"
        "SYNC_ERROR"->"Lỗi đồng bộ"
        else->if(typeRaw.isBlank())"Thao tác" else typeRaw
    }
    private fun historyFieldVi(keyRaw:String):String=when(keyRaw.trim().lowercase()){
        "work_choice"->"Công việc"
        "pda_serial","pda"->"Seri PDA"
        "user_pick"->"User Pick"
        "pack_table"->"Bàn Pack"
        "user_pack"->"User Pack"
        "shift"->"Ca làm việc"
        "main_position"->"Vị trí chính"
        "work_position","position"->"Vị trí trong ca"
        "enter_at"->"Giờ vào"
        "exit_at"->"Giờ ra"
        "reason"->"Lý do"
        "state"->"Trạng thái"
        "mnv"->"Mã nhân viên"
        "full_name"->"Họ tên"
        "mutation_kind"->"Loại thay đổi"
        else->keyRaw.replace('_',' ').replaceFirstChar{if(it.isLowerCase())it.titlecase() else it.toString()}
    }
    private fun historyValueVi(key:String,value:Any?):String{
        val raw=when{value==null||value===JSONObject.NULL->"";value is JSONObject||value is JSONArray->value.toString();else->value.toString()}.trim()
        if(raw.isBlank()||raw.equals("null",true))return "—"
        return when(key.trim().lowercase()){
            "work_choice"->when(raw.uppercase()){ "PICK"->"Pick";"PACK"->"Pack";"BOTH","PICK_PACK","PICK & PACK"->"Pick & Pack";"NONE","NO"->"Làm theo vị trí chính";else->raw }
            "state"->when(raw.uppercase()){ "ACTIVE"->"Đang hoạt động";"CLOSED","FINISHED"->"Đã kết thúc";"PENDING"->"Đang chờ";else->raw }
            "mutation_kind"->when(raw.uppercase()){ "ADD"->"Thêm";"DELETE"->"Xóa";"UPDATE","EDIT"->"Sửa";else->raw }
            else->raw
        }
    }
    private fun historyHumanChanges(payload:JSONObject):List<String>{
        val out=mutableListOf<String>()
        val ignored=setOf("event_id","checksum","origin","history_source","business_date","actor_id","actor_role","device_id","updated_at","created_at")
        val before=payload.optJSONObject("before");val after=payload.optJSONObject("after")
        if(before!=null||after!=null){
            val keys=linkedSetOf<String>();before?.keys()?.asSequence()?.forEach{keys.add(it)};after?.keys()?.asSequence()?.forEach{keys.add(it)}
            keys.filter{it !in ignored}.sortedWith(Comparator{a,b->naturalUserCompare(a,b)}).forEach{k->
                val left=historyValueVi(k,before?.opt(k));val right=historyValueVi(k,after?.opt(k))
                if(left!=right)out.add("${historyFieldVi(k)}: $left → $right")
            }
        }
        if(out.isEmpty()){
            listOf("work_choice","pda_serial","user_pick","pack_table","user_pack","shift","main_position","work_position","enter_at","exit_at","reason","state").forEach{k->
                if(payload.has(k)){val v=historyValueVi(k,payload.opt(k));if(v!="—")out.add("${historyFieldVi(k)}: $v")}
            }
        }
        return out.distinct().take(12)
    }
    private fun historyTimeline(items:List<JSONObject>){
        screenState="HISTORY_DETAIL";val root=baseRoot("LỊCH SỬ");val body=body();val first=items.firstOrNull()?:return
        val mnv=first.optString("mnv");val full=first.optString("full_name").ifBlank{MasterDataCache.employee(this,mnv)?.optString("full_name").orEmpty()}
        val subject=listOf(mnv,full).filter{it.isNotBlank()}.joinToString(" – ").ifBlank{first.optString("entity_id").ifBlank{"Hệ thống"}}
        val intro=column(surface).apply{setPadding(dp(13),dp(11),dp(13),dp(11));background=outlineBg(surface,16);addView(txt("Đối tượng: $subject",13.5f,navy,true));addView(txt("Mỗi thẻ cho biết ai thực hiện, việc đã làm, thời gian, nội dung thay đổi và trạng thái ghi nhận.",9.8f,muted,false))}
        body.addView(intro,matchWrap());body.addView(gap(8))
        items.sortedBy{historyEventTime(it)}.forEach{e->
            val type=e.optString("event_type");val actor=e.optString("actor_id").ifBlank{e.optString("actor")}.ifBlank{"Hệ thống"};val role=e.optString("actor_role").ifBlank{"—"};val status=historyGroupStatus(listOf(e));val statusColor=when(status){"Đã đồng bộ"->green;"Lỗi đồng bộ"->red;else->orange};val fill=when(status){"Đã đồng bộ"->Color.rgb(239,250,244);"Lỗi đồng bộ"->Color.rgb(255,239,239);else->Color.rgb(255,248,230)}
            val p=runCatching{JSONObject(e.optString("payload_json","{}"))}.getOrDefault(JSONObject());val changes=historyHumanChanges(p);val detail=e.optString("detail").trim();val device=e.optString("device_id").trim();val source=e.optString("history_source").ifBlank{e.optString("origin")}.trim();val eventId=e.optString("event_id").trim()
            val card=column(fill).apply{setPadding(dp(13),dp(11),dp(13),dp(11));background=GradientDrawable().apply{setColor(fill);cornerRadius=dp(15).toFloat();setStroke(dp(1),statusColor)}}
            val head=row(Color.TRANSPARENT).apply{gravity=Gravity.CENTER_VERTICAL};head.addView(txt(historyActionVi(type),12.8f,navy,true),LinearLayout.LayoutParams(0,-2,1f).apply{marginEnd=dp(6)});head.addView(txt(status,8.9f,statusColor,true).apply{setPadding(dp(7),dp(4),dp(7),dp(4));background=round(fill,9)});card.addView(head,matchWrap())
            card.addView(txt("Ai thực hiện: $actor${if(role!="—")" • $role" else ""}",10f,ink,true));card.addView(txt("Thời gian: ${formatIso(e.optString("at_iso").ifBlank{e.optString("at")})}",9.8f,muted,false))
            if(changes.isNotEmpty()){card.addView(gap(5));card.addView(txt("Nội dung thay đổi",9.6f,navy,true));changes.forEach{card.addView(txt("• $it",9.8f,ink,false))}}
            if(detail.isNotBlank()&&changes.none{detail.contains(it.substringBefore(':'),true)}){card.addView(txt("Chi tiết: $detail",9.8f,ink,false))}
            val err=e.optString("local_error").trim();if(err.isNotBlank())card.addView(txt("Cần xử lý: $err",9.6f,red,true))
            val system=listOf(if(device.isBlank())"" else "Thiết bị $device",if(source.isBlank())"" else "Nguồn $source",if(eventId.isBlank())"" else "Mã đối soát $eventId").filter{it.isNotBlank()}.joinToString(" • ")
            if(system.isNotBlank()){card.addView(gap(4));card.addView(txt("Thông tin hệ thống: $system",8.6f,muted,false).apply{maxLines=2})}
            body.addView(card,matchWrap());body.addView(gap(7))
        }
        attach(root,body)
    }


    // S51B_BETA45_COMPILE_GUARD
    // S51_BETA45_MANUAL_UPDATE_SYNC_DETAIL_VI: detailed Vietnamese sync view shared by all roles.
    // S53_BETA47_SHEET_LOGIC_UI: concise sync screen + unified APP/WEB presence.
    private fun syncScreen(){
        module="SYNC";screenState="SYNC"
        val root=baseRoot("ĐỒNG BỘ");val body=body()
        val overview=column(surface).apply{setPadding(dp(14),dp(12),dp(14),dp(12));background=outlineBg(surface,18)}
        val overviewTitle=txt("Đang kiểm tra trạng thái...",14f,navy,true);val overviewSub=txt("Đang kiểm tra PDA, Service và Google Sheet.",10f,muted,false)
        overview.addView(overviewTitle);overview.addView(gap(4));overview.addView(overviewSub);body.addView(overview,matchWrap());body.addView(gap(9))
        val pdaBox=column(bg);val serviceBox=column(bg);val sheetBox=column(bg);val otherBox=column(bg)
        body.addView(pdaBox,matchWrap());body.addView(serviceBox,matchWrap());body.addView(sheetBox,matchWrap());body.addView(otherBox,matchWrap())
        val actions=row(bg);val syncNow=smallButton("ĐỒNG BỘ NGAY",teal);val refresh=smallButton("LÀM MỚI",navy);actions.addView(syncNow,LinearLayout.LayoutParams(0,dp(46),1f).apply{marginEnd=dp(4)});actions.addView(refresh,LinearLayout.LayoutParams(0,dp(46),1f).apply{marginStart=dp(4)});body.addView(gap(9));body.addView(actions,matchWrap())
        fun dateVi(v:String)=runCatching{java.time.LocalDate.parse(v.take(10)).format(DateTimeFormatter.ofPattern("dd/MM/yyyy"))}.getOrDefault(v.ifBlank{"—"})
        fun timeVi(v:String)=if(v.isBlank())"—" else formatIso(v)
        fun authorityVi(v:String)=when(v.uppercase()){ "SERVICE_PRIMARY"->"Dịch vụ chính";"GOOGLE_FALLBACK"->"Google dự phòng";"RECONCILING"->"Đang đối chiếu dữ liệu";"OFFLINE_LOCAL"->"Chỉ lưu trên PDA";else->"Chưa xác định" }
        fun replicaVi(v:String)=when(v.uppercase()){ "SYNCED","HEALTHY","OK"->"Đã đồng bộ";"PENDING","INFLIGHT","RUNNING"->"Đang chuyển dữ liệu";"RETRY"->"Đang chờ gửi lại";"ERROR","FAILED"->"Có lỗi";else->if(v.isBlank())"Chưa có dữ liệu" else "Đang theo dõi" }
        fun loadPda(){
            pdaBox.removeAllViews()
            val pending=runCatching{operationalStore.pendingMutationCount()}.getOrDefault(0)
            val active=runCatching{SyncDirectionTracker.snapshot().active}.getOrDefault(false)
            val dates=runCatching{operationalStore.availableDates()}.getOrDefault(emptyList())
            val network=DeviceNetworkStatus.snapshot(this).header(lastLatencyMs)
            val syncText=when{active->"Đang trao đổi dữ liệu";pending>0->"Đang chờ đồng bộ";lastConnected==true->"Đã đồng bộ";else->"Chưa xác định"}
            overviewTitle.text=when{lastConnected==false->"Chưa kết nối được Service";active->"Đang đồng bộ dữ liệu";pending>0->"Có dữ liệu đang chờ đồng bộ";else->"Hệ thống đang hoạt động bình thường"}
            overviewTitle.setTextColor(if(lastConnected==false)red else if(active||pending>0)orange else teal)
            overviewSub.text="$network • PDA: $syncText"
            pdaBox.addView(section("THÔNG TIN TRÊN PDA"))
            pdaBox.addView(details(listOf(
                "Kết nối mạng" to network,
                "Trạng thái đồng bộ trên PDA" to syncText,
                "Hàng đợi đồng bộ trên PDA" to pending.toString(),
                "Dữ liệu người dùng" to humanBytes(appStorageUsage().userDataBytes),
                "Bộ nhớ đệm" to humanBytes(appStorageUsage().cacheBytes),
                "Ngày nghiệp vụ hiện tại" to dateVi(operationalStore.businessDate()),
                "Ngày dữ liệu mới nhất trên PDA" to dateVi(dates.firstOrNull().orEmpty())
            )))
            pdaBox.addView(gap(8))
            otherBox.removeAllViews();otherBox.addView(section("THÔNG TIN ĐỒNG BỘ KHÁC"));otherBox.addView(details(listOf(
                "Luồng trao đổi dữ liệu" to if(active)"Đang hoạt động" else "Đang nghỉ",
                "Trạng thái mạng" to network,
                "Cơ chế gửi lại" to if(pending>0)"Tự động khi kết nối phù hợp" else "Không có dữ liệu cần gửi lại"
            )));otherBox.addView(gap(8))
        }
        fun loadService(){
            serviceBox.removeAllViews();serviceBox.addView(section("THÔNG TIN TRÊN SERVICE"));serviceBox.addView(info("Đang kiểm tra Service..."))
            sheetBox.removeAllViews();sheetBox.addView(section("THÔNG TIN TRÊN GOOGLE SHEET"));sheetBox.addView(info("Đang kiểm tra trạng thái sao chép Google Sheet..."))
            val started=android.os.SystemClock.elapsedRealtime()
            api.call("sync_status",JSONObject()){r->runOnUiThread{
                if(screenState!="SYNC")return@runOnUiThread
                val rt=(android.os.SystemClock.elapsedRealtime()-started).coerceAtLeast(0);lastLatencyMs=rt
                serviceBox.removeAllViews();serviceBox.addView(section("THÔNG TIN TRÊN SERVICE"))
                sheetBox.removeAllViews();sheetBox.addView(section("THÔNG TIN TRÊN GOOGLE SHEET"))
                if(!r.ok||r.json==null){
                    lastConnected=false;refreshHeaderConnection()
                    serviceBox.addView(details(listOf("Trạng thái Service" to "Chưa phản hồi","Độ trễ lần kiểm tra" to "$rt ms","Dữ liệu trên PDA" to "Vẫn được lưu an toàn")))
                    sheetBox.addView(details(listOf("Trạng thái Google Sheet" to "Chưa lấy được từ Service","Lần sao chép thành công" to "Chưa xác định")))
                    serviceBox.addView(gap(8));sheetBox.addView(gap(8));loadPda();return@runOnUiThread
                }
                lastConnected=true;refreshHeaderConnection()
                val j=r.json?:JSONObject();val auth=j.optJSONObject("authority")?:JSONObject();val rep=j.optJSONObject("replication")?:JSONObject()
                serviceBox.addView(details(listOf(
                    "Trạng thái Service" to "Đang hoạt động",
                    "Độ trễ tới Service" to "$rt ms",
                    "Nguồn dữ liệu đang dùng" to authorityVi(auth.optString("mode").ifBlank{j.optString("authority_mode")}),
                    "Mốc dữ liệu trên Service" to auth.optLong("authority_seq",j.optLong("server_seq",0L)).toString()
                )))
                sheetBox.addView(details(listOf(
                    "Trạng thái Google Sheet" to replicaVi(rep.optString("state")),
                    "Bản ghi chờ sao chép Google Sheet" to rep.optInt("pending_count",0).toString(),
                    "Lần sao chép thành công" to timeVi(rep.optString("last_success_at"))
                )))
                serviceBox.addView(gap(8));sheetBox.addView(gap(8));loadPda()
            }}
        }
        fun load(){loadPda();loadService()}
        syncNow.setOnClickListener{foregroundSync.requestSync();flushDeferredHistoryDeletes();TopNotice.show(this,"Đã yêu cầu đồng bộ dữ liệu.",TopNotice.Kind.INFO);android.os.Handler(android.os.Looper.getMainLooper()).postDelayed({if(screenState=="SYNC")load();flushDeferredHistoryDeletes()},900L)}
        refresh.setOnClickListener{load()}
        attach(root,body);load()
    }

    private fun confirmPdaHandoverCondition(ses:JSONObject,serial:String,operation:String,done:(String)->Unit){
        val expected=ses.optString("pda_enter_status").trim();val statuses=mutableListOf<String>();val arr=MasterDataCache.snapshot(this)?.optJSONArray("pda_statuses")?:JSONArray();for(i in 0 until arr.length()){val v=arr.optString(i).trim();if(v.isNotBlank()&&!statuses.contains(v))statuses.add(v)};if(expected.isNotBlank()&&!statuses.contains(expected))statuses.add(0,expected);if(statuses.isEmpty())statuses.add("Nguyên vẹn")
        val sp=spinner(statuses.toTypedArray());val pos=statuses.indexOf(expected);if(pos>=0)sp.setSelection(pos);val note=input("Ghi chú tình trạng (tùy chọn)",false)
        val box=column(surface).apply{setPadding(dp(12),dp(4),dp(12),dp(8));addView(details(listOf("Seri PDA" to serial,"Tình trạng khi nhận" to expected.ifBlank{"—"},"Thao tác" to operation)));addView(gap(7));addView(labelled("Tình trạng PDA hiện tại",sp));addView(gap(7));addView(note,matchWrap())}
        AlertDialog.Builder(this).setTitle("Xác nhận tình trạng PDA").setView(box).setNegativeButton("Hủy",null).setPositiveButton("XÁC NHẬN"){_,_->val v=sp.selectedItem?.toString().orEmpty();val n=note.text.toString().trim();done(if(n.isBlank())v else "$v • $n")}.show()
    }

    private fun pdaExchangeScreen(){
        module="PDA_EXCHANGE";screenState="PDA_EXCHANGE";val root=baseRoot("ĐỔI / TRẢ PDA");val body=body()
        val serialField=mnvInput("Nhập 5 số cuối PDA").apply{imeOptions=EditorInfo.IME_ACTION_DONE}
        body.addView(txt("PDA ĐANG ĐƯỢC SỬ DỤNG",13f,navy,true))
        body.addView(gap(5));body.addView(labelled("Tìm nhanh PDA",serialField));body.addView(gap(8))
        val listBox=column(bg);body.addView(listBox,matchWrap())
        val changeReasons=arrayOf("PDA lỗi quét / không đọc mã","PDA lỗi mạng / không đồng bộ","PDA yếu pin / hết pin","PDA lỗi phần cứng / hư hỏng","PDA treo / hoạt động không ổn định","Đổi theo điều phối vận hành","Khác")
        val returnReasons=arrayOf("Đi công nhật","Làm xong sớm","Về sớm","Chuyển sang Pack","Điều chuyển sang công việc / vị trí không cần PDA","Tạm dừng Pick theo điều phối","Khác")
        fun chooseReason(title:String,items:Array<String>,done:(String)->Unit){
            AlertDialog.Builder(this).setTitle(title).setItems(items){_,which->
                val chosen=items[which];if(chosen!="Khác"){done(chosen);return@setItems}
                val other=input("Nhập lý do",false)
                AlertDialog.Builder(this).setTitle("Lý do khác").setView(other).setNegativeButton("Hủy",null).setPositiveButton("XÁC NHẬN"){_,_->val v=other.text.toString().trim();if(v.isBlank())showError("Nhập lý do.")else done(v)}.show()
            }.setNegativeButton("Hủy",null).show()
        }
        fun clean(v:String)=v.trim().takeUnless{it.isBlank()||it.equals("null",true)||it=="—"}.orEmpty()
        fun matches(serial:String,typed:String):Boolean{val q=typed.trim();if(q.isBlank())return true;return q.length<=5&&q.all{it.isDigit()}&&serial.takeLast(5).startsWith(q)}
        data class Holder(val serial:String,val mnv:String,var status:String)
        val holders=linkedMapOf<String,Holder>()

        fun loadLocal(){
            holders.clear()
            val day=operationalStore.loadDay(operationalStore.businessDate())
            val sessions=day?.optJSONArray("sessions")?:JSONArray()
            for(i in 0 until sessions.length()){
                val x=sessions.optJSONObject(i)?:continue
                if(!x.optString("state").equals("ACTIVE",true))continue
                val serial=clean(x.optString("pda_serial"));val mnv=x.optString("mnv").trim()
                if(serial.isNotBlank()&&mnv.isNotBlank())holders[serial]=Holder(serial,mnv,x.optString("pda_enter_status").ifBlank{"—"})
            }
        }
        fun loadSession(h:Holder,done:(JSONObject,JSONObject)->Unit){
            api.call("employee_context",JSONObject().put("mnv",h.mnv).put("include_options",true)){r->runOnUiThread{
                if(handleAuth(r))return@runOnUiThread;if(!r.ok){showError(r.error?:"Không tải được phiên");return@runOnUiThread}
                val c=r.json?:JSONObject();val ses=c.optJSONObject("session")?:JSONObject()
                if(!c.optString("state").equals("ACTIVE",true)||!clean(ses.optString("pda_serial")).equals(h.serial,true)){showError("PDA đã thay đổi người dùng hoặc phiên. Đồng bộ lại rồi thử lại.");foregroundSync.requestSync();loadLocal();render(serialField.text.toString());return@runOnUiThread}
                done(c,ses)
            }}
        }
        fun mutate(h:Holder,ses:JSONObject,next:String,kind:String,why:String){
            val p=JSONObject()
            PdaOnlyMutationPayload.fields(sessionId=ses.optString("session_id"),mnv=h.mnv,pdaSerial=next,kind=kind,reason=why,idempotencyKey=UUID.randomUUID().toString()).forEach{(k,v)->p.put(k,v)}
            api.call("session_work_update",p){x->runOnUiThread{
                if(handleAuth(x))return@runOnUiThread;if(!x.ok){showError(x.error?:"Không cập nhật được PDA");return@runOnUiThread}
                TopNotice.show(this,"Đã ${if(kind=="Đổi")"đổi" else "trả"} PDA và lưu lịch sử.",TopNotice.Kind.SUCCESS)
                // optimistic local display; Service reconcile runs in background.
                if(kind=="Trả")holders.remove(h.serial) else{holders.remove(h.serial);holders[next]=Holder(next,h.mnv,h.status)}
                render(serialField.text.toString());foregroundSync.requestSync()
            }}
        }
        fun change(h:Holder){
            loadSession(h){_,ses->
                val pdas=MasterDataCache.resourceOptions(this).optJSONArray("pdas")?:JSONArray()
                val field=pdaInput(pdas,h.serial)
                val wrap=column(surface).apply{
                    setPadding(dp(10),dp(4),dp(10),dp(8))
                    addView(txt("PDA hiện tại: ${h.serial}",12f,navy,true));addView(gap(7))
                    addView(labelled("PDA mới",field));addView(gap(5));addView(pdaSelectedPanel(pdas,field))
                }
                AlertDialog.Builder(this).setTitle("Đổi PDA").setView(wrap).setNegativeButton("Hủy",null).setPositiveButton("TIẾP TỤC"){_,_->
                    val next=resolvePda(pdas,field.text.toString());if(next==null||next.equals(h.serial,true)){showError("Chọn PDA mới khác PDA hiện tại.");return@setPositiveButton}
                    confirmPdaHandoverCondition(ses,h.serial,"Đổi PDA"){condition->chooseReason("Lý do đổi PDA",changeReasons){why->mutate(h,ses,next,"Đổi","$why • Tình trạng bàn giao: $condition")}}
                }.show()
            }
        }
        fun giveBack(h:Holder){loadSession(h){_,ses->confirmPdaHandoverCondition(ses,h.serial,"Trả PDA"){condition->chooseReason("Lý do trả PDA",returnReasons){why->mutate(h,ses,"","Trả","$why • Tình trạng bàn giao: $condition")}}}}
        fun render(filter:String){
            listBox.removeAllViews()
            val rows=holders.values.filter{matches(it.serial,filter)}.sortedWith(Comparator{p,q->naturalUserCompare(p.serial,q.serial)})
            if(rows.isEmpty()){listBox.addView(info(if(filter.isBlank())"Hiện không có PDA nào đang được sử dụng." else "Không có PDA đang dùng khớp 5 số cuối."));return}
            rows.forEach{h->
                val e=MasterDataCache.employee(this,h.mnv)?:JSONObject().put("mnv",h.mnv)
                val item=column(surface).apply{setPadding(dp(9),dp(8),dp(9),dp(8));background=outlineBg(surface,12)}
                item.addView(txt("${h.serial.takeLast(5)} • ${h.serial}",13f,navy,true))
                item.addView(txt("${e.optString("mnv")} • ${dash(e.optString("full_name"))} • ${dash(e.optString("main_position"))}",9.5f,ink,false))
                item.addView(txt("Tình trạng: ${h.status.ifBlank{"—"}}",9.3f,teal,true));item.addView(gap(6))
                val actions=row(surface)
                actions.addView(smallButton("ĐỔI PDA",teal).apply{setOnClickListener{change(h)}},LinearLayout.LayoutParams(0,dp(42),1f).apply{marginEnd=dp(4)})
                actions.addView(smallButton("TRẢ PDA",orange).apply{setOnClickListener{giveBack(h)}},LinearLayout.LayoutParams(0,dp(42),1f).apply{marginStart=dp(4)})
                item.addView(actions,matchWrap());listBox.addView(item,matchWrap());listBox.addView(gap(6))
            }
        }
        fun reconcileRemote(){
            api.call("resource_master_list"){rr->runOnUiThread{
                if(rr.ok){
                    val resources=rr.json?.optJSONArray("resources")?:JSONArray()
                    for(i in 0 until resources.length()){
                        val x=resources.optJSONObject(i)?:continue;if(!x.optString("resource_type").equals("PDA",true))continue
                        holders[clean(x.optString("resource_id"))]?.status=x.optString("status_label").ifBlank{holders[clean(x.optString("resource_id"))]?.status?:"—"}
                    }
                    render(serialField.text.toString())
                }
            }}
        }
        loadLocal();render("")
        bindScannerEnter(serialField){hideSoftKeyboard(serialField);render(serialField.text.toString())}
        serialField.addTextChangedListener(object:TextWatcher{override fun beforeTextChanged(v:CharSequence?,a:Int,b:Int,c:Int)=Unit;override fun onTextChanged(v:CharSequence?,a:Int,b:Int,c:Int){render(v?.toString().orEmpty())};override fun afterTextChanged(v:Editable?)=Unit})
        attach(root,body);reconcileRemote();serialField.requestFocus()
    }

    private fun addVersionChangelog(body:LinearLayout,title:String,version:String,notes:String){
        val preview=UpdateManager.previewNotesForDisplay(notes,4)
        body.addView(txt("$title • $version",10.8f,navy,true).apply{setPadding(dp(2),dp(4),dp(2),dp(3))})
        body.addView(details(listOf("Thay đổi" to preview.first)))
        if(preview.second){
            body.addView(gap(4))
            body.addView(smallButton("XEM THÊM",teal).apply{setOnClickListener{
                AlertDialog.Builder(this@OperationsActivity).setTitle("$title • $version").setMessage(UpdateManager.bulletNotesForDisplay(notes)).setPositiveButton("ĐÓNG",null).show()
            }},LinearLayout.LayoutParams(-1,dp(40)))
        }
        body.addView(gap(7))
    }


    private fun qrBitmap(value:String,sizePx:Int):Bitmap{
        val matrix=QRCodeWriter().encode(value,BarcodeFormat.QR_CODE,sizePx,sizePx)
        val pixels=IntArray(sizePx*sizePx)
        for(y in 0 until sizePx)for(x in 0 until sizePx)pixels[y*sizePx+x]=if(matrix[x,y])Color.BLACK else Color.WHITE
        return Bitmap.createBitmap(sizePx,sizePx,Bitmap.Config.RGB_565).apply{setPixels(pixels,0,sizePx,0,0,sizePx,sizePx)}
    }
    private fun addReleaseQrCard(body:LinearLayout,label:String,result:BetaApiClient.Result){
        val json=result.json
        val url=json?.optString("apk_url").orEmpty().trim()
        val version=json?.optString("version_name").orEmpty().trim()
        body.addView(section(label))
        if(!result.ok||url.isBlank()||version.isBlank()){
            val message=if(label=="STABLE")"Stable chưa có bản phát hành công khai. QR Stable sẽ tự xuất hiện sau khi OWNER phát hành Stable." else "Không lấy được bản Beta công khai mới nhất. Kiểm tra mạng và thử lại."
            body.addView(info(message));body.addView(gap(8));return
        }
        val card=column(surface).apply{setPadding(dp(12),dp(10),dp(12),dp(12));background=outlineBg(surface,10)}
        card.addView(txt("$label • $version",12f,navy,true))
        card.addView(txt("Quét QR để tải trực tiếp APK mới nhất từ GitHub Release.",9.2f,muted,false))
        card.addView(gap(7))
        val qrSize=dp(210).coerceAtLeast(210)
        val qr=ImageView(this).apply{
            setImageBitmap(qrBitmap(url,qrSize))
            adjustViewBounds=true
            contentDescription="QR tải ứng dụng $label $version"
            setPadding(dp(5),dp(5),dp(5),dp(5))
            setBackgroundColor(Color.WHITE)
        }
        card.addView(qr,LinearLayout.LayoutParams(qrSize,qrSize).apply{gravity=Gravity.CENTER_HORIZONTAL})
        card.addView(gap(5))
        val sizeText=json?.optLong("size",0L)?.takeIf{it>0L}?.let{humanBytes(it)}?:"chưa có dung lượng"
        card.addView(txt("Nguồn tải: GitHub Release • $sizeText",8.8f,muted,false).apply{gravity=Gravity.CENTER_HORIZONTAL})
        body.addView(card,matchWrap());body.addView(gap(8))
    }
    private fun renderAppDownloadQrScreen(beta:BetaApiClient.Result,stable:BetaApiClient.Result){
        if(screenState!="APP_DOWNLOAD_QR")return
        val root=baseRoot("QR TẢI ỨNG DỤNG")
        val body=body()
        body.addView(info("Quét QR bằng điện thoại/PDA để tải APK mới nhất. Link được đọc động từ GitHub Release; không dùng Google Drive."))
        body.addView(gap(6))
        addReleaseQrCard(body,"BETA",beta)
        addReleaseQrCard(body,"STABLE",stable)
        attach(root,body)
    }
    private fun appDownloadQrScreen(){
        module="SETTINGS";screenState="APP_DOWNLOAD_QR"
        val root=baseRoot("QR TẢI ỨNG DỤNG")
        val body=body()
        body.addView(info("Đang lấy bản Beta và Stable mới nhất…"))
        attach(root,body)
        api.latestGithubRelease("BETA"){beta->
            api.latestGithubRelease("STABLE"){stable->
                runOnUiThread{renderAppDownloadQrScreen(beta,stable)}
            }
        }
    }

    private fun settingsScreen(){
        module="SETTINGS"
        screenState="SETTINGS"
        val root=baseRoot("CÀI ĐẶT")
        val body=body()
        body.addView(section("Tài khoản"))
        body.addView(listCard("$name • ${roleText(effectiveRole)}","$login${if(position.isBlank())"" else "  •  $position"}\nMail: ${email.ifBlank{"Chưa cấu hình"}}"))
        body.addView(gap(7))
        val accountButtons=row(bg)
        val passBtn=primary("ĐỔI MẬT KHẨU",navy){changePasswordDialog()}.apply{textSize=9.6f;setSingleLine(true)}
        val mailBtn=primary("ĐỔI MAIL",teal){changeEmailDialog()}.apply{textSize=9.6f;setSingleLine(true)}
        accountButtons.addView(passBtn,LinearLayout.LayoutParams(0,dp(46),1f).apply{marginEnd=dp(3)})
        accountButtons.addView(mailBtn,LinearLayout.LayoutParams(0,dp(46),1f).apply{marginStart=dp(3)})
        body.addView(accountButtons,matchWrap())
        if(isAdmin()){
            body.addView(gap(7))
            body.addView(primary("QUẢN LÝ TÀI KHOẢN",blue){accountManager()},matchWrap())
        }
        // S23_PDA_IMPORT_UI_APPLIED: SUPERADMIN uses the shared Service Import Engine.
        if(isSuper()){
            body.addView(gap(7))
            body.addView(primary("IMPORT EXCEL",teal){
                startActivity(android.content.Intent(this,PdaImportActivity::class.java))
            },matchWrap())
        }
        body.addView(section("Giao diện"))
        body.addView(themePicker(),matchWrap())
        body.addView(section("THÔNG TIN ỨNG DỤNG"))
        val storageUsage=appStorageUsage()
        body.addView(details(listOf(
            "Phiên bản" to BuildConfig.VERSION_NAME,
            "Kênh phát hành" to if(BuildConfig.CHANNEL=="BETA")"Bản thử nghiệm" else "Bản ổn định",
            "Dung lượng ứng dụng" to humanBytes(appBinaryBytes()),
            "Dữ liệu ứng dụng" to humanBytes(storageUsage.userDataBytes),
            "Bộ nhớ đệm (cache)" to humanBytes(storageUsage.cacheBytes)
        )))
        body.addView(section("CẬP NHẬT PHIÊN BẢN"))
        val pendingUpdate=UpdateManager.pendingInfo(this)
        val latestRelease=UpdateManager.latestInfo(this)
        val latestVersion=pendingUpdate?.version?:latestRelease?.version?.takeIf{it.isNotBlank()}?:BuildConfig.VERSION_NAME
        body.addView(details(listOf(
            "Trạng thái" to if(pendingUpdate==null&&latestVersion==BuildConfig.VERSION_NAME)"Đang dùng bản mới nhất: ${BuildConfig.VERSION_NAME}" else "Bản mới nhất: $latestVersion\nĐang dùng: ${BuildConfig.VERSION_NAME}"
        )))
        body.addView(gap(7))
        if(pendingUpdate!=null)addVersionChangelog(body,"THAY ĐỔI BẢN MỚI",pendingUpdate.version,pendingUpdate.notes)
        addVersionChangelog(body,"THAY ĐỔI BẢN HIỆN TẠI",BuildConfig.VERSION_NAME,ReleaseNotes.currentText())
        body.addView(primary(if(pendingUpdate!=null)"TIẾP TỤC CẬP NHẬT" else "KIỂM TRA CẬP NHẬT",teal){UpdateManager.openManual(this)},matchWrap())
        body.addView(gap(10))
        body.addView(section("QR TẢI ỨNG DỤNG"))
        body.addView(info("Tạo QR tải trực tiếp APK mới nhất theo từng kênh phát hành."))
        body.addView(gap(6))
        body.addView(primary("MỞ QR TẢI ỨNG DỤNG",teal){appDownloadQrScreen()},matchWrap())
        body.addView(gap(10))
        body.addView(section("NHẬT KÝ"))
        val basicLogRows=LocalLogManager.detailRows(this).filter{it.first in setOf("Tên tệp nhật ký","Dung lượng tệp","Thời gian cập nhật mới nhất","Trạng thái tải lên / đồng bộ")}
        body.addView(details(basicLogRows))
        body.addView(gap(7))
        body.addView(primary("GỬI BÁO LỖI",teal){sendDiagnostic()},matchWrap())
        if(role=="ADMIN"||role=="SUPERADMIN"){
            val lan=LanCoordinator.get(this)
            val ls=lan.status()
            body.addView(gap(10));body.addView(section("LAN DỰ PHÒNG"))
            body.addView(details(listOf(
                "Trạng thái" to ls.optString("health_state"),
                "Vai trò PDA" to ls.optString("node_role"),
                "Master" to dash(ls.optString("master_device_id")),
                "Backup" to dash(ls.optString("backup_device_id")),
                "Generation" to ls.optLong("generation").toString(),
                "LAN epoch" to ls.optLong("lan_epoch").toString(),
                "PDA LAN đang thấy" to ls.optInt("peer_count").toString()
            )))
            val hs=lan.healthState()
            if(hs==LanAuthorityPolicy.HealthState.SERVICE_UNAVAILABLE||hs==LanAuthorityPolicy.HealthState.LAN_AVAILABLE){
                body.addView(gap(7))
                body.addView(primary("KÍCH HOẠT LAN DỰ PHÒNG",orange){
                    LanCoordinator.get(this).requestActivation(role){ok,error->runOnUiThread{
                        if(ok){TopNotice.show(this,"LAN dự phòng đã được kích hoạt và đang chờ đủ Master + backup.",TopNotice.Kind.SUCCESS);settingsScreen()}
                        else showError(error?:"LAN_ACTIVATION_FAILED")
                    }}
                },matchWrap())
            }
        }
        if(isActualSuper()){
            body.addView(gap(10));body.addView(section("TRUNG TÂM KIỂM THỬ RESILIENCE"))
            val test=ResilienceTestCenter.latest(this)
            val testSpec=test?.optString("scenario")?.let{ResilienceTestScenario.fromCode(it)}
            val ev=test?.optJSONObject("evidence")?:JSONObject()
            val serviceEv=ev.optJSONObject("recovery_service")?:ev.optJSONObject("service")?:JSONObject()
            body.addView(details(listOf(
                "Phạm vi" to "Test kỹ thuật cô lập • không chặn traffic nghiệp vụ thật",
                "Kịch bản gần nhất" to (testSpec?.label?:"Chưa chạy"),
                "Kết quả" to ResilienceTestCenter.resultVi(test?.optString("status").orEmpty()),
                "Giai đoạn" to ResilienceTestCenter.stageVi(test?.optString("stage").orEmpty()),
                "Local durable" to if(ev.optBoolean("local_durable_readback",false))"PASS" else "—",
                "Google/GAS capture" to when{ev.optJSONObject("google")?.optBoolean("captured",false)==true->"PASS";else->"—"},
                "LAN ACK" to if(ev.optBoolean("lan_ack",false))"PASS" else "—",
                "Idempotency" to if(serviceEv.optBoolean("idempotency_verified",false))"PASS" else "—",
                "Không chạm business outbox" to if(ev.optBoolean("business_outbox_touched",true))"FAIL" else "PASS",
                "Điều khiển test" to when{resilienceTestStopping->"Đang dừng và khôi phục";resilienceTestInFlight->"Đang chạy";else->"Sẵn sàng"},
                "Lỗi" to dash(test?.optString("last_error").orEmpty())
            )))
            body.addView(gap(7))
            val controlText=when{resilienceTestStopping->"ĐANG DỪNG TEST...";resilienceTestInFlight->"DỪNG TEST / VỀ BÌNH THƯỜNG";else->"CHỌN KỊCH BẢN & CHẠY TEST"}
            body.addView(primary(controlText,if(resilienceTestInFlight)red else orange){
                when{
                    resilienceTestStopping->Unit
                    resilienceTestInFlight->stopResilienceTest()
                    else->showResilienceScenarioDialog()
                }
            },matchWrap())
            body.addView(gap(7))
            body.addView(primary("XEM LỊCH SỬ TEST",blue){showResilienceHistoryDialog()},matchWrap())
        }
        body.addView(gap(14))
        body.addView(primary("ĐĂNG XUẤT",red){
            AlertDialog.Builder(this)
                .setTitle("Xác nhận đăng xuất")
                .setMessage("Bạn có chắc muốn đăng xuất khỏi ứng dụng?")
                .setNegativeButton("Hủy",null)
                .setPositiveButton("ĐĂNG XUẤT"){_,_->
                    LanCoordinator.get(this).safeBeforeLogout{ok,error->runOnUiThread{
                        if(!ok){showError(error?:"LAN_SAFE_HANDOVER_REQUIRED");return@runOnUiThread}
                        api.logoutFast()
                        startActivity(android.content.Intent(this, FullBetaActivity::class.java).apply {
                            flags = android.content.Intent.FLAG_ACTIVITY_NEW_TASK or android.content.Intent.FLAG_ACTIVITY_CLEAR_TASK
                        })
                        finish()
                        @Suppress("DEPRECATION")
                        overridePendingTransition(0, 0)
                    }}
                }
                .show()
        },matchWrap())
        attach(root,body)
    }

    private fun showResilienceScenarioDialog(){
        if(!isActualSuper()){showError("SUPERADMIN_REQUIRED");return}
        val scenarios=ResilienceTestCenter.scenarios()
        val host=column(surface).apply{setPadding(dp(10),dp(6),dp(10),dp(10))}
        var dialog:AlertDialog?=null
        scenarios.forEachIndexed{index,s->
            val card=column(surface).apply{
                setPadding(dp(12),dp(10),dp(12),dp(10))
                background=GradientDrawable().apply{
                    setColor(surface);cornerRadius=dp(12).toFloat()
                    setStroke(dp(1),Color.argb(190,Color.red(teal),Color.green(teal),Color.blue(teal)))
                }
                addView(txt("${index+1}. ${s.label}",11.2f,navy,true))
                addView(gap(3))
                addView(txt(s.description,9.8f,ink,false).apply{maxLines=5})
                addView(gap(4))
                addView(txt("Kỳ vọng: ${s.expected}",9.3f,muted,false).apply{maxLines=6})
                isClickable=true
                isFocusable=true
                setOnClickListener{
                    dialog?.dismiss()
                    AlertDialog.Builder(this@OperationsActivity)
                        .setTitle(s.label)
                        .setMessage("${s.description}\n\nKỳ vọng:\n${s.expected}\n\nTest chỉ tạo event kỹ thuật cô lập; không tắt LIVE thật và không chạm mutation nghiệp vụ.")
                        .setNegativeButton("HỦY",null)
                        .setPositiveButton("CHẠY TEST"){_,_->runResilienceScenario(s)}
                        .show()
                }
            }
            host.addView(card,matchWrap())
            if(index<scenarios.lastIndex)host.addView(gap(7))
        }
        val scroll=ScrollView(this).apply{addView(host)}
        dialog=AlertDialog.Builder(this)
            .setTitle("Chọn kịch bản kiểm thử")
            .setView(scroll)
            .setNegativeButton("ĐÓNG",null)
            .create()
        dialog?.show()
    }

    private fun runResilienceScenario(scenario:ResilienceTestScenario){
        if(resilienceTestInFlight)return
        resilienceTestStopping=false
        resilienceTestInFlight=true
        TopNotice.show(this,"Đang kiểm thử: ${scenario.label}",TopNotice.Kind.INFO)
        if(screenState=="SETTINGS")settingsScreen()
        Thread{
            val result=runCatching{ResilienceTestCenter.run(applicationContext,scenario)}
                .getOrElse{JSONObject().put("status","FAIL").put("last_error",it.message?:it.javaClass.simpleName)}
            runOnUiThread{
                resilienceTestInFlight=false
                resilienceTestStopping=false
                if(screenState=="SETTINGS")settingsScreen()
                val status=result.optString("status")
                val ok=status=="PASS"
                val unavailable=status=="NOT_AVAILABLE"
                val cancelled=status=="CANCELLED"
                TopNotice.show(this,
                    when{ok->"Resilience test PASS: ${scenario.label}";unavailable->"Chưa đủ điều kiện để test: ${scenario.label}";cancelled->"Đã dừng test và trở về trạng thái bình thường.";else->"Resilience test FAIL: ${scenario.label}"},
                    when{ok->TopNotice.Kind.SUCCESS;unavailable||cancelled->TopNotice.Kind.WARNING;else->TopNotice.Kind.ERROR}
                )
            }
        }.start()
    }

    private fun stopResilienceTest(){
        if(!resilienceTestInFlight||resilienceTestStopping)return
        resilienceTestStopping=true
        ResilienceTestCenter.stop()
        TopNotice.show(this,"Đã yêu cầu dừng test. App sẽ kết thúc bước kỹ thuật đang chạy và trở về trạng thái bình thường.",TopNotice.Kind.WARNING)
        if(screenState=="SETTINGS")settingsScreen()
    }

    private fun showResilienceHistoryDialog(){
        val arr=ResilienceTestCenter.history(this,30)
        if(arr.length()==0){TopNotice.show(this,"Chưa có lịch sử kiểm thử resilience.",TopNotice.Kind.INFO);return}
        val host=column(surface).apply{setPadding(dp(10),dp(6),dp(10),dp(10))}
        host.addView(info("Mới nhất ở trên • ${arr.length()} lượt gần nhất • mỗi thẻ là một test độc lập"))
        host.addView(gap(7))
        for(i in 0 until arr.length()){
            val x=arr.optJSONObject(i)?:continue
            val spec=ResilienceTestScenario.fromCode(x.optString("scenario"))
            val ev=x.optJSONObject("evidence")?:JSONObject()
            val serviceEv=ev.optJSONObject("recovery_service")?:ev.optJSONObject("service")?:JSONObject()
            val statusRaw=x.optString("status")
            val statusText=ResilienceTestCenter.resultVi(statusRaw)
            val statusColor=when(statusRaw){ "PASS"->green;"FAIL"->red;"CANCELLED"->orange;"NOT_AVAILABLE"->orange;else->blue }
            val updated=x.optLong("updated_at",0L)
            val at=if(updated>0L)Instant.ofEpochMilli(updated).atZone(ZoneId.of("Asia/Ho_Chi_Minh")).format(DateTimeFormatter.ofPattern("dd/MM HH:mm:ss")) else "—"
            val eventShort=x.optString("event_id").take(8).ifBlank{"—"}
            val card=column(surface).apply{
                setPadding(dp(12),dp(10),dp(12),dp(10))
                background=GradientDrawable().apply{
                    setColor(surface);cornerRadius=dp(12).toFloat()
                    setStroke(dp(2),Color.argb(185,Color.red(statusColor),Color.green(statusColor),Color.blue(statusColor)))
                }
                addView(row(surface).apply{
                    addView(txt(statusText,10.5f,statusColor,true),LinearLayout.LayoutParams(0,-2,.34f))
                    addView(txt(at,9.2f,muted,true).apply{gravity=Gravity.END},LinearLayout.LayoutParams(0,-2,.66f))
                })
                addView(gap(4))
                addView(txt(spec?.label?:x.optString("scenario"),10.8f,navy,true))
                addView(gap(5))
                addView(details(listOf(
                    "Giai đoạn" to ResilienceTestCenter.stageVi(x.optString("stage")),
                    "Local durable" to if(ev.optBoolean("local_durable_readback",false))"PASS" else "—",
                    "Google/GAS" to if(ev.optJSONObject("google")?.optBoolean("captured",false)==true)"PASS" else "—",
                    "LAN ACK" to if(ev.optBoolean("lan_ack",false))"PASS" else "—",
                    "Idempotency" to if(serviceEv.optBoolean("idempotency_verified",false))"PASS" else "—",
                    "Business outbox" to if(ev.optBoolean("business_outbox_touched",true))"BỊ TÁC ĐỘNG" else "Không chạm",
                    "Mã test" to eventShort,
                    "Lỗi" to dash(x.optString("last_error"))
                )))
            }
            host.addView(card,matchWrap())
            if(i<arr.length()-1)host.addView(gap(8))
        }
        val scroll=ScrollView(this).apply{addView(host)}
        AlertDialog.Builder(this)
            .setTitle("Lịch sử kiểm thử resilience")
            .setView(scroll)
            .setPositiveButton("ĐÓNG",null)
            .show()
    }

    private fun themePicker()=row(surface).apply{
        gravity=Gravity.CENTER
        setPadding(dp(5),dp(8),dp(5),dp(8))
        background=outlineBg(surface,14)
        val selected=ThemeManager.selectedIndex(this@OperationsActivity)
        ThemeManager.swatches().forEachIndexed{i,c->
            val holder=FrameLayout(this@OperationsActivity).apply{
                background=if(i==selected)GradientDrawable().apply{setColor(Color.TRANSPARENT);cornerRadius=dp(10).toFloat();setStroke(dp(2),navy)}else null
                setPadding(dp(3),dp(3),dp(3),dp(3))
                addView(TextView(this@OperationsActivity).apply{
                    text=if(i==selected)"✓" else ""
                    textSize=15f
                    setTextColor(Color.WHITE)
                    typeface=Typeface.DEFAULT_BOLD
                    gravity=Gravity.CENTER
                    background=round(c,8)
                },FrameLayout.LayoutParams(-1,-1))
                setOnClickListener{ThemeManager.select(this@OperationsActivity,i);window.statusBarColor=ThemeManager.primaryDark(this@OperationsActivity);settingsScreen()}
            }
            addView(holder,LinearLayout.LayoutParams(0,dp(42),1f).apply{marginStart=dp(2);marginEnd=dp(2)})
        }
    }
    private fun changePasswordDialog(){val box=column(surface).apply{setPadding(dp(8),0,dp(8),0)};val current=input("Mật khẩu hiện tại",true);val next=input("Mật khẩu mới",true);val confirm=input("Nhập lại mật khẩu mới",true);box.addView(current);box.addView(gap(7));box.addView(next);box.addView(gap(7));box.addView(confirm);AlertDialog.Builder(this).setTitle("Đổi mật khẩu").setView(box).setNegativeButton("Hủy",null).setPositiveButton("CẬP NHẬT"){_,_->if(next.text.toString()!=confirm.text.toString()){showError("Mật khẩu xác nhận không khớp.");return@setPositiveButton};api.call("change_password",JSONObject().put("current_password",current.text.toString()).put("new_password",next.text.toString())){r->runOnUiThread{if(handleAuth(r))return@runOnUiThread;if(!r.ok)showError(r.error?:"Đổi mật khẩu thất bại")else TopNotice.show(this,"Đã đổi mật khẩu.",TopNotice.Kind.SUCCESS)}}}.show()}
    private fun changeEmailDialog(){val value=input("Địa chỉ mail nhận reset mật khẩu",false).apply{setText(email)};AlertDialog.Builder(this).setTitle("Đổi mail").setView(value).setNegativeButton("Hủy",null).setPositiveButton("CẬP NHẬT"){_,_->val next=value.text.toString().trim();api.call("change_email",JSONObject().put("email",next)){r->runOnUiThread{if(handleAuth(r))return@runOnUiThread;if(!r.ok)showError(r.error?:"Không đổi được mail")else{email=r.json?.optJSONObject("account")?.optString("email",next)?:next;TopNotice.show(this,"Đã cập nhật mail nhận reset.",TopNotice.Kind.SUCCESS);settingsScreen()}}}}.show()}
    private fun sendDiagnostic(){AlertDialog.Builder(this).setTitle("Gửi log thủ công?").setMessage("Gửi gói chẩn đoán hiện tại lên hệ thống?").setNegativeButton("NO",null).setPositiveButton("YES"){_,_->LocalLogManager.sendManualReport(this,api,module,connectionSummary()){r->runOnUiThread{if(handleAuth(r))return@runOnUiThread;if(!r.ok)showError(r.error?:"Không gửi được báo lỗi")else{TopNotice.show(this,"Đã gửi báo lỗi thành công. Nhật ký trên thiết bị đã được reset.",TopNotice.Kind.SUCCESS);settingsScreen()}}}}.show()}

    private fun accountManager(){
        screenState="ACCOUNT_MANAGER"
        val root=baseRoot("QUẢN LÝ TÀI KHOẢN")
        val body=body()
        val selected=linkedSetOf<String>()
        val checks=mutableListOf<CheckBox>()
        body.addView(primary("TẠO TÀI KHOẢN",green){accountCreateDialog()},matchWrap())
        if(isSuper()){
            body.addView(gap(7))
            val bulk=row(bg)
            bulk.addView(smallButton("CHỌN TẤT CẢ",navy).apply{
                setOnClickListener{checks.forEach{if(it.isEnabled)it.isChecked=true}}
            },LinearLayout.LayoutParams(0,dp(42),1f).apply{marginEnd=dp(3)})
            bulk.addView(smallButton("XÓA ĐÃ CHỌN",red).apply{
                setOnClickListener{deleteAccountsBulk(selected.toList())}
            },LinearLayout.LayoutParams(0,dp(42),1f).apply{marginStart=dp(3)})
            body.addView(bulk,matchWrap())
        }
        body.addView(gap(10))
        val box=column(bg)
        body.addView(box,matchWrap())
        api.call("account_list"){r->runOnUiThread{
            box.removeAllViews()
            if(handleAuth(r))return@runOnUiThread
            if(!r.ok){box.addView(info(r.error?:"Không tải được tài khoản"));return@runOnUiThread}
            val a=r.json?.optJSONArray("items")?:JSONArray()
            for(i in 0 until a.length()){
                val x=a.optJSONObject(i)?:continue
                val id=x.optString("login_id")
                val isProtectedAccount=id==login||x.optString("role")=="SUPERADMIN"
                val card=column(surface).apply{
                    setPadding(dp(12),dp(10),dp(12),dp(10))
                    background=outlineBg(surface,12)
                    val top=row(surface).apply{gravity=Gravity.CENTER_VERTICAL}
                    if(isSuper()){
                        val c=CheckBox(this@OperationsActivity).apply{
                            isEnabled=!isProtectedAccount
                            isChecked=id in selected
                            setOnCheckedChangeListener{_,on->if(on)selected.add(id)else selected.remove(id)}
                        }
                        checks.add(c)
                        top.addView(c,size(dp(42),dp(42)))
                    }
                    top.addView(column(surface).apply{
                        addView(txt("$id • ${x.optString("display_name")}",13f,navy,true))
                        addView(txt("${roleText(x.optString("role"))} • ${if(x.optString("status")=="ACTIVE")"Đang hoạt động" else "Đã vô hiệu hóa"} • ${x.optString("email")}",9.8f,muted,false))
                    },LinearLayout.LayoutParams(0,-2,1f))
                    addView(top,matchWrap())
                    if(id!=login){
                        addView(gap(6))
                        val actions=row(surface)
                        if(isSuper()){
                            actions.addView(smallButton("SỬA",teal).apply{setOnClickListener{accountEditDialog(x)}},LinearLayout.LayoutParams(0,dp(38),.85f).apply{marginEnd=dp(2)})
                            if(!isProtectedAccount)actions.addView(smallButton("ĐỔI MK",navy).apply{setOnClickListener{changeOtherAccountPassword(x)}},LinearLayout.LayoutParams(0,dp(38),1f).apply{marginStart=dp(2);marginEnd=dp(2)})
                        }
                        val newStatus=if(x.optString("status")=="ACTIVE")"DISABLED" else "ACTIVE"
                        actions.addView(smallButton(if(newStatus=="DISABLED")"VÔ HIỆU" else "KÍCH HOẠT",if(newStatus=="DISABLED")orange else green).apply{
                            setOnClickListener{verifyEditPassword("đổi trạng thái tài khoản"){api.call("account_status",JSONObject().put("login_id",id).put("status",newStatus)){rr->runOnUiThread{if(!rr.ok)showError(rr.error?:"Không cập nhật được")else accountManager()}}}}
                        },LinearLayout.LayoutParams(0,dp(38),1f).apply{marginStart=dp(3);marginEnd=dp(3)})
                        if(isSuper()&&!isProtectedAccount){
                            actions.addView(smallButton("XÓA",red).apply{setOnClickListener{deleteAccountsBulk(listOf(id))}},LinearLayout.LayoutParams(0,dp(38),1f).apply{marginStart=dp(3)})
                        }
                        addView(actions,matchWrap())
                    }
                }
                box.addView(card,matchWrap())
                box.addView(gap(7))
            }
        }}
        attach(root,body)
    }

    private fun changeOtherAccountPassword(x:JSONObject){
        if(!isSuper())return
        val id=x.optString("login_id").trim()
        if(id.isBlank()||id==login||x.optString("role").equals("SUPERADMIN",true)){showError("Không thể đổi mật khẩu tài khoản này.");return}
        val box=column(surface).apply{setPadding(dp(10),dp(4),dp(10),dp(8))}
        val next=input("Mật khẩu mới",true);val confirm=input("Nhập lại mật khẩu mới",true)
        box.addView(labelled("Tài khoản",txt("$id • ${x.optString("display_name")}",11f,navy,true)));box.addView(gap(7));box.addView(next);box.addView(gap(7));box.addView(confirm)
        val dialog=AlertDialog.Builder(this).setTitle("Đổi mật khẩu cho $id").setView(box).setNegativeButton("Hủy",null).setPositiveButton("CẬP NHẬT",null).create()
        dialog.setOnShowListener{dialog.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener{
            val a=next.text.toString();if(a.length !in 8..128){showError("Mật khẩu mới phải có ít nhất 8 ký tự.");return@setOnClickListener}
            if(a!=confirm.text.toString()){showError("Mật khẩu xác nhận không khớp.");return@setOnClickListener}
            dialog.dismiss()
            verifyActionPassword("đổi mật khẩu tài khoản $id"){
                api.call("account_upsert",JSONObject().put("login_id",id).put("display_name",x.optString("display_name")).put("position",x.optString("role").lowercase()).put("email",x.optString("email")).put("role",x.optString("role")).put("password",a)){r->runOnUiThread{
                    if(handleAuth(r))return@runOnUiThread
                    if(!r.ok)showError(r.error?:"Không đổi được mật khẩu") else{TopNotice.show(this,"Đã đổi mật khẩu cho $id.",TopNotice.Kind.SUCCESS);accountManager()}
                }}
            }
        }}
        dialog.show()
    }

    private fun accountEditDialog(x:JSONObject,verified:Boolean=false){
        if(!isSuper())return;if(!verified){verifyEditPassword("sửa tài khoản"){accountEditDialog(x,true)};return};val box=column(surface).apply{setPadding(dp(10),dp(4),dp(10),dp(8))};val display=input("Tên hiển thị",false).apply{setText(x.optString("display_name"))};val mail=input("Mail",false).apply{setText(x.optString("email"))};val roles=arrayOf("USER","ADMIN");val roleSp=spinner(roles);roleSp.setSelection(if(x.optString("role")=="ADMIN")1 else 0);box.addView(labelled("Tên hiển thị",display));box.addView(gap(7));box.addView(labelled("Quyền",roleSp));box.addView(gap(7));box.addView(labelled("Mail",mail));AlertDialog.Builder(this).setTitle("Sửa tài khoản ${x.optString("login_id")}").setView(box).setNegativeButton("Hủy",null).setPositiveButton("LƯU"){_,_->val rr=roleSp.selectedItem.toString();api.call("account_upsert",JSONObject().put("login_id",x.optString("login_id")).put("display_name",display.text.toString().trim()).put("position",rr.lowercase()).put("email",mail.text.toString().trim()).put("role",rr)){r->runOnUiThread{if(!r.ok)showError(r.error?:"Không sửa được tài khoản")else accountManager()}}}.show()
    }

    private fun deleteAccountsBulk(ids:List<String>){
        if(!isSuper()){showError("Chỉ Quản trị cao nhất được xóa tài khoản.");return};val clean=ids.filter{it.isNotBlank()&&it!=login}.distinct();if(clean.isEmpty()){showError("Chọn ít nhất một tài khoản có thể xóa.");return}
        AlertDialog.Builder(this).setTitle("Xóa ${clean.size} tài khoản?").setMessage("Tài khoản Quản trị cao nhất và tài khoản đang đăng nhập được bảo vệ. Nhật ký kiểm toán vẫn được giữ.").setNegativeButton("Hủy",null).setPositiveButton("TIẾP TỤC"){_,_->verifyDeletePassword("xóa ${clean.size} tài khoản"){api.call("account_delete",JSONObject().put("login_ids",JSONArray(clean))){r->runOnUiThread{if(handleAuth(r))return@runOnUiThread;if(!r.ok){showError(r.error?:"Không xóa được tài khoản");return@runOnUiThread};val blocked=r.json?.optJSONArray("blocked")?:JSONArray();TopNotice.show(this,if(blocked.length()>0)"Đã xóa các tài khoản hợp lệ; ${blocked.length()} mục được bảo vệ hoặc không thể xóa." else "Đã xóa tài khoản.",if(blocked.length()>0)TopNotice.Kind.WARNING else TopNotice.Kind.SUCCESS);accountManager()}}}}.show()
    }

    private fun accountCreateDialog(){
        val box=column(surface).apply{setPadding(dp(10),dp(4),dp(10),dp(8))}
        val loginInput=input("Tài khoản",false)
        val display=input("Tên hiển thị",false)
        val allowedPositions=if(isSuper())arrayOf("USER","ADMIN")else arrayOf("USER")
        val positionSp=spinner(allowedPositions)
        val mail=input("Mail nhận reset",false).apply{setText("tam95.supra@gmail.com")}
        val pass=input("Mật khẩu ban đầu",true)
        fun addField(label:String,view:View){box.addView(txt(label,10.2f,ink,true));box.addView(gap(4));box.addView(view,matchWrap());box.addView(gap(8))}
        addField("Tài khoản",loginInput);addField("Tên hiển thị",display);addField("Vị trí",positionSp);addField("Mail nhận reset",mail);addField("Mật khẩu ban đầu",pass)
        AlertDialog.Builder(this).setTitle("Tạo tài khoản").setView(ScrollView(this).apply{addView(box)}).setNegativeButton("Hủy",null).setPositiveButton("TẠO"){_,_->
            val fixedRole=positionSp.selectedItem.toString().uppercase()
            api.call("account_upsert",JSONObject().put("login_id",loginInput.text.toString().trim()).put("display_name",display.text.toString().trim()).put("position",fixedRole.lowercase()).put("email",mail.text.toString().trim()).put("role",fixedRole).put("password",pass.text.toString())){r->runOnUiThread{if(!r.ok)showError(r.error?:"Không tạo được tài khoản")else accountManager()}}
        }.show()
    }

    private fun refreshMasterCache(){cacheApi.call("master_snapshot"){r->if(r.ok&&r.json!=null)MasterDataCache.save(applicationContext,r.json)}}
    private fun installSystemBackHandler(){
        if(Build.VERSION.SDK_INT>=33)onBackInvokedDispatcher.registerOnBackInvokedCallback(android.window.OnBackInvokedDispatcher.PRIORITY_DEFAULT){handleBackNavigation()}
    }
    private fun handleBackNavigation(){if(screenBackStack.isNotEmpty())navigateBack()}
    @Suppress("DEPRECATION")
    override fun onBackPressed(){handleBackNavigation()}

    private fun navigateBack(){
        if(screenBackStack.isEmpty())return
        val snapshot=screenBackStack.removeLast()
        if(screenState=="DOCUMENT_MANAGEMENT"){documentController?.dispose();documentController=null}
        if(screenState=="MEAL_ATTENDANCE")PostMealAttendanceFeature.leave()
        module=snapshot.module;screenState=snapshot.screenState;initialMnv=snapshot.initialMnv;liveEmployeeMnv=snapshot.liveEmployeeMnv
        val frame=contentHost?:return
        frame.suppressLayout(true)
        try{(snapshot.view.parent as? ViewGroup)?.removeView(snapshot.view);frame.removeAllViews();frame.addView(snapshot.view,FrameLayout.LayoutParams(-1,-1))}finally{frame.suppressLayout(false)}
        displayedModule=module;displayedScreenState=screenState;displayedInitialMnv=initialMnv;displayedLiveEmployeeMnv=liveEmployeeMnv
        refreshBottomNav();frame.requestLayout();frame.invalidate()
    }

    private fun simpleMessage(title:String,message:String){val root=baseRoot(title);val body=body();body.addView(info("ⓘ $message"));attach(root,body)}
    private fun baseRoot(title:String)=column(bg).apply{addView(appBar(title))}
    private fun body()=column(bg).apply{setPadding(dp(10),dp(8),dp(10),dp(76))}
    private fun attach(root:LinearLayout,body:LinearLayout){
        root.addView(ScrollView(this).apply{addView(body)},LinearLayout.LayoutParams(-1,0,1f))
        setScreen(root)
    }
    private fun setScreen(content:View){
        val frame=contentHost
        if(frame==null){setContentView(host(content));displayedModule=module;displayedScreenState=screenState;displayedInitialMnv=initialMnv;displayedLiveEmployeeMnv=liveEmployeeMnv;return}
        val current=frame.getChildAt(0)
        if(current!=null&&displayedScreenState.isNotBlank()&&(displayedScreenState!=screenState||displayedModule!=module)){
            screenBackStack.addLast(ScreenSnapshot(current,displayedModule,displayedScreenState,displayedInitialMnv,displayedLiveEmployeeMnv))
            while(screenBackStack.size>40)screenBackStack.removeFirst()
        }
        frame.suppressLayout(true)
        try{frame.removeAllViews();frame.addView(content,FrameLayout.LayoutParams(-1,-1))}finally{frame.suppressLayout(false)}
        displayedModule=module;displayedScreenState=screenState;displayedInitialMnv=initialMnv;displayedLiveEmployeeMnv=liveEmployeeMnv
        refreshBottomNav()
    }
    private fun isRootScreen()=screenState=="BUSINESS"||screenState=="STAFF"||screenState=="HISTORY"||screenState=="SYNC"||screenState=="SETTINGS"||screenState=="ROLE_MODE"

    private fun hideSoftKeyboard(view:View){(getSystemService(android.content.Context.INPUT_METHOD_SERVICE) as? android.view.inputmethod.InputMethodManager)?.hideSoftInputFromWindow(view.windowToken,0)}
    private fun hideKeyboardForResult(root:View,input:EditText){input.clearFocus();root.isFocusableInTouchMode=true;root.requestFocus();input.post{hideSoftKeyboard(input)}}
    private fun bytesVi(v:Long):String=when{v<1024->"$v byte";v<1024L*1024->String.format(java.util.Locale.US,"%.1f KB",v/1024.0);else->String.format(java.util.Locale.US,"%.1f MB",v/(1024.0*1024.0))}
    private fun statusTimeVi(v:Long):String=if(v<=0L)"Chưa có" else runCatching{java.time.Instant.ofEpochMilli(v).atZone(ZoneId.of("Asia/Ho_Chi_Minh")).format(DateTimeFormatter.ofPattern("dd/MM/yyyy HH:mm:ss"))}.getOrDefault("Chưa có")
    private fun authorityViHeader(v:String):String=when(v.uppercase()){ "SERVICE_PRIMARY"->"Dịch vụ chính đang giữ quyền ghi";"GOOGLE_FALLBACK"->"Google Drive đang làm đường dự phòng";"RECONCILING"->"Đang đối chiếu để thống nhất dữ liệu";"OFFLINE_LOCAL"->"Đang lưu tạm trên PDA";else->"Chưa xác định quyền ghi" }
    private fun routeViHeader(v:String):String=when(v.uppercase()){ "SERVICE_D1_DIRECT"->"Đi thẳng qua dịch vụ chính";"SERVICE_D1_PENDING"->"Dịch vụ chính đang chờ xác nhận";"GOOGLE_FALLBACK","GAS_COMPAT"->"Đi qua Google Drive dự phòng";"UNRESOLVED"->"Chưa xác định đường đi";else->if(v.isBlank())"Chưa xác định đường đi" else v }
    private fun replicaViHeader(v:String):String=when(v.uppercase()){ "SYNCED","HEALTHY","OK"->"Đã sao chép";"PENDING","INFLIGHT","RUNNING"->"Đang sao chép";"RETRY"->"Chờ gửi lại";"ERROR","FAILED"->"Lỗi";else->if(v.isBlank())"Chưa có trạng thái" else v }
    private fun runtimeErrorVi(v:String):String{val x=v.uppercase();return when{v.isBlank()->"Không có";x.contains("TEST_CLOUDFLARE_DISABLED")->"Cloudflare đang tắt thử nghiệm";x.contains("TEST_GOOGLE_DISABLED")->"Google Drive đang tắt thử nghiệm";x.contains("SESSION_EXCHANGE")->"Không tạo được phiên Cloudflare";x.contains("SERVICE_SESSION_UNAVAILABLE")->"Phiên Cloudflare chưa sẵn sàng";x.contains("AUTHORITY_NOT_SERVICE_PRIMARY")->"Cloudflare không giữ quyền ghi";x.contains("NETWORK")||x.contains("TIMEOUT")->"Lỗi kết nối";else->v.take(120)}}
    private fun transportViHeader(v:String):String=when(v.trim().uppercase()){
        "WIFI","WI-FI"->"Wi‑Fi"
        "CELLULAR","MOBILE","DATA"->"Dữ liệu di động"
        "ETHERNET"->"Mạng dây"
        "NONE","OFFLINE"->"Không có kết nối"
        else->if(v.isBlank())"Chưa xác định" else v
    }
    private fun latencyQualityViHeader(v:Long?):String=when{
        v==null->"Chưa có số đo"
        v<=150L->"Tốt"
        v<=350L->"Bình thường"
        v<=800L->"Chậm"
        else->"Rất chậm"
    }
    private fun faultViHeader(v:String):String=when(v.trim().uppercase()){
        "NONE","OFF","NORMAL"->"Không bật thử nghiệm lỗi"
        "DISABLE_CLOUDFLARE"->"Đang tắt dịch vụ chính để thử nghiệm"
        "DISABLE_GOOGLE"->"Đang tắt Google Drive để thử nghiệm"
        "DISABLE_BOTH"->"Đang tắt cả hai đường kết nối để thử nghiệm"
        else->if(v.isBlank())"Không bật thử nghiệm lỗi" else v
    }
    private fun lanHealthViHeader(v:LanAuthorityPolicy.HealthState):String=when(v){
        LanAuthorityPolicy.HealthState.NORMAL->"Bình thường"
        LanAuthorityPolicy.HealthState.DEGRADED->"Suy giảm"
        LanAuthorityPolicy.HealthState.SERVICE_UNAVAILABLE->"Service không khả dụng"
        LanAuthorityPolicy.HealthState.LAN_AVAILABLE->"LAN sẵn sàng"
        LanAuthorityPolicy.HealthState.LAN_ACTIVE->"LAN đang hoạt động"
        LanAuthorityPolicy.HealthState.RECOVERING->"Đang phục hồi"
        LanAuthorityPolicy.HealthState.CLOUD_DR_ACTIVE->"Cloud DR đang hoạt động"
    }
    private fun serviceEndpointSummary(raw:String):String=runCatching{
        val u=java.net.URI(raw.trim());val host=u.host.orEmpty();if(host.isBlank())"Chưa có" else host
    }.getOrDefault("Chưa có")
    private fun showHeaderStatusDetail(kind:String){
        val runtime=api.runtimeStatus()
        val counts=runCatching{operationalStore.mutationStatusCounts()}.getOrDefault(OperationalDataStore.MutationStatusCounts(0,0,0,0))
        val flow=SyncDirectionTracker.snapshot()
        val provider=serviceProviderFromRuntime()
        val net=DeviceNetworkStatus.snapshot(this)
        val lanState=LanCoordinator.get(this).healthState()
        val latestTest=ResilienceTestCenter.latest(this)
        val latestSpec=latestTest?.optString("scenario")?.let{ResilienceTestScenario.fromCode(it)}
        val title=when(kind){"NETWORK"->"Thông tin Mạng";"SYNC"->"Thông tin Đồng bộ";else->"Thông tin Dịch vụ"}
        val rows=when(kind){
            "NETWORK"->listOf(
                "Loại kết nối" to transportViHeader(net.transport),
                "Internet" to when{!net.hasInternet->"Không có kết nối Internet";net.validated->"Đã kết nối / đã xác thực";else->"Có kết nối / chưa xác thực"},
                "Mạng tính theo dung lượng" to if(net.metered)"Có" else "Không",
                "Độ trễ tới Service" to (lastSyncLatencyMs?.let{"$it ms"}?:"Chưa có số đo"),
                "Chất lượng kết nối" to latencyQualityViHeader(lastSyncLatencyMs),
                "Lần kiểm tra" to statusTimeVi(lastStatusUpdateAt)
            )
            "SYNC"->listOf(
                "Trạng thái" to when{flow.active->"Đang đồng bộ";counts.pending>0->"Đang chờ gửi dữ liệu";lastConnected==true->"Đã đồng bộ";else->"Chờ kết nối"},
                "Bản ghi chờ gửi" to counts.pending.toString(),
                "Cần kiểm tra thủ công" to counts.review.toString(),
                "Bị từ chối" to counts.rejected.toString(),
                "Đã Service xác nhận" to counts.confirmed.toString(),
                "Google Sheets chờ sao chép" to lastReplicationPending.toString(),
                "Google Sheets replica" to replicaViHeader(lastReplicationState),
                "Sao chép thành công gần nhất" to if(lastReplicationSuccessAt.isBlank())"Chưa có" else formatIso(lastReplicationSuccessAt),
                "Đã gửi" to bytesVi(flow.uploadedBytes),
                "Đã nhận" to bytesVi(flow.downloadedBytes)
            )
            else->listOf(
                "Service hiện dùng" to when(provider){"Cloudflare"->"Cloudflare Service";"Google Drive"->"Google/GAS dự phòng";"OFFLINE"->"Ngoại tuyến";else->provider},
                "Authority" to authorityViHeader(runtime.optString("authority_mode")),
                "Route dữ liệu" to routeViHeader(runtime.optString("route")),
                "Phiên Service" to if(runtime.optBoolean("service_session",false))"Sẵn sàng" else "Chưa sẵn sàng",
                "LAN / DR" to lanHealthViHeader(lanState),
                "Google Sheets replica" to replicaViHeader(lastReplicationState),
                "Replication pending" to lastReplicationPending.toString(),
                "Sự cố gần nhất" to runtimeErrorVi(runtime.optString("last_error")),
                "Độ trễ Service" to (lastSyncLatencyMs?.let{"$it ms • ${latencyQualityViHeader(it)}"}?:"Chưa đo"),
                "Endpoint" to serviceEndpointSummary(runtime.optString("service_url")),
                "Test resilience gần nhất" to if(latestTest==null)"Chưa chạy" else "${latestSpec?.label?:latestTest.optString("scenario")} • ${ResilienceTestCenter.resultVi(latestTest.optString("status"))}",
                "Lần kiểm tra" to statusTimeVi(lastStatusUpdateAt)
            )
        }
        val box=column(surface).apply{setPadding(dp(14),dp(10),dp(14),dp(8));addView(details(rows),matchWrap())}
        val builder=AlertDialog.Builder(this).setTitle(title).setView(ScrollView(this).apply{addView(box)}).setPositiveButton("ĐÓNG",null)
        if(kind=="SYNC")builder.setNeutralButton("ĐỒNG BỘ NGAY"){_,_->manualRefreshFromHeader(syncStatusText?:box)}
        builder.show()
    }
    private fun manualRefreshFromHeader(icon:View){
        if(manualRefreshInFlight)return
        manualRefreshInFlight=true;icon.isEnabled=false;icon.alpha=.55f
        M2ImmediateOutbox.kick(this);foregroundSync.requestSync();refreshMasterCache();historyLastCanonicalRefreshAt=0L
        Thread{
            val ok=runCatching{M2BackgroundSync.catchUp(applicationContext)}.getOrDefault(false)
            runOnUiThread{
                manualRefreshInFlight=false;icon.isEnabled=true;icon.alpha=1f;historyLastCanonicalRefreshAt=System.currentTimeMillis()
                when(screenState){
                    "HISTORY"->historyScreen()
                    "SYNC"->syncScreen()
                    "EMPLOYEE","EMPLOYEE_LOADING","EMPLOYEE_LOOKUP_ERROR"->if(liveEmployeeMnv.isNotBlank())loadEmployee(liveEmployeeMnv)
                    "REPORT"->reportScreen()
                    else->refreshHeaderConnection()
                }
                TopNotice.show(this,if(ok)"Đã đồng bộ lại dữ liệu từ Service." else "Đã yêu cầu đồng bộ; dữ liệu sẽ tiếp tục gửi lại khi kết nối phù hợp.",if(ok)TopNotice.Kind.SUCCESS else TopNotice.Kind.WARNING)
            }
        }.start()
    }

    private fun serviceProviderFromRuntime():String{
        val fault=ServiceFaultInjection.mode(this)
        if(fault==ServiceFaultInjection.Mode.DISABLE_BOTH)return "OFFLINE"
        val st=api.runtimeStatus();val mode=st.optString("authority_mode");val route=st.optString("route")
        if(ServiceFaultInjection.cloudflareDisabled(this))return "Service OFFLINE (test)"
        if(lastConnected==false)return "OFFLINE"
        return when{
            mode=="GOOGLE_FALLBACK"||route=="GOOGLE_FALLBACK"||route=="GAS_COMPAT"->if(ServiceFaultInjection.googleDisabled(this))"OFFLINE" else "Google Drive"
            lastConnected==true&&(mode=="SERVICE_PRIMARY"||mode=="RECONCILING"||route.startsWith("SERVICE_")||st.optBoolean("service_session",false))->"Cloudflare"
            else->"Đang xác định"
        }
    }
    private fun connectionSummary():String{val network=when(lastConnected){true->lastSyncLatencyMs?.let{"$it ms"}?:"Có mạng";false->"Mất kết nối";null->"Chưa kiểm tra"};val pending=runCatching{operationalStore.pendingMutationCount()}.getOrDefault(0);return "Mạng: $network | Đồng bộ: ${if(pending==0)"Hoàn tất" else "Đang chờ đồng bộ"} | Dịch vụ: ${serviceProviderFromRuntime()}"}
    private fun refreshHeaderConnection(){
        val net=runCatching{DeviceNetworkStatus.snapshot(this)}.getOrNull()
        val networkLabel=when{
            net==null->"Đang kiểm tra"
            !net.hasInternet->"Không Internet"
            else->transportViHeader(net.transport)
        }
        if(networkStatusText?.text?.toString()!=networkLabel)networkStatusText?.text=networkLabel
        val counts=runCatching{operationalStore.mutationStatusCounts()}.getOrDefault(OperationalDataStore.MutationStatusCounts(0,0,0,0))
        val queue=(counts.pending+counts.review+counts.rejected).coerceAtLeast(0)
        val syncLabel=when{
            queue>0->"Chờ đồng bộ: $queue"
            lastConnected==true->"Đã đồng bộ"
            else->"Chờ kết nối"
        }
        if(syncStatusText?.text?.toString()!=syncLabel)syncStatusText?.text=syncLabel
        val provider=serviceProviderFromRuntime()
        val lanState=LanCoordinator.get(this).healthState()
        val serviceLabel=when(lanState){
            LanAuthorityPolicy.HealthState.NORMAL->when(provider){"Cloudflare"->"Hoạt động";"Google Drive"->"Dự phòng";"OFFLINE","Service OFFLINE (test)"->"Ngoại tuyến";else->"Đang kiểm tra"}
            LanAuthorityPolicy.HealthState.DEGRADED->"Suy giảm"
            LanAuthorityPolicy.HealthState.SERVICE_UNAVAILABLE->"Mất dịch vụ"
            LanAuthorityPolicy.HealthState.LAN_AVAILABLE->"LAN sẵn sàng"
            LanAuthorityPolicy.HealthState.LAN_ACTIVE->"LAN"
            LanAuthorityPolicy.HealthState.RECOVERING->"Đang phục hồi"
            LanAuthorityPolicy.HealthState.CLOUD_DR_ACTIVE->"Cloud DR"
        }
        if(serviceStatusText?.text?.toString()!=serviceLabel)serviceStatusText?.text=serviceLabel
    }
    private fun headerStatusChip(iconRes:Int,label:String,valueView:TextView,click:((View)->Unit)?=null)=row(Color.TRANSPARENT).apply{
        gravity=Gravity.CENTER_VERTICAL
        setPadding(dp(5),dp(3),dp(5),dp(3))
        background=round(Color.argb(32,255,255,255),12)
        isClickable=click!=null;isFocusable=click!=null
        if(click!=null)setOnClickListener{v->click(v)}
        addView(ImageView(this@OperationsActivity).apply{setImageResource(iconRes);imageTintList=ColorStateList.valueOf(Color.WHITE);setPadding(dp(1),dp(1),dp(1),dp(1))},size(dp(19),dp(19)))
        addView(column(Color.TRANSPARENT).apply{
            addView(txt(label,7f,Color.argb(210,255,255,255),false).apply{maxLines=1;setAutoSizeTextTypeUniformWithConfiguration(6,8,1,android.util.TypedValue.COMPLEX_UNIT_SP)})
            addView(valueView.apply{maxLines=1;setAutoSizeTextTypeUniformWithConfiguration(6,9,1,android.util.TypedValue.COMPLEX_UNIT_SP)})
        },LinearLayout.LayoutParams(0,-2,1f).apply{marginStart=dp(3)})
    }
    private fun appBar(title:String)=column(Color.TRANSPARENT).apply{
        setPadding(dp(12),dp(7),dp(12),dp(8));background=gradient(navy,accent,0)
        val statuses=row(Color.TRANSPARENT).apply{gravity=Gravity.CENTER}
        val net=txt("—",8.8f,Color.WHITE,true);networkStatusText=net
        val syn=txt("—",8.8f,Color.WHITE,true);syncStatusText=syn
        val svc=txt("—",8.8f,Color.WHITE,true);serviceStatusText=svc
        statuses.addView(headerStatusChip(R.drawable.ic_pp_network,"Mạng",net){showHeaderStatusDetail("NETWORK")},LinearLayout.LayoutParams(0,dp(38),1f).apply{marginEnd=dp(2)})
        statuses.addView(headerStatusChip(R.drawable.ic_pp_sync,"Đồng bộ",syn){showHeaderStatusDetail("SYNC")},LinearLayout.LayoutParams(0,dp(38),1f).apply{marginStart=dp(1);marginEnd=dp(1)})
        statuses.addView(headerStatusChip(R.drawable.ic_pp_service,"Dịch vụ",svc){showHeaderStatusDetail("SERVICE")},LinearLayout.LayoutParams(0,dp(38),1f).apply{marginStart=dp(2)})
        addView(statuses,matchWrap());refreshHeaderConnection()
    }
    private fun activeTab()=when(module){"STAFF"->"STAFF";"HISTORY"->"HISTORY";"SYNC"->"SYNC";"SETTINGS"->"SETTINGS";"ROLE_MODE"->"ROLE_MODE";else->"BUSINESS"}

    private fun bottomNav():LinearLayout=row(surface).apply{
        gravity=Gravity.CENTER;setPadding(dp(3),dp(5),dp(3),dp(5));background=outlineBg(surface,16);elevation=dp(8).toFloat();navRefs.clear()
        val items=mutableListOf(
            Triple(R.drawable.ic_pp_business,"Nghiệp vụ","BUSINESS"),
            Triple(R.drawable.ic_pp_staff,"Nhân sự","STAFF")
        )
        if(isAdmin())items.add(Triple(R.drawable.ic_pp_history,"Lịch sử","HISTORY"))
        items.add(Triple(R.drawable.ic_pp_settings,"Cài đặt","SETTINGS"))
        if(isActualSuper())items.add(Triple(R.drawable.ic_pp_account,"Quyền","ROLE_MODE"))
        items.forEach{item->
            val iconView=ImageView(this@OperationsActivity).apply{setImageResource(item.first);setPadding(dp(4),dp(4),dp(4),dp(2))}
            val labelView=txt(item.second,7.2f,muted,item.third==activeTab()).apply{gravity=Gravity.CENTER;maxLines=1;setAutoSizeTextTypeUniformWithConfiguration(6,9,1,android.util.TypedValue.COMPLEX_UNIT_SP)}
            val cell=column(Color.TRANSPARENT).apply{gravity=Gravity.CENTER;setPadding(dp(1),dp(2),dp(1),dp(2));addView(iconView,size(dp(30),dp(27)));addView(labelView);setOnClickListener{navigateTab(item.third)}}
            navRefs[item.third]=NavRefs(cell,iconView,labelView);addView(cell,LinearLayout.LayoutParams(0,-1,1f))
        };post{refreshBottomNav()}
    }

    private fun refreshBottomNav(){val active=activeTab();navRefs.forEach{(key,ref)->val chosen=key==active;ref.cell.background=if(chosen)round(ThemeManager.soft(this@OperationsActivity),10)else null;ref.icon.imageTintList=ColorStateList.valueOf(if(chosen)teal else muted);ref.label.setTextColor(if(chosen)teal else muted);ref.label.typeface=if(chosen)Typeface.DEFAULT_BOLD else Typeface.DEFAULT}}
    private fun navigateTab(target:String,remember:Boolean=true){
        if(target=="HISTORY"&&!isAdmin()){module="BUSINESS";businessHome();return}
        val current=activeTab()
        if(target==current&&isRootScreen())return
        if(remember&&target!=current)tabHistory.addLast(current)
        module=target;initialMnv="";liveEmployeeMnv=""
        when(target){
            "BUSINESS"->businessHome()
            "STAFF"->staffScreen()
            "HISTORY"->historyScreen()
            "SYNC"->syncScreen()
            "SETTINGS"->settingsScreen()
            "ROLE_MODE"->if(isActualSuper())roleModeScreen() else businessHome()
        }
    }

    private fun roleModeScreen(){
        if(!isActualSuper()){module="BUSINESS";businessHome();return}
        module="ROLE_MODE";screenState="ROLE_MODE"
        val root=baseRoot("CHẾ ĐỘ QUYỀN");val body=body()
        body.addView(section("Quyền giao diện đang áp dụng"))
        body.addView(info("Đang hiển thị ứng dụng theo quyền: ${roleText(effectiveRole)}"))
        body.addView(gap(9))
        body.addView(primary("ÁP QUYỀN USER",teal){effectiveRole="USER";TopNotice.show(this,"Đã chuyển giao diện sang quyền USER.",TopNotice.Kind.SUCCESS);navigateTab("BUSINESS")},matchWrap())
        body.addView(gap(8))
        body.addView(primary("ÁP QUYỀN ADMIN",blue){effectiveRole="ADMIN";TopNotice.show(this,"Đã chuyển giao diện sang quyền ADMIN.",TopNotice.Kind.SUCCESS);navigateTab("BUSINESS")},matchWrap())
        body.addView(gap(8))
        body.addView(primary("QUAY VỀ QUYỀN SUPERADMIN",navy){effectiveRole="SUPERADMIN";TopNotice.show(this,"Đã quay về quyền SUPERADMIN.",TopNotice.Kind.SUCCESS);navigateTab("BUSINESS")},matchWrap())
        attach(root,body)
    }

    private fun sessionExpired(){
        api.clearSession()
        AlertDialog.Builder(this).setTitle("Phiên đăng nhập đã thay đổi").setMessage("Vui lòng đăng nhập lại để tiếp tục.").setCancelable(false).setPositiveButton("ĐĂNG NHẬP"){_,_->finishAffinity()}.show()
    }

    private fun handleAuth(r:BetaApiClient.Result):Boolean{if(r.code==401){api.clearSession();AlertDialog.Builder(this).setTitle("Phiên đăng nhập đã được thay thế").setMessage("Tài khoản đã đăng nhập ở thiết bị khác hoặc quyền tài khoản đã thay đổi.").setCancelable(false).setPositiveButton("OK"){_,_->finishAffinity()}.show();return true};return false}
    private fun showError(raw:String){val msg=when{
raw.contains("EXCLUSIVE_RESOURCE_CONFLICT")->"Tài nguyên vừa bị phiên hoặc máy khác giữ / dùng trước. Bản ghi này không tự gửi lại để tránh cấp trùng. Hãy bấm đồng bộ, quét lại nhân sự và chọn tài nguyên còn trống.";
raw.contains("ATTENDANCE_NOT_ACTIVE")||raw.contains("SESSION_NOT_ACTIVE")->"Không còn phiên đang hoạt động để ra ca. Hãy quét lại nhân sự và đồng bộ trạng thái.";
raw.contains("SESSION_ACTIVE_AMBIGUOUS")->"Có nhiều phiên đang hoạt động cho cùng nhân sự. Không tự chọn phiên để tránh ghi sai dữ liệu.";
raw.contains("SESSION_EMPLOYEE_MISMATCH")->"Phiên đang mở không khớp mã nhân viên. Hãy quét lại nhân sự.";
raw.contains("SESSION_EXIT_FIELDS_REQUIRED")->"Chưa xác định được đúng phiên ACTIVE để ra ca. Ứng dụng đã chặn gửi yêu cầu thiếu dữ liệu; hãy đồng bộ rồi quét lại nhân sự.";
raw.contains("SESSION_EXIT_RESOLVE_FAILED")->"Chưa xác nhận được phiên ACTIVE từ Service. Hãy kiểm tra mạng, đồng bộ rồi quét lại nhân sự.";
raw.contains("OPEN_LABOR_BLOCKS_EXIT")->"Nhân sự còn công nhật chưa hoàn thành. Hoàn thành công nhật trước khi ra ca.";
raw.contains("PDA_EXIT_STATUS_REQUIRED")->"Cần chọn tình trạng PDA hiện tại trước khi ra ca.";
raw.contains("PDA_STATUS_MISMATCH_NOTIFY_SPECIALIST")->"Tình trạng PDA hiện tại khác lúc nhận. Báo chuyên viên phụ trách trước khi ra ca.";
raw.contains("STALE_BASE_VERSION")->"Dữ liệu phiên vừa thay đổi trên thiết bị khác. Ứng dụng sẽ đồng bộ lại; hãy quét lại nhân sự.";
raw.contains("TEST_CLOUDFLARE_DISABLED")->"Cloudflare đang được tắt bằng chế độ thử nghiệm lỗi service.";
raw.contains("TEST_GOOGLE_DISABLED")->"Google Drive đang được tắt bằng chế độ thử nghiệm lỗi service.";
raw.contains("SERVICE_NOT_WRITE_AUTHORITY")->"Dịch vụ hiện tại không có quyền ghi dữ liệu.";
raw.contains("PDA_IN_USE")->"PDA này đang được một phiên khác giữ. Hãy đồng bộ lại và chọn PDA khác.";
raw.contains("USER_PICK_IN_USE")->"User Pick này đang được phiên khác giữ. Hãy chọn User Pick khác.";
raw.contains("USER_PACK_IN_USE")->"User Pack này đang được phiên khác giữ. Hãy chọn User Pack khác.";
raw.contains("PACK_TABLE_IN_USE")->"Bàn Pack này đang được phiên khác giữ. Hãy chọn bàn khác.";
raw.contains("USER_PICK_ALREADY_USED_TODAY")->"User Pick này đã dùng hôm nay. Nếu hiện đã rảnh, dùng nút Phát lại user pick.";
raw.contains("USER_PACK_ALREADY_USED_TODAY")->"User Pack này đã dùng hôm nay. Nếu hiện đã rảnh, dùng nút Phát lại user pack.";
raw.contains("PACK_MAPPING_INVALID")->"Bàn Pack và User Pack không còn khớp cấu hình hiện tại. Hãy đồng bộ và chọn lại.";
raw.contains("OPEN_LABOR_BLOCKS_EXIT")->"Còn công nhật đang làm. Hoàn thành công nhật trước khi ra ca.";
raw.contains("PDA_EXIT_STATUS_REQUIRED")->"Cần chọn tình trạng PDA hiện tại trước khi ra ca.";
raw.contains("SESSION_NOT_FOUND")->"Phiên trên PDA chưa khớp phiên Service. Bấm đồng bộ rồi quét lại nhân sự.";
raw.contains("SESSION_NOT_ACTIVE")->"Phiên này không còn ACTIVE trên Service. Bấm đồng bộ rồi quét lại nhân sự.";
raw.contains("SESSION_WORK_CONFLICT")->"Phiên vừa thay đổi trên máy khác. Dữ liệu cũ không bị ghi đè; hãy đồng bộ rồi sửa lại.";
raw.contains("SESSION_EXIT_CONFLICT")->"Phiên vừa thay đổi trên máy khác nên chưa thể ra ca. Hãy đồng bộ rồi quét lại.";
raw.contains("SERVICE_DISCOVERY_UNAVAILABLE")->"Chưa lấy được địa chỉ Service. Kiểm tra mạng rồi bấm đồng bộ lại.";
raw.contains("SERVICE_NOT_WRITE_AUTHORITY")->"Service hiện chưa ở quyền ghi chính. Hãy đồng bộ lại trước khi thao tác.";
raw.contains("SUPERADMIN_REQUIRED")->"Thao tác này hiện yêu cầu quyền Superadmin trên Service.";
raw.contains("CORRECTION_TARGET_NOT_FOUND")->"Không tìm thấy bản ghi gốc cần sửa trên Service. Hãy đồng bộ lịch sử rồi mở lại.";
raw.contains("CORRECTION_CONFLICT")->"Bản ghi vừa thay đổi trên máy khác. Hãy đồng bộ rồi sửa lại.";
raw.isBlank()||raw.equals("UNKNOWN",true)->"Service chưa trả mã lỗi cụ thể. Hãy bấm đồng bộ và thử lại; nếu còn lỗi hãy gửi log.";
raw.contains("PDA_STATUS_MISMATCH_NOTIFY_SPECIALIST")->"Tình trạng PDA hiện tại không khớp lúc vào ca. Không thể RA CA. Phải thông báo cho Chuyên viên sự việc.";raw.contains("PDA_ENTRY_STATUS_MISSING_NOTIFY_SPECIALIST")->"Không xác định được tình trạng PDA lúc vào ca. Không thể RA CA. Phải thông báo cho Chuyên viên sự việc.";raw.contains("PDA_ENTRY_STATUS_STALE")->"Tình trạng PDA vừa thay đổi trên hệ thống. Chọn lại PDA trước khi VÀO CA.";raw.contains("DUPLICATE_USER_OVERRIDE_NOT_REQUIRED")->"User này hiện không thuộc nhóm đang dùng/đã dùng; hãy chọn từ danh sách thường.";raw.contains("PP_RESOURCE_CONFLICT")->"Tài nguyên vừa được người khác nhận. Tài nguyên cũ vẫn được giữ.";raw.contains("PP_USER_PICK_USED_TODAY")->"User Pick này đã được dùng trong ngày.";raw.contains("PP_USER_PACK_USED_TODAY")->"User Pack này đã được dùng trong ngày.";raw.contains("PP_LABOR_ALREADY_ACTIVE")->"Mã nhân viên đang có công nhật chưa hoàn thành.";raw.contains("PP_LABOR_NOT_ACTIVE")->"Mã nhân viên không có công nhật đang hoạt động.";raw.contains("CURRENT_PASSWORD_INVALID")->"Mật khẩu hiện tại không đúng.";raw.contains("PASSWORD_POLICY")->"Mật khẩu mới phải có ít nhất 8 ký tự.";raw.contains("EMAIL_INVALID")->"Địa chỉ mail không hợp lệ.";raw.contains("EMPLOYEE_NOT_FOUND")->"Không tìm thấy nhân sự.";raw.contains("STAFF_ACTIVE_SESSION")->"Nhân sự đang có phiên ACTIVE, chưa thể xóa.";raw.contains("FORBIDDEN")->"Tài khoản không có quyền thực hiện thao tác này.";else->raw};TopNotice.show(this,msg,TopNotice.Kind.ERROR)}

    private fun iconBubble(res:Int,color:Int)=FrameLayout(this).apply{
        background=round(ThemeManager.soft(this@OperationsActivity),14)
        addView(ImageView(this@OperationsActivity).apply{setImageResource(res);imageTintList=ColorStateList.valueOf(color);setPadding(dp(9),dp(9),dp(9),dp(9))},FrameLayout.LayoutParams(-1,-1))
    }
    private fun businessIconBubble(res:Int):FrameLayout{
        val colors=when(res){
            R.drawable.ic_pp_scan->intArrayOf(teal,accent)
            R.drawable.ic_pp_pda_exchange->intArrayOf(Color.rgb(2,132,199),Color.rgb(14,165,233))
            R.drawable.ic_pp_drop_receive->intArrayOf(Color.rgb(234,88,12),Color.rgb(249,115,22))
            R.drawable.ic_pp_report->intArrayOf(Color.rgb(124,58,237),Color.rgb(168,85,247))
            R.drawable.ic_pp_task->intArrayOf(Color.rgb(37,99,235),Color.rgb(14,165,233))
            R.drawable.ic_pp_resource->intArrayOf(Color.rgb(5,150,105),Color.rgb(16,185,129))
            R.drawable.ic_pp_ccdc->intArrayOf(Color.rgb(71,85,105),Color.rgb(100,116,139))
            R.drawable.ic_pp_document->intArrayOf(Color.rgb(79,70,229),Color.rgb(99,102,241))
            else->intArrayOf(Color.rgb(6,182,212),Color.rgb(14,165,233))
        }
        return FrameLayout(this).apply{
            background=GradientDrawable(GradientDrawable.Orientation.TL_BR,colors).apply{shape=GradientDrawable.OVAL}
            elevation=dp(5).toFloat()
            addView(ImageView(this@OperationsActivity).apply{setImageResource(res);imageTintList=ColorStateList.valueOf(Color.WHITE);setPadding(dp(13),dp(13),dp(13),dp(13))},FrameLayout.LayoutParams(-1,-1))
        }
    }
    private fun businessCard(iconRes:Int,title:String,sub:String,enabled:Boolean=true,click:()->Unit)=column(surface).apply{
        gravity=Gravity.CENTER
        setPadding(dp(8),dp(6),dp(8),dp(6))
        background=outlineBg(surface,18)
        elevation=if(enabled)dp(5).toFloat() else 0f
        alpha=if(enabled)1f else .38f
        isEnabled=enabled
        addView(businessIconBubble(iconRes),size(dp(48),dp(48)))
        addView(gap(6))
        addView(txt(title,13.1f,ink,true).apply{gravity=Gravity.CENTER;maxLines=2;ellipsize=android.text.TextUtils.TruncateAt.END})
        addView(gap(3))
        addView(View(this@OperationsActivity).apply{background=round(teal,2)},size(dp(26),dp(3)))
        if(sub.isNotBlank()){addView(gap(6));addView(txt(sub,9.8f,muted,false).apply{gravity=Gravity.CENTER;maxLines=3;ellipsize=android.text.TextUtils.TruncateAt.END;setAutoSizeTextTypeUniformWithConfiguration(8,10,1,android.util.TypedValue.COMPLEX_UNIT_SP)},matchWrap())}
        if(enabled)setOnClickListener{tapFeedback(this);click()} else setOnClickListener(null)
    }

    private fun businessRow(a:View,b:View)=row(bg).apply{
        addView(a,LinearLayout.LayoutParams(0,dp(112),1f).apply{marginEnd=dp(3)})
        addView(b,LinearLayout.LayoutParams(0,dp(112),1f).apply{marginStart=dp(3)})
    }
    private fun businessSingleRow(a:View)=row(bg).apply{
        addView(a,LinearLayout.LayoutParams(0,dp(112),1f).apply{marginEnd=dp(3)})
        addView(Space(this@OperationsActivity),LinearLayout.LayoutParams(0,dp(112),1f).apply{marginStart=dp(3)})
    }

    private fun tapFeedback(v:View){
        v.animate().cancel();v.animate().scaleX(.96f).scaleY(.96f).translationY(-dp(1).toFloat()).setDuration(70L).withEndAction{
            v.animate().scaleX(1f).scaleY(1f).translationY(0f).setDuration(90L).start()
        }.start()
    }
    private fun iconActionButton(res:Int,color:Int,desc:String,click:()->Unit)=FrameLayout(this).apply{
        contentDescription=desc
        background=round(ThemeManager.soft(this@OperationsActivity),10)
        setOnClickListener{tapFeedback(this);click()}
        addView(ImageView(this@OperationsActivity).apply{setImageResource(res);imageTintList=ColorStateList.valueOf(color);setPadding(dp(8),dp(8),dp(8),dp(8))},FrameLayout.LayoutParams(-1,-1))
    }

    private fun employeeCard(e:JSONObject,state:String="")=column(surface).apply{
        val fill=when(state.uppercase()){"ACTIVE"->Color.rgb(255,249,214);"ENDED"->Color.rgb(231,247,237);else->surface}
        setPadding(dp(10),dp(8),dp(10),dp(8))
        background=GradientDrawable().apply{setColor(fill);cornerRadius=dp(11).toFloat();setStroke(dp(1),if(state.equals("ACTIVE",true))Color.rgb(217,165,32) else if(state.equals("ENDED",true))Color.rgb(54,142,91) else line)}
        addView(txt("${dash(e.optString("mnv"))} • ${dash(e.optString("full_name"))}",13.2f,navy,true).apply{maxLines=2})
        addView(txt("${dash(e.optString("main_position"))} • ${dash(e.optString("supplier"))}",9.6f,ink,false).apply{maxLines=2})
        addView(txt("SĐT: ${dash(e.optString("phone"))} • Bắt đầu: ${dash(e.optString("start_date"))}",9.5f,teal,true).apply{maxLines=2})
        addView(txt("${dash(e.optString("department"))} • Site ${dash(e.optString("site"))} • Kho ${dash(e.optString("warehouse"))}",9.1f,muted,false).apply{maxLines=3})
    }
    private fun listCard(title:String,sub:String)=column(surface).apply{setPadding(dp(10),dp(7),dp(10),dp(7));background=outlineBg(surface,10);addView(txt(title,11.6f,ink,true));addView(gap(1));addView(txt(sub,9.3f,muted,false))}
    private fun metric(title:String,value:String,color:Int)=txt("$title: $value",10.2f,color,true).apply{gravity=Gravity.CENTER;setPadding(dp(6),dp(8),dp(6),dp(8));background=outlineBg(surface,10)}
    private fun jsonMapCard(title:String,j:JSONObject?)=column(surface).apply{setPadding(dp(14),dp(11),dp(14),dp(11));background=outlineBg(surface,14);addView(txt(title,11f,navy,true));if(j==null||j.length()==0)addView(txt("Chưa có dữ liệu",10f,muted,false))else{val keys=j.keys();while(keys.hasNext()){val k=keys.next();addView(txt("$k: ${j.optInt(k)}",10.5f,ink,false))}}}
    private fun details(items:List<Pair<String,String>>)=column(surface).apply{setPadding(dp(9),dp(6),dp(9),dp(6));background=outlineBg(surface,10);items.forEach{(k,raw)->val v=dash(raw);val longValue=v.length>26||v.contains(", ")||v.contains(" & ");if(longValue)addView(column(surface).apply{setPadding(0,dp(3),0,dp(3));addView(txt(k,9.3f,muted,false));addView(txt(v,10f,ink,true).apply{maxLines=8;ellipsize=null})})else addView(row(surface).apply{addView(txt(k,9.5f,muted,false),LinearLayout.LayoutParams(0,-2,.42f));addView(txt(v,9.7f,ink,true).apply{gravity=Gravity.END;maxLines=3},LinearLayout.LayoutParams(0,-2,.58f));setPadding(0,dp(2),0,dp(2))})}}
    private fun section(v:String)=row(bg).apply{
        gravity=Gravity.CENTER_VERTICAL;setPadding(0,dp(8),0,dp(3))
        addView(ImageView(this@OperationsActivity).apply{setImageResource(sectionIconRes(v));imageTintList=ColorStateList.valueOf(teal)},size(dp(20),dp(20)))
        addView(txt(v,12.2f,navy,true),LinearLayout.LayoutParams(-2,-2).apply{marginStart=dp(5)})
    }
    private fun sectionIconRes(v:String)=when{
        v.contains("Tài khoản",true)->R.drawable.ic_pp_account
        v.contains("Giao diện",true)->R.drawable.ic_pp_palette
        v.contains("Đồng bộ",true)->R.drawable.ic_pp_sync
        v.contains("Cập nhật",true)->R.drawable.ic_pp_update
        v.contains("Nhật ký",true)->R.drawable.ic_pp_log
        v.contains("Thiết bị",true)->R.drawable.ic_pp_device
        v.contains("Ứng dụng",true)->R.drawable.ic_pp_device
        v.contains("Google Sheet",true)->R.drawable.ic_pp_sync
        v.contains("Service",true)->R.drawable.ic_pp_service
        v.contains("PDA",true)->R.drawable.ic_pp_device
        else->R.drawable.ic_pp_task
    }
    private fun status(v:String,fg:Int,c:Int)=txt(v,11.3f,fg,true).apply{gravity=Gravity.CENTER;setPadding(dp(10),dp(10),dp(10),dp(10));background=round(c,12)}
    private fun info(v:String)=txt(v,9.6f,muted,false).apply{setPadding(dp(10),dp(7),dp(10),dp(7));background=outlineBg(ThemeManager.soft(this@OperationsActivity),10)}
    private fun scanField(h:String,numeric:Boolean,heightDp:Int)=input(h,false).apply{
        if(numeric){
            inputType=InputType.TYPE_CLASS_NUMBER
            keyListener=DigitsKeyListener.getInstance("0123456789")
            imeOptions=EditorInfo.IME_ACTION_DONE
        }else{
            inputType=InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_FLAG_MULTI_LINE
            imeOptions=EditorInfo.IME_ACTION_SEARCH
        }
        setSingleLine(false)
        minLines=2
        maxLines=2
        setHorizontallyScrolling(false)
        gravity=Gravity.CENTER_VERTICAL
        minHeight=dp(heightDp)
        maxHeight=dp(heightDp)
        textSize=12.4f
        setHintTextColor(Color.rgb(100,116,139))
        setPadding(dp(12),dp(7),dp(12),dp(7))
        setCompoundDrawablesWithIntrinsicBounds(R.drawable.ic_pp_scan,0,0,0)
        compoundDrawableTintList=ColorStateList.valueOf(teal)
        compoundDrawablePadding=dp(9)
        background=GradientDrawable().apply{
            setColor(ThemeManager.soft(this@OperationsActivity))
            setStroke(dp(1),teal)
            cornerRadius=dp(14).toFloat()
        }
        elevation=0f
    }
    private fun mnvInput(h:String)=scanField(h,true,50).apply{
        setSingleLine(true);minLines=1;maxLines=1;setHorizontallyScrolling(true)
        textSize=13.6f;typeface=Typeface.DEFAULT_BOLD
        setHintTextColor(Color.rgb(51,65,85))
        background=GradientDrawable().apply{
            setColor(surface);setStroke(dp(2),teal);cornerRadius=dp(12).toFloat()
        }
        elevation=dp(1).toFloat()
    }
    private fun scanSearchInput(h:String)=scanField(h,false,72)
    private fun bindScannerEnter(v:EditText,submit:()->Unit){v.setOnEditorActionListener{_,id,_->if(id==EditorInfo.IME_ACTION_DONE||id==EditorInfo.IME_ACTION_GO||id==EditorInfo.IME_ACTION_SEARCH){submit();true}else false};v.setOnKeyListener{_,key,event->if(key==KeyEvent.KEYCODE_ENTER&&event.action==KeyEvent.ACTION_UP){submit();true}else false}}
    private fun segmentedChoice(items:List<Pair<String,String>>,initial:String,onChanged:(String)->Unit):LinearLayout{
        val host=row(bg);val buttons=mutableListOf<Button>();var selected=initial
        fun paint(){buttons.forEachIndexed{i,b->val on=items[i].second==selected;b.setTextColor(if(on)Color.WHITE else navy);b.background=if(on)gradient(teal,darken(teal),12) else outlineBg(surface,12);b.elevation=if(on)dp(2).toFloat() else 0f}}
        items.forEachIndexed{i,item->val b=Button(this).apply{text=item.first;textSize=10.5f;isAllCaps=false;typeface=Typeface.DEFAULT_BOLD;minHeight=dp(46);setPadding(dp(3),0,dp(3),0);setOnClickListener{selected=item.second;paint();onChanged(selected)}};buttons.add(b);host.addView(b,LinearLayout.LayoutParams(0,dp(46),1f).apply{if(i>0)marginStart=dp(3);if(i<items.lastIndex)marginEnd=dp(3)})};paint();return host
    }
    private fun resolvePdaObject(pdas:JSONArray,rawValue:String):JSONObject?{
        val raw=rawValue.trim();val candidate=raw.substringBefore(" • ").trim();val hits=mutableListOf<JSONObject>();for(i in 0 until pdas.length()){val p=pdas.optJSONObject(i)?:continue;val serial=p.optString("serial").trim();val last5=p.optString("last5").trim().ifBlank{serial.takeLast(5)};if(serial.isBlank())continue;if(candidate==serial||candidate==last5||(raw.contains(serial)&&raw.contains("Tình trạng:")))hits.add(p)};return hits.distinctBy{it.optString("serial")}.singleOrNull()
    }
    private fun pdaSelectedPanel(pdas:JSONArray,field:AutoCompleteTextView):TextView{
        val panel=txt("Serial PDA\nChưa chọn\nTình trạng PDA\n—",11.2f,navy,false).apply{setPadding(dp(10),dp(8),dp(10),dp(8));background=ColorDrawable(Color.rgb(239,246,255))}
        fun update(){val p=(field.tag as? JSONObject)?:resolvePdaObject(pdas,field.text?.toString().orEmpty());val serial=p?.optString("serial").orEmpty();val status=p?.optString("status").orEmpty();val full="Serial PDA\n${serial.ifBlank{"Chưa chọn"}}\nTình trạng PDA\n${status.ifBlank{"—"}}";val styled=android.text.SpannableStringBuilder(full);val a=full.indexOf('\n')+1;val b=full.indexOf('\n',a);val c=full.lastIndexOf('\n')+1;if(b>a){styled.setSpan(android.text.style.StyleSpan(Typeface.BOLD),a,b,android.text.Spanned.SPAN_EXCLUSIVE_EXCLUSIVE);styled.setSpan(android.text.style.RelativeSizeSpan(1.18f),a,b,android.text.Spanned.SPAN_EXCLUSIVE_EXCLUSIVE)};if(c<full.length)styled.setSpan(android.text.style.StyleSpan(Typeface.BOLD),c,full.length,android.text.Spanned.SPAN_EXCLUSIVE_EXCLUSIVE);panel.text=styled;panel.setTextColor(if(serial.isBlank())muted else navy)}
        field.addTextChangedListener(object:TextWatcher{override fun beforeTextChanged(v:CharSequence?,start:Int,count:Int,after:Int)=Unit;override fun onTextChanged(v:CharSequence?,start:Int,before:Int,count:Int)=update();override fun afterTextChanged(v:Editable?)=Unit});update();return panel
    }
    private fun naturalUserCompare(aRaw:String,bRaw:String):Int{
        val a=aRaw.trim();val b=bRaw.trim();val rx=Regex("^(.*?)(\\d+)$")
        val am=rx.matchEntire(a);val bm=rx.matchEntire(b)
        if(am!=null&&bm!=null){
            val ap=am.groupValues[1].lowercase();val bp=bm.groupValues[1].lowercase();val prefix=ap.compareTo(bp)
            if(prefix!=0)return prefix
            val an=am.groupValues[2].toLongOrNull();val bn=bm.groupValues[2].toLongOrNull()
            if(an!=null&&bn!=null&&an!=bn)return an.compareTo(bn)
        }
        return a.compareTo(b,ignoreCase=true)
    }
    private fun <T> sortedByNaturalUser(items:List<T>,value:(T)->String):List<T> = items.sortedWith(Comparator{a,b->naturalUserCompare(value(a),value(b))})

    private fun showReissueChooser(title:String,labels:List<String>,onSelected:(Int)->Unit){
        if(labels.isEmpty()){showError("Không có user đã dùng có thể phát lại.");return}
        AlertDialog.Builder(this).setTitle(title).setItems(labels.toTypedArray()){_,which->if(which in labels.indices)onSelected(which)}.setNegativeButton("Hủy",null).show()
    }

    private fun compactReissueButton(label:String,enabled:Boolean,onClick:()->Unit)=smallButton(label,orange).apply{
        isAllCaps=false;textSize=8.6f;setSingleLine(true);setPadding(dp(3),0,dp(3),0);isEnabled=enabled;alpha=if(enabled)1f else .45f;setOnClickListener{if(isEnabled)onClick()}
    }

    private fun pdaInput(pdas:JSONArray,currentSerial:String="",onSelected:(JSONObject?)->Unit={}):AutoCompleteTextView{
        val labels=mutableListOf<String>()
        for(i in 0 until pdas.length()){
            val p=pdas.optJSONObject(i)?:continue
            val serial=p.optString("serial").trim()
            val last5=p.optString("last5").trim().ifBlank{serial.takeLast(5)}
            val status=p.optString("status").trim()
            if(serial.isNotBlank()&&last5.isNotBlank())labels.add("$last5 • $serial • Tình trạng: ${status.ifBlank{"—"}}")
        }
        val field=AutoCompleteTextView(this);var selectedLast5="";var internal=false
        field.hint="Gõ 5 số cuối Seri PDA";field.threshold=1;field.textSize=13f;field.setTextColor(navy);field.typeface=Typeface.DEFAULT_BOLD;field.setHintTextColor(Color.rgb(100,116,139));field.inputType=InputType.TYPE_CLASS_TEXT;field.setPadding(dp(13),dp(10),dp(13),dp(10));field.minHeight=dp(50);field.background=outline()
        field.setAdapter(object:ArrayAdapter<String>(this,android.R.layout.simple_dropdown_item_1line,labels){
            override fun getView(position:Int,convertView:View?,parent:ViewGroup):View{
                val v=super.getView(position,convertView,parent) as TextView
                v.textSize=12.5f;v.setTextColor(ink);v.typeface=Typeface.DEFAULT;v.minHeight=dp(46);v.setPadding(dp(14),dp(7),dp(14),dp(7));return v
            }
        })
        field.setOnItemClickListener{parent,_,pos,_->val label=parent.getItemAtPosition(pos).toString();val p=resolvePdaObject(pdas,label);if(p!=null){selectedLast5=p.optString("last5").trim().ifBlank{p.optString("serial").takeLast(5)};internal=true;field.setText(selectedLast5,false);field.setSelection(field.text.length);field.tag=JSONObject(p.toString());internal=false;onSelected(JSONObject(p.toString()))}}
        field.addTextChangedListener(object:TextWatcher{override fun beforeTextChanged(s:CharSequence?,st:Int,c:Int,a:Int)=Unit;override fun onTextChanged(s:CharSequence?,st:Int,b:Int,c:Int)=Unit;override fun afterTextChanged(e:Editable?){if(!internal&&selectedLast5.isNotBlank()&&e?.toString()?.trim()!=selectedLast5){selectedLast5="";field.tag=null;onSelected(null)}}})
        field.setOnClickListener{field.showDropDown()}
        if(currentSerial.isNotBlank()){for(i in 0 until pdas.length()){val p=pdas.optJSONObject(i)?:continue;if(p.optString("serial")==currentSerial){selectedLast5=p.optString("last5").trim().ifBlank{currentSerial.takeLast(5)};internal=true;field.setText(selectedLast5,false);field.tag=JSONObject(p.toString());internal=false;onSelected(JSONObject(p.toString()));break}}}
        return field
    }
    private fun resolvePda(pdas:JSONArray,rawValue:String):String?=resolvePdaObject(pdas,rawValue)?.optString("serial")?.takeIf{it.isNotBlank()}
    private fun input(h:String,password:Boolean)=EditText(this).apply{hint=h;textSize=13.0f;setTextColor(ink);setHintTextColor(Color.rgb(148,163,184));inputType=if(password)InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_VARIATION_PASSWORD else InputType.TYPE_CLASS_TEXT;setPadding(dp(11),dp(8),dp(11),dp(8));minHeight=dp(46);background=outline();elevation=0f}
    private fun labelled(l:String,v:View)=column(bg).apply{
        addView(txt(l.uppercase(),9.2f,muted,true).apply{letterSpacing=.025f;setPadding(dp(2),0,dp(2),0)})
        addView(gap(3));addView(v,matchWrap())
    }
    private fun spinner(items:Array<String>)=Spinner(this).apply{
        val values=items.toList()
        adapter=object:ArrayAdapter<String>(this@OperationsActivity,android.R.layout.simple_spinner_item,values){
            override fun getView(position:Int,convertView:View?,parent:ViewGroup):View{
                val v=super.getView(position,convertView,parent) as TextView
                v.textSize=13f;v.setTextColor(navy);v.typeface=Typeface.DEFAULT_BOLD;v.gravity=Gravity.CENTER_VERTICAL
                v.setPadding(dp(12),0,dp(34),0);return v
            }
            override fun getDropDownView(position:Int,convertView:View?,parent:ViewGroup):View{
                val v=super.getDropDownView(position,convertView,parent) as TextView
                v.textSize=12.5f;v.setTextColor(ink);v.typeface=Typeface.DEFAULT
                v.gravity=Gravity.CENTER_VERTICAL;v.minHeight=dp(46);v.setPadding(dp(14),dp(7),dp(14),dp(7))
                return v
            }
        }
        setPadding(0,0,0,0);minimumHeight=dp(46);background=outline();elevation=0f
    }
    private fun primary(t:String,c:Int,click:()->Unit)=Button(this).apply{text=t;textSize=11.5f;setTextColor(Color.WHITE);typeface=Typeface.DEFAULT_BOLD;isAllCaps=false;minHeight=dp(46);background=gradient(c,darken(c),12);elevation=0f;setOnClickListener{tapFeedback(this);click()}}
    private fun smallButton(t:String,c:Int)=Button(this).apply{text=t;textSize=9.5f;setTextColor(Color.WHITE);typeface=Typeface.DEFAULT_BOLD;isAllCaps=false;background=round(c,10);setPadding(dp(4),0,dp(4),0);setOnTouchListener{v,e->if(e.action==android.view.MotionEvent.ACTION_UP)tapFeedback(v);false}}
    private fun reconciliationButton(t:String,balanced:Boolean)=ReviewAlertUi.button(
        this,
        t,
        if(balanced)ReviewAlertUi.Tone.OK else ReviewAlertUi.Tone.WARNING
    )
    private fun host(content:View):View{
        val root=EdgeSwipeBackLayout(this){handleBackNavigation()}.apply{setBackgroundColor(bg)}
        val contentFrame=FrameLayout(this).apply{addView(content,FrameLayout.LayoutParams(-1,-1))}
        val navFrame=FrameLayout(this).apply{setPadding(dp(8),0,dp(8),0);addView(bottomNav(),FrameLayout.LayoutParams(-1,-1))}
        contentHost=contentFrame;navHost=navFrame
        root.addView(contentFrame,FrameLayout.LayoutParams(-1,-1).apply{bottomMargin=dp(86)})
        root.addView(navFrame,FrameLayout.LayoutParams(-1,dp(62),Gravity.BOTTOM).apply{bottomMargin=dp(20)})
        root.addView(txt(FOOTER,7.2f,Color.rgb(113,122,136),false).apply{gravity=Gravity.CENTER;maxLines=1},FrameLayout.LayoutParams(-1,dp(18),Gravity.BOTTOM))
        root.setOnApplyWindowInsetsListener{v,i->val top:Int;val bottom:Int;if(Build.VERSION.SDK_INT>=30){top=i.getInsets(WindowInsets.Type.statusBars()).top;bottom=i.getInsets(WindowInsets.Type.navigationBars()).bottom}else{@Suppress("DEPRECATION")val tt=i.systemWindowInsetTop;@Suppress("DEPRECATION")val bb=i.systemWindowInsetBottom;top=tt;bottom=bb};v.setPadding(0,top+dp(2),0,bottom+dp(1));i}
        root.requestApplyInsets();return root
    }
    private fun jsonStrings(a:JSONArray?):MutableList<String>{val out=mutableListOf<String>();if(a!=null)for(i in 0 until a.length()){val v=a.optString(i);if(v.isNotBlank())out.add(v)};return out}
    private fun catalogValues(key:String,fallback:List<String> = emptyList()):MutableList<String>{
        val fields=MasterDataCache.snapshot(this)?.optJSONObject("catalog_fields")
        var arr=fields?.optJSONArray(key)
        if(arr==null && fields!=null){val keys=fields.keys();while(keys.hasNext()){val k=keys.next();if(foldLocal(k)==foldLocal(key)){arr=fields.optJSONArray(k);break}}}
        val out=jsonStrings(arr)
        if(out.isEmpty())fallback.filter{it.isNotBlank()}.forEach{if(!out.contains(it))out.add(it)}
        return out
    }
    private fun catalogSpinner(key:String,current:String="",allowBlank:Boolean=false):Spinner{
        val values=catalogValues(key)
        if(allowBlank)values.add(0,"—")
        if(current.isNotBlank()&&!values.contains(current))values.add(current)
        if(values.isEmpty())values.add("Chưa cấu hình")
        return spinner(values.toTypedArray()).also{sp->selectByValue(sp,values,if(current.isBlank()&&allowBlank)"—" else current)}
    }
    private fun catalogSelection(sp:Spinner)=sp.selectedItem?.toString().orEmpty().let{if(it=="—")"" else it}
    private fun selectByValue(sp:Spinner,values:List<String>,target:String){val i=values.indexOf(target);if(i>=0)sp.setSelection(i)}
    private fun formatIso(v:String):String{if(v.isBlank()||v=="null")return "—";return try{Instant.parse(v).atZone(ZoneId.of("Asia/Ho_Chi_Minh")).format(DateTimeFormatter.ofPattern("HH:mm:ss dd/MM/yyyy"))}catch(_:Throwable){v}}
    private fun greeting():String{
        val hour=java.util.Calendar.getInstance().get(java.util.Calendar.HOUR_OF_DAY)
        return when(hour){in 5..10->"Chào buổi sáng";in 11..12->"Chào buổi trưa";in 13..17->"Chào buổi chiều";else->"Chào buổi tối"}
    }
    private fun normalizePhone(v:String):String{
        val digits=v.filter{it.isDigit()}
        return if(digits.length==9&&!digits.startsWith("0"))"0$digits" else digits
    }
    private fun historyIcon(action:String)=when(action){
        "enter","exit"->R.drawable.ic_pp_scan
        "labor_start","labor_finish"->R.drawable.ic_pp_task
        "resource_change"->R.drawable.ic_pp_resource
        "staff_upsert","staff_delete"->R.drawable.ic_pp_staff
        "change_password","change_email","account_upsert","account_status"->R.drawable.ic_pp_account
        "diagnostic_log"->R.drawable.ic_pp_log
        else->R.drawable.ic_pp_history
    }
    private fun historyFriendlyDetail(action:String,raw:String,ok:Boolean):String{
        if(ok)return when(action){
            "enter"->"Đã ghi nhận vào ca.";"exit"->"Đã ghi nhận ra ca.";"resource_change"->"Đã cập nhật tài nguyên."
            "labor_start"->"Đã bắt đầu công nhật.";"labor_finish"->"Đã hoàn thành công nhật."
            "staff_upsert"->"Đã lưu thông tin nhân sự.";"staff_delete"->"Đã xóa nhân sự.";"diagnostic_log"->"Đã gửi báo lỗi."
            "change_password"->"Đã đổi mật khẩu.";"change_email"->"Đã đổi mail.";"account_upsert"->"Đã cập nhật tài khoản.";"account_status"->"Đã đổi trạng thái tài khoản."
            else->"Đã hoàn tất thao tác."
        }
        val e=raw.uppercase()
        return when{
            e.contains("EXCLUSIVE_RESOURCE_CONFLICT")->"Tài nguyên vừa bị phiên hoặc máy khác giữ / dùng trước. Bản ghi cũ được dừng để tránh cấp trùng; hãy đồng bộ lại rồi tạo thao tác mới với tài nguyên còn trống."
            e.contains("RESOURCE_CONFLICT")->"Tài nguyên vừa được người khác nhận. Hãy chọn tài nguyên khác."
            e.contains("USER_PICK_USED_TODAY")->"User Pick này đã được sử dụng trong ngày."
            e.contains("USER_PACK_USED_TODAY")->"User Pack này đã được sử dụng trong ngày."
            e.contains("LABOR_ALREADY_ACTIVE")->"Nhân sự đang có công nhật chưa hoàn thành."
            e.contains("UNAUTHORIZED")->"Phiên đăng nhập đã thay đổi. Vui lòng đăng nhập lại."
            e.contains("FORBIDDEN")->"Tài khoản không có quyền thực hiện thao tác này."
            e.contains("EMPLOYEE_NOT_FOUND")->"Không tìm thấy nhân sự."
            raw.isBlank()->"Thao tác chưa hoàn tất. Vui lòng thử lại."
            else->"Thao tác chưa hoàn tất. Kiểm tra kết nối hoặc dữ liệu rồi thử lại."
        }
    }
    private fun roleText(v:String)=when(v){"SUPERADMIN"->"Superadmin";"ADMIN"->"Admin";"USER"->"Điều phối";else->v}
    private fun workText(v:String)=when(v){"PICK"->"Pick";"PACK"->"Pack";else->"Không"}
    private fun foldLocal(v:String)=java.text.Normalizer.normalize(v,java.text.Normalizer.Form.NFD).replace(Regex("\\p{Mn}+"),"").uppercase().trim()

    private fun appCacheBytes():Long{
        fun sizeOf(f:java.io.File?):Long{if(f==null||!f.exists())return 0L;if(f.isFile)return f.length();return f.listFiles()?.sumOf{sizeOf(it)}?:0L}
        return sizeOf(cacheDir)+runCatching{sizeOf(codeCacheDir)}.getOrDefault(0L)
    }

    private data class AppStorageUsage(val userDataBytes:Long,val cacheBytes:Long)
    private fun directoryBytes(root:java.io.File?):Long{
        if(root==null||!root.exists())return 0L
        if(root.isFile)return root.length().coerceAtLeast(0L)
        return runCatching{root.listFiles()?.sumOf{directoryBytes(it)}?:0L}.getOrDefault(0L)
    }
    private fun appBinaryBytes():Long{
        val paths=mutableListOf<String>();paths.add(applicationInfo.sourceDir);applicationInfo.splitSourceDirs?.let{paths.addAll(it)}
        return paths.distinct().sumOf{runCatching{java.io.File(it).length()}.getOrDefault(0L)}
    }
    private fun appStorageUsage():AppStorageUsage{
        val cacheRoots=listOf(cacheDir,codeCacheDir).distinctBy{it.absolutePath}
        val cache=cacheRoots.sumOf{directoryBytes(it)}
        val total=directoryBytes(runCatching{java.io.File(applicationInfo.dataDir)}.getOrNull())
        return AppStorageUsage((total-cache).coerceAtLeast(0L),cache.coerceAtLeast(0L))
    }
    private fun humanBytes(bytes:Long):String=when{bytes<1024L->"$bytes B";bytes<1024L*1024L->String.format(java.util.Locale.US,"%.1f KB",bytes/1024.0);bytes<1024L*1024L*1024L->String.format(java.util.Locale.US,"%.1f MB",bytes/(1024.0*1024.0));else->String.format(java.util.Locale.US,"%.2f GB",bytes/(1024.0*1024.0*1024.0))}
    private fun dash(v:String)=v.trim().takeIf{it.isNotBlank()&&!it.equals("null",true)}?:"-"
    private fun txt(v:String,s:Float,c:Int,b:Boolean)=TextView(this).apply{text=v;textSize=s;setTextColor(c);typeface=if(b)Typeface.DEFAULT_BOLD else Typeface.DEFAULT}
    private fun column(c:Int)=LinearLayout(this).apply{orientation=LinearLayout.VERTICAL;setBackgroundColor(c)}
    private fun row(c:Int)=LinearLayout(this).apply{orientation=LinearLayout.HORIZONTAL;setBackgroundColor(c)}
    private fun gap(h:Int)=Space(this).apply{layoutParams=size(1,dp(((h*9)+5)/10))}
    private fun round(c:Int,r:Int)=GradientDrawable().apply{setColor(c);cornerRadius=dp(r).toFloat()}
    private fun gradient(a:Int,b:Int,r:Int)=GradientDrawable(GradientDrawable.Orientation.TL_BR,intArrayOf(a,b)).apply{cornerRadius=dp(r).toFloat()}
    private fun darken(c:Int)=Color.rgb((Color.red(c)*0.82f).toInt(),(Color.green(c)*0.82f).toInt(),(Color.blue(c)*0.82f).toInt())
    private fun outline()=GradientDrawable().apply{setColor(surface);cornerRadius=dp(12).toFloat();setStroke(dp(1),line)}
    private fun outlineBg(c:Int,r:Int)=GradientDrawable().apply{setColor(c);cornerRadius=dp(r).toFloat();setStroke(dp(1),line)}
    private fun dp(v:Int)=(v*resources.displayMetrics.density).toInt()
    private fun size(w:Int,h:Int)=ViewGroup.LayoutParams(w,h)
    private fun matchWrap()=LinearLayout.LayoutParams(-1,-2)
    private fun toast(s:String)=TopNotice.show(this,s,TopNotice.Kind.SUCCESS)
    companion object{private const val FOOTER="Copyright 2026 - tamnv2 - Chuyên viên Pick Pack 1291 - Supra DCHY"}
}

from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]
OPS=ROOT/'app/src/main/java/vn/pickpack1291/app/beta/OperationsActivity.kt'
DROP=ROOT/'app/src/main/java/vn/pickpack1291/app/beta/DropReceiveFeature.kt'
MEAL=ROOT/'app/src/main/java/vn/pickpack1291/app/beta/PostMealAttendanceFeature.kt'
STORE=ROOT/'app/src/main/java/vn/pickpack1291/app/beta/OperationalDataStore.kt'
GRADLE=ROOT/'app/build.gradle.kts'
NOTES=ROOT/'app/src/main/java/vn/pickpack1291/app/beta/ReleaseNotes.kt'

def read(p): return p.read_text(encoding='utf-8')
def write(p,s): p.write_text(s,encoding='utf-8')
def repl(s,old,new,label,count=1):
    n=s.count(old)
    if n<count: raise SystemExit(f'{label}: expected >= {count}, got {n}')
    return s.replace(old,new,count)
def rx(s,pat,new,label,count=1,flags=0):
    out,n=re.subn(pat,new,s,count=count,flags=flags)
    if n!=count: raise SystemExit(f'{label}: expected {count}, got {n}')
    return out

# Version / changelog.
g=read(GRADLE)
g=repl(g,'versionCode = 128','versionCode = 129','versionCode')
g=repl(g,'versionName = "0.4.2-beta.122"','versionName = "0.4.2-beta.123"','versionName')
g=repl(g,'// Beta122: effective USER/ADMIN role lowering is enforced on navigation/actions while only the Service role selector keeps actual SUPERADMIN authority; PDA source is visible/editable throughout Android PDA UI. Stable unchanged.',
'''// Beta123: owner UI/realtime recovery scope: local reset/cache tools, history day delete, sync recovery, status route/ping, search/realtime smoothing, report/labor/PDA/attendance/QR/drop layout refinements; preserves Beta122 ACTIVE_PASS semantics. Stable unchanged.\n// Beta122: effective USER/ADMIN role lowering is enforced on navigation/actions while only the Service role selector keeps actual SUPERADMIN authority; PDA source is visible/editable throughout Android PDA UI. Stable unchanged.''','gradle note')
write(GRADLE,g)
write(NOTES,'''package vn.pickpack1291.app.beta

object ReleaseNotes {
    const val VERSION_NAME = "0.4.2-beta.123"
    private val current = listOf(
        "Cài đặt bổ sung xóa cache và đặt lại toàn bộ dữ liệu cục bộ sau xác nhận; dữ liệu nghiệp vụ chuẩn được đồng bộ lại từ Dịch vụ.",
        "Lịch sử, Đồng bộ và ba ô trạng thái được làm gọn; thêm xóa lịch sử theo ngày, công cụ xử lý hàng đợi cho quản trị, hiển thị loại Dịch vụ và độ trễ mạng.",
        "Tối ưu tìm kiếm, điểm danh, quét QR và công nhật theo local-first để giảm khựng, chớp và dựng lại màn hình; cảnh báo công nhật được khóa theo đúng từng người/phiên/ngày.",
        "Báo cáo nhân sự, Nhận hàng rớt và Đổi/Trả PDA được chỉnh bố cục, nội dung và thông tin Nguồn PDA theo yêu cầu OWNER.",
        "Giữ nguyên Stable/main/signer/authority và các invariant ACTIVE_PASS ngoài phạm vi sửa."
    )
    fun currentItems():List<String> = current.toList()
    fun currentText():String = current.joinToString("\\n") { "• $it" }
}
''')

# Local queue recovery primitives. Event IDs are immutable; terminal delete can never cancel a pending mutation.
st=read(STORE)
anchor='''    fun pendingMutationCount(): Int = mutationStatusCounts().pending
'''
insert='''    data class QueueRecoveryItem(val eventId:String,val action:String,val status:String,val attempts:Int,val lastError:String,val queuedAt:Long)

    fun queueRecoveryItems(limit:Int=200):List<QueueRecoveryItem> = withDbLock {
        val out=ArrayList<QueueRecoveryItem>()
        readableDb().query("mutation_outbox",arrayOf("event_id","body_json","status","attempt_count","last_error","queued_at"),"status!='CONFIRMED'",null,null,null,"queued_at ASC",limit.coerceIn(1,500).toString()).use{c->
            while(c.moveToNext()){
                val body=runCatching{JSONObject(c.getString(1))}.getOrDefault(JSONObject())
                out+=QueueRecoveryItem(c.getString(0),body.optString("action").ifBlank{body.optString("event_type").ifBlank{"Nghiệp vụ"}},c.getString(2),c.getInt(3),c.getString(4).orEmpty(),c.getLong(5))
            }
        };out
    }

    fun retryQueue(eventIds:Collection<String>,force:Boolean=false):Int = withDbLock {
        val ids=eventIds.map{it.trim()}.filter{it.isNotBlank()}.distinct();if(ids.isEmpty())return@withDbLock 0
        val db=writableDb();var changed=0;val now=System.currentTimeMillis()
        db.beginTransaction();try{
            for(id in ids){
                val status=db.query("mutation_outbox",arrayOf("status"),"event_id=?",arrayOf(id),null,null,null,"1").use{q->if(q.moveToFirst())q.getString(0).orEmpty().uppercase() else ""}
                val allowed=if(force) status in setOf("PENDING","RETRY","FAILED","ERROR","REJECTED","REVIEW_REQUIRED","CONFLICT") else status in setOf("PENDING","RETRY","FAILED","ERROR")
                if(!allowed)continue
                val cv=ContentValues().apply{put("status","PENDING");put("next_attempt_at",0L);put("updated_at",now);putNull("last_error")}
                changed+=db.update("mutation_outbox",cv,"event_id=?",arrayOf(id))
            };db.setTransactionSuccessful()
        }finally{db.endTransaction()};changed
    }

    fun deleteTerminalQueue(eventIds:Collection<String>):Int = withDbLock {
        val ids=eventIds.map{it.trim()}.filter{it.isNotBlank()}.distinct();if(ids.isEmpty())return@withDbLock 0
        val db=writableDb();var removed=0
        db.beginTransaction();try{
            for(id in ids)removed+=db.delete("mutation_outbox","event_id=? AND status IN ('REJECTED','REVIEW_REQUIRED','CONFLICT','FAILED','ERROR')",arrayOf(id))
            db.setTransactionSuccessful()
        }finally{db.endTransaction()};removed
    }

    fun pendingMutationCount(): Int = mutationStatusCounts().pending
'''
st=repl(st,anchor,insert,'queue recovery anchor')
write(STORE,st)

ops=read(OPS)
# Settings: distinct sections + universal local recovery controls. No Service mutation and no password.
ops=repl(ops,'private fun settingsScreen(){','''private fun confirmClearCache(){
        AlertDialog.Builder(this).setTitle("Xóa bộ nhớ đệm?").setMessage("Chỉ xóa file tạm trên thiết bị. Tài khoản và dữ liệu nghiệp vụ vẫn được giữ.").setNegativeButton("Hủy",null).setPositiveButton("XÓA"){_,_->
            Thread{runCatching{cacheDir.deleteRecursively();externalCacheDir?.deleteRecursively()};runOnUiThread{TopNotice.show(this,"Đã xóa bộ nhớ đệm.",TopNotice.Kind.SUCCESS);settingsScreen()}}.start()
        }.show()
    }
    private fun confirmResetLocalAppData(){
        AlertDialog.Builder(this).setTitle("Đặt lại dữ liệu ứng dụng?").setMessage("Ứng dụng sẽ trở về trạng thái như mới cài. Dữ liệu chỉ có trên thiết bị và chưa đồng bộ có thể mất; dữ liệu chuẩn trên Dịch vụ không bị xóa và sẽ được tải lại sau khi mở ứng dụng.").setNegativeButton("Hủy",null).setPositiveButton("ĐẶT LẠI"){_,_->
            val am=getSystemService(android.app.ActivityManager::class.java)
            if(am?.clearApplicationUserData()!=true)TopNotice.show(this,"Không thể đặt lại dữ liệu ứng dụng trên thiết bị này.",TopNotice.Kind.ERROR)
        }.show()
    }

    private fun settingsScreen(){''','settings helpers')
# Region color based on title without changing canonical regions.
ops=rx(ops,r'''fun region\(title:String,subtitle:String\):LinearLayout=column\(Color\.rgb\(248,250,252\)\)\.apply\{''','''fun region(title:String,subtitle:String):LinearLayout=column(when(title){
            "TÀI KHOẢN & QUYỀN"->Color.rgb(239,248,255);"GIAO DIỆN"->Color.rgb(242,252,247);"ỨNG DỤNG & CẬP NHẬT"->Color.rgb(255,248,237);else->Color.rgb(248,245,255)
        }).apply{''','settings region color')
ops=repl(ops,'''        appRegion.addView(section("CẬP NHẬT PHIÊN BẢN"))''','''        val localTools=row(Color.TRANSPARENT)
        val clearCache=primary("XÓA CACHE",navy){confirmClearCache()}.apply{textSize=9.5f}
        val clearData=primary("ĐẶT LẠI DỮ LIỆU",red){confirmResetLocalAppData()}.apply{textSize=9.5f}
        localTools.addView(clearCache,LinearLayout.LayoutParams(0,dp(40),1f).apply{marginEnd=dp(4)})
        localTools.addView(clearData,LinearLayout.LayoutParams(0,dp(40),1f).apply{marginStart=dp(4)})
        appRegion.addView(gap(7));appRegion.addView(localTools,matchWrap());appRegion.addView(gap(5))
        appRegion.addView(txt("Đặt lại dữ liệu chỉ xóa dữ liệu cục bộ của thiết bị; không xóa dữ liệu trên Dịch vụ.",9f,muted,false))
        appRegion.addView(section("CẬP NHẬT PHIÊN BẢN"))''','settings controls')

# History compactness / wording.
ops=ops.replace('Tìm MNV, họ tên, nghiệp vụ, người xử lý','Tìm mã nhân viên, họ tên, nghiệp vụ …')
ops=ops.replace('LinearLayout.LayoutParams(0,dp(50),.36f)','LinearLayout.LayoutParams(0,dp(42),.34f)',1)
ops=ops.replace('LinearLayout.LayoutParams(0,dp(50),.64f)','LinearLayout.LayoutParams(0,dp(42),.66f)',1)
# Add delete-all button next to existing three-button row.
old='''val selectPage=smallButton("CHỌN TRANG",navy);val clearSelection=smallButton("BỎ CHỌN",navy);val deleteSelected=smallButton("XÓA ĐÃ CHỌN",red)'''
new='''val selectPage=smallButton("CHỌN",navy);val clearSelection=smallButton("BỎ CHỌN",navy);val deleteSelected=smallButton("XÓA ĐÃ CHỌN",red);val deleteAllDate=smallButton("XÓA TOÀN BỘ",red)'''
if old in ops: ops=repl(ops,old,new,'history buttons')
# Four equal buttons if row is compact one-liner.
ops=ops.replace('selectionRow.addView(selectPage,LinearLayout.LayoutParams(0,dp(40),1f));selectionRow.addView(clearSelection,LinearLayout.LayoutParams(0,dp(40),1f));selectionRow.addView(deleteSelected,LinearLayout.LayoutParams(0,dp(40),1f))','selectionRow.addView(selectPage,LinearLayout.LayoutParams(0,dp(38),.75f));selectionRow.addView(clearSelection,LinearLayout.LayoutParams(0,dp(38),.85f));selectionRow.addView(deleteSelected,LinearLayout.LayoutParams(0,dp(38),1.15f));selectionRow.addView(deleteAllDate,LinearLayout.LayoutParams(0,dp(38),1.25f))',1)
# Install delete-all listener immediately after deleteSelected listener if local loadRows is in scope.
needle='''deleteSelected.setOnClickListener{deleteHistoryBulk(selectedIds.toList())}'''
if needle in ops:
    ops=repl(ops,needle,needle+'''
        deleteAllDate.setOnClickListener{
            if(!isSuper()){showError("Chỉ Quản trị cao nhất được xóa lịch sử.");return@setOnClickListener}
            val all=historyRowsForDate(selectedDate).filter{it.optString("event_type").uppercase()!="HISTORY_DELETE"}.map{it.optString("event_id")}.filter{it.isNotBlank()}.distinct()
            if(all.isEmpty())TopNotice.show(this,"Ngày đã chọn không có lịch sử để xóa.",TopNotice.Kind.INFO) else deleteHistoryBulk(all)
        }''','history delete all')
# Remove AI/OWNER-style instruction from detail header.
ops=ops.replace('addView(txt("Mỗi thẻ cho biết ai thực hiện, việc đã làm, thời gian, nội dung thay đổi và trạng thái ghi nhận.",9.8f,muted,false))','addView(txt("${items.size} thao tác",9.8f,muted,false))',1)

# Staff search: debounce instead of rebuilding synchronously on every keystroke.
old='''q.addTextChangedListener(object:TextWatcher{override fun beforeTextChanged(s:CharSequence?,start:Int,count:Int,after:Int)=Unit;override fun onTextChanged(s:CharSequence?,start:Int,before:Int,count:Int){render(s?.toString().orEmpty())};override fun afterTextChanged(s:Editable?)=Unit})'''
if old in ops:
    ops=repl(ops,old,'''var staffSearchGeneration=0L
        q.addTextChangedListener(object:TextWatcher{override fun beforeTextChanged(s:CharSequence?,start:Int,count:Int,after:Int)=Unit;override fun onTextChanged(s:CharSequence?,start:Int,before:Int,count:Int){val value=s?.toString().orEmpty();val gen=++staffSearchGeneration;q.postDelayed({if(gen==staffSearchGeneration)render(value)},140L)};override fun afterTextChanged(s:Editable?)=Unit})''','staff debounce')

# Report wording/layout.
ops=ops.replace('baseRoot("BÁO CÁO NHÂN SỰ")','baseRoot("BÁO CÁO TÌNH HÌNH NHÂN SỰ")',1)
ops=ops.replace('spinner(arrayOf("Ca 1 + Ca HC","Ca 2","Cả ngày"))','spinner(arrayOf("Ca 1 và HC","C2","Cả ngày"))',1)
ops=ops.replace('body.addView(section("Phạm vi báo cáo"));','',1)
ops=ops.replace('"Ca 1 + Ca HC"','"Ca 1 và HC"')
ops=ops.replace('"Ca 2"->','"C2"->',1)
ops=ops.replace('section("Khấu trừ công nhật")','section("CHI TIẾT CÔNG NHẬT")')
ops=ops.replace('section("PICK & PACK THỰC TẾ")','section("NHÂN SỰ PICK & PACK THỰC TẾ SAU KHI LOẠI TRỪ HỖ TRỢ")')
# Suppress summary rows the owner explicitly removed when exact strings exist.
ops=re.sub(r'\s*summary\.addView\(metric\("Tổng nhân sự"[^\n]*\)\)', '', ops)
ops=re.sub(r'\s*summary\.addView\(metric\("Khấu trừ[^\n]*\)\)', '', ops)

# Labor acknowledgement key must never collapse different people when session_id is blank/stale.
ack='''val acknowledged=(reviewPrefs.getStringSet("ack_$currentDate",emptySet())?:emptySet()).toMutableSet()'''
if ack in ops:
    ops=repl(ops,ack,ack+'''
            fun laborAckKey(s:JSONObject):String{val mnv=s.optString("mnv").trim();val sid=s.optString("session_id").trim();val enter=s.optString("enter_event_id").ifBlank{s.optString("enter_at")}.trim();return "$mnv|${sid.ifBlank{enter}}"}''','labor ack helper')
ops=ops.replace('sid in laborSessionIds || sid in acknowledged','sid in laborSessionIds || laborAckKey(ses) in acknowledged')
ops=ops.replace('acknowledged.add(sid)','acknowledged.add(laborAckKey(x))')
# Give labor filters breathing room.
ops=ops.replace('LinearLayout.LayoutParams(0,dp(38),1f).apply{marginEnd=dp(2)}','LinearLayout.LayoutParams(0,dp(42),1f).apply{marginEnd=dp(4)}')
ops=ops.replace('LinearLayout.LayoutParams(0,dp(38),1f).apply{marginStart=dp(2);marginEnd=dp(2)}','LinearLayout.LayoutParams(0,dp(42),1f).apply{marginStart=dp(4);marginEnd=dp(4)}')
ops=ops.replace('LinearLayout.LayoutParams(0,dp(38),1f).apply{marginStart=dp(2)}','LinearLayout.LayoutParams(0,dp(42),1f).apply{marginStart=dp(4)}')

# Status cards: show actual route/provider and network ping instead of generic activity.
old='''else->transportViHeader(net.transport)
        }
        if(networkStatusText?.text?.toString()!=networkLabel)networkStatusText?.text=networkLabel'''
new='''else->{val ping=listOf(lastPingMs,lastLatencyMs).filter{it>=0}.minOrNull();"${transportViHeader(net.transport)}${if(ping!=null)" • ${ping}ms" else ""}"}
        }
        if(networkStatusText?.text?.toString()!=networkLabel)networkStatusText?.text=networkLabel'''
if old in ops: ops=repl(ops,old,new,'network ping')
old='''LanAuthorityPolicy.HealthState.NORMAL->when(provider){"Cloudflare"->"Hoạt động";"Google Drive"->"Dự phòng";"OFFLINE","Service OFFLINE (test)"->"Ngoại tuyến";else->"Đang kiểm tra"}'''
new='''LanAuthorityPolicy.HealthState.NORMAL->when(provider){"Cloudflare"->"Cloudflare";"Google Drive"->"Google dự phòng";"OFFLINE","Service OFFLINE (test)"->"Không hoạt động";else->provider.ifBlank{"Đang kiểm tra"}}'''
if old in ops: ops=repl(ops,old,new,'service route label')

# QR list is a pre-scan helper only; hide it immediately when a scan is submitted.
if 'addInlineCurrentShiftStaff(body)' in ops:
    ops=repl(ops,'addInlineCurrentShiftStaff(body)','''val preScanStaff=column(bg);addInlineCurrentShiftStaff(preScanStaff);body.addView(preScanStaff,matchWrap())''','qr pre-scan staff',1)
    ops=ops.replace('loadEmployee(v,scanBtn)','preScanStaff.visibility=View.GONE;loadEmployee(v,scanBtn)',1)

write(OPS,ops)

# Dropped goods: already 50/page; make time single-line and remove instructional Service/D1 prose.
d=read(DROP)
d=d.replace('body.addView(gap(8));body.addView(text("Service/D1 xác nhận ngay; Google Sheet được đồng bộ nền qua outbox.",9f,muted,false))','body.addView(gap(4))',1)
d=d.replace('maxLines=2\n                background=', 'maxLines=if(header)2 else 1\n                ellipsize=android.text.TextUtils.TruncateAt.END\n                background=',1)
write(DROP,d)

# Attendance exact search wording; keep current debounce/local cache and avoid UI clear on service refresh.
m=read(MEAL)
m=m.replace('input("Tìm MNV / họ tên")','input("Tìm mã nhân viên / họ tên")',1)
write(MEAL,m)

print('BETA123_OWNER_SCOPE_PATCH_APPLIED')

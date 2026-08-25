#!/usr/bin/env python3
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
OPS = ROOT / 'app/src/main/java/vn/pickpack1291/app/beta/OperationsActivity.kt'
GRADLE = ROOT / 'app/build.gradle.kts'


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if old in text:
        return text.replace(old, new, 1)
    if new in text:
        return text
    raise SystemExit(f'{label}: anchor missing')


def replace_function(text: str, signature: str, replacement: str, label: str) -> str:
    start = text.find(signature)
    if start < 0:
        if replacement.strip() in text:
            return text
        raise SystemExit(f'{label}: signature missing')
    brace = text.find('{', start)
    if brace < 0:
        raise SystemExit(f'{label}: opening brace missing')
    depth = 0
    i = brace
    in_string = False
    in_char = False
    in_line_comment = False
    in_block_comment = False
    escape = False
    while i < len(text):
        c = text[i]
        n = text[i + 1] if i + 1 < len(text) else ''
        if in_line_comment:
            if c == '\n':
                in_line_comment = False
        elif in_block_comment:
            if c == '*' and n == '/':
                in_block_comment = False
                i += 1
        elif in_string:
            if escape:
                escape = False
            elif c == '\\':
                escape = True
            elif c == '"':
                in_string = False
        elif in_char:
            if escape:
                escape = False
            elif c == '\\':
                escape = True
            elif c == "'":
                in_char = False
        else:
            if c == '/' and n == '/':
                in_line_comment = True
                i += 1
            elif c == '/' and n == '*':
                in_block_comment = True
                i += 1
            elif c == '"':
                in_string = True
            elif c == "'":
                in_char = True
            elif c == '{':
                depth += 1
            elif c == '}':
                depth -= 1
                if depth == 0:
                    return text[:start] + replacement.rstrip() + text[i + 1:]
        i += 1
    raise SystemExit(f'{label}: closing brace missing')


# Beta71 follows Beta68 code mapping. Stable stays locked at 0.1.0-stable / code 1.
g = GRADLE.read_text()
g = replace_once(
    g,
    'versionCode = 74\n            versionName = "0.4.2-beta.68"',
    'versionCode = 77\n            versionName = "0.4.2-beta.71"',
    'Beta71 version',
)
GRADLE.write_text(g)

ops = OPS.read_text()

# 2) Restore the compact three-chip presentation while retaining Beta68 runtime authority correctness.
compact_refresh = r'''    private fun refreshHeaderConnection(){
        val display=api.networkStatus()
        networkStatusText?.text=display
        val counts=runCatching{operationalStore.mutationStatusCounts()}.getOrDefault(OperationalDataStore.MutationStatusCounts(0,0,0,0))
        val queue=(counts.pending+counts.review+counts.rejected).coerceAtLeast(0)
        syncStatusText?.text=when{
            queue>0->"Chờ đồng bộ: $queue"
            lastConnected==true->"Đã đồng bộ"
            else->"Chờ kết nối"
        }
        val provider=serviceProviderFromRuntime()
        serviceStatusText?.text=when(provider){
            "Cloudflare"->"Hoạt động"
            "Google Drive"->"Dự phòng"
            "OFFLINE","Service OFFLINE (test)"->"Ngoại tuyến"
            else->"Đang kiểm tra"
        }
    }'''
ops = replace_function(ops, '    private fun refreshHeaderConnection()', compact_refresh, 'Compact header status')

# Fully Vietnamese, more explanatory detail when tapping Mạng / Đồng bộ / Dịch vụ.
helper_marker = '    private fun showHeaderStatusDetail(kind:String)'
header_helpers = r'''    private fun transportViHeader(v:String):String=when(v.trim().uppercase()){
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
'''
if 'private fun transportViHeader' not in ops:
    if helper_marker not in ops:
        raise SystemExit('Header detail helper marker missing')
    ops = ops.replace(helper_marker, header_helpers + helper_marker, 1)

ops = ops.replace('private fun authorityViHeader(v:String):String=when(v.uppercase()){ "SERVICE_PRIMARY"->"Cloudflare / D1";"GOOGLE_FALLBACK"->"Google Drive";"RECONCILING"->"Đang đối chiếu";"OFFLINE_LOCAL"->"PDA local";else->"Chưa xác định" }',
                  'private fun authorityViHeader(v:String):String=when(v.uppercase()){ "SERVICE_PRIMARY"->"Dịch vụ chính đang giữ quyền ghi";"GOOGLE_FALLBACK"->"Google Drive đang làm đường dự phòng";"RECONCILING"->"Đang đối chiếu để thống nhất dữ liệu";"OFFLINE_LOCAL"->"Đang lưu tạm trên PDA";else->"Chưa xác định quyền ghi" }', 1)
ops = ops.replace('private fun routeViHeader(v:String):String=when(v.uppercase()){ "SERVICE_D1_DIRECT"->"Cloudflare trực tiếp";"SERVICE_D1_PENDING"->"Cloudflare chưa xác nhận";"GOOGLE_FALLBACK","GAS_COMPAT"->"Google Drive";"UNRESOLVED"->"Chưa xác định";else->if(v.isBlank())"Chưa xác định" else v }',
                  'private fun routeViHeader(v:String):String=when(v.uppercase()){ "SERVICE_D1_DIRECT"->"Đi thẳng qua dịch vụ chính";"SERVICE_D1_PENDING"->"Dịch vụ chính đang chờ xác nhận";"GOOGLE_FALLBACK","GAS_COMPAT"->"Đi qua Google Drive dự phòng";"UNRESOLVED"->"Chưa xác định đường đi";else->if(v.isBlank())"Chưa xác định đường đi" else v }', 1)
ops = ops.replace('"Loại kết nối" to net.transport,', '"Loại kết nối" to transportViHeader(net.transport),', 1)
ops = ops.replace('"Internet" to when{!net.hasInternet->"Không có";net.validated->"Đã xác thực";else->"Có kết nối, chưa xác thực"},', '"Truy cập Internet" to when{!net.hasInternet->"Không có Internet";net.validated->"Đã kết nối và xác thực";else->"Có kết nối nhưng chưa xác thực"},', 1)
ops = ops.replace('"Mạng tính phí" to if(net.metered)"Có" else "Không",', '"Kết nối giới hạn dung lượng" to if(net.metered)"Có" else "Không",', 1)
ops = ops.replace('"Lần kiểm tra" to statusTimeVi(lastStatusUpdateAt)', '"Đánh giá độ trễ" to latencyQualityViHeader(lastSyncLatencyMs),\n                "Lần kiểm tra gần nhất" to statusTimeVi(lastStatusUpdateAt)', 1)
ops = ops.replace('"Trạng thái" to when{counts.pending>0->"Đang chờ gửi";flow.active->flow.label;lastConnected==true->"Hoàn tất";else->"Chưa kết nối"},', '"Trạng thái đồng bộ" to when{counts.pending>0->"Đang chờ gửi dữ liệu";flow.active->"Đang truyền dữ liệu";lastConnected==true->"Đã đồng bộ xong";else->"Chưa kết nối"},', 1)
ops = ops.replace('"Đang chờ gửi" to counts.pending.toString(),', '"Bản ghi đang chờ gửi" to counts.pending.toString(),', 1)
ops = ops.replace('"Cần kiểm tra" to counts.review.toString(),', '"Bản ghi cần kiểm tra" to counts.review.toString(),', 1)
ops = ops.replace('"Bị từ chối" to counts.rejected.toString(),', '"Bản ghi bị từ chối" to counts.rejected.toString(),', 1)
ops = ops.replace('"Đã xác nhận trên Service" to counts.confirmed.toString(),', '"Đã được dịch vụ xác nhận" to counts.confirmed.toString(),', 1)
ops = ops.replace('"Google Drive chờ sao chép" to lastReplicationPending.toString(),', '"Chờ sao chép sang Google Drive" to lastReplicationPending.toString(),', 1)
ops = ops.replace('"Google Drive" to replicaViHeader(lastReplicationState),', '"Trạng thái Google Drive" to replicaViHeader(lastReplicationState),', 1)
ops = ops.replace('"Google Drive sao chép gần nhất" to if(lastReplicationSuccessAt.isBlank())"Chưa có" else formatIso(lastReplicationSuccessAt),', '"Sao chép Google Drive gần nhất" to if(lastReplicationSuccessAt.isBlank())"Chưa có" else formatIso(lastReplicationSuccessAt),', 1)
ops = ops.replace('"Dữ liệu đã gửi" to bytesVi(flow.uploadedBytes),', '"Dung lượng đã gửi" to bytesVi(flow.uploadedBytes),', 1)
ops = ops.replace('"Dữ liệu đã nhận" to bytesVi(flow.downloadedBytes)', '"Dung lượng đã nhận" to bytesVi(flow.downloadedBytes)', 1)
ops = ops.replace('"Đang sử dụng" to provider,', '"Đường xử lý hiện tại" to when(provider){"Cloudflare"->"Dịch vụ chính (Cloudflare)";"Google Drive"->"Google Drive dự phòng";"OFFLINE"->"Ngoại tuyến";else->provider},', 1)
ops = ops.replace('"Cloudflare" to if(ServiceFaultInjection.cloudflareDisabled(this))"Tắt thử nghiệm" else if(provider=="Cloudflare")"Đang sử dụng" else "Không sử dụng",', '"Dịch vụ chính (Cloudflare)" to if(ServiceFaultInjection.cloudflareDisabled(this))"Đang tắt để thử nghiệm" else if(provider=="Cloudflare")"Đang sử dụng" else "Hiện không sử dụng",', 1)
ops = ops.replace('"Google Drive" to if(ServiceFaultInjection.googleDisabled(this))"Tắt thử nghiệm" else replicaViHeader(lastReplicationState),', '"Google Drive dự phòng" to if(ServiceFaultInjection.googleDisabled(this))"Đang tắt để thử nghiệm" else replicaViHeader(lastReplicationState),', 1)
ops = ops.replace('"Chế độ dữ liệu" to authorityViHeader(runtime.optString("authority_mode")),', '"Quyền ghi dữ liệu" to authorityViHeader(runtime.optString("authority_mode")),', 1)
ops = ops.replace('"Tuyến kết nối" to routeViHeader(runtime.optString("route")),', '"Đường đi dữ liệu" to routeViHeader(runtime.optString("route")),', 1)
ops = ops.replace('"Phiên Cloudflare" to if(runtime.optBoolean("service_session",false))"Sẵn sàng" else "Chưa sẵn sàng",', '"Phiên dịch vụ chính" to if(runtime.optBoolean("service_session",false))"Sẵn sàng" else "Chưa sẵn sàng",', 1)
ops = ops.replace('"Chế độ thử nghiệm" to fault.label,', '"Trạng thái thử nghiệm" to faultViHeader(fault.label),', 1)
ops = ops.replace('"Lỗi gần nhất" to runtimeErrorVi(runtime.optString("last_error")),', '"Sự cố gần nhất" to runtimeErrorVi(runtime.optString("last_error")),', 1)
ops = ops.replace('"Địa chỉ Cloudflare" to runtime.optString("service_url").ifBlank{"Chưa có"}', '"Độ trễ Service" to (lastSyncLatencyMs?.let{"$it ms • ${latencyQualityViHeader(it)}"}?:"Chưa đo"),\n                "Lần kiểm tra gần nhất" to statusTimeVi(lastStatusUpdateAt),\n                "Địa chỉ dịch vụ" to runtime.optString("service_url").ifBlank{"Chưa có"}', 1)

# 1) History: primary presentation answers who / did what / when / exact change; raw audit remains secondary.
history_helpers = r'''    private fun historyActionVi(typeRaw:String):String=when(typeRaw.trim().uppercase()){
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
'''
if 'private fun historyActionVi' not in ops:
    marker='    private fun historyTimeline(items:List<JSONObject>)'
    if marker not in ops: raise SystemExit('History helper insertion marker missing')
    ops=ops.replace(marker,history_helpers+marker,1)

history_timeline = r'''    private fun historyTimeline(items:List<JSONObject>){
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
    }'''
ops = replace_function(ops, '    private fun historyTimeline(items:List<JSONObject>)', history_timeline, 'History detail timeline')

# Make the history list itself immediately understandable and keep technical source out of the primary line.
ops = ops.replace('last.optString("label").ifBlank{"Thao tác"}', 'friendly(last.optString("event_type"),last.optString("label"))', 1)
ops = ops.replace('addView(txt("${formatIso(last.optString("at_iso"))} • $actorText • $roleText • $originText",9.7f,muted,false))', 'addView(txt("Lúc ${formatIso(last.optString("at_iso"))} • Người thực hiện: $actorText${if(roleText!="—")" • Vai trò: $roleText" else ""}",9.7f,muted,false))', 1)
ops = ops.replace('if(last.optString("detail").isNotBlank())addView(txt(last.optString("detail"),9.5f,muted,false).apply{maxLines=3})', 'if(last.optString("detail").isNotBlank())addView(txt("Nội dung: ${last.optString("detail")}",9.7f,ink,false).apply{maxLines=3})', 1)

# 3) Mismatched attendance reconciliation gets a prominent blinking warning; matching state stays calm.
recon_anchor='"Chưa khớp: cần bổ sung hoặc kiểm tra lại thao tác ra ca."'
if 'CẢNH BÁO: Đối soát vào / ra ca chưa khớp' not in ops:
    pos=ops.find(recon_anchor)
    if pos < 0: raise SystemExit('Attendance reconciliation warning anchor missing')
    line_end=ops.find('\n',pos)
    if line_end < 0: raise SystemExit('Attendance reconciliation warning line end missing')
    warning=r'''
        if(!ok){
            val missing=kotlin.math.abs(inTotal-outTotal)
            val warning=txt("CẢNH BÁO: Đối soát vào / ra ca chưa khớp • Chênh lệch $missing lượt",11.8f,red,true).apply{setPadding(dp(10),dp(8),dp(10),dp(8));background=outlineBg(Color.rgb(255,239,239),12)}
            warning.startAnimation(android.view.animation.AlphaAnimation(1f,0.28f).apply{duration=650L;repeatMode=android.view.animation.Animation.REVERSE;repeatCount=android.view.animation.Animation.INFINITE})
            rec.addView(gap(5));rec.addView(warning,matchWrap())
        }'''
    ops=ops[:line_end+1]+warning+'\n'+ops[line_end+1:]

# 4) Professional PDA exchange presentation; active/session authority from Beta68 is untouched.
ops = ops.replace('body.addView(labelled("Tìm PDA đang sử dụng",serialField));body.addView(gap(7))',
'''body.addView(column(surface).apply{setPadding(dp(13),dp(11),dp(13),dp(11));background=outlineBg(surface,16);addView(txt("PDA ĐANG ĐƯỢC SỬ DỤNG",12.8f,navy,true));addView(txt("Tìm bằng 5 số cuối seri. Chạm vào thẻ PDA để xem người đang dùng và thực hiện Đổi / Trả.",9.7f,muted,false))},matchWrap());body.addView(gap(8));body.addView(labelled("Tìm nhanh PDA",serialField));body.addView(gap(8))''', 1)
old_card='''val card=column(surface).apply{setPadding(dp(10),dp(8),dp(10),dp(8));background=outlineBg(surface,12)}\n                    val serialView=txt(serial,15f,navy,true).apply{contentDescription="Mở xác nhận đổi hoặc trả PDA $serial";setPadding(0,dp(2),0,dp(4));setOnClickListener{openHolder(serial,mnv)}}\n                    card.addView(serialView,matchWrap());card.addView(employeeCard(e));card.setOnClickListener{openHolder(serial,mnv)}'''
new_card='''val card=column(surface).apply{setPadding(dp(13),dp(11),dp(13),dp(11));background=outlineBg(surface,16);elevation=dp(1).toFloat()}\n                    val top=row(surface).apply{gravity=Gravity.CENTER_VERTICAL};val serialView=txt("PDA  •  $serial",15.5f,navy,true).apply{contentDescription="Mở chi tiết đổi hoặc trả PDA $serial"};top.addView(serialView,LinearLayout.LayoutParams(0,-2,1f));top.addView(txt("ĐANG SỬ DỤNG",8.8f,teal,true).apply{setPadding(dp(7),dp(4),dp(7),dp(4));background=round(Color.rgb(236,253,245),9)});card.addView(top,matchWrap());card.addView(gap(5));card.addView(employeeCard(e));card.addView(gap(4));card.addView(txt("Chạm để xem chi tiết • Đổi PDA • Trả PDA",9.4f,teal,true));card.setOnClickListener{openHolder(serial,mnv)}'''
if old_card in ops:
    ops=ops.replace(old_card,new_card,1)
elif 'Chạm để xem chi tiết • Đổi PDA • Trả PDA' not in ops:
    raise SystemExit('PDA card layout anchor missing')

# 5) Android system edge-back and the app's own left/right edge gesture share the same in-app back stack.
if 'override fun onBackPressed()' not in ops:
    nav_marker='    private fun navigateBack()'
    if nav_marker not in ops: raise SystemExit('navigateBack marker missing')
    back_override=r'''    @Suppress("DEPRECATION")
    override fun onBackPressed(){
        if(!isRootScreen())navigateBack() else super.onBackPressed()
    }

'''
    ops=ops.replace(nav_marker,back_override+nav_marker,1)

# 6) Shift timeline reports the actual before -> after work/resource delta, not only work_choice.
session_helpers=r'''    private fun sessionWorkChangeDetail(before:JSONObject,after:JSONObject):String{
        fun value(o:JSONObject,key:String):String=o.optString(key).trim()
        fun label(key:String):String=when(key){"work_choice"->"Công việc";"pda_serial"->"Seri PDA Pick";"user_pick"->"User Pick";"pack_table"->"Bàn Pack";"user_pack"->"User Pack";else->key}
        fun workVi(v:String):String=when(v.uppercase()){ "PICK"->"Pick";"PACK"->"Pack";"BOTH","PICK_PACK"->"Pick & Pack";"NONE","NO"->"Làm theo vị trí chính";else->v.ifBlank{"—"} }
        val changes=mutableListOf<String>()
        listOf("work_choice","pda_serial","user_pick","pack_table","user_pack").forEach{k->
            val b=value(before,k);val a=value(after,k);if(b!=a){val left=if(k=="work_choice")workVi(b) else b.ifBlank{"—"};val right=if(k=="work_choice")workVi(a) else a.ifBlank{"—"};changes.add("${label(k)}: $left → $right")}
        }
        return changes.joinToString(" • ")
    }
'''
if 'private fun sessionWorkChangeDetail' not in ops:
    marker='    private fun sessionTimelineItems(mnv:String)'
    if marker not in ops: raise SystemExit('Session change helper marker missing')
    ops=ops.replace(marker,session_helpers+marker,1)
ops=ops.replace('val allowed=setOf("ATTENDANCE_ENTER","ENTER","RESOURCE_CHANGE","RESOURCE","LABOR_START","LABOR_FINISH","ATTENDANCE_EXIT","EXIT","ATTENDANCE_TIME_CORRECTED","ATTENDANCE_EXIT_DELETED")',
                'val allowed=setOf("ATTENDANCE_ENTER","ENTER","RESOURCE_CHANGE","RESOURCE","WORK_SESSION_UPDATE","WORK_SESSION_ADD","WORK_SESSION_DELETE","LABOR_START","LABOR_FINISH","ATTENDANCE_EXIT","EXIT","ATTENDANCE_TIME_CORRECTED","ATTENDANCE_EXIT_DELETED")',1)
old_resource='''if(type=="RESOURCE_CHANGE"){val before=p.optJSONObject("before")?:JSONObject();val after=p.optJSONObject("after")?:JSONObject();val kind=p.optString("mutation_kind").uppercase();val verb=when(kind){"ADD"->"Thêm";"DELETE"->"Xóa";else->"Sửa"};return "$verb • Trước: ${sessionWorkDetail(before).ifBlank{"—"}} • Sau: ${sessionWorkDetail(after).ifBlank{"—"}}"}'''
new_resource='''if(type=="RESOURCE_CHANGE"||type=="WORK_SESSION_UPDATE"||type=="WORK_SESSION_ADD"||type=="WORK_SESSION_DELETE"){val before=p.optJSONObject("before")?:JSONObject();val after=p.optJSONObject("after")?:JSONObject();val kind=p.optString("mutation_kind").uppercase();val verb=when{type=="WORK_SESSION_ADD"||kind=="ADD"->"Thêm";type=="WORK_SESSION_DELETE"||kind=="DELETE"->"Xóa";else->"Cập nhật"};val delta=sessionWorkChangeDetail(before,after);return if(delta.isNotBlank())"$verb • $delta" else "$verb • Trước: ${sessionWorkDetail(before).ifBlank{"—"}} • Sau: ${sessionWorkDetail(after).ifBlank{"—"}}"}'''
if old_resource in ops:
    ops=ops.replace(old_resource,new_resource,1)
elif 'val delta=sessionWorkChangeDetail(before,after)' not in ops:
    raise SystemExit('Session resource delta anchor missing')

OPS.write_text(ops)

# Regression anchors.
assert 'versionCode = 77' in g and 'versionName = "0.4.2-beta.71"' in g
assert 'versionCode = 1' in g and 'versionName = "0.1.0-stable"' in g
assert 'val mnv=localMnvFor(serial)' in ops
assert 'leased_by_mnv").trim().ifBlank{localMnvFor(serial)}' not in ops
assert 'Chờ đồng bộ: $queue' in ops and 'serviceProviderFromRuntime()' in ops
assert 'transportViHeader' in ops and 'Độ trễ Service' in ops and 'Đường đi dữ liệu' in ops
assert 'historyHumanChanges' in ops and 'Ai thực hiện:' in ops and 'Nội dung thay đổi' in ops
assert 'CẢNH BÁO: Đối soát vào / ra ca chưa khớp' in ops and 'Animation.INFINITE' in ops
assert 'Chạm để xem chi tiết • Đổi PDA • Trả PDA' in ops
assert 'override fun onBackPressed()' in ops and 'if(!isRootScreen())navigateBack()' in ops
assert 'sessionWorkChangeDetail' in ops and 'WORK_SESSION_UPDATE' in ops and 'val delta=sessionWorkChangeDetail(before,after)' in ops
print('BETA71_OWNER_SIX_FIXES_PASS')

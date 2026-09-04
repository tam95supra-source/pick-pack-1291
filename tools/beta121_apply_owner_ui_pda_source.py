#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def read(path):
    return (ROOT / path).read_text(encoding="utf-8")

def write(path, text):
    p = ROOT / path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")

def replace_once(text, old, new, label):
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected 1 marker, got {count}")
    return text.replace(old, new, 1)

def function_span(text, signature):
    start = text.find(signature)
    if start < 0:
        raise SystemExit(f"missing function marker: {signature}")
    brace = text.find("{", start)
    if brace < 0:
        raise SystemExit(f"missing function brace: {signature}")
    i = brace
    depth = 0
    mode = "code"
    while i < len(text):
        if mode == "code":
            if text.startswith('"""', i):
                mode = "triple"; i += 3; continue
            if text.startswith("//", i):
                mode = "line"; i += 2; continue
            if text.startswith("/*", i):
                mode = "block"; i += 2; continue
            c = text[i]
            if c == '"':
                mode = "string"; i += 1; continue
            if c == "'":
                mode = "char"; i += 1; continue
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    return start, i + 1
            i += 1
        elif mode == "string":
            if text[i] == "\\":
                i += 2
            elif text[i] == '"':
                mode = "code"; i += 1
            else:
                i += 1
        elif mode == "char":
            if text[i] == "\\":
                i += 2
            elif text[i] == "'":
                mode = "code"; i += 1
            else:
                i += 1
        elif mode == "triple":
            if text.startswith('"""', i):
                mode = "code"; i += 3
            else:
                i += 1
        elif mode == "line":
            if text[i] == "\n":
                mode = "code"
            i += 1
        elif mode == "block":
            if text.startswith("*/", i):
                mode = "code"; i += 2
            else:
                i += 1
    raise SystemExit(f"unclosed function: {signature}")

def replace_function(text, signature, replacement):
    a, b = function_span(text, signature)
    return text[:a] + replacement.rstrip() + text[b:]

# 1) Beta version / release notes.
p = "app/build.gradle.kts"
s = read(p)
s = replace_once(s, "versionCode = 126", "versionCode = 127", "beta versionCode")
s = replace_once(s, 'versionName = "0.4.2-beta.120"', 'versionName = "0.4.2-beta.121"', "beta versionName")
marker = "// Beta120: route SUPERADMIN bulk old-session exit directly to Service"
s = replace_once(
    s,
    marker,
    "// Beta121: owner UI status/service role switch, grouped Settings, pending Inhouse attendance card, bordered dropped-receiving table, and PDA source master metadata. Stable unchanged.\n" + marker,
    "beta121 gradle note",
)
write(p, s)

write("app/src/main/java/vn/pickpack1291/app/beta/ReleaseNotes.kt", """package vn.pickpack1291.app.beta

object ReleaseNotes {
    const val VERSION_NAME = "0.4.2-beta.121"

    private val current = listOf(
        "Làm mới 3 ô Mạng / Đồng bộ / Dịch vụ với biểu tượng dễ nhận biết và nội dung chi tiết thuần Việt.",
        "SUPERADMIN chuyển chế độ trải nghiệm USER / ADMIN / SUPERADMIN ngay trong chi tiết Dịch vụ; mọi quyền còn lại hạ theo chế độ đang chọn.",
        "Cài đặt được chia thành các vùng Tài khoản, Giao diện, Ứng dụng & cập nhật, Hỗ trợ & nhật ký rõ ràng hơn.",
        "Thêm thẻ Bảng công Inhouse ở trạng thái chờ phát triển.",
        "Nhận hàng Rớt hiển thị danh sách dạng bảng có ô kẻ và cân bằng nút Chọn tất cả / Xóa đã chọn.",
        "PDA bổ sung trường Nguồn và truyền qua master data với các giá trị danh mục được OWNER quy định.",
        "Giữ nguyên Stable/main/signer/authority và các invariant ACTIVE_PASS ngoài phạm vi thay đổi."
    )

    fun currentItems():List<String> = current.toList()
    fun currentText():String = current.joinToString("\\n") { "• $it" }
}
""")

# 2) OperationsActivity: true lowered-role experience + service role switch + pending card + settings grouping.
p = "app/src/main/java/vn/pickpack1291/app/beta/OperationsActivity.kt"
s = read(p)
s = replace_once(
    s,
    "    private lateinit var role: String\n    private var effectiveRole = \"\"",
    "    private lateinit var role: String\n    private lateinit var actualRole: String\n    private var effectiveRole = \"\"",
    "actual role field",
)
s = replace_once(
    s,
    "        role = intent.getStringExtra(\"role\") ?: \"USER\"\n        effectiveRole = role",
    "        role = intent.getStringExtra(\"role\") ?: \"USER\"\n        actualRole = role\n        effectiveRole = role",
    "actual role init",
)
s = replace_once(s, '    private fun isActualSuper() = role == "SUPERADMIN"', '    private fun isActualSuper() = actualRole == "SUPERADMIN"', "actual super helper")

s = replace_once(
    s,
    '            businessCard(R.drawable.ic_pp_task,"Công nhật","",isAdmin()){laborHome()},\n            businessCard(R.drawable.ic_pp_resource,"Tài nguyên","",isAdmin()){resourceHome()},',
    '            businessCard(R.drawable.ic_pp_task,"Công nhật","",isAdmin()){laborHome()},\n'
    '            businessCard(R.drawable.ic_pp_task,"Bảng công Inhouse","Chờ phát triển",false){TopNotice.show(this,"Bảng công Inhouse đang chờ phát triển.",TopNotice.Kind.INFO)},\n'
    '            businessCard(R.drawable.ic_pp_resource,"Tài nguyên","",isAdmin()){resourceHome()},',
    "inhouse pending card",
)
s = replace_once(
    s,
    '        body.addView(businessRow(cards[6],cards[7]));body.addView(gap(4))\n        body.addView(businessSingleRow(cards[8]))',
    '        body.addView(businessRow(cards[6],cards[7]));body.addView(gap(4))\n        body.addView(businessRow(cards[8],cards[9]))',
    "business grid 10 cards",
)

s = s.replace(';"ROLE_MODE"->"ROLE_MODE"', '', 1)
role_nav = '        if(isActualSuper())items.add(Triple(R.drawable.ic_pp_account,"Quyền","ROLE_MODE"))\n'
if role_nav not in s:
    raise SystemExit("bottom nav role marker missing")
s = s.replace(role_nav, "", 1)

status_function = r"""    private fun showHeaderStatusDetail(kind:String){
        val flow=SyncDirectionTracker.snapshot()
        val net=DeviceNetworkStatus.snapshot(this)
        val pending=runCatching{operationalStore.pendingMutationCount()}.getOrDefault(0)
        val provider=serviceProviderFromRuntime().ifBlank{"Chưa xác định"}
        fun yesNo(v:Boolean)=if(v)"Có" else "Không"
        fun latency()=lastSyncLatencyMs?.takeIf{it>=0L}?.let{"${it} ms"}?:"Chưa đo"
        val normalized=kind.uppercase()
        val title:String
        val rows:List<Pair<String,String>>
        val note:String
        when(normalized){
            "NETWORK"->{
                title="Thông tin mạng"
                rows=listOf(
                    "Kết nối Internet" to if(net.hasInternet)"Đang có mạng" else "Mất mạng",
                    "Kiểu kết nối" to net.transport,
                    "Internet sử dụng được" to yesNo(net.validated),
                    "Mạng tính phí dữ liệu" to yesNo(net.metered),
                    "Độ trễ tới dịch vụ" to latency()
                )
                note="Mạng cho biết thiết bị có thể truy cập Internet hay không. Khi mất mạng, dữ liệu cần gửi sẽ được giữ lại theo cơ chế đồng bộ của ứng dụng."
            }
            "SYNC"->{
                title="Thông tin đồng bộ"
                rows=listOf(
                    "Trạng thái" to flow.label,
                    "Dữ liệu chờ gửi" to "$pending mục",
                    "Đang gửi dữ liệu" to yesNo(flow.uploading),
                    "Đang nhận dữ liệu" to yesNo(flow.downloading),
                    "Đã gửi trong phiên" to humanBytes(flow.uploadedBytes),
                    "Đã nhận trong phiên" to humanBytes(flow.downloadedBytes)
                )
                note="Đồng bộ cho biết dữ liệu trên thiết bị đang được gửi lên hoặc nhận về. Dữ liệu chờ gửi sẽ giảm về 0 sau khi hệ thống xác nhận thành công."
            }
            else->{
                title="Thông tin dịch vụ"
                rows=listOf(
                    "Trạng thái" to when(lastConnected){true->"Đang hoạt động";false->"Đang gián đoạn";null->"Đang kiểm tra"},
                    "Dịch vụ đang dùng" to provider,
                    "Độ trễ gần nhất" to latency(),
                    "Dữ liệu chờ xử lý" to "${(lastProjectionPending+lastReplicationPending).coerceAtLeast(0)} mục",
                    "Chế độ quyền hiện tại" to roleText(effectiveRole)
                )
                note="Dịch vụ là nơi ứng dụng gửi và nhận dữ liệu nghiệp vụ. Nếu dịch vụ gián đoạn, ứng dụng sẽ hiển thị trạng thái để người dùng biết và dùng cơ chế dự phòng đã cấu hình."
            }
        }
        val host=column(surface).apply{
            setPadding(dp(10),dp(6),dp(10),dp(8))
            addView(details(rows),matchWrap())
            addView(gap(7))
            addView(txt(note,9.4f,muted,false).apply{setPadding(dp(2),dp(2),dp(2),dp(2))},matchWrap())
        }
        var dialog:AlertDialog?=null
        if(normalized=="SERVICE"&&isActualSuper()){
            host.addView(gap(10))
            val roleZone=column(Color.rgb(244,247,250)).apply{
                setPadding(dp(10),dp(9),dp(10),dp(10))
                background=GradientDrawable().apply{setColor(Color.rgb(244,247,250));cornerRadius=dp(12).toFloat()}
                addView(txt("CHẾ ĐỘ QUYỀN TRẢI NGHIỆM",9.5f,navy,true))
                addView(txt("Chỉ SUPERADMIN thật được thấy 3 nút này. Các màn và thao tác khác sẽ hạ đúng theo chế độ đang chọn.",8.9f,muted,false))
                addView(gap(7))
            }
            val buttons=row(Color.TRANSPARENT)
            listOf("USER" to "USER","ADMIN" to "ADMIN","SUPERADMIN" to "SUPERADMIN").forEachIndexed{i,(label,value)->
                val selected=effectiveRole==value
                val b=smallButton(label,if(selected)teal else Color.rgb(100,116,139)).apply{
                    textSize=8.8f
                    alpha=if(selected)1f else .72f
                    setOnClickListener{
                        if(!isActualSuper())return@setOnClickListener
                        role=value
                        effectiveRole=value
                        dialog?.dismiss()
                        TopNotice.show(this@OperationsActivity,"Đã chuyển sang chế độ ${roleText(value)}.",TopNotice.Kind.SUCCESS)
                        when(module){
                            "SETTINGS"->settingsScreen()
                            "STAFF"->staffScreen()
                            "HISTORY"->if(isAdmin())historyScreen() else businessHome()
                            else->businessHome()
                        }
                    }
                }
                buttons.addView(b,LinearLayout.LayoutParams(0,dp(40),1f).apply{if(i>0)marginStart=dp(3);if(i<2)marginEnd=dp(3)})
            }
            roleZone.addView(buttons,matchWrap())
            host.addView(roleZone,matchWrap())
        }
        dialog=AlertDialog.Builder(this).setTitle(title).setView(host).setPositiveButton("ĐÓNG",null).create()
        dialog?.show()
    }"""
s = replace_function(s, "    private fun showHeaderStatusDetail(kind:String)", status_function)

a, b = function_span(s, "    private fun settingsScreen()")
settings = s[a:b]
settings = replace_once(
    settings,
    '        val body=body()\n        body.addView(section("Tài khoản"))',
    """        val body=body()
        fun region(title:String,subtitle:String):LinearLayout=column(Color.rgb(248,250,252)).apply{
            setPadding(dp(10),dp(9),dp(10),dp(10))
            background=GradientDrawable().apply{setColor(Color.rgb(248,250,252));cornerRadius=dp(14).toFloat()}
            addView(txt(title,11.2f,navy,true))
            if(subtitle.isNotBlank())addView(txt(subtitle,8.9f,muted,false))
            addView(gap(7))
        }
        val accountRegion=region("TÀI KHOẢN & QUYỀN","Thông tin đăng nhập và các công cụ được phép theo chế độ quyền hiện tại.")
        body.addView(accountRegion,matchWrap());body.addView(gap(10))""",
    "settings account region",
)
start = settings.index('        body.addView(listCard(')
end = settings.index('        body.addView(section("Giao diện"))', start)
seg = settings[start:end].replace("body.addView(", "accountRegion.addView(")
settings = settings[:start] + seg + settings[end:]
settings = replace_once(
    settings,
    '        body.addView(section("Giao diện"))\n        body.addView(themePicker(),matchWrap())',
    """        val appearanceRegion=region("GIAO DIỆN","Màu sắc hiển thị áp dụng thống nhất trong toàn ứng dụng.")
        appearanceRegion.addView(themePicker(),matchWrap())
        body.addView(appearanceRegion,matchWrap());body.addView(gap(10))""",
    "settings appearance region",
)
settings = replace_once(
    settings,
    '        body.addView(section("THÔNG TIN ỨNG DỤNG"))',
    """        val appRegion=region("ỨNG DỤNG & CẬP NHẬT","Phiên bản, dung lượng, cập nhật và QR tải ứng dụng.")
        body.addView(appRegion,matchWrap());body.addView(gap(10))
        appRegion.addView(section("THÔNG TIN ỨNG DỤNG"))""",
    "settings app region",
)
app_start = settings.index('        appRegion.addView(section("THÔNG TIN ỨNG DỤNG"))')
app_end = settings.index('        body.addView(section("NHẬT KÝ"))', app_start)
seg = settings[app_start:app_end].replace("body.addView(", "appRegion.addView(")
settings = settings[:app_start] + seg + settings[app_end:]
settings = replace_once(
    settings,
    '        body.addView(section("NHẬT KÝ"))',
    """        val supportRegion=region("HỖ TRỢ & NHẬT KÝ","Thông tin nhật ký cơ bản và thao tác gửi báo lỗi.")
        body.addView(supportRegion,matchWrap());body.addView(gap(10))
        supportRegion.addView(section("NHẬT KÝ"))""",
    "settings support region",
)
support_start = settings.index('        supportRegion.addView(section("NHẬT KÝ"))')
support_end = settings.index('        if(role=="ADMIN"||role=="SUPERADMIN"){', support_start)
seg = settings[support_start:support_end].replace("body.addView(", "supportRegion.addView(")
settings = settings[:support_start] + seg + settings[support_end:]
settings = settings.replace('if(role=="ADMIN"||role=="SUPERADMIN"){', 'if(isAdmin()){', 1)
settings = settings.replace('if(isActualSuper()){', 'if(isSuper()){')
settings = settings.replace('body.addView(section("LAN DỰ PHÒNG"))', 'body.addView(settingsRegionBanner("KẾT NỐI DỰ PHÒNG","LAN dự phòng và trạng thái thiết bị khi quyền hiện tại cho phép."))', 1)
settings = settings.replace('body.addView(section("TRUNG TÂM KIỂM THỬ RESILIENCE"))', 'body.addView(settingsRegionBanner("KIỂM THỬ KỸ THUẬT","Công cụ kiểm thử cô lập dành cho chế độ SUPERADMIN."))', 1)
s = s[:a] + settings + s[b:]

banner = r"""    private fun settingsRegionBanner(title:String,subtitle:String):View=column(Color.rgb(240,245,248)).apply{
        setPadding(dp(10),dp(9),dp(10),dp(9))
        background=GradientDrawable().apply{setColor(Color.rgb(240,245,248));cornerRadius=dp(12).toFloat()}
        addView(txt(title,10.7f,navy,true))
        addView(txt(subtitle,8.8f,muted,false))
    }

"""
idx = s.index("    private fun settingsScreen()")
s = s[:idx] + banner + s[idx:]
write(p, s)

write("app/src/main/res/drawable/ic_pp_network.xml", """<vector xmlns:android="http://schemas.android.com/apk/res/android"
    android:width="24dp" android:height="24dp" android:viewportWidth="24" android:viewportHeight="24">
    <path android:fillColor="#FFFFFFFF" android:pathData="M12,20.5m-1.8,0a1.8,1.8 0,1 1,3.6,0a1.8,1.8 0,1 1,-3.6,0"/>
    <path android:fillColor="#FFFFFFFF" android:pathData="M5.5,14.7c3.6,-3.2 9.4,-3.2 13,0l-1.7,1.9c-2.7,-2.4 -6.9,-2.4 -9.6,0z"/>
    <path android:fillColor="#FFFFFFFF" android:pathData="M2,10.7c5.5,-5 14.5,-5 20,0l-1.7,1.9c-4.6,-4.1 -12,-4.1 -16.6,0z"/>
</vector>
""")
write("app/src/main/res/drawable/ic_pp_sync.xml", """<vector xmlns:android="http://schemas.android.com/apk/res/android"
    android:width="24dp" android:height="24dp" android:viewportWidth="24" android:viewportHeight="24">
    <path android:fillColor="#FFFFFFFF" android:pathData="M7,7h9.2l-2.6,-2.6L15,3l5,5 -5,5 -1.4,-1.4L16.2,9H7c-2.2,0 -4,1.8 -4,4 0,0.7 0.2,1.4 0.5,2L2,16.5A6,6 0,0 1,7 7z"/>
    <path android:fillColor="#FFFFFFFF" android:pathData="M17,17H7.8l2.6,2.6L9,21l-5,-5 5,-5 1.4,1.4L7.8,15H17c2.2,0 4,-1.8 4,-4 0,-0.7 -0.2,-1.4 -0.5,-2L22,7.5A6,6 0,0 1,17 17z"/>
</vector>
""")
write("app/src/main/res/drawable/ic_pp_service.xml", """<vector xmlns:android="http://schemas.android.com/apk/res/android"
    android:width="24dp" android:height="24dp" android:viewportWidth="24" android:viewportHeight="24">
    <path android:fillColor="#FFFFFFFF" android:pathData="M4,4h16a2,2 0,0 1,2 2v4a2,2 0,0 1,-2 2H4a2,2 0,0 1,-2 -2V6a2,2 0,0 1,2 -2zM6,7a1,1 0,1 0,0 2,1 1,0 0,0 0,-2zM9,7h9v2H9z"/>
    <path android:fillColor="#FFFFFFFF" android:pathData="M4,13h16a2,2 0,0 1,2 2v3a2,2 0,0 1,-2 2H4a2,2 0,0 1,-2 -2v-3a2,2 0,0 1,2 -2zM6,15.5a1,1 0,1 0,0 2,1 1,0 0,0 0,-2zM9,15.5h9v2H9z"/>
</vector>
""")

p = "app/src/main/java/vn/pickpack1291/app/beta/DropReceiveFeature.kt"
d = read(p)
d = replace_once(
    d,
    'actions.addView(selectAll,LinearLayout.LayoutParams(0,dp(44),.9f).apply{marginStart=dp(3);marginEnd=dp(3)});actions.addView(deleteSelected,LinearLayout.LayoutParams(0,dp(44),1f).apply{marginStart=dp(3)})',
    'actions.addView(selectAll,LinearLayout.LayoutParams(0,dp(44),.95f).apply{marginStart=dp(3);marginEnd=dp(3)});actions.addView(deleteSelected,LinearLayout.LayoutParams(0,dp(44),.95f).apply{marginStart=dp(3)})',
    "equal drop action buttons",
)
render = r"""        fun renderDropList(items:List<JSONObject>){
            val sorted=items.sortedByDescending{runCatching{java.time.Instant.parse(it.optString("created_at")).toEpochMilli()}.getOrDefault(0L)}
            lastDropItems=sorted
            if(dropPageStart>=sorted.size&&dropPageStart>0)dropPageStart=((sorted.size-1).coerceAtLeast(0)/dropPageSize)*dropPageSize
            val pageItems=sorted.drop(dropPageStart).take(dropPageSize)
            val generation=++dropRenderGeneration
            dropList.removeAllViews();displayedDropIds=pageItems.map{it.optString("record_id")}.filter{it.isNotBlank()}
            selectedDropIds.retainAll(sorted.map{it.optString("record_id")}.filter{it.isNotBlank()}.toSet());updateDeleteSelection()
            if(sorted.isEmpty()){dropList.addView(text("Chưa có dữ liệu nhận hàng rớt.",9.7f,muted,false));return}
            val border=Color.rgb(203,213,225)
            val headerFill=Color.rgb(238,244,247)
            fun tableCell(value:String,header:Boolean=false,gravityValue:Int=Gravity.START):TextView=text(value,if(header)8.5f else 8.8f,ink,header).apply{
                gravity=gravityValue or Gravity.CENTER_VERTICAL
                minHeight=dp(if(header)36 else 44)
                setPadding(dp(5),dp(4),dp(5),dp(4))
                maxLines=2
                background=GradientDrawable().apply{setColor(if(header)headerFill else Color.WHITE);setStroke(dp(1),border)}
            }
            fun addTableHeader(){
                val header=row().apply{gravity=Gravity.CENTER_VERTICAL}
                if(canDelete)header.addView(tableCell("Chọn",true,Gravity.CENTER),LinearLayout.LayoutParams(0,dp(38),.58f))
                header.addView(tableCell("Thời gian",true),LinearLayout.LayoutParams(0,dp(38),1.22f))
                header.addView(tableCell("Vị trí",true),LinearLayout.LayoutParams(0,dp(38),.82f))
                header.addView(tableCell("DO",true),LinearLayout.LayoutParams(0,dp(38),1.08f))
                header.addView(tableCell("Số kiện",true,Gravity.CENTER),LinearLayout.LayoutParams(0,dp(38),.78f))
                dropList.addView(header,LinearLayout.LayoutParams(-1,dp(38)))
            }
            fun addPager(){
                val from=dropPageStart+1;val to=(dropPageStart+pageItems.size).coerceAtMost(sorted.size)
                val nav=row()
                val prev=button("‹ 50 TRƯỚC",navy).apply{visibility=if(dropPageStart>0)View.VISIBLE else View.INVISIBLE;setOnClickListener{dropPageStart=(dropPageStart-dropPageSize).coerceAtLeast(0);renderDropList(lastDropItems)}}
                val count=text("$from–$to / ${sorted.size}",8.8f,muted,true).apply{gravity=Gravity.CENTER}
                val next=button("50 TIẾP ›",teal).apply{visibility=if(dropPageStart+dropPageSize<sorted.size)View.VISIBLE else View.INVISIBLE;setOnClickListener{dropPageStart+=dropPageSize;renderDropList(lastDropItems)}}
                nav.addView(prev,LinearLayout.LayoutParams(0,dp(36),1f).apply{marginEnd=dp(3)});nav.addView(count,LinearLayout.LayoutParams(0,dp(36),.8f));nav.addView(next,LinearLayout.LayoutParams(0,dp(36),1f).apply{marginStart=dp(3)})
                dropList.addView(gap(7));dropList.addView(nav,LinearLayout.LayoutParams(-1,dp(36)))
            }
            addTableHeader()
            fun addDropChunk(from:Int){
                if(generation!=dropRenderGeneration)return
                val to=minOf(from+20,pageItems.size)
                for(i in from until to){
                    val x=pageItems[i];val id=x.optString("record_id")
                    val line=row().apply{gravity=Gravity.CENTER_VERTICAL}
                    if(canDelete){
                        val holder=FrameLayout(activity).apply{
                            background=GradientDrawable().apply{setColor(Color.WHITE);setStroke(dp(1),border)}
                            val check=CheckBox(activity).apply{
                                isChecked=id in selectedDropIds
                                setOnCheckedChangeListener{_,on->if(on)selectedDropIds.add(id)else selectedDropIds.remove(id);updateDeleteSelection()}
                            }
                            addView(check,FrameLayout.LayoutParams(dp(38),dp(38),Gravity.CENTER))
                        }
                        line.addView(holder,LinearLayout.LayoutParams(0,dp(46),.58f))
                    }
                    line.addView(tableCell(fmtDropTime(x.optString("created_at"))),LinearLayout.LayoutParams(0,dp(46),1.22f))
                    line.addView(tableCell(x.optString("location").ifBlank{"-"}),LinearLayout.LayoutParams(0,dp(46),.82f))
                    line.addView(tableCell(x.optString("do_number").ifBlank{"-"}),LinearLayout.LayoutParams(0,dp(46),1.08f))
                    line.addView(tableCell(x.optInt("package_count").toString(),false,Gravity.CENTER),LinearLayout.LayoutParams(0,dp(46),.78f))
                    dropList.addView(line,LinearLayout.LayoutParams(-1,dp(46)))
                }
                if(to<pageItems.size)dropList.post{addDropChunk(to)} else addPager()
            }
            dropList.post{addDropChunk(0)}
        }"""
d = replace_function(d, "        fun renderDropList(items:List<JSONObject>)", render)
write(p, d)

p = "google-apps-script/PICK_PACK_API.gs"
g = read(p)
g = replace_once(
    g,
    "return {serial:r['Seri PDA'],last5:r['5 số cuối Seri']||'',status:r['Tình trạng']||''};",
    "return {serial:r['Seri PDA'],last5:r['5 số cuối Seri']||'',source:r['Nguồn']||'',status:r['Tình trạng']||''};",
    "GAS PDA source",
)
write(p, g)

p = "service/src/mobile_hotfix.ts"
t = read(p)
t = replace_once(
    t,
    'return{serial:x.resource_id,last5:String(m["5 số cuối Seri"]||x.resource_id.slice(-5)),status:x.status_label};',
    'return{serial:x.resource_id,last5:String(m["5 số cuối Seri"]||x.resource_id.slice(-5)),source:String(m["Nguồn"]||m["source"]||""),status:x.status_label};',
    "service PDA source",
)
write(p, t)

write("tools/beta121_owner_ui_pda_source_contract.py", r"""#!/usr/bin/env python3
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
ops=(ROOT/"app/src/main/java/vn/pickpack1291/app/beta/OperationsActivity.kt").read_text(encoding="utf-8")
drop=(ROOT/"app/src/main/java/vn/pickpack1291/app/beta/DropReceiveFeature.kt").read_text(encoding="utf-8")
gradle=(ROOT/"app/build.gradle.kts").read_text(encoding="utf-8")
notes=(ROOT/"app/src/main/java/vn/pickpack1291/app/beta/ReleaseNotes.kt").read_text(encoding="utf-8")
gas=(ROOT/"google-apps-script/PICK_PACK_API.gs").read_text(encoding="utf-8")
service=(ROOT/"service/src/mobile_hotfix.ts").read_text(encoding="utf-8")

assert 'versionCode = 127' in gradle and 'versionName = "0.4.2-beta.121"' in gradle
assert 'const val VERSION_NAME = "0.4.2-beta.121"' in notes

for label in ("Mạng","Đồng bộ","Dịch vụ"):
    assert label in ops
for kind in ('"NETWORK"','"SYNC"','"SERVICE"'):
    assert kind in ops
assert "Thông tin mạng" in ops and "Thông tin đồng bộ" in ops and "Thông tin dịch vụ" in ops

assert 'Triple(R.drawable.ic_pp_account,"Quyền","ROLE_MODE")' not in ops
assert 'normalized=="SERVICE"&&isActualSuper()' in ops
assert 'private lateinit var actualRole: String' in ops
assert 'private fun isActualSuper() = actualRole == "SUPERADMIN"' in ops
assert 'role=value' in ops and 'effectiveRole=value' in ops
assert 'listOf("USER" to "USER","ADMIN" to "ADMIN","SUPERADMIN" to "SUPERADMIN")' in ops

for label in ("TÀI KHOẢN & QUYỀN","GIAO DIỆN","ỨNG DỤNG & CẬP NHẬT","HỖ TRỢ & NHẬT KÝ"):
    assert label in ops
assert 'background=GradientDrawable().apply{setColor(Color.rgb(248,250,252))' in ops

assert 'businessCard(R.drawable.ic_pp_task,"Bảng công Inhouse","Chờ phát triển",false)' in ops

assert 'LinearLayout.LayoutParams(0,dp(44),.95f)' in drop
assert drop.count('LinearLayout.LayoutParams(0,dp(44),.95f)') >= 2
for header in ('"Thời gian"','"Vị trí"','"DO"','"Số kiện"'):
    assert header in drop
assert 'setStroke(dp(1),border)' in drop and 'addTableHeader()' in drop

assert "source:r['Nguồn']||''" in gas
assert 'source:String(m["Nguồn"]||m["source"]||"")' in service

for name in ("ic_pp_network.xml","ic_pp_sync.xml","ic_pp_service.xml"):
    x=(ROOT/"app/src/main/res/drawable"/name).read_text(encoding="utf-8")
    assert "<vector" in x and x.count("<path") >= 2

print("BETA121_OWNER_UI_PDA_SOURCE_CONTRACT_PASS")
""")
print("beta121 deterministic patch applied")

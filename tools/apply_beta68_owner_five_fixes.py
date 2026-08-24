#!/usr/bin/env python3
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
FULL = ROOT / 'app/src/main/java/vn/pickpack1291/app/beta/FullBetaActivity.kt'
OPS = ROOT / 'app/src/main/java/vn/pickpack1291/app/beta/OperationsActivity.kt'
UPDATE = ROOT / 'app/src/main/java/vn/pickpack1291/app/beta/UpdateManager.kt'
GRADLE = ROOT / 'app/build.gradle.kts'


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if old in text:
        return text.replace(old, new, 1)
    if new in text:
        return text
    raise SystemExit(f'{label}: anchor missing')


# Beta67 is abandoned/reserved. Beta68 follows the established code mapping:
# Beta64=70, Beta65=71, Beta66=72, Beta67=73 reserved, therefore Beta68=74.
g = GRADLE.read_text()
g = replace_once(
    g,
    'versionCode = 72\n            versionName = "0.4.2-beta.66"',
    'versionCode = 74\n            versionName = "0.4.2-beta.68"',
    'Beta68 version',
)
GRADLE.write_text(g)


# 1) Replace the abandoned full-frame demo treatment with a restrained login screen
# that uses the same theme language as the rest of the app. Keep company logo + owner copyright.
full = FULL.read_text()
start = full.find('    private fun login() {')
end = full.find('    private fun openMainShell()', start)
if start < 0 or end < 0:
    raise SystemExit('FullBetaActivity.login range missing')

login = r'''    private fun login() {
        foregroundSync.stop()
        liveEmployeeMnv = ""
        currentScreen = "LOGIN"
        accountLogin = ""; accountName = ""; accountRole = ""; accountPosition = ""; accountEmail = ""

        window.statusBarColor = navy
        window.navigationBarColor = Color.WHITE
        @Suppress("DEPRECATION")
        window.decorView.systemUiVisibility = View.SYSTEM_UI_FLAG_LIGHT_NAVIGATION_BAR

        val compact = resources.configuration.screenHeightDp < 620 || resources.configuration.screenWidthDp < 340
        val user = EditText(this).apply {
            hint = "Tài khoản"; setSingleLine(true); textSize = 14f
            setTextColor(ink); setHintTextColor(Color.rgb(148,163,184)); imeOptions = EditorInfo.IME_ACTION_NEXT
            setPadding(dp(13),dp(8),dp(13),dp(8)); minHeight=dp(48)
            background = GradientDrawable().apply { setColor(Color.WHITE); cornerRadius=dp(13).toFloat(); setStroke(dp(1),line) }
        }
        val saved = getPreferences(MODE_PRIVATE).getString("last_login", "").orEmpty()
        if (saved.isNotBlank()) user.setText(saved)
        val pass = EditText(this).apply {
            hint = "Mật khẩu"; setSingleLine(true); textSize = 14f
            setTextColor(ink); setHintTextColor(Color.rgb(148,163,184)); imeOptions = EditorInfo.IME_ACTION_DONE
            inputType = InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_VARIATION_PASSWORD
            setPadding(dp(13),dp(8),dp(13),dp(8)); minHeight=dp(48); background=null
        }
        var passwordVisible=false
        val eye=ImageButton(this).apply {
            setImageResource(R.drawable.ic_login_eye); setBackgroundColor(Color.TRANSPARENT); contentDescription="Hiện mật khẩu"
            setPadding(dp(9),dp(9),dp(9),dp(9)); alpha=.72f
            setOnClickListener {
                passwordVisible=!passwordVisible
                val cursor=pass.selectionStart.coerceAtLeast(0)
                pass.inputType=InputType.TYPE_CLASS_TEXT or if(passwordVisible) InputType.TYPE_TEXT_VARIATION_VISIBLE_PASSWORD else InputType.TYPE_TEXT_VARIATION_PASSWORD
                pass.setSelection(cursor.coerceAtMost(pass.text.length)); alpha=if(passwordVisible)1f else .72f
                contentDescription=if(passwordVisible)"Ẩn mật khẩu" else "Hiện mật khẩu"
            }
        }
        val passWrap=row(Color.WHITE).apply {
            gravity=Gravity.CENTER_VERTICAL; minHeight=dp(48); setPadding(0,0,dp(5),0)
            background=GradientDrawable().apply{setColor(Color.WHITE);cornerRadius=dp(13).toFloat();setStroke(dp(1),line)}
            addView(pass,LinearLayout.LayoutParams(0,dp(48),1f));addView(eye,size(dp(44),dp(44)))
        }

        val card=column(Color.WHITE).apply {
            gravity=Gravity.CENTER_HORIZONTAL
            setPadding(dp(if(compact)16 else 20),dp(if(compact)17 else 22),dp(if(compact)16 else 20),dp(if(compact)18 else 22))
            background=GradientDrawable().apply{setColor(Color.WHITE);cornerRadius=dp(18).toFloat();setStroke(dp(1),line)}
            elevation=dp(2).toFloat()
        }
        card.addView(ImageView(this).apply {
            setImageResource(R.drawable.login_supra_logo);adjustViewBounds=true;scaleType=ImageView.ScaleType.FIT_CENTER
        },size(dp(if(compact)88 else 104),dp(if(compact)88 else 104)))
        card.addView(gap(4))
        card.addView(txt("PICK PACK 1291",if(compact)18f else 20f,navy,true).center())
        card.addView(txt("Supra DC Hưng Yên",11.5f,muted,true).center())
        card.addView(gap(if(compact)14 else 18))
        card.addView(txt("Tài khoản",9.8f,muted,true));card.addView(gap(3));card.addView(user,matchWrap())
        card.addView(gap(9));card.addView(txt("Mật khẩu",9.8f,muted,true));card.addView(gap(3));card.addView(passWrap,matchWrap())

        val forgot=TextView(this).apply {
            text="Quên mật khẩu?";textSize=11.2f;setTextColor(teal);typeface=Typeface.DEFAULT_BOLD;gravity=Gravity.END
            setPadding(dp(4),dp(7),0,dp(9))
            setOnClickListener {
                val loginId=user.text.toString().trim()
                if(loginId.isBlank()){toast("Nhập đúng tài khoản trước khi chọn Quên mật khẩu.");return@setOnClickListener}
                isEnabled=false;text="Đang gửi yêu cầu..."
                api.forgotPassword(loginId){r->runOnUiThread{
                    isEnabled=true;text="Quên mật khẩu?"
                    if(!r.ok){showError(r.error?:"Không gửi được yêu cầu đặt lại mật khẩu");return@runOnUiThread}
                    TopNotice.show(this@FullBetaActivity,"Nếu tài khoản hợp lệ, mật khẩu mới đã được gửi tới mail đã cấu hình.",TopNotice.Kind.SUCCESS)
                }}
            }
        }
        card.addView(forgot,matchWrap())
        val button=Button(this).apply {
            text="Đăng nhập";textSize=14.5f;setTextColor(Color.WHITE);typeface=Typeface.DEFAULT_BOLD;isAllCaps=false;minHeight=dp(50)
            background=gradient(teal,navy,13);elevation=0f
        }
        fun submit(){
            val loginId=user.text.toString().trim();val password=pass.text.toString()
            if(loginId.isBlank()||password.isBlank()){toast("Nhập tài khoản và mật khẩu.");return}
            button.isEnabled=false;button.text="Đang xác thực..."
            api.login(loginId,password){result->runOnUiThread{
                button.isEnabled=true;button.text="Đăng nhập"
                if(!result.ok){showError(result.error?:"Đăng nhập thất bại");return@runOnUiThread}
                val a=result.json?.optJSONObject("account")?:JSONObject()
                accountLogin=a.optString("login_id",loginId);accountName=a.optString("display_name",accountLogin);accountRole=a.optString("role","USER")
                accountPosition=a.optString("position","");accountEmail=a.optString("email","")
                getPreferences(MODE_PRIVATE).edit().putString("last_login",accountLogin).apply();pass.setText("")
                openMainShell();if(MasterDataCache.revision(this@FullBetaActivity)==0L)refreshMasterCache();LocalLogManager.uploadAutomaticPending(this@FullBetaActivity,api)
            }}
        }
        button.setOnClickListener{submit()};user.setOnEditorActionListener{_,id,_->if(id==EditorInfo.IME_ACTION_NEXT){pass.requestFocus();true}else false};pass.setOnEditorActionListener{_,id,_->if(id==EditorInfo.IME_ACTION_DONE){submit();true}else false}
        card.addView(button,matchWrap())

        val copyright=txt("Copyright 2026 Supra DC Hưng Yên - tamnv2 - Chuyên viên Pick Pack 1291",8.6f,muted,false).apply {
            gravity=Gravity.CENTER;maxLines=2;setPadding(dp(8),dp(8),dp(8),0)
        }
        val root=FrameLayout(this).apply{setBackgroundColor(bg)}
        val scroll=ScrollView(this).apply{isFillViewport=true;isVerticalScrollBarEnabled=false}
        val stage=column(bg).apply{
            gravity=Gravity.CENTER;setPadding(dp(16),dp(18),dp(16),dp(14))
            addView(card,LinearLayout.LayoutParams(-1,-2).apply{width=minOf(dp(400),(resources.displayMetrics.widthPixels-dp(32)).coerceAtLeast(dp(260)))})
            addView(gap(12));addView(copyright,matchWrap())
        }
        scroll.addView(stage,ViewGroup.LayoutParams(-1,-1));root.addView(scroll,FrameLayout.LayoutParams(-1,-1))
        root.setOnApplyWindowInsetsListener{v,i->
            val top:Int;val bottom:Int
            if(Build.VERSION.SDK_INT>=30){val bars=i.getInsets(WindowInsets.Type.systemBars());top=bars.top;bottom=bars.bottom}else{@Suppress("DEPRECATION")val t=i.systemWindowInsetTop;@Suppress("DEPRECATION")val b=i.systemWindowInsetBottom;top=t;bottom=b}
            v.setPadding(0,top,0,bottom);i
        }
        setScreen(root);root.requestApplyInsets();user.requestFocus()
    }

'''
full = full[:start] + login + full[end:]
full = replace_once(
    full,
    '    override fun onStart() {\n        super.onStart()\n        if (api.token != null) foregroundSync.start()\n    }',
    '    override fun onStart() {\n        super.onStart()\n        UpdateManager.checkAutomatic(this)\n        if (api.token != null) foregroundSync.start()\n    }',
    'FullBeta automatic OTA foreground hook',
)
FULL.write_text(full)


# 4) Foreground-only automatic OTA discovery. It never polls while background/screen-off.
# Every release-note item is normalized to a visible bullet.
UPDATE.write_text(r'''package vn.pickpack1291.app.beta

import android.app.Activity
import android.app.AlertDialog
import android.app.DownloadManager
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.net.Uri
import android.os.Build
import android.os.Environment
import android.provider.Settings
import android.widget.Toast
import java.security.MessageDigest

object UpdateManager {
    private var busy=false
    private var lastAutomaticCheckAt=0L
    private const val AUTO_DEDUP_MS=30_000L

    fun checkAutomatic(activity:Activity){
        val now=android.os.SystemClock.elapsedRealtime()
        if(busy||activity.isFinishing||activity.isDestroyed||now-lastAutomaticCheckAt<AUTO_DEDUP_MS)return
        lastAutomaticCheckAt=now
        check(activity,false)
    }

    fun openManual(activity:Activity){
        if(busy||activity.isFinishing||activity.isDestroyed)return
        Toast.makeText(activity,"Đang kiểm tra phiên bản mới...",Toast.LENGTH_SHORT).show()
        check(activity,true)
    }

    private fun check(activity:Activity,manual:Boolean){
        if(busy)return
        busy=true
        BetaApiClient(activity.applicationContext).updateCheck(BuildConfig.CHANNEL,BuildConfig.VERSION_NAME){result->activity.runOnUiThread{
            busy=false
            if(activity.isFinishing||activity.isDestroyed)return@runOnUiThread
            if(!result.ok){
                if(manual)AlertDialog.Builder(activity).setTitle("Không kiểm tra được cập nhật").setMessage("Không lấy được thông tin phiên bản mới. Vui lòng kiểm tra mạng và thử lại.\n\nChi tiết: ${result.error?:"Không xác định"}").setPositiveButton("OK",null).show()
                return@runOnUiThread
            }
            val j=result.json
            if(j==null){if(manual)AlertDialog.Builder(activity).setTitle("Không có dữ liệu cập nhật").setMessage("Hệ thống không trả về thông tin phiên bản.").setPositiveButton("OK",null).show();return@runOnUiThread}
            if(!j.optBoolean("available",false)){
                if(manual)AlertDialog.Builder(activity).setTitle("Đang dùng phiên bản mới nhất").setMessage("Phiên bản hiện tại: ${BuildConfig.VERSION_NAME}\nKhông có bản cập nhật mới cho ${channelLabel()}.").setPositiveButton("OK",null).show()
                return@runOnUiThread
            }
            val version=j.optString("version_name").trim();val url=j.optString("apk_url").trim();val sha=j.optString("sha256").trim();val notes=j.optString("notes").trim().take(4000)
            if(version.isBlank()||url.isBlank()){
                if(manual)AlertDialog.Builder(activity).setTitle("Thông tin cập nhật chưa đầy đủ").setMessage("Bản phát hành chưa có đủ phiên bản hoặc đường dẫn tải APK.").setPositiveButton("OK",null).show()
                return@runOnUiThread
            }
            showRelease(activity,version,url,sha,notes)
        }}
    }

    private fun channelLabel():String=if(BuildConfig.CHANNEL=="BETA")"kênh Bản thử nghiệm" else "kênh Bản ổn định"

    private fun bulletNotes(raw:String):String{
        val lines=raw.replace("\r","\n").split('\n').map{it.trim()}.filter{it.isNotBlank()}.map{
            it.replace(Regex("^(?:[-•*]+|\\d+[.)])\\s*"),"").trim()
        }.filter{it.isNotBlank()}
        val items=if(lines.isEmpty())listOf("Chưa có ghi chú chi tiết cho bản phát hành này.") else lines
        return items.joinToString("\n"){"• $it"}
    }

    private fun showRelease(activity:Activity,version:String,url:String,sha:String,notes:String){
        val message=buildString{
            append("Phiên bản đang dùng: ").append(BuildConfig.VERSION_NAME)
            append("\nPhiên bản mới: ").append(version)
            append("\n\nNội dung cập nhật:\n").append(bulletNotes(notes))
            append("\n\nAPK chỉ được tải khi bạn bấm TẢI APK. Sau khi tải xong, ứng dụng kiểm tra SHA-256 rồi mở trình cài đặt Android để bạn xác nhận cài đặt.")
        }
        AlertDialog.Builder(activity).setTitle("Có bản cập nhật $version").setMessage(message).setNegativeButton("ĐỂ SAU",null).setPositiveButton("TẢI APK"){_,_->ensureInstallPermissionThenDownload(activity,version,url,sha)}.show()
    }

    private fun ensureInstallPermissionThenDownload(activity:Activity,version:String,url:String,sha:String){
        if(Build.VERSION.SDK_INT>=Build.VERSION_CODES.O&&!activity.packageManager.canRequestPackageInstalls()){
            AlertDialog.Builder(activity).setTitle("Cần quyền cài APK").setMessage("Android đang chặn cài APK từ Pick Pack 1291. Mở Cài đặt và cho phép nguồn này. Khi quay lại ứng dụng, OTA sẽ được kiểm tra tự động ở foreground; bạn cũng có thể bấm KIỂM TRA CẬP NHẬT trong Cài đặt.").setNegativeButton("HỦY",null).setPositiveButton("MỞ CÀI ĐẶT"){_,_->
                lastAutomaticCheckAt=0L
                activity.startActivity(Intent(Settings.ACTION_MANAGE_UNKNOWN_APP_SOURCES,Uri.parse("package:${activity.packageName}")))
            }.show();return
        }
        download(activity,version,url,sha)
    }

    private fun download(activity:Activity,version:String,url:String,expectedSha:String){
        val manager=activity.getSystemService(Context.DOWNLOAD_SERVICE) as DownloadManager
        val fileName="pick-pack-1291-${BuildConfig.CHANNEL.lowercase()}-$version.apk"
        val request=DownloadManager.Request(Uri.parse(url)).setTitle("Pick Pack 1291 $version").setDescription("Đang tải APK cập nhật").setNotificationVisibility(DownloadManager.Request.VISIBILITY_VISIBLE_NOTIFY_COMPLETED).setAllowedOverMetered(true).setAllowedOverRoaming(false).setMimeType("application/vnd.android.package-archive").setDestinationInExternalFilesDir(activity,Environment.DIRECTORY_DOWNLOADS,fileName)
        val id=manager.enqueue(request);Toast.makeText(activity,"Đang tải APK $version...",Toast.LENGTH_SHORT).show()
        val receiver=object:BroadcastReceiver(){override fun onReceive(context:Context?,intent:Intent?){
            if(intent?.getLongExtra(DownloadManager.EXTRA_DOWNLOAD_ID,-1L)!=id)return
            try{activity.unregisterReceiver(this)}catch(_:Throwable){}
            val uri=manager.getUriForDownloadedFile(id)
            if(uri==null){AlertDialog.Builder(activity).setTitle("Tải APK thất bại").setMessage("Không lấy được file APK sau khi tải.").setPositiveButton("OK",null).show();return}
            Thread{val actual=sha256(activity,uri);activity.runOnUiThread{
                if(expectedSha.isNotBlank()&&!actual.equals(expectedSha,ignoreCase=true)){AlertDialog.Builder(activity).setTitle("APK không hợp lệ").setMessage("SHA-256 không khớp. Ứng dụng sẽ không mở file cài đặt.").setPositiveButton("OK",null).show();return@runOnUiThread}
                val install=Intent(Intent.ACTION_VIEW).apply{setDataAndType(uri,"application/vnd.android.package-archive");addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)}
                activity.startActivity(install)
            }}.start()
        }}
        if(Build.VERSION.SDK_INT>=33)activity.registerReceiver(receiver,IntentFilter(DownloadManager.ACTION_DOWNLOAD_COMPLETE),Context.RECEIVER_NOT_EXPORTED)else{@Suppress("DEPRECATION") activity.registerReceiver(receiver,IntentFilter(DownloadManager.ACTION_DOWNLOAD_COMPLETE))}
    }

    private fun sha256(context:Context,uri:Uri):String{
        val md=MessageDigest.getInstance("SHA-256")
        context.contentResolver.openInputStream(uri)?.use{input->val buf=ByteArray(64*1024);while(true){val n=input.read(buf);if(n<=0)break;md.update(buf,0,n)}}?:return ""
        return md.digest().joinToString(""){"%02x".format(it)}
    }
}
''')


# 2,3,5) Operations UI/data correctness.
ops = OPS.read_text()
ops = replace_once(
    ops,
    'val mnv=x.optString("leased_by_mnv").trim().ifBlank{localMnvFor(serial)}',
    'val mnv=localMnvFor(serial)',
    'PDA exchange active-session authority',
)
ops = replace_once(
    ops,
    '"Dung lượng cache" to humanBytes(operationalStore.storageBytes()),',
    '"Dữ liệu người dùng" to humanBytes(appStorageUsage().userDataBytes),\n                "Bộ nhớ đệm" to humanBytes(appStorageUsage().cacheBytes),',
    'App storage labels',
)

storage_helper = r'''    private data class AppStorageUsage(val userDataBytes:Long,val cacheBytes:Long)
    private fun directoryBytes(root:java.io.File?):Long{
        if(root==null||!root.exists())return 0L
        if(root.isFile)return root.length().coerceAtLeast(0L)
        return runCatching{root.listFiles()?.sumOf{directoryBytes(it)}?:0L}.getOrDefault(0L)
    }
    private fun appStorageUsage():AppStorageUsage{
        val cacheRoots=listOf(cacheDir,codeCacheDir).distinctBy{it.absolutePath}
        val cache=cacheRoots.sumOf{directoryBytes(it)}
        val total=directoryBytes(runCatching{java.io.File(applicationInfo.dataDir)}.getOrNull())
        return AppStorageUsage((total-cache).coerceAtLeast(0L),cache.coerceAtLeast(0L))
    }
'''
marker = '    private fun humanBytes(bytes:Long):String=when{'
if 'private data class AppStorageUsage' not in ops:
    if marker not in ops: raise SystemExit('App storage helper insertion marker missing')
    ops = ops.replace(marker, storage_helper + marker, 1)

ops = replace_once(
    ops,
    '        val deviceName="${Build.MANUFACTURER} ${Build.MODEL}".trim()\n        body.addView(details(listOf(',
    '        val deviceName="${Build.MANUFACTURER} ${Build.MODEL}".trim()\n        val storageUsage=appStorageUsage()\n        body.addView(details(listOf(',
    'Settings storage snapshot',
)
def insert_detail_rows(text: str, anchor: str, rows: list[str], label: str) -> str:
    if all(row.split(' to ')[0].strip() in text for row in rows):
        return text
    pattern = re.compile(re.escape(anchor) + r',?')
    m = pattern.search(text)
    if not m:
        raise SystemExit(f'{label}: anchor missing')
    indent = '            '
    block = anchor + ',\n' + ',\n'.join(indent + row for row in rows)
    return text[:m.start()] + block + text[m.end():]

ops = insert_detail_rows(
    ops,
    '"Mã phiên bản" to BuildConfig.VERSION_CODE.toString()',
    [
        '"Dữ liệu người dùng" to humanBytes(storageUsage.userDataBytes)',
        '"Bộ nhớ đệm" to humanBytes(storageUsage.cacheBytes)',
    ],
    'Settings app storage rows',
)
ops = insert_detail_rows(
    ops,
    '"Kiểm tra APK" to "SHA-256 + chữ ký ứng dụng"',
    [
        '"Tự động kiểm tra OTA" to "Khi mở / quay lại ứng dụng"',
        '"Nội dung cập nhật" to "Hiển thị từng mục dạng gạch đầu dòng"',
    ],
    'Settings OTA mode rows',
)

# Trigger OTA detection when the operational shell returns to foreground; de-dup is centralized in UpdateManager.
ops = replace_once(
    ops,
    '    override fun onStart() {\n        super.onStart()\n        PpForegroundGate.enter()',
    '    override fun onStart() {\n        super.onStart()\n        UpdateManager.checkAutomatic(this)\n        PpForegroundGate.enter()',
    'Operations automatic OTA foreground hook',
)

# Better compact values in the three exact header chips: Mạng / Đồng bộ / Dịch vụ.
pattern = re.compile(r'    private fun refreshHeaderConnection\(\)\{[^\n]*\}\n')
replacement = r'''    private fun refreshHeaderConnection(){
        val counts=runCatching{operationalStore.mutationStatusCounts()}.getOrDefault(OperationalDataStore.MutationStatusCounts(0,0,0,0))
        val flow=runCatching{SyncDirectionTracker.snapshot()}.getOrNull()
        val net=runCatching{DeviceNetworkStatus.snapshot(this)}.getOrNull()
        networkStatusText?.text=when{
            net==null->"Đang kiểm tra"
            !net.hasInternet->"Không Internet"
            lastSyncLatencyMs!=null->"${net.transport} • ${lastSyncLatencyMs}ms"
            else->net.transport
        }
        syncStatusText?.text=when{
            counts.review>0->"${counts.review} cần kiểm tra"
            counts.rejected>0->"${counts.rejected} bị từ chối"
            counts.pending>0&&flow?.active==true->"${counts.pending} chờ • đang gửi"
            counts.pending>0->"${counts.pending} chờ"
            lastConnected==true->"0 chờ • hoàn tất"
            else->"Chờ kết nối"
        }
        val provider=serviceProviderFromRuntime()
        serviceStatusText?.text=when{
            provider=="Cloudflare"&&lastSyncLatencyMs!=null->"Cloudflare • ${lastSyncLatencyMs}ms"
            provider=="Google Drive"->"Google Drive • dự phòng"
            provider=="OFFLINE"->"Offline"
            else->provider
        }
    }
'''
ops, n = pattern.subn(replacement, ops, count=1)
if n != 1: raise SystemExit('Header status refresh function anchor missing')
ops = ops.replace('"Độ trễ Cloudflare" to if(ServiceFaultInjection.cloudflareDisabled(this))"Tắt thử nghiệm" else (lastSyncLatencyMs?.let{"$it ms"}?:"Chưa đo")', '"Độ trễ Service" to if(ServiceFaultInjection.cloudflareDisabled(this))"Tắt thử nghiệm" else (lastSyncLatencyMs?.let{"$it ms"}?:"Chưa đo")', 1)

# Do not infer Cloudflare health merely because a configured URL exists.
svc_start = ops.find('    private fun serviceProviderFromRuntime():String{')
svc_end = ops.find('    private fun connectionSummary():String', svc_start)
if svc_start < 0 or svc_end < 0: raise SystemExit('serviceProviderFromRuntime range missing')
svc = r'''    private fun serviceProviderFromRuntime():String{
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
'''
ops = ops[:svc_start] + svc + ops[svc_end:]

# Refresh the current-use PDA list after foreground reconciliation as well as immediately.
ops = replace_once(
    ops,
    '        attach(root,body);refreshList("");serialField.requestFocus()\n    }',
    '        attach(root,body);foregroundSync.requestSync();refreshList("");android.os.Handler(android.os.Looper.getMainLooper()).postDelayed({if(screenState=="PDA_EXCHANGE")refreshList(serialField.text.toString())},900L);serialField.requestFocus()\n    }',
    'PDA exchange post-sync refresh',
)
OPS.write_text(ops)


# Materializer self-checks / regression anchors.
assert 'versionCode = 74' in g and 'versionName = "0.4.2-beta.68"' in g
assert 'versionCode = 1' in g and 'versionName = "0.1.0-stable"' in g
assert 'login_supra_logo' in login
assert 'Copyright 2026 Supra DC Hưng Yên - tamnv2 - Chuyên viên Pick Pack 1291' in login
assert 'login_vietnam_bg' not in login
assert 'Đăng ký' not in login
assert 'Quên mật khẩu?' in login and 'Hiện mật khẩu' in login
assert 'UpdateManager.checkAutomatic(this)' in full
assert 'fun checkAutomatic(activity:Activity)' in UPDATE.read_text()
assert 'return items.joinToString("\\n")' in UPDATE.read_text()
assert 'val mnv=localMnvFor(serial)' in ops
assert 'leased_by_mnv").trim().ifBlank{localMnvFor(serial)}' not in ops
assert '"Dữ liệu người dùng"' in ops and '"Bộ nhớ đệm"' in ops
assert 'private data class AppStorageUsage' in ops
assert '"Mạng"' in ops and '"Đồng bộ"' in ops and '"Dịch vụ"' in ops
assert '0 chờ • hoàn tất' in ops and 'Google Drive • dự phòng' in ops
assert 'UpdateManager.checkAutomatic(this)' in ops
print('BETA68_OWNER_FIVE_FIXES_PASS')

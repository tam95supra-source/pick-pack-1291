package vn.pickpack1291.app.beta

import android.app.Activity
import android.app.AlertDialog
import android.app.DownloadManager
import android.content.BroadcastReceiver
import android.content.Context
import android.content.ClipData
import android.content.Intent
import android.content.IntentFilter
import android.net.Uri
import android.os.Build
import android.os.Environment
import android.provider.Settings
import android.widget.Toast
import androidx.core.content.FileProvider
import java.io.File
import java.security.MessageDigest

object UpdateManager {
    private var busy=false
    private var lastAutomaticCheckAt=0L
    private const val AUTO_DEDUP_MS=30_000L
    private const val PREFS="pp1291_pending_update_v1"
    data class PendingUpdate(val version:String,val url:String,val sha:String,val notes:String,val versionCode:Int)
    data class LatestRelease(val version:String,val notes:String,val versionCode:Int,val publishedAt:String)
    private fun prefs(c:Context)=c.getSharedPreferences(PREFS,Context.MODE_PRIVATE)
    private fun clearPending(c:Context){prefs(c).edit().remove("version").remove("url").remove("sha").remove("notes").remove("version_code").apply()}
    fun latestInfo(c:Context):LatestRelease?{
        val p=prefs(c);val version=p.getString("latest_version","").orEmpty().trim()
        if(version.isBlank())return null
        return LatestRelease(version,p.getString("latest_notes","").orEmpty(),p.getInt("latest_version_code",0),p.getString("latest_published_at","").orEmpty())
    }
    private fun saveLatest(c:Context,version:String,notes:String,code:Int,publishedAt:String){
        if(version.isBlank())return
        prefs(c).edit().putString("latest_version",version).putString("latest_notes",notes).putInt("latest_version_code",code).putString("latest_published_at",publishedAt).apply()
    }
    private fun managedApkName(version:String)="pick-pack-1291-${BuildConfig.CHANNEL.lowercase()}-$version.apk"
    private fun managedDownloadDir(c:Context)=c.getExternalFilesDir(Environment.DIRECTORY_DOWNLOADS)
    private fun pruneManagedUpdateApks(c:Context,keepName:String?=null){
        val dir=managedDownloadDir(c)?:return
        dir.listFiles()?.forEach{file->
            val managed=file.isFile&&file.name.startsWith("pick-pack-1291-")&&file.name.endsWith(".apk",ignoreCase=true)
            if(managed&&file.name!=keepName)runCatching{file.delete()}
        }
    }
    fun pendingInfo(c:Context):PendingUpdate?{
        val p=prefs(c);val v=p.getString("version","").orEmpty().trim()
        if(v.isBlank()){
            pruneManagedUpdateApks(c)
            return null
        }
        if(v==BuildConfig.VERSION_NAME){
            clearPending(c)
            pruneManagedUpdateApks(c)
            return null
        }
        val url=p.getString("url","").orEmpty()
        if(url.isBlank()){
            pruneManagedUpdateApks(c)
            return null
        }
        pruneManagedUpdateApks(c,managedApkName(v))
        return PendingUpdate(v,url,p.getString("sha","").orEmpty(),p.getString("notes","").orEmpty(),p.getInt("version_code",0))
    }
    private fun savePending(c:Context,v:String,url:String,sha:String,notes:String,code:Int){prefs(c).edit().putString("version",v).putString("url",url).putString("sha",sha).putString("notes",notes).putInt("version_code",code).apply()}

    fun checkAutomatic(activity:Activity){
        pendingInfo(activity)
        val now=android.os.SystemClock.elapsedRealtime()
        if(busy||activity.isFinishing||activity.isDestroyed||now-lastAutomaticCheckAt<AUTO_DEDUP_MS)return
        lastAutomaticCheckAt=now
        check(activity,false)
    }

    fun openManual(activity:Activity){
        if(busy||activity.isFinishing||activity.isDestroyed)return
        val pending=pendingInfo(activity)
        if(pending!=null){showRelease(activity,pending.version,pending.url,pending.sha,pending.notes);return}
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
            val version=j.optString("version_name").trim();val url=j.optString("apk_url").trim();val sha=j.optString("sha256").trim();val notes=j.optString("notes").trim().take(4000);val versionCode=j.optInt("version_code",0);val publishedAt=j.optString("published_at").trim()
            if(version.isNotBlank())saveLatest(activity,version,notes,versionCode,publishedAt)
            if(!j.optBoolean("available",false)){
                clearPending(activity)
                if(manual)AlertDialog.Builder(activity).setTitle("Đang dùng phiên bản mới nhất").setMessage("Phiên bản hiện tại: ${BuildConfig.VERSION_NAME}\nKhông có bản cập nhật mới cho ${channelLabel()}.").setPositiveButton("OK",null).show()
                return@runOnUiThread
            }
            if(version.isBlank()||url.isBlank()){
                if(manual)AlertDialog.Builder(activity).setTitle("Thông tin cập nhật chưa đầy đủ").setMessage("Bản phát hành chưa có đủ phiên bản hoặc đường dẫn tải APK.").setPositiveButton("OK",null).show()
                return@runOnUiThread
            }
            savePending(activity,version,url,sha,notes,versionCode)
            showRelease(activity,version,url,sha,notes)
        }}
    }

    private fun channelLabel():String=if(BuildConfig.CHANNEL=="BETA")"kênh Bản thử nghiệm" else "kênh Bản ổn định"

    fun noteItemsForDisplay(raw:String):List<String>{
        val lines=raw.replace("\r","\n").split('\n').map{it.trim()}.filter{it.isNotBlank()}.flatMap{line->
            if(line.contains(" • "))line.split(" • ").map{it.trim()} else listOf(line)
        }.map{it.replace(Regex("^(?:[-•*]+|\\d+[.)])\\s*"),"").trim()}.filter{it.isNotBlank()}
        return if(lines.isEmpty())listOf("Chưa có ghi chú chi tiết cho bản phát hành này.") else lines
    }
    fun bulletNotesForDisplay(raw:String):String=noteItemsForDisplay(raw).joinToString("\n"){"• $it"}
    fun previewNotesForDisplay(raw:String,limit:Int=4):Pair<String,Boolean>{
        val items=noteItemsForDisplay(raw);val shown=items.take(limit.coerceAtLeast(1))
        return shown.joinToString("\n"){"• $it"} to (items.size>shown.size)
    }
    private fun bulletNotes(raw:String):String=bulletNotesForDisplay(raw)

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
        val fileName=managedApkName(version)
        val dir=managedDownloadDir(activity)
        if(dir==null){AlertDialog.Builder(activity).setTitle("Không tạo được file cập nhật").setMessage("Thiết bị không cấp vùng lưu APK cho ứng dụng.").setPositiveButton("OK",null).show();return}
        pruneManagedUpdateApks(activity,fileName)
        val apkFile=File(dir,fileName)
        if(apkFile.exists()&&!apkFile.delete()){AlertDialog.Builder(activity).setTitle("Không chuẩn bị được file cập nhật").setMessage("Không thể thay file APK tải trước đó.").setPositiveButton("OK",null).show();return}
        val request=DownloadManager.Request(Uri.parse(url)).setTitle("Pick Pack 1291 $version").setDescription("Đang tải APK cập nhật").setNotificationVisibility(DownloadManager.Request.VISIBILITY_VISIBLE_NOTIFY_COMPLETED).setAllowedOverMetered(true).setAllowedOverRoaming(false).setMimeType("application/vnd.android.package-archive").setDestinationInExternalFilesDir(activity,Environment.DIRECTORY_DOWNLOADS,fileName)
        val id=manager.enqueue(request);Toast.makeText(activity,"Đang tải APK $version...",Toast.LENGTH_SHORT).show()
        val receiver=object:BroadcastReceiver(){override fun onReceive(context:Context?,intent:Intent?){
            if(intent?.getLongExtra(DownloadManager.EXTRA_DOWNLOAD_ID,-1L)!=id)return
            try{activity.unregisterReceiver(this)}catch(_:Throwable){}
            Thread{
                val actual=if(apkFile.isFile)sha256(apkFile) else ""
                activity.runOnUiThread{
                    if(!apkFile.isFile){AlertDialog.Builder(activity).setTitle("Tải APK thất bại").setMessage("Không tìm thấy APK trong vùng tải an toàn của ứng dụng.").setPositiveButton("OK",null).show();return@runOnUiThread}
                    if(expectedSha.isNotBlank()&&!actual.equals(expectedSha,ignoreCase=true)){apkFile.delete();AlertDialog.Builder(activity).setTitle("APK không hợp lệ").setMessage("SHA-256 không khớp. Ứng dụng sẽ không mở trình cài đặt.").setPositiveButton("OK",null).show();return@runOnUiThread}
                    val uri=FileProvider.getUriForFile(activity,"${activity.packageName}.fileprovider",apkFile)
                    val install=Intent(Intent.ACTION_VIEW).apply{
                        setDataAndType(uri,"application/vnd.android.package-archive")
                        clipData=ClipData.newRawUri("Pick Pack 1291 OTA",uri)
                        addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
                    }
                    runCatching{activity.startActivity(install)}.onFailure{
                        AlertDialog.Builder(activity).setTitle("Không mở được trình cài đặt").setMessage("Android không nhận trình cài APK trên thiết bị này.\n\nChi tiết: ${it.message?:"Không xác định"}").setPositiveButton("OK",null).show()
                    }
                }
            }.start()
        }}
        if(Build.VERSION.SDK_INT>=33)activity.registerReceiver(receiver,IntentFilter(DownloadManager.ACTION_DOWNLOAD_COMPLETE),Context.RECEIVER_NOT_EXPORTED)else{@Suppress("DEPRECATION") activity.registerReceiver(receiver,IntentFilter(DownloadManager.ACTION_DOWNLOAD_COMPLETE))}
    }

    private fun sha256(file:File):String{
        val md=MessageDigest.getInstance("SHA-256")
        file.inputStream().use{input->val buf=ByteArray(64*1024);while(true){val n=input.read(buf);if(n<=0)break;md.update(buf,0,n)}}
        return md.digest().joinToString(""){"%02x".format(it)}
    }
}

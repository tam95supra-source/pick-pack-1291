package vn.pickpack1291.app.beta

import android.content.Context
import android.os.Build
import android.os.SystemClock
import org.json.JSONObject
import java.io.File
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.UUID

object LocalLogManager {
    // S44_SESSION_SINGLEFLIGHT_OBSERVABILITY
    private const val PREFS = "pp1291_log_state"
    private const val KEY_DAILY = "last_daily_log"
    private const val KEY_STATS_INIT = "log_stats_init_v58"
    private const val KEY_TOTAL_FILES = "log_total_files_v58"
    private const val KEY_TOTAL_BYTES = "log_total_bytes_v58"
    private const val KEY_LATEST_AT = "log_latest_at_v58"
    private const val KEY_LATEST_NAME = "log_latest_name_v89"
    private const val KEY_LATEST_FILE_BYTES = "log_latest_file_bytes_v89"

    fun installCrashHandler(context: Context) {
        val previous = Thread.getDefaultUncaughtExceptionHandler()
        Thread.setDefaultUncaughtExceptionHandler { thread, error ->
            runCatching {
                write(context, "CRASH", buildString {
                    appendLine("type=CRASH"); appendCommon(context)
                    appendLine("thread=${safe(thread.name)}")
                    appendLine("exception=${safe(error.javaClass.name)}")
                    appendLine("message=${safe(error.message)}")
                    appendLine("stacktrace="); appendLine(error.stackTraceToString().take(50000))
                })
            }
            previous?.uncaughtException(thread, error)
        }
    }

    fun createDailyIfNeeded(context: Context): File? {
        val day = SimpleDateFormat("yyyyMMdd", Locale.US).format(Date())
        val dailyMarker = "$day|${BuildConfig.VERSION_NAME}"
        val prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        if (prefs.getString(KEY_DAILY, null) == dailyMarker) return null
        val file = write(context, "ANDROID_DAILY", buildString {
            appendLine("type=DAILY"); appendCommon(context)
            appendLine("uptime_ms=${SystemClock.elapsedRealtime()}")
        })
        prefs.edit().putString(KEY_DAILY, dailyMarker).apply()
        return file
    }

    /** Compatibility for the non-launcher preview screen. Production manual reports use sendManualReport(). */
    fun createManualReport(context: Context, screen: String, syncState: String): File =
        write(context, "MANUAL_REPORT", buildString {
            appendLine("type=MANUAL"); appendCommon(context)
            appendLine("screen=${safe(screen)}")
            appendLine("sync_state=${safe(syncState)}")
            appendLine("pending_upload=true")
        })

    fun uploadAutomaticPending(context: Context, api: BetaApiClient) {
        val files = logDir(context).listFiles()?.filter { it.name.startsWith("CRASH_") || it.name.startsWith("ANDROID_DAILY_") }?.sortedBy { it.lastModified() }.orEmpty()
        uploadNext(api, files, 0)
    }

    fun pendingCount(context: Context): Int = logDir(context).listFiles()?.count { it.isFile } ?: 0

    // S59_BETA58_LOG_ACCOUNTING: uploaded files may be deleted locally, but journal totals remain visible.
    fun summary(context:Context):String{
        ensureStats(context)
        val files=logDir(context).listFiles()?.filter{it.isFile}.orEmpty()
        val prefs=context.getSharedPreferences(PREFS,Context.MODE_PRIVATE)
        val total=prefs.getLong(KEY_TOTAL_FILES,files.size.toLong()).coerceAtLeast(files.size.toLong())
        val bytes=prefs.getLong(KEY_TOTAL_BYTES,files.sumOf{it.length()}).coerceAtLeast(files.sumOf{it.length()})
        val latest=maxOf(prefs.getLong(KEY_LATEST_AT,0L),files.maxOfOrNull{it.lastModified()}?:0L)
        fun size(v:Long)=when{v<1024L->"$v B";v<1024L*1024L->String.format(Locale.US,"%.1f KB",v/1024.0);else->String.format(Locale.US,"%.1f MB",v/(1024.0*1024.0))}
        val at=if(latest<=0L)"—" else SimpleDateFormat("HH:mm:ss dd/MM/yyyy",Locale.US).format(Date(latest))
        return "$total tệp • ${size(bytes)} • còn trên máy ${files.size} • mới nhất $at"
    }


    fun detailRows(context:Context):List<Pair<String,String>>{
        ensureStats(context)
        val files=logDir(context).listFiles()?.filter{it.isFile}.orEmpty().sortedByDescending{it.lastModified()}
        val latest=files.firstOrNull()
        val prefs=context.getSharedPreferences(PREFS,Context.MODE_PRIVATE)
        fun size(v:Long)=when{v<1024L->"$v B";v<1024L*1024L->String.format(Locale.US,"%.1f KB",v/1024.0);else->String.format(Locale.US,"%.1f MB",v/(1024.0*1024.0))}
        val latestName=latest?.name?:prefs.getString(KEY_LATEST_NAME,"").orEmpty()
        val latestBytes=latest?.length()?:prefs.getLong(KEY_LATEST_FILE_BYTES,0L)
        val latestAt=maxOf(latest?.lastModified()?:0L,prefs.getLong(KEY_LATEST_AT,0L))
        val at=latestAt.takeIf{it>0L}?.let{SimpleDateFormat("HH:mm:ss dd/MM/yyyy",Locale.US).format(Date(it))}?:"—"
        val state=if(files.isEmpty())"Đã đồng bộ / không có tệp chờ" else "Chờ tải lên hoặc đồng bộ: ${files.size} tệp"
        return listOf(
            "Tên tệp nhật ký" to latestName.ifBlank{"—"},
            "Dung lượng tệp" to size(latestBytes),
            "Thời gian cập nhật mới nhất" to at,
            "Dung lượng lưu trữ còn trống" to size(context.filesDir.usableSpace.coerceAtLeast(0L)),
            "Trạng thái tải lên / đồng bộ" to state
        )
    }

    fun sendManualReport(context: Context, api: BetaApiClient, screen: String, syncState: String, callback: (BetaApiClient.Result) -> Unit) {
        val file = write(context, "MANUAL_REPORT", buildString {
            appendLine("type=MANUAL"); appendCommon(context)
            appendLine("screen=${safe(screen)}")
            appendLine("sync_state=${safe(syncState)}")
            appendLine("uptime_ms=${SystemClock.elapsedRealtime()}")
            appendLine("memory_max_mb=${Runtime.getRuntime().maxMemory() / 1024 / 1024}")
            appendLine("memory_total_mb=${Runtime.getRuntime().totalMemory() / 1024 / 1024}")
            appendLine("memory_free_mb=${Runtime.getRuntime().freeMemory() / 1024 / 1024}")
        })
        uploadFile(api, file, "MANUAL") { r -> if (r.ok) resetAfterSuccessfulManualSend(context); callback(r) }
    }

    @Synchronized private fun resetAfterSuccessfulManualSend(context:Context){
        // Keep journal accounting/last-file metadata after upload; only acknowledged local payload files are cleared.
        logDir(context).listFiles()?.filter{it.isFile}?.forEach{runCatching{it.delete()}}
        DirectOwnerDiagnostics.clear(context)
    }

    private fun uploadNext(api: BetaApiClient, files: List<File>, index: Int) {
        if (index >= files.size) return
        val f = files[index]
        val type = if (f.name.startsWith("CRASH_")) "CRASH" else "DAILY"
        uploadFile(api, f, type) { r ->
            if (r.ok) f.delete()
            if (r.ok || r.code != 401) uploadNext(api, files, index + 1)
        }
    }

    private fun uploadFile(api: BetaApiClient, file: File, type: String, callback: (BetaApiClient.Result) -> Unit) {
        val eventId = UUID.randomUUID().toString()
        val payload = JSONObject().put("text", runCatching { file.readText().take(60000) }.getOrDefault("LOG_READ_FAILED")).put("file_name", file.name)
        api.call("diagnostic_log", JSONObject()
  .put("event_id", eventId)
  .put("log_type", type)
  .put("channel", BuildConfig.CHANNEL)
  .put("app_version", BuildConfig.VERSION_NAME)
  .put("payload", payload)) { result ->
  val ack = result.json?.optString("ack_event_id").orEmpty()
  if (result.ok && ack == eventId) callback(result)
  else callback(BetaApiClient.Result(false, if(result.code>0)result.code else 502, result.json, result.error ?: "LOG_ACK_MISMATCH"))
        }
    }

    private fun StringBuilder.appendCommon(context: Context) {
        appendLine("timestamp=${SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss.SSSZ", Locale.US).format(Date())}")
        appendLine("package=${context.packageName}")
        appendLine("version=${BuildConfig.VERSION_NAME}")
        appendLine("channel=${BuildConfig.CHANNEL}")
        appendLine("manufacturer=${safe(Build.MANUFACTURER)}")
        appendLine("model=${safe(Build.MODEL)}")
        appendLine("android=${safe(Build.VERSION.RELEASE)}")
        appendLine("api=${Build.VERSION.SDK_INT}")
        appendLine("device=${safe(Build.DEVICE)}")
        appendLine("diagnostics_begin=S44_V1")
        runCatching { M2TransportDiagnostics.snapshotLines(context).forEach { appendLine(it) } }
            .onFailure { appendLine("transport_diag_error=${safe(it.javaClass.simpleName+":"+(it.message?:""))}") }
        runCatching { DirectOwnerDiagnostics.snapshotLines(context).forEach { appendLine(it) } }
            .onFailure { appendLine("direct_owner_diag_error=${safe(it.javaClass.simpleName+":"+(it.message?:""))}") }
        runCatching { QrPerformanceDiagnostics.snapshotLines(context).forEach { appendLine(it) } }
            .onFailure { appendLine("qr_perf_diag_error=${safe(it.javaClass.simpleName+":"+(it.message?:""))}") }
        runCatching { ResilienceTestCenter.snapshotLines(context).forEach { appendLine(it) } }
            .onFailure { appendLine("resilience_test_diag_error=${safe(it.javaClass.simpleName+\":\"+(it.message?:\"\"))}") }
        runCatching {
            val arr=OperationalDataStore(context).diagnosticOutbox(50)
            appendLine("outbox_rows=${arr.length()}")
            for(i in 0 until arr.length()){
                val x=arr.optJSONObject(i)?:continue
                appendLine("outbox[$i].event_id=${safe(x.optString("event_id"))}")
                appendLine("outbox[$i].action=${safe(x.optString("action"))}")
                appendLine("outbox[$i].status=${safe(x.optString("status"))}")
                appendLine("outbox[$i].exclusive=${x.optBoolean("exclusive")}")
                appendLine("outbox[$i].attempt_count=${x.optInt("attempt_count")}")
                appendLine("outbox[$i].next_attempt_at=${x.optLong("next_attempt_at")}")
                appendLine("outbox[$i].queued_at=${x.optLong("queued_at")}")
                appendLine("outbox[$i].updated_at=${x.optLong("updated_at")}")
                appendLine("outbox[$i].last_error=${safe(x.optString("last_error"))}")
            }
        }.onFailure { appendLine("outbox_diag_error=${safe(it.javaClass.simpleName+":"+(it.message?:""))}") }
        appendLine("diagnostics_end=S44_V1")
    }

    private fun logDir(context: Context) = File(context.filesDir, "diagnostic_logs").apply { mkdirs() }

    @Synchronized private fun ensureStats(context:Context){
        val prefs=context.getSharedPreferences(PREFS,Context.MODE_PRIVATE)
        if(prefs.getBoolean(KEY_STATS_INIT,false))return
        val files=logDir(context).listFiles()?.filter{it.isFile}.orEmpty()
        prefs.edit()
            .putBoolean(KEY_STATS_INIT,true)
            .putLong(KEY_TOTAL_FILES,files.size.toLong())
            .putLong(KEY_TOTAL_BYTES,files.sumOf{it.length()})
            .putLong(KEY_LATEST_AT,files.maxOfOrNull{it.lastModified()}?:0L)
            .putString(KEY_LATEST_NAME,files.maxByOrNull{it.lastModified()}?.name.orEmpty())
            .putLong(KEY_LATEST_FILE_BYTES,files.maxByOrNull{it.lastModified()}?.length()?:0L)
            .commit()
    }

    @Synchronized private fun recordCreated(context:Context,file:File){
        val prefs=context.getSharedPreferences(PREFS,Context.MODE_PRIVATE)
        if(!prefs.getBoolean(KEY_STATS_INIT,false)){
            val files=logDir(context).listFiles()?.filter{it.isFile}.orEmpty()
            prefs.edit()
                .putBoolean(KEY_STATS_INIT,true)
                .putLong(KEY_TOTAL_FILES,files.size.toLong())
                .putLong(KEY_TOTAL_BYTES,files.sumOf{it.length()})
                .putLong(KEY_LATEST_AT,files.maxOfOrNull{it.lastModified()}?:file.lastModified())
                .putString(KEY_LATEST_NAME,files.maxByOrNull{it.lastModified()}?.name?:file.name)
                .putLong(KEY_LATEST_FILE_BYTES,files.maxByOrNull{it.lastModified()}?.length()?:file.length())
                .commit()
            return
        }
        prefs.edit()
            .putLong(KEY_TOTAL_FILES,prefs.getLong(KEY_TOTAL_FILES,0L)+1L)
            .putLong(KEY_TOTAL_BYTES,prefs.getLong(KEY_TOTAL_BYTES,0L)+file.length())
            .putLong(KEY_LATEST_AT,maxOf(prefs.getLong(KEY_LATEST_AT,0L),file.lastModified()))
            .putString(KEY_LATEST_NAME,file.name)
            .putLong(KEY_LATEST_FILE_BYTES,file.length())
            .commit()
    }

    private fun write(context: Context, prefix: String, content: String): File {
        val stamp = SimpleDateFormat("yyyyMMdd_HHmmss_SSS", Locale.US).format(Date())
        val file=File(logDir(context), "${prefix}_${stamp}.log").apply { writeText(content) }
        recordCreated(context,file)
        return file
    }
    private fun safe(value: String?): String = value.orEmpty().replace("\n", " ").replace("\r", " ").take(300)
}
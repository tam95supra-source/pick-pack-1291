from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, text: str) -> None:
    (ROOT / path).write_text(text, encoding="utf-8")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected 1 occurrence, found {count}")
    return text.replace(old, new, 1)


# 1) Beta58 metadata — Beta57 remains immutable.
gradle_path = "app/build.gradle.kts"
gradle = read(gradle_path)
gradle = replace_once(gradle, 'versionCode = 63\n            versionName = "0.4.2-beta.57"', 'versionCode = 64\n            versionName = "0.4.2-beta.58"', "beta version")
gradle = replace_once(gradle, '// Beta57: owner operational-reset fence; Beta56 remains denylisted/cancelled and VC62 is intentionally skipped.', '// Beta58: owner fixes for log accounting, fallback provider label, and shift reconciliation placement.\n// Beta57 remains immutable; Beta56 remains denylisted/cancelled and VC62 is intentionally skipped.', "beta comment")
write(gradle_path, gradle)


# 2) Persistent diagnostic-log accounting. Uploaded files may be deleted locally, so
# the settings summary must not equate the local queue with the journal total.
log_path = "app/src/main/java/vn/pickpack1291/app/beta/LocalLogManager.kt"
log = read(log_path)
log = replace_once(
    log,
    '    private const val KEY_DAILY = "last_daily_log"\n',
    '    private const val KEY_DAILY = "last_daily_log"\n'
    '    private const val KEY_STATS_INIT = "log_stats_init_v58"\n'
    '    private const val KEY_TOTAL_FILES = "log_total_files_v58"\n'
    '    private const val KEY_TOTAL_BYTES = "log_total_bytes_v58"\n'
    '    private const val KEY_LATEST_AT = "log_latest_at_v58"\n',
    "log stats keys",
)
log = replace_once(
    log,
    '        val day = SimpleDateFormat("yyyyMMdd", Locale.US).format(Date())\n        val prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)\n        if (prefs.getString(KEY_DAILY, null) == day) return null\n',
    '        val day = SimpleDateFormat("yyyyMMdd", Locale.US).format(Date())\n'
    '        val dailyMarker = "$day|${BuildConfig.VERSION_NAME}"\n'
    '        val prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)\n'
    '        if (prefs.getString(KEY_DAILY, null) == dailyMarker) return null\n',
    "daily marker",
)
log = replace_once(log, '        prefs.edit().putString(KEY_DAILY, day).apply()\n', '        prefs.edit().putString(KEY_DAILY, dailyMarker).apply()\n', "daily marker save")
old_summary = '''    // S54_BETA48_OWNER_10_FIXES
    fun summary(context:Context):String{
        val files=logDir(context).listFiles()?.filter{it.isFile}.orEmpty();val bytes=files.sumOf{it.length()};val latest=files.maxOfOrNull{it.lastModified()}?:0L
        fun size(v:Long)=when{v<1024L->"$v B";v<1024L*1024L->String.format(Locale.US,"%.1f KB",v/1024.0);else->String.format(Locale.US,"%.1f MB",v/(1024.0*1024.0))}
        val at=if(latest<=0L)"—" else SimpleDateFormat("HH:mm:ss dd/MM/yyyy",Locale.US).format(Date(latest))
        return "${files.size} tệp • ${size(bytes)} • mới nhất $at"
    }
'''
new_summary = '''    // S59_BETA58_LOG_ACCOUNTING: journal totals survive successful upload cleanup.
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
'''
log = replace_once(log, old_summary, new_summary, "log summary")
old_write = '''    private fun logDir(context: Context) = File(context.filesDir, "diagnostic_logs").apply { mkdirs() }
    private fun write(context: Context, prefix: String, content: String): File {
        val stamp = SimpleDateFormat("yyyyMMdd_HHmmss_SSS", Locale.US).format(Date())
        return File(logDir(context), "${prefix}_${stamp}.log").apply { writeText(content) }
    }
'''
new_write = '''    private fun logDir(context: Context) = File(context.filesDir, "diagnostic_logs").apply { mkdirs() }
    @Synchronized private fun ensureStats(context:Context){
        val prefs=context.getSharedPreferences(PREFS,Context.MODE_PRIVATE)
        if(prefs.getBoolean(KEY_STATS_INIT,false))return
        val files=logDir(context).listFiles()?.filter{it.isFile}.orEmpty()
        prefs.edit()
            .putBoolean(KEY_STATS_INIT,true)
            .putLong(KEY_TOTAL_FILES,files.size.toLong())
            .putLong(KEY_TOTAL_BYTES,files.sumOf{it.length()})
            .putLong(KEY_LATEST_AT,files.maxOfOrNull{it.lastModified()}?:0L)
            .commit()
    }
    @Synchronized private fun recordCreated(context:Context,file:File){
        ensureStats(context)
        val prefs=context.getSharedPreferences(PREFS,Context.MODE_PRIVATE)
        prefs.edit()
            .putLong(KEY_TOTAL_FILES,prefs.getLong(KEY_TOTAL_FILES,0L)+1L)
            .putLong(KEY_TOTAL_BYTES,prefs.getLong(KEY_TOTAL_BYTES,0L)+file.length())
            .putLong(KEY_LATEST_AT,maxOf(prefs.getLong(KEY_LATEST_AT,0L),file.lastModified()))
            .commit()
    }
    private fun write(context: Context, prefix: String, content: String): File {
        val stamp = SimpleDateFormat("yyyyMMdd_HHmmss_SSS", Locale.US).format(Date())
        val file=File(logDir(context), "${prefix}_${stamp}.log").apply { writeText(content) }
        recordCreated(context,file)
        return file
    }
'''
log = replace_once(log, old_write, new_write, "log write accounting")
write(log_path, log)


# 3) UI/provider + discrepancy placement.
op_path = "app/src/main/java/vn/pickpack1291/app/beta/OperationsActivity.kt"
op = read(op_path)
op = replace_once(
    op,
    '                when (screenState) {\n                    "LISTS" -> listsScreen()\n                    "REPORT" -> reportScreen()\n                    "HISTORY" -> historyScreen()\n                }',
    '                when (screenState) {\n                    "BUSINESS" -> businessHome()\n                    "LISTS" -> listsScreen()\n                    "REPORT" -> reportScreen()\n                    "HISTORY" -> historyScreen()\n                }',
    "business refresh",
)
op = replace_once(
    op,
    '        val root=baseRoot("NGHIỆP VỤ");val body=body()\n        val cards=listOf(',
    '        val root=baseRoot("NGHIỆP VỤ");val body=body()\n        addBusinessShiftReconciliation(body)\n        val cards=listOf(',
    "business discrepancy placement",
)
helper = r'''
    // S59_BETA58_SHIFT_RECONCILIATION_HOME: show only shifts that actually have attendance.
    private fun addBusinessShiftReconciliation(body:LinearLayout){
        val day=operationalStore.loadDay(operationalStore.businessDate())?:return
        val sessions=day.optJSONArray("sessions")?:JSONArray()
        val byShift=linkedMapOf("Ca 1" to mutableListOf<JSONObject>(),"Ca HC" to mutableListOf(),"Ca 2" to mutableListOf())
        for(i in 0 until sessions.length()){
            val ses=sessions.optJSONObject(i)?:continue
            val shift=ses.optString("shift").trim().ifBlank{"Chưa xác định"}
            byShift.getOrPut(shift){mutableListOf()}.add(JSONObject(ses.toString()))
        }
        val visible=byShift.mapNotNull{(shift,rows)->
            val entered=rows.filter{it.optString("enter_at").isNotBlank()||it.optString("state").uppercase() in setOf("ACTIVE","ENDED")}
            if(entered.isEmpty())null else shift to entered
        }
        if(visible.isEmpty())return
        body.addView(section("ĐỐI SOÁT VÀO / RA"))
        visible.forEach{(shift,entered)->
            val exited=entered.filter{it.optString("exit_at").isNotBlank()||it.optString("state").equals("ENDED",true)}
            val pending=entered.filter{it.optString("state").equals("ACTIVE",true)&&it.optString("exit_at").isBlank()}
            val button=smallButton("$shift  •  Vào ${entered.size}  •  Ra ${exited.size}  •  Chưa ra ${pending.size}",if(pending.isNotEmpty())orange else teal)
            button.setOnClickListener{
                if(pending.isEmpty()){
                    TopNotice.show(this,"$shift không có nhân sự đã vào nhưng chưa ra.",TopNotice.Kind.SUCCESS)
                }else{
                    val labels=pending.map{ses->
                        val mnv=ses.optString("mnv").trim()
                        val emp=MasterDataCache.employee(this,mnv)
                        val display=emp?.optString("full_name").orEmpty().ifBlank{ses.optJSONObject("employee_snapshot")?.optString("full_name").orEmpty()}
                        "$mnv • ${display.ifBlank{"Chưa có tên"}}"
                    }
                    AlertDialog.Builder(this)
                        .setTitle("$shift • ${pending.size} nhân sự chưa ra")
                        .setItems(labels.toTypedArray()){_,which->pending.getOrNull(which)?.optString("mnv")?.takeIf{it.isNotBlank()}?.let(::loadEmployee)}
                        .setNegativeButton("Đóng",null)
                        .show()
                }
            }
            body.addView(button,matchWrap());body.addView(gap(5))
        }
        body.addView(gap(4))
    }

'''
op = replace_once(op, '    private fun employeeScan() {\n', helper + '    private fun employeeScan() {\n', "discrepancy helper")
pattern = re.compile(r'\n\s*// S58_BETA57_SHIFT_DISCREPANCY: canonical selected-day Vao/Ra/Chua-ra drilldown\..*?\n\s*val box=column\(bg\);body\.addView\(box,matchWrap\(\)\)', re.S)
m = pattern.search(op)
if not m:
    raise SystemExit("report discrepancy block: not found")
op = op[:m.start()] + '\n        val box=column(bg);body.addView(box,matchWrap())' + op[m.end():]
op = op.replace(';renderShiftDiscrepancy()', '')
if 'renderShiftDiscrepancy' in op:
    raise SystemExit('report discrepancy cleanup: residual renderShiftDiscrepancy')
op = replace_once(
    op,
    '        if(ServiceFaultInjection.cloudflareDisabled(this)){return if(mode=="GOOGLE_FALLBACK"&&!ServiceFaultInjection.googleDisabled(this))"Google Drive" else "OFFLINE"}',
    '        if(ServiceFaultInjection.cloudflareDisabled(this)){return if(!ServiceFaultInjection.googleDisabled(this))"Google Drive" else "OFFLINE"}',
    "fault-injection provider label",
)
write(op_path, op)

print("Beta58 owner fixes applied")

#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OPS = ROOT / 'app/src/main/java/vn/pickpack1291/app/beta/OperationsActivity.kt'
PROJ = ROOT / 'app/src/main/java/vn/pickpack1291/app/beta/PdaLocalProjection.kt'
GRADLE = ROOT / 'app/build.gradle.kts'


def replace_once(path: Path, old: str, new: str, label: str) -> None:
    src = path.read_text(encoding='utf-8')
    count = src.count(old)
    if count != 1:
        raise SystemExit(f'{label}: expected 1 anchor, got {count}')
    path.write_text(src.replace(old, new, 1), encoding='utf-8')


# Beta74 / VC80 is the next Android version after live Beta73 / VC79.
replace_once(GRADLE, 'versionCode = 79\n            versionName = "0.4.2-beta.73"',
             'versionCode = 80\n            versionName = "0.4.2-beta.74"', 'beta74 version')

# Local projection must select the current/latest business session for an employee, not the
# first row returned by the day snapshot. Active wins ended; then the newest timestamps/version win.
replace_once(PROJ,
'''        var session: JSONObject? = null
        for (i in 0 until sessions.length()) {
            val candidate = sessions.optJSONObject(i) ?: continue
            if (candidate.optString("mnv") == mnv) { session = JSONObject(candidate.toString()); break }
        }''',
'''        var session: JSONObject? = null
        for (i in 0 until sessions.length()) {
            val candidate = sessions.optJSONObject(i) ?: continue
            if (candidate.optString("mnv") != mnv) continue
            val copy = JSONObject(candidate.toString())
            if (session == null || preferSession(copy, session!!)) session = copy
        }''', 'employee latest session')

replace_once(PROJ,
'''            val copy=JSONObject(src.toString());byMnv[who]=copy
            copy.optString("user_pick").trim().takeIf{it.isNotBlank()}?.let(usedPicks::add)''',
'''            val copy=JSONObject(src.toString());val previous=byMnv[who];if(previous==null||preferSession(copy,previous))byMnv[who]=copy
            copy.optString("user_pick").trim().takeIf{it.isNotBlank()}?.let(usedPicks::add)''', 'resource options latest session')

replace_once(PROJ,
'''    private fun copyIfPresent(from: JSONObject, to: JSONObject, vararg keys: String) {''',
'''    private fun preferSession(candidate:JSONObject,current:JSONObject):Boolean {
        val candidateActive=candidate.optString("state").equals("ACTIVE",true)
        val currentActive=current.optString("state").equals("ACTIVE",true)
        if(candidateActive!=currentActive)return candidateActive
        val candidateAt=candidate.optString("enter_at").ifBlank{candidate.optString("exit_at")}
        val currentAt=current.optString("enter_at").ifBlank{current.optString("exit_at")}
        if(candidateAt!=currentAt)return candidateAt>currentAt
        val candidateVersion=candidate.optInt("version",0)
        val currentVersion=current.optInt("version",0)
        if(candidateVersion!=currentVersion)return candidateVersion>currentVersion
        val candidateId=candidate.optString("session_id")
        val currentId=current.optString("session_id")
        return candidateId.isNotBlank()&&currentId.isBlank()
    }

    private fun copyIfPresent(from: JSONObject, to: JSONObject, vararg keys: String) {''', 'prefer session helper')

# Suppress identical employee-tree rebuilds. This preserves the current screen/scroll/form while
# Service confirms the exact same local-pending projection, giving incremental/realtime UX instead
# of a visible full-screen refresh.
replace_once(OPS,
'''    private var liveEmployeeMnv=""
    private var employeeLookupGeneration=0L // S39_EMPLOYEE_SESSION_HISTORY''',
'''    private var liveEmployeeMnv=""
    private var employeeLookupGeneration=0L // S39_EMPLOYEE_SESSION_HISTORY
    private var lastEmployeeRenderSignature="" // Beta74: suppress identical employee full-tree rebuilds.''', 'employee render signature field')

replace_once(OPS,
'''    private fun renderLocalEmployee(mnv:String):Boolean{
        val ctx=PdaLocalProjection.employeeContext(this,mnv) ?: return false''',
'''    private fun employeeRenderSignature(ctx:JSONObject,masters:JSONObject?):String{
        val e=ctx.optJSONObject("employee")?:JSONObject();val s=ctx.optJSONObject("session");val state=ctx.optString("state")
        val parts=mutableListOf(e.optString("mnv"),e.optString("full_name"),e.optString("main_position"),e.optString("supplier"),e.optString("department"),e.optString("site"),e.optString("warehouse"),state,ctx.optString("reconciliation_state"))
        if(s!=null)parts.addAll(listOf(s.optString("session_id"),s.optString("state"),s.optString("version"),s.optString("shift"),s.optString("enter_at"),s.optString("exit_at"),s.optString("pda_serial"),s.optString("user_pick"),s.optString("pack_table"),s.optString("user_pack"),(s.optJSONArray("positions_v64")?:JSONArray()).toString(),(s.optJSONArray("resource_assignments_v64")?:JSONArray()).toString()))
        if(state=="NOT_ENTERED"&&masters!=null)parts.add(masters.toString())
        return parts.joinToString("\\u001f")
    }
    private fun renderEmployeeIfChanged(ctx:JSONObject,masters:JSONObject?){
        val mnv=ctx.optJSONObject("employee")?.optString("mnv").orEmpty();val signature=employeeRenderSignature(ctx,masters)
        if(screenState=="EMPLOYEE"&&liveEmployeeMnv==mnv&&lastEmployeeRenderSignature==signature)return
        renderEmployee(ctx,masters)
    }

    private fun renderLocalEmployee(mnv:String):Boolean{
        val ctx=PdaLocalProjection.employeeContext(this,mnv) ?: return false''', 'employee render dedupe helper')

replace_once(OPS, '        renderEmployee(ctx,masters)\n        return true\n    }', '        renderEmployeeIfChanged(ctx,masters)\n        return true\n    }', 'render local dedupe')
replace_once(OPS, '        if(localNow!=null)renderEmployee(localNow,localOptions)else if(cached!=null)renderCachedEmployee(cached)', '        if(localNow!=null)renderEmployeeIfChanged(localNow,localOptions)else if(cached!=null)renderCachedEmployee(cached)', 'load initial dedupe')
replace_once(OPS, '                if(overlay!=null){renderEmployee(overlay,refreshedOptions);TopNotice.show(this@OperationsActivity,"Service chưa xác nhận được; thao tác vẫn lưu local và sẽ đồng bộ khi ứng dụng ở foreground.",TopNotice.Kind.WARNING)}', '                if(overlay!=null){renderEmployeeIfChanged(overlay,refreshedOptions);TopNotice.show(this@OperationsActivity,"Service chưa xác nhận được; thao tác vẫn lưu local và sẽ đồng bộ khi ứng dụng ở foreground.",TopNotice.Kind.WARNING)}', 'load error dedupe')
replace_once(OPS, '            if(overlay!=null&&overlay.optString("reconciliation_state")=="LOCAL_PENDING"){renderEmployee(overlay,refreshedOptions);return@runOnUiThread}', '            if(overlay!=null&&overlay.optString("reconciliation_state")=="LOCAL_PENDING"){renderEmployeeIfChanged(overlay,refreshedOptions);return@runOnUiThread}', 'local pending dedupe')
replace_once(OPS, '                if(overlay!=null)renderEmployee(overlay,refreshedOptions)else if(cached!=null)renderCachedEmployee(cached)', '                if(overlay!=null)renderEmployeeIfChanged(overlay,refreshedOptions)else if(cached!=null)renderCachedEmployee(cached)', 'remote date dedupe')
replace_once(OPS, '            renderEmployee(ctx,options)\n        }}\n    }', '            renderEmployeeIfChanged(ctx,options)\n        }}\n    }', 'remote success dedupe')

# Never ask Service for a resource snapshot with a blank session_id. This is the direct root cause
# seen in the Beta73 manual log: 404 SESSION_NOT_FOUND immediately around otherwise successful
# attendance_enter_v2/session_resource_mutate calls.
replace_once(OPS,
'''        val ses=ctx.optJSONObject("session")
        if((state=="ACTIVE"||state=="ENDED")&&ses!=null&&!ses.has("resource_assignments_v64")){''',
'''        val ses=ctx.optJSONObject("session");val sessionId=ses?.optString("session_id").orEmpty().trim()
        if((state=="ACTIVE"||state=="ENDED")&&ses!=null&&!ses.has("resource_assignments_v64")&&sessionId.isNotBlank()){''', 'blank session snapshot guard')
replace_once(OPS, 'JSONObject().put("session_id",ses.optString("session_id")).put("mnv",currentMnv)', 'JSONObject().put("session_id",sessionId).put("mnv",currentMnv)', 'snapshot exact session id')

# Record the signature only when a new employee tree is actually rendered.
replace_once(OPS,
'''        screenState="EMPLOYEE"
        val e=ctx.optJSONObject("employee")?:JSONObject();val state=ctx.optString("state");val currentMnv=e.optString("mnv");liveEmployeeMnv=currentMnv''',
'''        screenState="EMPLOYEE"
        val e=ctx.optJSONObject("employee")?:JSONObject();val state=ctx.optString("state");val currentMnv=e.optString("mnv");liveEmployeeMnv=currentMnv;lastEmployeeRenderSignature=employeeRenderSignature(ctx,masters)''', 'record render signature')

# While local-pending has no canonical assignment array yet, render the resources already confirmed
# by the user's just-submitted local payload instead of temporarily blanking them until catch-up.
replace_once(OPS,
'''    private fun shiftResourceValue(s:JSONObject,type:String,ended:Boolean):String{
        val rows=if(ended)visibleAssignments(s,type) else activeAssignments(s,type)
        val value=rows.map{it.optString("resource_id").trim()}.filter{it.isNotBlank()}.distinct().joinToString(" • ")
        return if(value.isNotBlank())value else "—"
    }''',
'''    private fun shiftResourceValue(s:JSONObject,type:String,ended:Boolean):String{
        val rows=if(ended)visibleAssignments(s,type) else activeAssignments(s,type)
        val value=rows.map{it.optString("resource_id").trim()}.filter{it.isNotBlank()}.distinct().joinToString(" • ")
        val direct=when(type.uppercase()){ "PDA"->s.optString("pda_serial");"USER_PICK"->s.optString("user_pick");"PACK_TABLE"->s.optString("pack_table");"USER_PACK"->s.optString("user_pack");else->"" }.trim()
        return value.ifBlank{direct}.ifBlank{"—"}
    }''', 'local pending resource display')
replace_once(OPS,
'''    private fun workInfoRows(s:JSONObject,ended:Boolean):List<Pair<String,String>>{
        val positions=(if(ended)allPositionLabels(s) else activePositionLabels(s)).distinct()
        return listOf(''',
'''    private fun workInfoRows(s:JSONObject,ended:Boolean):List<Pair<String,String>>{
        val positions=(if(ended)allPositionLabels(s) else activePositionLabels(s)).distinct().toMutableList()
        if(positions.isEmpty()){
            if(s.optString("pda_serial").isNotBlank()||s.optString("user_pick").isNotBlank())positions.add("Pick")
            if(s.optString("pack_table").isNotBlank()||s.optString("user_pack").isNotBlank())positions.add("Pack")
        }
        return listOf(''', 'local pending position display')

# Regression markers: existing OWNER-requested layout/status/storage/update behavior must remain.
final_ops = OPS.read_text(encoding='utf-8')
for marker in (
    'THÔNG TIN CA', 'THÔNG TIN CÔNG VIỆC',
    'if(!completed)startAnimation',
    'Đã chọn User Pick $id.',
    '"Dung lượng ứng dụng" to humanBytes(appBinaryBytes())',
    '"Dữ liệu ứng dụng trên máy" to humanBytes(appStorageUsage().userDataBytes)',
    '"Bộ nhớ đệm (cache)" to humanBytes(appStorageUsage().cacheBytes)',
    'UpdateManager.pendingInfo(this)',
):
    if marker not in final_ops:
        raise SystemExit(f'beta74 regression marker missing: {marker}')

print('BETA74_OWNER_SCOPE_MATERIALIZED')

#!/usr/bin/env python3
from pathlib import Path

p=Path('app/src/main/java/vn/pickpack1291/app/beta/OperationsActivity.kt')
s=p.read_text(encoding='utf-8')

# Existing deterministic fixes retained.
s=s.replace(
    'val ping=listOf(lastPingMs,lastLatencyMs).filter{it>=0}.minOrNull()',
    'val ping=listOf(lastPingMs,lastLatencyMs).filterNotNull().filter{it>=0}.minOrNull()',
    1,
)

update_anchor='''        fun updateSelectedCount(){selectionCount.text="Đã chọn ${selectedHistoryIds.size} lịch sử"}
        if(isSuper()){
'''
if update_anchor in s:
    s=s.replace(update_anchor,'''        fun updateSelectedCount(){selectionCount.text="Đã chọn ${selectedHistoryIds.size} lịch sử"}
        var deleteAllDateAction:(()->Unit)?=null
        if(isSuper()){
''',1)

early='''            deleteAllDate.setOnClickListener{
                val priorQuery=query;query=""
                val all=loadRows().filter{eventDate(it,selectedDate)==selectedDate&&it.optString("event_type").uppercase()!="HISTORY_DELETE"}.map{it.optString("event_id")}.filter{it.isNotBlank()}.distinct()
                query=priorQuery
                if(all.isEmpty())TopNotice.show(this,"Ngày đã chọn không có lịch sử để xóa.",TopNotice.Kind.INFO) else deleteHistoryBulk(all)
            }
'''
if early in s:
    s=s.replace(early,'''            deleteAllDate.setOnClickListener{deleteAllDateAction?.invoke()}
''',1)

load_pos=s.find('        fun loadRows():MutableList<JSONObject>{')
if load_pos<0:
    raise SystemExit('HISTORY_LOAD_ROWS_NOT_FOUND')
render_pos=s.find('\n        fun render(){',load_pos)
if render_pos<0:
    raise SystemExit('HISTORY_RENDER_AFTER_LOAD_ROWS_NOT_FOUND')
if 'deleteAllDateAction={' not in s[load_pos:render_pos]:
    bind='''
        deleteAllDateAction={
            val priorQuery=query;query=""
            val all=loadRows().filter{eventDate(it,selectedDate)==selectedDate&&it.optString("event_type").uppercase()!="HISTORY_DELETE"}.map{it.optString("event_id")}.filter{it.isNotBlank()}.distinct()
            query=priorQuery
            if(all.isEmpty())TopNotice.show(this,"Ngày đã chọn không có lịch sử để xóa.",TopNotice.Kind.INFO) else deleteHistoryBulk(all)
        }
'''
    s=s[:render_pos]+bind+s[render_pos:]

# Beta126: Kotlin lambda assigned to a variable cannot use return@pump.
old_runner='''        lateinit var pump:()->Unit
        pump={
            if(finished)return@pump
            while(running<maxInFlight&&queue.isNotEmpty()){
                val item=queue.removeFirst();running++
                worker(item){ok,error->runOnUiThread{
                    running--
                    if(ok)success++ else if(error.isNotBlank())failures.add(error)
                    if(queue.isEmpty()&&running==0){finished=true;done(success,failures.toList())}else pump()
                }}
            }
        }
        pump()
'''
new_runner='''        lateinit var pump:()->Unit
        pump={
            if(!finished){
                while(running<maxInFlight&&queue.isNotEmpty()){
                    val item=queue.removeFirst();running++
                    worker(item){ok,error->runOnUiThread{
                        running--
                        if(ok)success++ else if(error.isNotBlank())failures.add(error)
                        if(queue.isEmpty()&&running==0){finished=true;done(success,failures.toList())}else pump()
                    }}
                }
            }
        }
        pump()
'''
if old_runner not in s:
    raise SystemExit('BETA126_PARALLEL_RUNNER_ANCHOR_NOT_FOUND')
s=s.replace(old_runner,new_runner,1)

# Beta126: preserve provider identity only inside refreshHeaderConnection.
wrong='LanAuthorityPolicy.HealthState.DEGRADED->provider.ifBlank{"Đang xác định"}+" • Suy giảm"'
s=s.replace(wrong,'LanAuthorityPolicy.HealthState.DEGRADED->"Suy giảm"')
start=s.find('    private fun refreshHeaderConnection(){')
if start<0:
    raise SystemExit('REFRESH_HEADER_CONNECTION_NOT_FOUND')
end=s.find('\n    private fun ',start+20)
if end<0:
    end=len(s)
chunk=s[start:end]
needle='LanAuthorityPolicy.HealthState.DEGRADED->"Suy giảm"'
if needle not in chunk:
    raise SystemExit('DEGRADED_HEADER_BRANCH_NOT_FOUND')
chunk=chunk.replace(needle,'LanAuthorityPolicy.HealthState.DEGRADED->serviceProviderFromRuntime().ifBlank{"Đang xác định"}+" • Suy giảm"',1)
s=s[:start]+chunk+s[end:]

# Fail closed if deterministic defects remain.
assert 'listOf(lastPingMs,lastLatencyMs).filter{it>=0}.minOrNull()' not in s
assert 'deleteAllDate.setOnClickListener{\n                val priorQuery=query' not in s
assert 'deleteAllDate.setOnClickListener{deleteAllDateAction?.invoke()}' in s
assert 'deleteAllDateAction={' in s
assert 'return@pump' not in s
assert wrong not in s
header=s[start:end]
assert 'LanAuthorityPolicy.HealthState.DEGRADED->serviceProviderFromRuntime().ifBlank' in header

p.write_text(s,encoding='utf-8')
print('BETA126_COMPILE_FIX_PASS')

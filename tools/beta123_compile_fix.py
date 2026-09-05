#!/usr/bin/env python3
from pathlib import Path

p=Path('app/src/main/java/vn/pickpack1291/app/beta/OperationsActivity.kt')
s=p.read_text(encoding='utf-8')

# Nullable ping samples: discard nulls before numeric comparison/min.
s=s.replace(
    'val ping=listOf(lastPingMs,lastLatencyMs).filter{it>=0}.minOrNull()',
    'val ping=listOf(lastPingMs,lastLatencyMs).filterNotNull().filter{it>=0}.minOrNull()',
    1,
)

# History delete-all button is created before local loadRows/eventDate helpers are declared.
# Route the click through a lambda, then bind that lambda only after those helpers are in scope.
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

# Fail closed if either deterministic compile defect remains.
assert 'listOf(lastPingMs,lastLatencyMs).filter{it>=0}.minOrNull()' not in s
assert 'deleteAllDate.setOnClickListener{\n                val priorQuery=query' not in s
assert 'deleteAllDate.setOnClickListener{deleteAllDateAction?.invoke()}' in s
assert 'deleteAllDateAction={' in s

p.write_text(s,encoding='utf-8')
print('BETA123_COMPILE_FIX_PASS')

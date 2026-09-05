from pathlib import Path
p=Path('app/src/main/java/vn/pickpack1291/app/beta/OperationsActivity.kt')
s=p.read_text(encoding='utf-8')
s=s.replace('val all=historyRowsForDate(selectedDate).filter{it.optString("event_type").uppercase()!="HISTORY_DELETE"}.map{it.optString("event_id")}.filter{it.isNotBlank()}.distinct()','val priorQuery=query;query="";val all=loadRows().filter{it.optString("event_type").uppercase()!="HISTORY_DELETE"}.map{it.optString("event_id")}.filter{it.isNotBlank()}.distinct();query=priorQuery')
p.write_text(s,encoding='utf-8')
print('BETA123_FIXUPS_APPLIED')

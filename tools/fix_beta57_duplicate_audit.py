from pathlib import Path

p = Path('app/src/main/java/vn/pickpack1291/app/beta/OperationsActivity.kt')
s = p.read_text()

audit = 'val auditRole=e.optString("actor_role").ifBlank{"—"};val auditDevice=e.optString("device_id").ifBlank{"—"};val auditSource=e.optString("history_source").ifBlank{e.optString("origin")}.ifBlank{"Service"};'
while audit + audit in s:
    s = s.replace(audit + audit, audit)

before_after = 'if(before!=null)d.add("Trước: ${before.toString().take(500)}");if(after!=null)d.add("Sau: ${after.toString().take(500)}")'
while before_after + ';' + before_after in s:
    s = s.replace(before_after + ';' + before_after, before_after)

if audit + audit in s:
    raise SystemExit('duplicate audit identity declarations remain')
if before_after + ';' + before_after in s:
    raise SystemExit('duplicate before/after audit lines remain')
if 'private fun historyEditDialog(' in s:
    raise SystemExit('dead History editor still present')
if 'S58_BETA57_SHIFT_DISCREPANCY' not in s:
    raise SystemExit('shift discrepancy marker missing')
if 'rows.groupBy{e->e.optString("mnv").ifBlank{e.optString("event_id")}}' in s:
    raise SystemExit('History still grouped by employee')

p.write_text(s)
print('PASS - duplicate audit patch cleaned and final History guards hold')

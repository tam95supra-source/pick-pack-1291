#!/usr/bin/env python3
from pathlib import Path

# Reuse the already-reviewed deterministic patcher while removing only its stale one-line
# replication-failure anchor; apply that exact current-source anchor below.
src=Path('tools/r5_quota_circuit_apply.py').read_text(encoding='utf-8')
a=src.index('# On any canonical replica failure')
b=src.index('# ---- master projection ----',a)
exec(compile(src[:a]+src[b:], 'r5_quota_circuit_apply_base', 'exec'), {'__name__':'__main__'})

p=Path('service/src/replication.ts')
t=p.read_text(encoding='utf-8')
old='''const pending=await db.prepare("SELECT COUNT(*) n FROM sheet_replication_outbox WHERE status IN ('PENDING','RETRY','INFLIGHT')").first<{n:number}>();await db.prepare("UPDATE replication_status SET state='DEGRADED',pending_count=?1,retry_count=retry_count+1,last_attempt_at=?2,last_error_class='TRANSIENT',last_error=?3,updated_at=?2 WHERE singleton_id=1").bind(pending?.n??0,failedAt,msg).run();return{ok:false,processed:claimed.length,appended:0,operational:0,pending:pending?.n??0,error:msg};'''
new='''const pending=await db.prepare("SELECT COUNT(*) n FROM sheet_replication_outbox WHERE status IN ('PENDING','RETRY','INFLIGHT')").first<{n:number}>();await db.batch([db.prepare("UPDATE replication_status SET state='DEGRADED',pending_count=?1,retry_count=retry_count+1,last_attempt_at=?2,last_error_class='TRANSIENT',last_error=?3,updated_at=?2 WHERE singleton_id=1").bind(pending?.n??0,failedAt,msg),db.prepare("INSERT INTO system_meta(key,value,updated_at) VALUES('r5_operational_repair_dirty','1',?1) ON CONFLICT(key) DO UPDATE SET value='1',updated_at=excluded.updated_at").bind(failedAt)]);return{ok:false,processed:claimed.length,appended:0,operational:0,pending:pending?.n??0,error:msg};'''
if t.count(old)!=1: raise SystemExit('REPL_DIRTY_V2_ANCHOR_MISSING')
p.write_text(t.replace(old,new,1),encoding='utf-8')
print('R5_QUOTA_CIRCUIT_APPLY_V2_PASS')

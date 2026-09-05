from pathlib import Path

p = Path('service/src/replication.ts')
s = p.read_text(encoding='utf-8')

old_sig = 'export async function replicatePending(db:D1Database,env:Env,limit=50):Promise<{ok:boolean;processed:number;appended:number;operational:number;pending:number;checkpoint?:string;error?:string}>{'
new_sig = 'export async function replicatePending(db:D1Database,env:Env,limit=10):Promise<{ok:boolean;processed:number;appended:number;operational:number;pending:number;checkpoint?:string;error?:string}>{'
if old_sig in s:
    s = s.replace(old_sig, new_sig, 1)
elif new_sig not in s:
    raise SystemExit('REPLICATION_SIGNATURE_ANCHOR_MISSING')

old_limit = 'ORDER BY outbox_id LIMIT ?2").bind(nowIso(),Math.max(1,Math.min(limit,100))).all<OutboxRow>();'
new_limit = 'ORDER BY outbox_id LIMIT ?2").bind(nowIso(),Math.max(1,Math.min(limit,10))).all<OutboxRow>();'
if old_limit in s:
    s = s.replace(old_limit, new_limit, 1)
elif new_limit not in s:
    raise SystemExit('REPLICATION_LIMIT_ANCHOR_MISSING')

old_tail = '''    const operational=await replicateOperational(db,env,token,allEvents),doneAt=nowIso();
    await assertOwnership();
    await db.batch(claimed.map(x=>db.prepare("UPDATE sheet_replication_outbox SET status='SYNCED',claim_token=NULL,claimed_at=NULL,replicated_at=?1,google_checkpoint=?2,last_error_class=NULL,last_error=NULL WHERE outbox_id=?3 AND status='INFLIGHT' AND claim_token=?4").bind(doneAt,checkpoint,x.outbox_id,claim)));'''
new_tail = '''    const operational=await replicateOperational(db,env,token,allEvents);
    await assertOwnership();
    // OPERATIONAL_PROJECTION_ACK_GUARD_V1: attendance events are terminal only when both user-facing projections exist.
    // This makes stale-claim recovery idempotent: existing Event IDs are skipped, missing projections are repaired, and ACK cannot hide a partial write.
    const verifyIndex=await loadOperationalIndex(env,token);
    for(const e of allEvents){
      if(e.event_type==="ATTENDANCE_ENTER"||e.event_type==="ATTENDANCE_EXIT"){
        const raOk=verifyIndex.raEvents.has(e.event_id),historyOk=verifyIndex.historyEvents.has(e.event_id);
        if(!raOk||!historyOk)throw new Error(`REPLICATION_OPERATIONAL_INCOMPLETE:${e.event_id}:RA=${raOk?1:0}:HISTORY=${historyOk?1:0}`);
      }
    }
    await assertOwnership();
    const doneAt=nowIso();
    await db.batch(claimed.map(x=>db.prepare("UPDATE sheet_replication_outbox SET status='SYNCED',claim_token=NULL,claimed_at=NULL,replicated_at=?1,google_checkpoint=?2,last_error_class=NULL,last_error=NULL WHERE outbox_id=?3 AND status='INFLIGHT' AND claim_token=?4").bind(doneAt,checkpoint,x.outbox_id,claim)));'''
if old_tail in s:
    s = s.replace(old_tail, new_tail, 1)
elif 'OPERATIONAL_PROJECTION_ACK_GUARD_V1' not in s:
    raise SystemExit('REPLICATION_ACK_GUARD_ANCHOR_MISSING')

p.write_text(s, encoding='utf-8')
print('BETA123_REPLICATION_PROJECTION_RECOVERY_PATCH_OK')

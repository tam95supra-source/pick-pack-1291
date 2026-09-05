#!/usr/bin/env python3
from pathlib import Path

p=Path('service/src/replication.ts')
s=p.read_text(encoding='utf-8')
start='  const ids=due.map(x=>x.event_id),marks=ids.map(()=>"?").join(",");\n'
end='''    return{ok:false,processed:due.length,appended:0,operational:0,pending:pending?.n??0,error:msg};
  }
'''
if 'REPLICATION_ACK_FENCE_FAILED' in s:
    print('BETA123_REPLICATION_FENCING_ALREADY_APPLIED')
    raise SystemExit(0)
i=s.find(start)
if i<0: raise SystemExit('REPLICATION_PATCH_START_NOT_FOUND')
j=s.find(end,i)
if j<0: raise SystemExit('REPLICATION_PATCH_END_NOT_FOUND')
j+=len(end)
new='''  const claim=crypto.randomUUID(),claimAt=nowIso();
  let claimed:OutboxRow[]=[];
  try{
    await db.batch(due.map(x=>db.prepare("UPDATE sheet_replication_outbox SET status='INFLIGHT',claim_token=?1,claimed_at=?2,attempt_count=attempt_count+1,last_error_class=NULL,last_error=NULL WHERE outbox_id=?3 AND status IN ('PENDING','RETRY')").bind(claim,claimAt,x.outbox_id)));
    const owned=await db.prepare("SELECT outbox_id,event_id,attempt_count FROM sheet_replication_outbox WHERE status='INFLIGHT' AND claim_token=?1 ORDER BY outbox_id").bind(claim).all<OutboxRow>();
    claimed=owned.results??[];
    if(!claimed.length){
      const pending=await db.prepare("SELECT COUNT(*) n FROM sheet_replication_outbox WHERE status IN ('PENDING','RETRY','INFLIGHT')").first<{n:number}>();
      return{ok:true,processed:0,appended:0,operational:0,pending:pending?.n??0,checkpoint:null};
    }
    const assertOwnership=async()=>{
      const ownership=await db.prepare("SELECT COUNT(*) n FROM sheet_replication_outbox WHERE status='INFLIGHT' AND claim_token=?1").bind(claim).first<{n:number}>();
      if((ownership?.n??0)!==claimed.length)throw new Error(`REPLICATION_CLAIM_LOST:${claim}`);
      await db.prepare("UPDATE sheet_replication_outbox SET claimed_at=?1 WHERE status='INFLIGHT' AND claim_token=?2").bind(nowIso(),claim).run();
    };
    await assertOwnership();
    const ids=claimed.map(x=>x.event_id),marks=ids.map(()=>"?").join(",");
    const token=await googleAccessToken(env),present=await ensureReplicaSheet(env,token);
    await assertOwnership();
    const eventsResult=await db.prepare(`SELECT * FROM events WHERE event_id IN (${marks}) ORDER BY authority_epoch,authority_seq`).bind(...ids).all<EventRow>();
    const allEvents=eventsResult.results??[];
    if(allEvents.length!==claimed.length||new Set(allEvents.map(e=>e.event_id)).size!==claimed.length)throw new Error("REPLICATION_EVENT_SET_MISMATCH");
    const technical=allEvents.filter(e=>!present.has(e.event_id));
    await assertOwnership();
    const checkpoint=await appendTechnicalRows(env,token,technical);
    await assertOwnership();
    const operational=await replicateOperational(db,env,token,allEvents),doneAt=nowIso();
    await assertOwnership();
    await db.batch(claimed.map(x=>db.prepare("UPDATE sheet_replication_outbox SET status='SYNCED',claim_token=NULL,claimed_at=NULL,replicated_at=?1,google_checkpoint=?2,last_error_class=NULL,last_error=NULL WHERE outbox_id=?3 AND status='INFLIGHT' AND claim_token=?4").bind(doneAt,checkpoint,x.outbox_id,claim)));
    const ackMarks=claimed.map(()=>"?").join(","),acked=await db.prepare(`SELECT COUNT(*) n FROM sheet_replication_outbox WHERE outbox_id IN (${ackMarks}) AND status='SYNCED'`).bind(...claimed.map(x=>x.outbox_id)).first<{n:number}>();
    if((acked?.n??0)!==claimed.length)throw new Error(`REPLICATION_ACK_FENCE_FAILED:${claim}`);
    const pending=await db.prepare("SELECT COUNT(*) n FROM sheet_replication_outbox WHERE status IN ('PENDING','RETRY','INFLIGHT')").first<{n:number}>();
    await db.prepare("UPDATE replication_status SET target_identity=?1,state='HEALTHY',checkpoint=?2,pending_count=?3,last_attempt_at=?4,last_success_at=?4,last_error_class=NULL,last_error=NULL,updated_at=?4 WHERE singleton_id=1").bind(isStableEnvironment(env)?"STABLE_PRIMARY_GAS:__M1_SERVICE_REPLICA":env.GOOGLE_STAGING_SHEET_ID,checkpoint,pending?.n??0,doneAt).run();
    return{ok:true,processed:claimed.length,appended:technical.length,operational,pending:pending?.n??0,checkpoint};
  }catch(e){
    const msg=String(e).slice(0,700),failedAt=nowIso();
    if(claimed.length){
      await db.batch(claimed.map(x=>{const sec=retryDelaySeconds(x.attempt_count),next=new Date(Date.now()+sec*1000).toISOString();return db.prepare("UPDATE sheet_replication_outbox SET status='RETRY',claim_token=NULL,claimed_at=NULL,next_attempt_at=?1,last_error_class='TRANSIENT',last_error=?2 WHERE outbox_id=?3 AND status='INFLIGHT' AND claim_token=?4").bind(next,msg,x.outbox_id,claim);}));
    }else{
      const next=new Date(Date.now()+30*1000).toISOString();
      await db.prepare("UPDATE sheet_replication_outbox SET status='RETRY',claim_token=NULL,claimed_at=NULL,next_attempt_at=?1,last_error_class='TRANSIENT',last_error=?2 WHERE status='INFLIGHT' AND claim_token=?3").bind(next,msg,claim).run();
    }
    const pending=await db.prepare("SELECT COUNT(*) n FROM sheet_replication_outbox WHERE status IN ('PENDING','RETRY','INFLIGHT')").first<{n:number}>();
    await db.prepare("UPDATE replication_status SET state='DEGRADED',pending_count=?1,retry_count=retry_count+1,last_attempt_at=?2,last_error_class='TRANSIENT',last_error=?3,updated_at=?2 WHERE singleton_id=1").bind(pending?.n??0,failedAt,msg).run();
    return{ok:false,processed:claimed.length,appended:0,operational:0,pending:pending?.n??0,error:msg};
  }
'''
p.write_text(s[:i]+new+s[j:],encoding='utf-8')
print('BETA123_REPLICATION_FENCING_PATCH_APPLIED')

#!/usr/bin/env python3
from pathlib import Path

p=Path('service/src/replication.ts')
s=p.read_text(encoding='utf-8')
old='''  const ids=due.map(x=>x.event_id),marks=ids.map(()=>"?").join(",");
  try{
    const claim=crypto.randomUUID(),at=nowIso();
    await db.batch(due.map(x=>db.prepare("UPDATE sheet_replication_outbox SET status='INFLIGHT',claim_token=?1,claimed_at=?2,attempt_count=attempt_count+1,last_error_class=NULL,last_error=NULL WHERE outbox_id=?3 AND status IN ('PENDING','RETRY')").bind(claim,at,x.outbox_id)));
    const token=await googleAccessToken(env),present=await ensureReplicaSheet(env,token);
    const eventsResult=await db.prepare(`SELECT * FROM events WHERE event_id IN (${marks}) ORDER BY authority_epoch,authority_seq`).bind(...ids).all<EventRow>();
    const allEvents=eventsResult.results??[],technical=allEvents.filter(e=>!present.has(e.event_id));const checkpoint=await appendTechnicalRows(env,token,technical);const operational=await replicateOperational(db,env,token,allEvents);const doneAt=nowIso();
    await db.batch(due.map(x=>db.prepare("UPDATE sheet_replication_outbox SET status='SYNCED',claim_token=NULL,claimed_at=NULL,replicated_at=?1,google_checkpoint=?2,last_error_class=NULL,last_error=NULL WHERE outbox_id=?3").bind(doneAt,checkpoint,x.outbox_id)));
    const pending=await db.prepare("SELECT COUNT(*) n FROM sheet_replication_outbox WHERE status IN ('PENDING','RETRY','INFLIGHT')").first<{n:number}>();
    await db.prepare("UPDATE replication_status SET target_identity=?1,state='HEALTHY',checkpoint=?2,pending_count=?3,last_attempt_at=?4,last_success_at=?4,last_error_class=NULL,last_error=NULL,updated_at=?4 WHERE singleton_id=1").bind(isStableEnvironment(env)?"STABLE_PRIMARY_GAS:__M1_SERVICE_REPLICA":env.GOOGLE_STAGING_SHEET_ID,checkpoint,pending?.n??0,doneAt).run();
    return{ok:true,processed:due.length,appended:technical.length,operational,pending:pending?.n??0,checkpoint};
  }catch(e){
    const message=String(e),retryAt=new Date(Date.now()+retryDelaySeconds(Math.max(...due.map(x=>x.attempt_count+1)))*1000).toISOString(),failedAt=nowIso();
    await db.batch(due.map(x=>db.prepare("UPDATE sheet_replication_outbox SET status='RETRY',claim_token=NULL,claimed_at=NULL,next_attempt_at=?1,last_error_class='TRANSIENT',last_error=?2 WHERE outbox_id=?3").bind(retryAt,message.slice(0,1000),x.outbox_id)));
    const pending=await db.prepare("SELECT COUNT(*) n FROM sheet_replication_outbox WHERE status IN ('PENDING','RETRY','INFLIGHT')").first<{n:number}>();
    await db.prepare("UPDATE replication_status SET state='DEGRADED',pending_count=?1,last_attempt_at=?2,last_error_class='TRANSIENT',last_error=?3,updated_at=?2 WHERE singleton_id=1").bind(pending?.n??due.length,failedAt,message.slice(0,1000)).run();
    return{ok:false,processed:0,appended:0,operational:0,pending:pending?.n??due.length,error:message};
  }
'''
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
    const message=String(e),failedAt=nowIso();
    if(claimed.length){
      const retryAt=new Date(Date.now()+retryDelaySeconds(Math.max(...claimed.map(x=>x.attempt_count)))*1000).toISOString();
      await db.batch(claimed.map(x=>db.prepare("UPDATE sheet_replication_outbox SET status='RETRY',claim_token=NULL,claimed_at=NULL,next_attempt_at=?1,last_error_class='TRANSIENT',last_error=?2 WHERE outbox_id=?3 AND status='INFLIGHT' AND claim_token=?4").bind(retryAt,message.slice(0,1000),x.outbox_id,claim)));
    }else{
      const retryAt=new Date(Date.now()+30*1000).toISOString();
      await db.prepare("UPDATE sheet_replication_outbox SET status='RETRY',claim_token=NULL,claimed_at=NULL,next_attempt_at=?1,last_error_class='TRANSIENT',last_error=?2 WHERE status='INFLIGHT' AND claim_token=?3").bind(retryAt,message.slice(0,1000),claim).run();
    }
    const pending=await db.prepare("SELECT COUNT(*) n FROM sheet_replication_outbox WHERE status IN ('PENDING','RETRY','INFLIGHT')").first<{n:number}>();
    await db.prepare("UPDATE replication_status SET state='DEGRADED',pending_count=?1,last_attempt_at=?2,last_error_class='TRANSIENT',last_error=?3,updated_at=?2 WHERE singleton_id=1").bind(pending?.n??claimed.length,failedAt,message.slice(0,1000)).run();
    return{ok:false,processed:0,appended:0,operational:0,pending:pending?.n??claimed.length,error:message};
  }
'''
if old not in s:
    if 'REPLICATION_ACK_FENCE_FAILED' in s:
        print('BETA123_REPLICATION_FENCING_ALREADY_APPLIED')
        raise SystemExit(0)
    raise SystemExit('REPLICATION_PATCH_ANCHOR_NOT_FOUND')
p.write_text(s.replace(old,new,1),encoding='utf-8')
print('BETA123_REPLICATION_FENCING_PATCH_APPLIED')

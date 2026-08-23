import { json } from "./util";

type AuthorityRow={authority_epoch:number;authority_seq:number;mode:string;scope:string;service_generation:string;updated_at:string};
type ReplicationRow={target_kind:string|null;target_identity:string|null;schema_version:number|null;state:string|null;checkpoint:string|null;pending_count:number|null;retry_count:number|null;last_attempt_at:string|null;last_success_at:string|null;last_error_class:string|null;last_error:string|null;updated_at:string|null};
type PendingRow={n:number;oldest:string|null};

export async function productHealth(env:Env):Promise<Response>{
  const [a,r,p,c]=await Promise.all([
    env.DB.prepare("SELECT authority_epoch,authority_seq,mode,scope,service_generation,updated_at FROM authority_state WHERE singleton_id=1").first<AuthorityRow>(),
    env.DB.prepare("SELECT target_kind,target_identity,schema_version,state,checkpoint,pending_count,retry_count,last_attempt_at,last_success_at,last_error_class,last_error,updated_at FROM replication_status WHERE singleton_id=1").first<ReplicationRow>(),
    env.DB.prepare("SELECT COUNT(*) n,MIN(created_at) oldest FROM sheet_replication_outbox WHERE status IN ('PENDING','RETRY','INFLIGHT')").first<PendingRow>(),
    env.DB.prepare("SELECT COUNT(*) n FROM conflicts WHERE status='OPEN'").first<{n:number}>(),
  ]);
  if(!a)return json({ok:false,service:"pickpack",environment:"production",error:"AUTHORITY_STATE_MISSING"},503);

  const pending=Number(p?.n??0),oldest=p?.oldest??null;
  const oldestMs=oldest?Date.parse(oldest):NaN;
  const lagSeconds=pending>0&&Number.isFinite(oldestMs)?Math.max(0,Math.floor((Date.now()-oldestMs)/1000)):0;
  const drift=Number(c?.n??0);
  let state=String(r?.state??"UNKNOWN"),healthReason="CLEAN";
  if(drift>0){state="DRIFT";healthReason="OPEN_CONFLICTS";}
  else if(pending>0&&lagSeconds>=900){state="LAGGING";healthReason="REPLICATION_LAG";}
  else if(pending>0&&state==="HEALTHY"){state="PENDING";healthReason="REPLICATION_PENDING";}
  else if(state!=="HEALTHY"){healthReason=state;}

  return json({
    ok:true,
    service:"pickpack",
    environment:a.scope==="STAGING_SHADOW"?"staging-shadow":"production",
    generation:a.service_generation,
    authority:{authority_epoch:a.authority_epoch,authority_seq:a.authority_seq,mode:a.mode,scope:a.scope,service_generation:a.service_generation,updated_at:a.updated_at},
    replication:{
      target_kind:r?.target_kind??null,target_identity:r?.target_identity??null,schema_version:r?.schema_version??null,
      state,checkpoint:r?.checkpoint??null,pending_count:pending,retry_count:Number(r?.retry_count??0),
      failed_unresolved_count:0,drift_candidate_count:drift,oldest_pending_at:oldest,lag_seconds:lagSeconds,
      last_attempt_at:r?.last_attempt_at??null,last_success_at:r?.last_success_at??null,last_error_class:r?.last_error_class??null,last_error:r?.last_error??null,updated_at:r?.updated_at??null,
    },
    health_reason:healthReason,
  });
}

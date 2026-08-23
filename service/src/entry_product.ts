import current, { RealtimeHub } from "./entry";
import { authenticate } from "./auth";
import { exchangeGasSession, mobileRead } from "./mobile_hotfix";
import { resourceAdminList, resourceAdminMutate } from "./resource_admin";
import { attendanceEnterDelete, attendanceExitDelete, attendanceTimeCorrect, sessionExitGuarded, sessionWorkUpdate } from "./session_hotfix";
import { superadminDeleteAccounts } from "./beta44_owner";
import { serviceConnectionsV47 } from "./beta47_connections";
import { historyDelete } from "./history_delete";
import { productHealth } from "./health_product";
import { resetFenceGate } from "./reset_fence";
import { replicatePending } from "./replication";
import { flushPushOutbox } from "./push";
import { apiError, json, nowIso } from "./util";

export { RealtimeHub };

const REPLICATION_LEASE_MS=90_000;

async function historicalBusinessDates(request:Request,env:Env):Promise<Response>{
  const auth=await authenticate(env.DB,env,request);if(!auth)return apiError("UNAUTHORIZED","AUTH",401);if(auth.role!=="SUPERADMIN")return apiError("SUPERADMIN_REQUIRED","PERMISSION",403);
  const u=new URL(request.url),limit=Math.min(200,Math.max(1,Number(u.searchParams.get("limit")||50))),beforeRaw=Number(u.searchParams.get("before_sequence")||0),before=Number.isFinite(beforeRaw)&&beforeRaw>0?beforeRaw:null;
  const q=before===null
    ?env.DB.prepare("SELECT business_date,sequence_no FROM business_dates ORDER BY sequence_no DESC LIMIT ?1").bind(limit+1)
    :env.DB.prepare("SELECT business_date,sequence_no FROM business_dates WHERE sequence_no<?1 ORDER BY sequence_no DESC LIMIT ?2").bind(before,limit+1);
  const r=await q.all<{business_date:string;sequence_no:number}>(),all=r.results??[],rows=all.slice(0,limit),next=all.length>limit?rows[rows.length-1]?.sequence_no??null:null;
  return json({ok:true,items:rows,next_before_sequence:next,has_more:all.length>limit});
}

async function recoverAbandonedReplicationClaims(env:Env):Promise<number>{
  const now=nowIso(),cutoff=new Date(Date.now()-REPLICATION_LEASE_MS).toISOString();
  const r=await env.DB.prepare("UPDATE sheet_replication_outbox SET status='RETRY',claim_token=NULL,claimed_at=NULL,next_attempt_at=?1,last_error_class='STALE_INFLIGHT_RECOVERED',last_error='Recovered abandoned replication claim for canonical retry' WHERE status='INFLIGHT' AND (claimed_at IS NULL OR claimed_at<=?2)").bind(now,cutoff).run();
  return Number(r.meta?.changes??0);
}

async function runReplicationSerialized(env:Env,source:string):Promise<void>{
  const now=nowIso(),leaseCutoff=new Date(Date.now()-REPLICATION_LEASE_MS).toISOString();
  const lock=await env.DB.prepare("UPDATE replication_status SET state='RUNNING',last_attempt_at=?1,updated_at=?1 WHERE singleton_id=1 AND (state<>'RUNNING' OR last_attempt_at IS NULL OR last_attempt_at<=?2)").bind(now,leaseCutoff).run();
  if(Number(lock.meta?.changes??0)===0){
    console.log(JSON.stringify({level:"info",kind:"replication_kick_skipped",source,reason:"ACTIVE_LEASE"}));
    return;
  }
  try{
    const recovered=await recoverAbandonedReplicationClaims(env);
    const replication=await replicatePending(env.DB,env);
    if(replication.processed===0){
      const state=replication.pending===0?"HEALTHY":"DEGRADED";
      await env.DB.prepare("UPDATE replication_status SET state=?1,pending_count=?2,last_attempt_at=?3,last_success_at=CASE WHEN ?2=0 THEN ?3 ELSE last_success_at END,last_error_class=CASE WHEN ?2=0 THEN NULL ELSE last_error_class END,last_error=CASE WHEN ?2=0 THEN NULL ELSE last_error END,updated_at=?3 WHERE singleton_id=1").bind(state,replication.pending,nowIso()).run();
    }
    console.log(JSON.stringify({level:replication.ok?"info":"error",kind:"replication_kick_complete",source,recovered,...replication}));
  }catch(e){
    const at=nowIso(),error=String(e).slice(0,700);
    await env.DB.prepare("UPDATE replication_status SET state='DEGRADED',last_attempt_at=?1,last_error_class='TRANSIENT',last_error=?2,updated_at=?1 WHERE singleton_id=1").bind(at,error).run();
    console.log(JSON.stringify({level:"error",kind:"replication_kick_failed",source,error}));
  }
}

function kickReplication(ctx:ExecutionContext,env:Env,source:string):void{
  ctx.waitUntil(runReplicationSerialized(env,source));
}

async function runProductionScheduled(env:Env):Promise<void>{
  // Google projection is authoritative durability work and runs independently from push.
  await runReplicationSerialized(env,"CRON");
  try{
    const push=await flushPushOutbox(env.DB,env);
    console.log(JSON.stringify({level:"info",kind:"scheduled_push_complete",...push}));
  }catch(e){
    console.log(JSON.stringify({level:"error",kind:"scheduled_push_failed",error:String(e).slice(0,500)}));
  }
}

function shouldKickAfterResponse(method:string,response:Response):boolean{return method==="POST"&&response.status>=200&&response.status<300;}

export default {
  async fetch(request:Request,env:Env,ctx:ExecutionContext):Promise<Response>{
    const u=new URL(request.url),method=request.method.toUpperCase();
    if(u.pathname==="/health"&&method==="GET")return productHealth(env);
    const fence=await resetFenceGate(request,env);if(fence)return fence;
    if(u.pathname==="/v1/auth/gas-session"&&method==="POST")return exchangeGasSession(request,env);
    if(u.pathname==="/v1/mobile/read"&&method==="POST")return mobileRead(request,env);
    if(u.pathname==="/v1/admin/business-dates"&&method==="GET")return historicalBusinessDates(request,env);
    if(u.pathname==="/v1/service/connections"&&method==="GET")return serviceConnectionsV47(request,env);
    if(u.pathname==="/v1/admin/accounts/delete"&&method==="POST"){
      const response=await superadminDeleteAccounts(request,env);if(shouldKickAfterResponse(method,response))kickReplication(ctx,env,u.pathname);return response;
    }
    if(u.pathname==="/v1/admin/resources"&&method==="GET")return resourceAdminList(request,env);
    if(u.pathname==="/v1/admin/resources"&&method==="POST"){
      const response=await resourceAdminMutate(request,env);if(shouldKickAfterResponse(method,response))kickReplication(ctx,env,u.pathname);return response;
    }
    if(u.pathname==="/v1/history/delete"&&method==="POST"){
      const response=await historyDelete(request,env);if(shouldKickAfterResponse(method,response))kickReplication(ctx,env,u.pathname);return response;
    }
    if(u.pathname==="/v1/session/work"&&method==="POST"){
      const response=await sessionWorkUpdate(request,env);if(shouldKickAfterResponse(method,response))kickReplication(ctx,env,u.pathname);return response;
    }
    if(u.pathname==="/v1/session/exit"&&method==="POST"){
      const response=await sessionExitGuarded(request,env);if(shouldKickAfterResponse(method,response))kickReplication(ctx,env,u.pathname);return response;
    }
    if(u.pathname==="/v1/session/time-correction"&&method==="POST"){
      const response=await attendanceTimeCorrect(request,env);if(shouldKickAfterResponse(method,response))kickReplication(ctx,env,u.pathname);return response;
    }
    if(u.pathname==="/v1/session/delete-exit"&&method==="POST"){
      const response=await attendanceExitDelete(request,env);if(shouldKickAfterResponse(method,response))kickReplication(ctx,env,u.pathname);return response;
    }
    if(u.pathname==="/v1/session/delete-enter"&&method==="POST"){
      const response=await attendanceEnterDelete(request,env);if(shouldKickAfterResponse(method,response))kickReplication(ctx,env,u.pathname);return response;
    }
    const response=await current.fetch(request,env,ctx);
    if(shouldKickAfterResponse(method,response)&&!u.pathname.startsWith("/v1/auth/"))kickReplication(ctx,env,u.pathname);
    return response;
  },
  // Cron is now retry-only. Normal successful POST mutations kick projection immediately.
  async scheduled(_controller:ScheduledController,env:Env,ctx:ExecutionContext):Promise<void>{
    ctx.waitUntil(runProductionScheduled(env));
  },
} satisfies ExportedHandler<Env>;

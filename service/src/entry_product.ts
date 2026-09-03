import current, { RealtimeHub } from "./entry";
import { authenticate } from "./auth";
import { exchangeGasSession, mobileRead } from "./mobile_hotfix";
import { resourceAdminList, resourceAdminMutate } from "./resource_admin";
import { attendanceExitDelete, attendanceTimeCorrect, flushSessionSpecialProjections, sessionExitGuarded, sessionWorkUpdate } from "./session_hotfix";
import { attendanceEnterV2, sessionResourceMutateV2, sessionResourceSnapshotV2 } from "./session_v2_compat";
import { superadminDeleteAccounts } from "./beta44_owner";
import { serviceConnectionsV47 } from "./beta47_connections";
import { backfillAllHistoryAudit } from "./beta47_history_audit";
import { reconcileBeta47OperationalProjection } from "./beta47_projection";
import { historyDelete } from "./history_delete";
import { replicateOutboundPending } from "./outbound_beta78";
import { enqueueInvalidation } from "./push";
import { claimMaintenance, d1CapacitySnapshot, recordVerifiedBackup, runD1Retention } from "./d1_maintenance";
import { apiError, json, nowIso } from "./util";
import { lanReplayBatch } from "./lan_recovery";
import { documentCategories, documentCategoryMutate, documentComplete, documentDeleteMutate, documentList, documentMedia, documentUpdate, documentUploadSession, flushDocumentAuditHistory, processDocumentCategoryMutations, processDocumentDeleteMutations } from "./document_management";

export { RealtimeHub };

function environmentFence(request:Request,env:Env):Response|null{
  const path=new URL(request.url).pathname;
  if(path==="/health"||path.startsWith("/internal/"))return null;
  const expected=String(env.ENVIRONMENT_ID||"BETA").toUpperCase();
  const expectedAudience=String(env.SERVICE_AUDIENCE||(expected==="STABLE"?"PICK_PACK_1291_STABLE":"PICK_PACK_1291_BETA"));
  const got=String(request.headers.get("x-pick-pack-environment")||"").toUpperCase();
  const audience=String(request.headers.get("x-pick-pack-audience")||"");
  if(got&&got!==expected)return apiError("ENVIRONMENT_MISMATCH","PERMISSION",409,false);
  if(audience&&audience!==expectedAudience)return apiError("SERVICE_AUDIENCE_MISMATCH","PERMISSION",409,false);
  if(expected==="STABLE"&&(!got||!audience))return apiError("ENVIRONMENT_ID_REQUIRED","PERMISSION",403,false);
  return null;
}

async function infraCapacity(request:Request,env:Env):Promise<Response>{
  const auth=await authenticate(env.DB,env,request);if(!auth)return apiError("UNAUTHORIZED","AUTH",401);if(auth.role!=="SUPERADMIN")return apiError("SUPERADMIN_REQUIRED","PERMISSION",403);
  return json({ok:true,capacity:await d1CapacitySnapshot(env.DB)});
}
async function infraBackupVerified(request:Request,env:Env):Promise<Response>{
  const auth=await authenticate(env.DB,env,request);if(!auth)return apiError("UNAUTHORIZED","AUTH",401);if(auth.role!=="SUPERADMIN")return apiError("SUPERADMIN_REQUIRED","PERMISSION",403);
  let body:Record<string,unknown>;try{body=await request.json() as Record<string,unknown>;}catch{return apiError("JSON_INVALID","VALIDATION",400);}
  try{await recordVerifiedBackup(env.DB,{backup_id:String(body.backup_id||""),created_at:String(body.created_at||nowIso()),source:String(body.source||""),first_event:String(body.first_event||""),last_event:String(body.last_event||""),first_business_date:String(body.first_business_date||""),last_business_date:String(body.last_business_date||""),row_counts_json:JSON.stringify(body.row_counts||{}),table_counts_json:JSON.stringify(body.table_counts||{}),checksum:String(body.checksum||""),schema_version:Number(body.schema_version||0),checkpoint:String(body.checkpoint||"")});return json({ok:true});}
  catch(e){return apiError(String(e).includes("BACKUP_MANIFEST_REQUIRED")?"BACKUP_MANIFEST_REQUIRED":"BACKUP_VERIFY_RECORD_FAILED","VALIDATION",400);}
}

async function historicalBusinessDates(request:Request,env:Env):Promise<Response>{
  const auth=await authenticate(env.DB,env,request);if(!auth)return apiError("UNAUTHORIZED","AUTH",401);if(auth.role!=="SUPERADMIN")return apiError("SUPERADMIN_REQUIRED","PERMISSION",403);
  const u=new URL(request.url),limit=Math.min(200,Math.max(1,Number(u.searchParams.get("limit")||50))),beforeRaw=Number(u.searchParams.get("before_sequence")||0),before=Number.isFinite(beforeRaw)&&beforeRaw>0?beforeRaw:null;
  const q=before===null
    ?env.DB.prepare("SELECT business_date,sequence_no FROM business_dates ORDER BY sequence_no DESC LIMIT ?1").bind(limit+1)
    :env.DB.prepare("SELECT business_date,sequence_no FROM business_dates WHERE sequence_no<?1 ORDER BY sequence_no DESC LIMIT ?2").bind(before,limit+1);
  const r=await q.all<{business_date:string;sequence_no:number}>(),all=r.results??[],rows=all.slice(0,limit),next=all.length>limit?rows[rows.length-1]?.sequence_no??null:null;
  return json({ok:true,items:rows,next_before_sequence:next,has_more:all.length>limit});
}

async function broadcastCatalogRevision(env:Env):Promise<void>{
  const [rev,a]=await Promise.all([
    env.DB.prepare("SELECT revision FROM revision_state WHERE namespace='catalogs'").first<{revision:number}>(),
    env.DB.prepare("SELECT authority_epoch,authority_seq FROM authority_state WHERE singleton_id=1").first<{authority_epoch:number;authority_seq:number}>(),
  ]);
  const revision=Number(rev?.revision??0);if(revision<=0)return;
  await enqueueInvalidation(env.DB,"catalogs",revision);
  try{const hub=env.REALTIME_HUB.getByName("master:global") as unknown as {invalidate(message:Record<string,unknown>):Promise<number>};await hub.invalidate({type:"MASTER_CHANGED",namespace:"catalogs",revision,authority_epoch:Number(a?.authority_epoch??0),authority_seq:Number(a?.authority_seq??0)});}catch{}
}

export default {
  async fetch(request:Request,env:Env,ctx:ExecutionContext):Promise<Response>{
    const pre=new URL(request.url);
    if(pre.pathname==="/environment.json"&&request.method.toUpperCase()==="GET"){
      const environmentId=String(env.ENVIRONMENT_ID||"BETA").toUpperCase(),serviceAudience=String(env.SERVICE_AUDIENCE||(environmentId==="STABLE"?"PICK_PACK_1291_STABLE":"PICK_PACK_1291_BETA"));
      return json({ok:true,environment_id:environmentId,service_audience:serviceAudience,release_channel:environmentId,target_origin:environmentId==="STABLE"?"https://pickpack1291.cc.cd":"https://beta.pickpack1291.cc.cd"});
    }
    const fence=environmentFence(request,env);if(fence)return fence;
    const u=pre,method=request.method.toUpperCase();
    if(u.pathname==="/v1/auth/gas-session"&&method==="POST")return exchangeGasSession(request,env);
    if(u.pathname==="/v1/mobile/read"&&method==="POST")return mobileRead(request,env);
    if(u.pathname==="/v1/admin/business-dates"&&method==="GET")return historicalBusinessDates(request,env);
    if(u.pathname==="/v1/admin/infra/capacity"&&method==="GET")return infraCapacity(request,env);
    if(u.pathname==="/v1/admin/infra/backup-verification"&&method==="POST")return infraBackupVerified(request,env);
    if(u.pathname==="/v1/service/connections"&&method==="GET")return serviceConnectionsV47(request,env);
    if(u.pathname==="/v1/lan-replay/batch"&&method==="POST")return lanReplayBatch(request,env);
    if(u.pathname==="/v1/documents/categories"&&method==="GET")return documentCategories(request,env);
    if(u.pathname==="/v1/documents/categories"&&method==="POST")return documentCategoryMutate(request,env);
    if(u.pathname==="/v1/documents"&&method==="GET")return documentList(request,env);
    if(u.pathname==="/v1/documents/upload-session"&&method==="POST")return documentUploadSession(request,env);
    if(u.pathname==="/v1/documents/complete"&&method==="POST")return documentComplete(request,env);
    if(u.pathname==="/v1/documents/delete"&&method==="POST")return documentDeleteMutate(request,env);
    if(u.pathname==="/v1/documents/update"&&method==="POST")return documentUpdate(request,env);
    const documentMediaParts=u.pathname.split("/");
    if(method==="GET"&&documentMediaParts.length===5&&documentMediaParts[1]==="v1"&&documentMediaParts[2]==="documents"&&documentMediaParts[4]==="media"&&documentMediaParts[3]){
      return documentMedia(request,env,decodeURIComponent(documentMediaParts[3]));
    }
    if(u.pathname==="/v1/admin/accounts/delete"&&method==="POST")return superadminDeleteAccounts(request,env);
    if(u.pathname==="/v1/admin/resources"&&method==="GET")return resourceAdminList(request,env);
    if(u.pathname==="/v1/admin/resources"&&method==="POST")return resourceAdminMutate(request,env);
    if(u.pathname==="/v1/history/delete"&&method==="POST")return historyDelete(request,env);
    if(u.pathname==="/v1/session/work"&&method==="POST")return sessionWorkUpdate(request,env);
    if(u.pathname==="/v1/session/enter-v2"&&method==="POST")return attendanceEnterV2(request,env);
    if(u.pathname==="/v1/session/resources/snapshot"&&method==="POST")return sessionResourceSnapshotV2(request,env);
    if(u.pathname==="/v1/session/resources/mutate"&&method==="POST")return sessionResourceMutateV2(request,env);
    if(u.pathname==="/v1/session/exit-v2"&&method==="POST")return sessionExitGuarded(request,env);
    if(u.pathname==="/v1/session/exit"&&method==="POST")return sessionExitGuarded(request,env);
    if(u.pathname==="/v1/session/time-correction"&&method==="POST")return attendanceTimeCorrect(request,env);
    if(u.pathname==="/v1/session/delete-exit"&&method==="POST")return attendanceExitDelete(request,env);
    return current.fetch(request,env,ctx);
  },
  async scheduled(controller:ScheduledController,env:Env,ctx:ExecutionContext):Promise<void>{
    await current.scheduled(controller,env,ctx);
    await flushSessionSpecialProjections(env);
    try{
      const docMut=await processDocumentCategoryMutations(env);
      const docDelete=await processDocumentDeleteMutations(env);
      const docHistory=await flushDocumentAuditHistory(env);
      if(docMut.processed>0||docDelete.processed>0||docHistory>0)console.log(JSON.stringify({level:"info",kind:"document_maintenance",category:docMut,delete:docDelete,history:docHistory}));
    }catch(e){console.log(JSON.stringify({level:"error",kind:"document_category_mutations_failed",error:String(e).slice(0,500)}));}
    try{const outbound=await replicateOutboundPending(env);console.log(JSON.stringify({level:"info",kind:"beta78_outbound_replication",...outbound}));}
    catch(e){console.log(JSON.stringify({level:"error",kind:"beta78_outbound_replication_failed",error:String(e).slice(0,500)}));}
    try{
      if(await claimMaintenance(env.DB,"repair-30m",30*60_000)){
        const r=await reconcileBeta47OperationalProjection(env);
        if(r.catalog_changed)await broadcastCatalogRevision(env);
        const historyRows=await backfillAllHistoryAudit(env);
        console.log(JSON.stringify({level:"info",kind:"beta95_bounded_repair",...r,history_backfill_rows:historyRows}));
      }
    }catch(e){console.log(JSON.stringify({level:"error",kind:"beta95_bounded_repair_failed",error:String(e).slice(0,500)}));}
    try{
      if(await claimMaintenance(env.DB,"capacity-30m",30*60_000)){
        const r=await d1CapacitySnapshot(env.DB);
        console.log(JSON.stringify({level:"info",kind:"resilience_capacity",...r}));
      }
    }catch(e){console.log(JSON.stringify({level:"error",kind:"resilience_capacity_failed",error:String(e).slice(0,500)}));}
    try{
      if(await claimMaintenance(env.DB,"retention-daily",24*60*60_000)){
        const r=await runD1Retention(env.DB);
        console.log(JSON.stringify({level:"info",kind:"beta95_d1_retention",...r}));
      }
    }catch(e){console.log(JSON.stringify({level:"error",kind:"beta95_d1_retention_failed",error:String(e).slice(0,500)}));}
  },
} satisfies ExportedHandler<Env>;

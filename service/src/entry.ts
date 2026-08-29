import base, { RealtimeHub } from "./index";
import { authenticate, internalAuthorized } from "./auth";
import { commitAdminAudit, type AdminAuditInput } from "./admin_audit"; // S30_CANONICAL_ADMIN_AUDIT
import { bootstrapGoogleStart, bootstrapGoogleStatus, bootstrapGoogleStep } from "./bootstrap_resumable";
import { bootstrapResourceProjectionStep } from "./bootstrap_resources";
import { currentAuthority, sanitizeSensitive } from "./core";
import { rebuildGoogleStagingFromD1 } from "./dr";
import { importParseXlsx, importTemplateXlsx } from "./import_xlsx";
import { failbackFromFallbackInbox, reconciliationLocked } from "./recovery";
import { resumeFailbackWithLegacyCompat } from "./recovery_resume_compat";
import { apiError, constantTimeEqual, json, nowIso, readJsonBody, sha256Hex } from "./util";
import { legacySyncPortable } from "./legacy_sync_portable";

export { RealtimeHub };


async function recoveryFailback(request:Request,env:Env):Promise<Response>{
  if(!await internalAuthorized(request,env))return apiError("INTERNAL_UNAUTHORIZED","AUTH",401);
  const input=await readJsonBody<{fallback_epoch:number;expected_service_epoch:number;confirmation:string;initiated_by?:string}>(request);
  try{return json(await failbackFromFallbackInbox(env.DB,env,input));}catch(e){console.log(JSON.stringify({level:"error",kind:"failback_failed",error:String(e)}));return apiError("FAILBACK_FAILED","INTEGRITY",409,false,String(e).slice(0,500));}
}
async function recoveryResume(request:Request,env:Env):Promise<Response>{
  if(!await internalAuthorized(request,env))return apiError("INTERNAL_UNAUTHORIZED","AUTH",401);
  const input=await readJsonBody<{fallback_epoch:number;confirmation:string;initiated_by?:string}>(request);
  try{return json(await resumeFailbackWithLegacyCompat(env.DB,env,input));}catch(e){console.log(JSON.stringify({level:"error",kind:"failback_resume_failed",error:String(e)}));return apiError("FAILBACK_RESUME_FAILED","INTEGRITY",409,false,String(e).slice(0,500));}
}
async function adminAudit(request:Request,env:Env):Promise<Response>{
  const auth=await authenticate(env.DB,env,request);if(!auth)return apiError("UNAUTHORIZED","AUTH",401);
  const input=await readJsonBody<AdminAuditInput>(request);
  try{const result=await commitAdminAudit(env.DB,auth,input);return json({ok:true,duplicate:result.duplicate,event:result.event},result.duplicate?200:201);}
  catch(e){if(e instanceof Error)console.log(JSON.stringify({level:"warn",kind:"admin_audit_failed",error:String(e).slice(0,240)}));throw e;}
}

async function drRebuildGoogle(request:Request,env:Env):Promise<Response>{
  if(!await internalAuthorized(request,env))return apiError("INTERNAL_UNAUTHORIZED","AUTH",401);
  try{return json(await rebuildGoogleStagingFromD1(env.DB,env));}catch(e){console.log(JSON.stringify({level:"error",kind:"dr_google_rebuild_failed",error:String(e)}));return apiError("DR_GOOGLE_REBUILD_FAILED","INTEGRITY",409,false,String(e).slice(0,500));}
}

async function resumableBootstrap(request:Request,env:Env,action:"start"|"step"|"status"):Promise<Response>{
  if(!await internalAuthorized(request,env))return apiError("INTERNAL_UNAUTHORIZED","AUTH",401);
  try{
    if(action==="start")return json(await bootstrapGoogleStart(env.DB,env));
    const body=await readJsonBody<{run_id?:string}>(request),runId=String(body.run_id||"").trim();
    if(action==="step"){
      if(!runId)return apiError("BOOTSTRAP_RUN_ID_REQUIRED","VALIDATION",400);
      const status=await bootstrapGoogleStatus(env.DB,runId) as {state?:{phase?:string}};
      if(status.state?.phase==="RESOURCES")return json(await bootstrapResourceProjectionStep(env.DB,runId));
      return json(await bootstrapGoogleStep(env.DB,env,runId));
    }
    return json(await bootstrapGoogleStatus(env.DB,runId||undefined));
  }catch(e){console.log(JSON.stringify({level:"error",kind:"resumable_bootstrap_failed",action,error:String(e)}));return apiError("BOOTSTRAP_RESUMABLE_FAILED","INTERNAL",500,true,String(e).slice(0,500));}
}

async function gasBridgeAuthorized(request:Request,env:Env):Promise<boolean>{
  const supplied=request.headers.get("x-gas-bridge-secret")||"";if(!supplied)return false;
  return constantTimeEqual(await sha256Hex(supplied),await sha256Hex(env.GAS_BRIDGE_SHARED_SECRET));
}
async function fallbackIngestFenced(request:Request,env:Env):Promise<Response>{
  if(!await gasBridgeAuthorized(request,env))return apiError("GAS_BRIDGE_UNAUTHORIZED","AUTH",401);
  const body=await readJsonBody<{event_id:string;authority_epoch:number;authority_seq:number;service_generation:string;event:Record<string,unknown>;checksum:string}>(request);
  const eventId=String(body.event_id||"").trim(),generation=String(body.service_generation||"").trim(),checksum=String(body.checksum||"").trim();
  if(!eventId||!generation||!checksum||!Number.isInteger(body.authority_epoch)||!Number.isInteger(body.authority_seq)||body.authority_seq<1||!body.event||typeof body.event!=="object")return apiError("FALLBACK_INGEST_INVALID","VALIDATION",400);
  const e=body.event as Record<string,unknown>,sourceRaw=[eventId,body.authority_epoch,body.authority_seq,generation,String(e.action||""),String(e.business_date||""),String(e.actor||""),String(e.role||""),String(e.device_id||""),String(e.occurred_at||""),String(e.payload_json||"")].join("|");
  if(await sha256Hex(sourceRaw)!==checksum)return apiError("FALLBACK_SOURCE_CHECKSUM_MISMATCH","INTEGRITY",409);
  let cleanPayload:unknown={};try{cleanPayload=sanitizeSensitive(JSON.parse(String(e.payload_json||"{}")));}catch{cleanPayload={};}
  const cleanEvent={...e,payload_json:JSON.stringify(cleanPayload)},cleanJson=JSON.stringify(cleanEvent),sanitizedChecksum=await sha256Hex(cleanJson);
  const a=await currentAuthority(env.DB),futureFallback=a.mode==="SERVICE_PRIMARY"&&body.authority_epoch===a.authority_epoch+1,currentFallback=["GOOGLE_FALLBACK","RECONCILING"].includes(a.mode)&&body.authority_epoch===a.authority_epoch;
  if(!futureFallback&&!currentFallback)return apiError("FALLBACK_EPOCH_NOT_ACCEPTABLE","CONFLICT",409,false,undefined,{current_epoch:a.authority_epoch,current_mode:a.mode,incoming_epoch:body.authority_epoch});
  const existing=await env.DB.prepare("SELECT authority_epoch,authority_seq,checksum FROM fallback_event_inbox WHERE event_id=?1").bind(eventId).first<{authority_epoch:number;authority_seq:number;checksum:string}>();
  if(existing){if(existing.authority_epoch!==body.authority_epoch||existing.authority_seq!==body.authority_seq||existing.checksum!==checksum)return apiError("FALLBACK_EVENT_ID_COLLISION","INTEGRITY",409);return json({ok:true,event_id:eventId,duplicate:true,authority_epoch:body.authority_epoch,authority_seq:body.authority_seq});}
  const seqCollision=await env.DB.prepare("SELECT event_id,checksum FROM fallback_event_inbox WHERE authority_epoch=?1 AND authority_seq=?2").bind(body.authority_epoch,body.authority_seq).first<{event_id:string;checksum:string}>();
  if(seqCollision)return apiError("FALLBACK_SEQUENCE_COLLISION","INTEGRITY",409,false,undefined,{existing_event_id:seqCollision.event_id,incoming_event_id:eventId,authority_epoch:body.authority_epoch,authority_seq:body.authority_seq});
  await env.DB.prepare(`INSERT INTO fallback_event_inbox(event_id,authority_epoch,authority_seq,service_generation,event_json,checksum,source,ingest_status,received_at,source_checksum_verified,sanitized_checksum)
    VALUES(?1,?2,?3,?4,?5,?6,'GOOGLE_FALLBACK','PENDING',?7,1,?8)`).bind(eventId,body.authority_epoch,body.authority_seq,generation,cleanJson,checksum,nowIso(),sanitizedChecksum).run();
  return json({ok:true,event_id:eventId,duplicate:false,staged_for_failback:true,authority_epoch:body.authority_epoch,authority_seq:body.authority_seq});
}

export default {
  async fetch(request:Request,env:Env,_ctx:ExecutionContext):Promise<Response>{
    const u=new URL(request.url),path=u.pathname;
    if(path==="/internal/bootstrap-google/start"&&request.method==="POST")return resumableBootstrap(request,env,"start");
    if(path==="/internal/bootstrap-google/step"&&request.method==="POST")return resumableBootstrap(request,env,"step");
    if(path==="/internal/bootstrap-google/status"&&request.method==="POST")return resumableBootstrap(request,env,"status");
    if(path==="/internal/fallback/ingest"&&request.method==="POST")return fallbackIngestFenced(request,env);
    if(path==="/internal/recovery/failback"&&request.method==="POST")return recoveryFailback(request,env);
    if(path==="/internal/recovery/failback-resume"&&request.method==="POST")return recoveryResume(request,env);
    if(path==="/internal/dr/rebuild-google-staging"&&request.method==="POST")return drRebuildGoogle(request,env);
    if(path==="/v1/import/template"&&request.method==="GET")return importTemplateXlsx(request,env);
    if(path==="/v1/import/xlsx/parse"&&request.method==="POST")return importParseXlsx(request,env);
    if(path==="/v1/legacy-sync"&&request.method==="POST"){
      try{return await legacySyncPortable(request,env);}catch(e){console.log(JSON.stringify({level:"error",kind:"legacy_sync_failed",error:String(e)}));return apiError("LEGACY_SYNC_FAILED","INTERNAL",500,true);}
    }
    if(await reconciliationLocked(env.DB)){
      if(path==="/v1/mutations"||path==="/v1/mutations/batch"||path==="/v1/legacy-mutations"||path==="/v1/legacy-mutations/batch"||path==="/v1/admin-audit"||path==="/internal/legacy-bridge")return apiError("RECONCILING_RETRY","CONFLICT",409,true);
    }
    if(path==="/v1/admin-audit"&&request.method==="POST")return adminAudit(request,env);
    return base.fetch(request,env);
  },
  async scheduled(controller:ScheduledController,env:Env,ctx:ExecutionContext):Promise<void>{return base.scheduled(controller,env,ctx);},
} satisfies ExportedHandler<Env>;

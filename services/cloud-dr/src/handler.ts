import { LibsqlD1Adapter } from "./libsql_adapter";
import { authenticate } from "../../../service/src/auth";
import { commitMutation, CoreError, currentAuthority } from "../../../service/src/core";
import { commitLegacyMutation, type LegacyMutationInput } from "../../../service/src/legacy";
import type { CanonicalMutationRequest } from "../../../service/src/domain";
import { json } from "../../../service/src/util";
import { exchangeGasSession, mobileRead } from "../../../service/src/mobile_hotfix";
import { legacySyncPortable } from "../../../service/src/legacy_sync_portable";
import { attendanceEnterV2, sessionResourceMutateV2, sessionResourceSnapshotV2 } from "../../../service/src/session_v2_compat";
import { sessionExitGuarded } from "../../../service/src/session_hotfix";

export type DrRuntimeEnv={TURSO_DATABASE_URL:string;TURSO_AUTH_TOKEN:string;SERVICE_TOKEN_SECRET:string;SERVICE_GENERATION:string;DISCOVERY_URL:string;DR_WRITER_MODE:string;ENVIRONMENT_ID?:string;SERVICE_AUDIENCE?:string;GAS_API_URL?:string};
const err=(code:string,status=400)=>json({ok:false,error:{code,error_class:status===401?"AUTH":status===409?"CONFLICT":"VALIDATION",retryable:status>=500}},status);
const realtimeNoop={getByName:(_name:string)=>({invalidate:async(_message:Record<string,unknown>)=>0,broadcast:async(_event:Record<string,unknown>)=>0})};
const envFor=(db:D1Database,e:DrRuntimeEnv):Env=>({
  DB:db,SERVICE_TOKEN_SECRET:e.SERVICE_TOKEN_SECRET,SERVICE_GENERATION:e.SERVICE_GENERATION,
  ENVIRONMENT_ID:String(e.ENVIRONMENT_ID||"BETA").toUpperCase(),SERVICE_AUDIENCE:String(e.SERVICE_AUDIENCE||"PICK_PACK_1291_BETA"),GAS_API_URL:String(e.GAS_API_URL||""),M1_ADMIN_TOKEN:"",
  GAS_BRIDGE_SHARED_SECRET:"",GOOGLE_OAUTH_CLIENT_ID:"",GOOGLE_OAUTH_CLIENT_SECRET:"",GOOGLE_OAUTH_REFRESH_TOKEN:"",
  GOOGLE_SOURCE_SHEET_ID:"",GOOGLE_OUTBOUND_SHEET_ID:"",REALTIME_HUB:realtimeNoop,
});

async function legacyBatch(request:Request,db:D1Database,e:DrRuntimeEnv):Promise<Response>{
  const env=envFor(db,e),auth=await authenticate(db,env,request);if(!auth)return err("UNAUTHORIZED",401);
  const body=await request.json() as {events?:LegacyMutationInput[]},events=Array.isArray(body.events)?body.events:[];if(!events.length||events.length>100)return err("LEGACY_MUTATION_BATCH_INVALID");
  const results:Record<string,unknown>[]=[];
  for(const input of events){const local=String(input?.event_id||"");try{const x=await commitLegacyMutation(db,env,auth,input),v=x.event as {event_id:string;authority_epoch:number;authority_seq:number;new_version:number};results.push({local_event_id:local,status:x.duplicate?"DUPLICATE":"CONFIRMED",canonical_event_id:v.event_id,authority_epoch:v.authority_epoch,authority_seq:v.authority_seq,new_version:v.new_version,error_code:null,conflict:null,realtime_delivered:0});}catch(ex){if(ex instanceof CoreError){const review=ex.errorClass==="CONFLICT"||ex.errorClass==="RESOURCE";results.push({local_event_id:local,status:review?"REVIEW_REQUIRED":"REJECTED",canonical_event_id:null,error_code:ex.code,conflict:ex.conflict??null,retryable:ex.retryable});}else throw ex}}
  return json({ok:true,results});
}
async function canonicalBatch(request:Request,db:D1Database,e:DrRuntimeEnv):Promise<Response>{
  const env=envFor(db,e),auth=await authenticate(db,env,request);if(!auth)return err("UNAUTHORIZED",401);
  const body=await request.json() as {events?:CanonicalMutationRequest[]},events=Array.isArray(body.events)?body.events:[];if(!events.length||events.length>100)return err("MUTATION_BATCH_INVALID");
  const results:Record<string,unknown>[]=[];
  for(const input of events){const local=String(input?.event_id||"");try{const x=await commitMutation(db,env,auth,input),v=x.event;results.push({local_event_id:local,status:x.duplicate?"DUPLICATE":"CONFIRMED",canonical_event_id:v.event_id,authority_epoch:v.authority_epoch,authority_seq:v.authority_seq,new_version:v.new_version,error_code:null,conflict:null,realtime_delivered:0});}catch(ex){if(ex instanceof CoreError){const review=ex.errorClass==="CONFLICT"||ex.errorClass==="RESOURCE";results.push({local_event_id:local,status:review?"REVIEW_REQUIRED":"REJECTED",canonical_event_id:null,error_code:ex.code,conflict:ex.conflict??null,retryable:ex.retryable});}else throw ex}}
  return json({ok:true,results});
}

export async function handle(request:Request,e:DrRuntimeEnv):Promise<Response>{
  const db=new LibsqlD1Adapter(e.TURSO_DATABASE_URL,e.TURSO_AUTH_TOKEN),env=envFor(db,e);
  try{
    const u=new URL(request.url),method=request.method;
    if(u.pathname==="/health"){const a=await currentAuthority(db);return json({ok:true,service:"pick-pack-1291-cloud-dr",provider:"TURSO",writer_mode:e.DR_WRITER_MODE,generation:e.SERVICE_GENERATION,authority:a});}
    if(e.DR_WRITER_MODE!=="ACTIVE_WRITE")return err("DR_PASSIVE_FENCED",409);
    if(u.pathname==="/v1/auth/gas-session"&&method==="POST")return exchangeGasSession(request,env);
    if(u.pathname==="/v1/mobile/read"&&method==="POST")return mobileRead(request,env);
    if(u.pathname==="/v1/legacy-sync"&&method==="POST")return legacySyncPortable(request,env);
    if(u.pathname==="/v1/legacy-mutations/batch"&&method==="POST")return legacyBatch(request,db,e);
    if(u.pathname==="/v1/mutations/batch"&&method==="POST")return canonicalBatch(request,db,e);
    if(u.pathname==="/v1/session/enter-v2"&&method==="POST")return attendanceEnterV2(request,env);
    if(u.pathname==="/v1/session/resources/snapshot"&&method==="POST")return sessionResourceSnapshotV2(request,env);
    if(u.pathname==="/v1/session/resources/mutate"&&method==="POST")return sessionResourceMutateV2(request,env);
    if((u.pathname==="/v1/session/exit-v2"||u.pathname==="/v1/session/exit")&&method==="POST")return sessionExitGuarded(request,env);
    return err("NOT_FOUND",404);
  }finally{db.close()}
}

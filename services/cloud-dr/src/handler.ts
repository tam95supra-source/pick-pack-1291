import { LibsqlD1Adapter } from "./libsql_adapter";
import { authenticate } from "../../../service/src/auth";
import { commitMutation, CoreError, currentAuthority } from "../../../service/src/core";
import { commitLegacyMutation, type LegacyMutationInput } from "../../../service/src/legacy";
import type { CanonicalMutationRequest } from "../../../service/src/domain";
import { b64u, b64uDecode, hmacB64u, json, nowIso } from "../../../service/src/util";

export type DrRuntimeEnv={TURSO_DATABASE_URL:string;TURSO_AUTH_TOKEN:string;SERVICE_TOKEN_SECRET:string;SERVICE_GENERATION:string;DISCOVERY_URL:string;DR_WRITER_MODE:string};
const err=(code:string,status=400)=>json({ok:false,error:{code,error_class:status===401?"AUTH":"VALIDATION",retryable:status>=500}},status);
const envFor=(db:D1Database,e:DrRuntimeEnv):Env=>({DB:db,SERVICE_TOKEN_SECRET:e.SERVICE_TOKEN_SECRET,SERVICE_GENERATION:e.SERVICE_GENERATION});

async function exchangeGasSession(request:Request,db:D1Database,e:DrRuntimeEnv):Promise<Response>{
  const input=await request.json() as {gas_token?:string;device_id?:string;device_label?:string};
  const gasToken=String(input.gas_token||"").trim(),deviceId=String(input.device_id||"").trim().slice(0,180);
  if(!gasToken||!deviceId)return err("SESSION_EXCHANGE_FIELDS_REQUIRED");
  let p:{l?:string;r?:string;v?:string;s?:string;d?:string}|null=null;
  try{const first=gasToken.split(".")[0];if(first)p=JSON.parse(new TextDecoder().decode(b64uDecode(first)))}catch{}
  if(!p?.l||!p.r||!p.v||!p.s||!p.d)return err("GAS_SESSION_INVALID",401);
  const vr=await fetch(e.DISCOVERY_URL,{method:"POST",headers:{"content-type":"application/json"},body:JSON.stringify({action:"m2_authority_status",_token:gasToken,_device_id:p.d,_app_channel:"BETA",_app_version:"cloud-dr-exchange-v1"})});
  const discovery=await vr.json() as Record<string,unknown>;if(!vr.ok||discovery.ok!==true)return err("GAS_SESSION_INVALID",401);
  if(String(discovery.authority_mode)!=="SERVICE_PRIMARY")return err("SERVICE_NOT_PRIMARY",409);
  const account=await db.prepare("SELECT login_id,role,display_name,position,email,verifier_hash,status FROM accounts WHERE login_id=?1").bind(p.l).first<{login_id:string;role:string;display_name:string;position:string;email:string;verifier_hash:string;status:string}>();
  if(!account||account.status!=="ACTIVE"||account.role!==p.r)return err("SESSION_EXCHANGE_ACCOUNT_MISMATCH",401);
  const current=await db.prepare("SELECT session_id,device_id FROM auth_sessions WHERE login_id=?1").bind(account.login_id).first<{session_id:string;device_id:string}>();
  const sessionId=current?.device_id===deviceId&&current.session_id?current.session_id:crypto.randomUUID(),issuedAt=nowIso();
  await db.prepare(`INSERT INTO auth_sessions(login_id,session_id,device_id,issued_at) VALUES(?1,?2,?3,?4) ON CONFLICT(login_id) DO UPDATE SET session_id=excluded.session_id,device_id=excluded.device_id,issued_at=excluded.issued_at`).bind(account.login_id,sessionId,deviceId,issuedAt).run();
  const payload={l:account.login_id,r:account.role,v:account.verifier_hash,s:sessionId,d:deviceId,c:"PDA"};
  const encoded=b64u(new TextEncoder().encode(JSON.stringify(payload))),sig=await hmacB64u(new TextEncoder().encode(e.SERVICE_TOKEN_SECRET),encoded);
  return json({ok:true,token:`${encoded}.${sig}`,account:{login_id:account.login_id,role:account.role,display_name:account.display_name,position:account.position,email:account.email},session:{issued_at:issuedAt,session_id:sessionId},authority:discovery.authority,authority_mode:discovery.authority_mode,service_generation:e.SERVICE_GENERATION});
}
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
  const db=new LibsqlD1Adapter(e.TURSO_DATABASE_URL,e.TURSO_AUTH_TOKEN);
  try{
    const u=new URL(request.url);
    if(u.pathname==="/health"){const a=await currentAuthority(db);return json({ok:true,service:"pick-pack-1291-cloud-dr",provider:"TURSO",writer_mode:e.DR_WRITER_MODE,generation:e.SERVICE_GENERATION,authority:a});}
    if(e.DR_WRITER_MODE!=="ACTIVE_WRITE")return err("DR_PASSIVE_FENCED",409);
    if(u.pathname==="/v1/auth/gas-session"&&request.method==="POST")return exchangeGasSession(request,db,e);
    if(u.pathname==="/v1/legacy-mutations/batch"&&request.method==="POST")return legacyBatch(request,db,e);
    if(u.pathname==="/v1/mutations/batch"&&request.method==="POST")return canonicalBatch(request,db,e);
    return err("NOT_FOUND",404);
  }finally{db.close()}
}

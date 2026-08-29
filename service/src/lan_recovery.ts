import { authenticate } from "./auth";
import { commitLegacyMutation } from "./legacy";
import { CoreError } from "./core";
import type { AuthContext } from "./domain";
import { apiError, json, sha256Hex } from "./util";

type RawLanEvent={action?:string;event_id?:string;business_date?:string;device_id?:string;payload?:Record<string,unknown>;event_envelope?:Record<string,unknown>};

export async function lanReplayBatch(request:Request,env:Env):Promise<Response>{
  const replayer=await authenticate(env.DB,env,request);
  if(!replayer)return apiError("UNAUTHORIZED","AUTH",401);
  if(replayer.role!=="ADMIN"&&replayer.role!=="SUPERADMIN")return apiError("LAN_REPLAY_ADMIN_REQUIRED","PERMISSION",403);
  let body:{events?:RawLanEvent[]};
  try{body=await request.json() as {events?:RawLanEvent[]};}catch{return apiError("JSON_INVALID","VALIDATION",400);}
  const items=Array.isArray(body.events)?body.events:[];
  if(!items.length||items.length>100)return apiError("LAN_REPLAY_BATCH_INVALID","VALIDATION",400);
  const results:Record<string,unknown>[]=[];
  for(const raw of items){
    const eventId=String(raw.event_id||"").trim();
    try{
      const envl=(raw.event_envelope&&typeof raw.event_envelope==="object")?raw.event_envelope:{};
      const envelopeEvent=String(envl.event_id||"").trim();
      const userId=String(envl.user_id||"").trim();
      const role=String(envl.role||"").toUpperCase();
      const sourceDevice=String(envl.device_id||raw.device_id||"").trim();
      const payload=(raw.payload&&typeof raw.payload==="object")?raw.payload:{};
      const checksum=String(envl.checksum||"").trim();
      if(!eventId||envelopeEvent!==eventId||!userId||!sourceDevice||Number(envl.schema_version||0)!==1||!checksum)throw new CoreError("LAN_ENVELOPE_INVALID","VALIDATION",400);
      if(!["SUPERADMIN","ADMIN","USER"].includes(role))throw new CoreError("LAN_ACTOR_ROLE_INVALID","VALIDATION",400);
      const actualChecksum=await sha256Hex(JSON.stringify(payload));
      if(actualChecksum!==checksum)throw new CoreError("LAN_PAYLOAD_CHECKSUM_MISMATCH","INTEGRITY",409,false);
      const account=await env.DB.prepare("SELECT login_id,role,display_name,verifier_hash,status FROM accounts WHERE login_id=?1").bind(userId)
        .first<{login_id:string;role:"SUPERADMIN"|"ADMIN"|"USER";display_name:string;verifier_hash:string;status:string}>();
      if(!account||account.status!=="ACTIVE"||account.role!==role)throw new CoreError("LAN_ACTOR_ACCOUNT_MISMATCH","AUTH",401,false);
      const actor:AuthContext={login_id:account.login_id,role:account.role,display_name:account.display_name,device_id:sourceDevice,session_id:"LAN_REPLAY",verifier_hash:account.verifier_hash,session_kind:"PDA"};
      const action=String(raw.action||"") as "enter"|"exit"|"resource_change"|"labor_start"|"labor_finish"|"meal_checkin"|"meal_status";
      if(!["enter","exit","resource_change","labor_start","labor_finish","meal_checkin","meal_status"].includes(action))throw new CoreError("LAN_ACTION_INVALID","VALIDATION",400);
      const result=await commitLegacyMutation(env.DB,env,actor,{action,payload,event_id:eventId,business_date:String(raw.business_date||envl.business_date||""),device_id:sourceDevice});
      const event=result.event as {event_id:string;authority_epoch:number;authority_seq:number;new_version:number};
      results.push({local_event_id:eventId,status:result.duplicate?"DUPLICATE":"CONFIRMED",canonical_event_id:event.event_id,authority_epoch:event.authority_epoch,authority_seq:event.authority_seq,new_version:event.new_version,error_code:null});
    }catch(err){
      if(err instanceof CoreError){
        const review=err.errorClass==="CONFLICT"||err.errorClass==="RESOURCE"||err.errorClass==="INTEGRITY";
        results.push({local_event_id:eventId,status:review?"REVIEW_REQUIRED":"REJECTED",canonical_event_id:null,error_code:err.code,conflict:err.conflict??null,retryable:err.retryable});
      }else throw err;
    }
  }
  return json({ok:true,results});
}

import { authenticate } from "./auth";
import { currentAuthority } from "./core";
import { apiError, json, nowIso, readJsonBody } from "./util";

type PushEnv=Env&{FCM_SERVICE_ACCOUNT_JSON?:string;FCM_PROJECT_ID?:string;FCM_CLIENT_EMAIL?:string;FCM_PRIVATE_KEY?:string};
interface FcmCreds{projectId:string;clientEmail:string;privateKey:string}
interface TokenCache{token:string;expires:number;projectId:string}
let tokenCache:TokenCache|null=null;

function b64u(input:string|ArrayBuffer):string{const bytes=typeof input==="string"?new TextEncoder().encode(input):new Uint8Array(input);let s="";for(const b of bytes)s+=String.fromCharCode(b);return btoa(s).replace(/\+/g,"-").replace(/\//g,"_").replace(/=+$/g,"");}
function pemBytes(pem:string):ArrayBuffer{const raw=pem.replace(/\\n/g,"\n").replace(/-----[^-]+-----/g,"").replace(/\s/g,"");const bin=atob(raw),out=new Uint8Array(bin.length);for(let i=0;i<bin.length;i++)out[i]=bin.charCodeAt(i);return out.buffer;}
function fcmCredentials(env:PushEnv):FcmCreds|null{
  if(env.FCM_SERVICE_ACCOUNT_JSON){
    try{const j=JSON.parse(env.FCM_SERVICE_ACCOUNT_JSON) as Record<string,unknown>,projectId=String(j.project_id||"").trim(),clientEmail=String(j.client_email||"").trim(),privateKey=String(j.private_key||"");if(projectId&&clientEmail&&privateKey.includes("PRIVATE KEY"))return{projectId,clientEmail,privateKey};}catch{}
  }
  if(env.FCM_PROJECT_ID&&env.FCM_CLIENT_EMAIL&&env.FCM_PRIVATE_KEY)return{projectId:env.FCM_PROJECT_ID,clientEmail:env.FCM_CLIENT_EMAIL,privateKey:env.FCM_PRIVATE_KEY};
  return null;
}
async function fcmAccessToken(env:PushEnv):Promise<{token:string;projectId:string}|null>{
  const creds=fcmCredentials(env);if(!creds)return null;
  if(tokenCache&&tokenCache.projectId===creds.projectId&&tokenCache.expires>Date.now()+60_000)return{token:tokenCache.token,projectId:tokenCache.projectId};
  const now=Math.floor(Date.now()/1000),header=b64u(JSON.stringify({alg:"RS256",typ:"JWT"})),claims=b64u(JSON.stringify({iss:creds.clientEmail,scope:"https://www.googleapis.com/auth/firebase.messaging",aud:"https://oauth2.googleapis.com/token",iat:now,exp:now+3600})),unsigned=`${header}.${claims}`;
  const key=await crypto.subtle.importKey("pkcs8",pemBytes(creds.privateKey),{name:"RSASSA-PKCS1-v1_5",hash:"SHA-256"},false,["sign"]),sig=await crypto.subtle.sign("RSASSA-PKCS1-v1_5",key,new TextEncoder().encode(unsigned)),assertion=`${unsigned}.${b64u(sig)}`;
  const r=await fetch("https://oauth2.googleapis.com/token",{method:"POST",headers:{"content-type":"application/x-www-form-urlencoded"},body:new URLSearchParams({grant_type:"urn:ietf:params:grant-type:jwt-bearer",assertion})});
  if(!r.ok)throw new Error(`FCM_OAUTH_${r.status}`);const j=await r.json<{access_token?:string;expires_in?:number}>();if(!j.access_token)throw new Error("FCM_OAUTH_TOKEN_MISSING");tokenCache={token:j.access_token,expires:Date.now()+Math.max(300,Number(j.expires_in||3600))*1000,projectId:creds.projectId};return{token:j.access_token,projectId:creds.projectId};
}

export async function registerPushDevice(request:Request,env:Env):Promise<Response>{
  const auth=await authenticate(env.DB,env,request);if(!auth)return apiError("UNAUTHORIZED","AUTH",401);
  const b=await readJsonBody<{fcm_token:string;app_version?:string;channel?:string}>(request),token=String(b.fcm_token||"").trim();if(token.length<32||token.length>4096)return apiError("FCM_TOKEN_INVALID","VALIDATION",400);
  const at=nowIso();await env.DB.prepare(`INSERT INTO push_devices(device_id,login_id,fcm_token,platform,app_version,channel,status,registered_at,updated_at)
    VALUES(?1,?2,?3,'ANDROID',?4,?5,'ACTIVE',?6,?6) ON CONFLICT(device_id,login_id) DO UPDATE SET fcm_token=excluded.fcm_token,app_version=excluded.app_version,channel=excluded.channel,status='ACTIVE',updated_at=excluded.updated_at,last_error_class=NULL`).bind(auth.device_id,auth.login_id,token,String(b.app_version||"").slice(0,80),String(b.channel||"").slice(0,40),at).run();
  return json({ok:true,device_id:auth.device_id,push:"FCM_WAKE_ONLY"});
}
export async function revokePushDevice(request:Request,env:Env):Promise<Response>{const auth=await authenticate(env.DB,env,request);if(!auth)return apiError("UNAUTHORIZED","AUTH",401);await env.DB.prepare("UPDATE push_devices SET status='REVOKED',updated_at=?1 WHERE device_id=?2 AND login_id=?3").bind(nowIso(),auth.device_id,auth.login_id).run();return json({ok:true});}

function wakeScope(namespace:string,businessDate?:string):string{return businessDate?`DAY:${businessDate}`:`MASTER:${namespace}`;}
async function upsertWake(db:D1Database,namespace:string,revision:number|undefined,businessDate:string|undefined,authorityEpoch:number,authoritySeq:number,at:string):Promise<void>{
  const scope=wakeScope(namespace,businessDate),payload={type:businessDate?"DAY_CHANGED":"MASTER_CHANGED",namespace,revision:revision??null,business_date:businessDate??null,authority_epoch:authorityEpoch,authority_seq:authoritySeq};
  await db.prepare(`INSERT INTO push_wake_outbox(scope_key,namespace,revision,business_date,authority_epoch,authority_seq,payload_json,status,attempt_count,next_attempt_at,created_at,updated_at)
    VALUES(?1,?2,?3,?4,?5,?6,?7,'PENDING',0,?8,?8,?8)
    ON CONFLICT(scope_key) DO UPDATE SET namespace=excluded.namespace,revision=excluded.revision,business_date=excluded.business_date,
      authority_epoch=excluded.authority_epoch,authority_seq=excluded.authority_seq,payload_json=excluded.payload_json,status='PENDING',attempt_count=0,
      next_attempt_at=excluded.next_attempt_at,last_error_class=NULL,updated_at=excluded.updated_at
    WHERE excluded.authority_epoch>push_wake_outbox.authority_epoch OR (excluded.authority_epoch=push_wake_outbox.authority_epoch AND excluded.authority_seq>=push_wake_outbox.authority_seq)`).bind(scope,namespace,revision??null,businessDate??null,authorityEpoch,authoritySeq,JSON.stringify(payload),at).run();
}
export async function enqueueInvalidation(db:D1Database,namespace:string,revision:number|undefined,businessDate?:string):Promise<void>{const a=await currentAuthority(db);await upsertWake(db,namespace,revision,businessDate,a.authority_epoch,a.authority_seq,nowIso());}

/** Stage at most one current wake per changed business day. This reads the O(days) revision projection, never scans event rows. */
async function stageRecentDayInvalidations(db:D1Database):Promise<void>{
  const cutoff=new Date(Date.now()-10*60_000).toISOString(),a=await currentAuthority(db),rows=(await db.prepare(`SELECT business_date,revision,updated_at FROM day_revision_state WHERE authority_epoch=?1 AND service_generation=?2 AND updated_at>=?3 ORDER BY updated_at DESC LIMIT 7`).bind(a.authority_epoch,a.service_generation,cutoff).all<{business_date:string;revision:number;updated_at:string}>()).results??[];
  for(const r of rows)await upsertWake(db,"business_day",r.revision,r.business_date,a.authority_epoch,Math.max(a.authority_seq,r.revision),r.updated_at||nowIso());
}

type PushWake={scope_key:string;payload_json:string;attempt_count:number};
type PushDevice={device_id:string;login_id:string;fcm_token:string};
export async function flushPushOutbox(db:D1Database,rawEnv:Env,limit=12):Promise<{configured:boolean;sent:number;invalid:number;retry:number;pending:number}>{
  await stageRecentDayInvalidations(db);
  const env=rawEnv as PushEnv,access=await fcmAccessToken(env);if(!access)return{configured:false,sent:0,invalid:0,retry:0,pending:(await db.prepare("SELECT COUNT(*) n FROM push_wake_outbox WHERE status IN ('PENDING','RETRY')").first<{n:number}>())?.n??0};
  const now=nowIso(),pushes=(await db.prepare("SELECT scope_key,payload_json,attempt_count FROM push_wake_outbox WHERE status IN ('PENDING','RETRY') AND next_attempt_at<=?1 ORDER BY updated_at LIMIT ?2").bind(now,Math.max(1,Math.min(24,limit))).all<PushWake>()).results??[],devices=(await db.prepare("SELECT device_id,login_id,fcm_token FROM push_devices WHERE status='ACTIVE'").all<PushDevice>()).results??[];let sent=0,invalid=0,retry=0;
  const deviceState=new Map<string,{token:string;ok:boolean;invalid:boolean;error:string|null}>();
  for(const d of devices)deviceState.set(d.fcm_token,{token:d.fcm_token,ok:false,invalid:false,error:null});
  for(const p of pushes){let transient=false;for(const d of devices){const state=deviceState.get(d.fcm_token)!;if(state.invalid)continue;const data=JSON.parse(p.payload_json) as Record<string,unknown>,stringData=Object.fromEntries(Object.entries(data).map(([k,v])=>[k,v==null?"":String(v)]));const r=await fetch(`https://fcm.googleapis.com/v1/projects/${encodeURIComponent(access.projectId)}/messages:send`,{method:"POST",headers:{authorization:`Bearer ${access.token}`,"content-type":"application/json"},body:JSON.stringify({message:{token:d.fcm_token,data:stringData,android:{priority:"high"}}})});if(r.ok){sent++;state.ok=true;continue;}const text=(await r.text()).slice(0,800);if(r.status===404||/UNREGISTERED|registration-token-not-registered/i.test(text)){invalid++;state.invalid=true;state.error='UNREGISTERED';}else if(r.status===429||r.status>=500){transient=true;retry++;state.error=`FCM_HTTP_${r.status}`;}else state.error=`FCM_HTTP_${r.status}`;}
    const attempts=p.attempt_count+1,next=new Date(Date.now()+Math.min(3600_000,Math.pow(2,Math.min(attempts,8))*5000)).toISOString();await db.prepare("UPDATE push_wake_outbox SET status=?1,attempt_count=?2,next_attempt_at=?3,last_error_class=?4,updated_at=?5 WHERE scope_key=?6").bind(transient&&attempts<8?"RETRY":transient?"FAILED":"SENT",attempts,next,transient?"FCM_TRANSIENT":null,nowIso(),p.scope_key).run();
  }
  const updates:D1PreparedStatement[]=[];for(const s of deviceState.values()){if(s.invalid)updates.push(db.prepare("UPDATE push_devices SET status='INVALID',last_error_class='UNREGISTERED',updated_at=?1 WHERE fcm_token=?2").bind(nowIso(),s.token));else if(s.ok)updates.push(db.prepare("UPDATE push_devices SET last_success_at=?1,last_error_class=?2,updated_at=?1 WHERE fcm_token=?3").bind(nowIso(),s.error,s.token));else if(s.error)updates.push(db.prepare("UPDATE push_devices SET last_error_class=?1,updated_at=?2 WHERE fcm_token=?3").bind(s.error,nowIso(),s.token));}if(updates.length)await db.batch(updates);
  const pending=(await db.prepare("SELECT COUNT(*) n FROM push_wake_outbox WHERE status IN ('PENDING','RETRY')").first<{n:number}>())?.n??0;return{configured:true,sent,invalid,retry,pending};
}

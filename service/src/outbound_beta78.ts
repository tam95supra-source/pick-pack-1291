import type { AuthContext, EventRow } from "./domain";
import { currentAuthority } from "./core";
import { bangkokToday } from "./business_date";
import { apiError, json, nowIso, sha256Hex } from "./util";
import { isStableEnvironment, stableSheetBridge } from "./stable_sheet_bridge";

const OWNER_EMAIL="tam95.supra@gmail.com";
const LOCATION_SHEET="Vị trí";
const DROP_SHEET="Nhận hàng rớt";

type Authority={authority_epoch:number;authority_seq:number;mode:string;scope:string;service_generation:string};
type CommitPlan={eventType:string;entityType:string;entityId:string;businessDate:string;idempotencyKey:string;payload:Record<string,unknown>;baseVersion:number;newVersion:number;projection:(eventId:string)=>D1PreparedStatement[];preconditionSql:string;preconditionBindings:unknown[]};

function norm(v:unknown):string{return String(v??"").trim().replace(/\s+/g," ");}
function key(v:unknown):string{return norm(v).normalize("NFD").replace(/[\u0300-\u036f]/g,"").toUpperCase();}
function visibleDate(iso:string):string{const m=/^(\d{4})-(\d{2})-(\d{2})$/.exec(iso);return m?`${m[3]}/${m[2]}/${m[1]}`:iso;}
function visibleDateTime(iso:string):string{const d=new Date(iso);return Number.isNaN(d.getTime())?iso:new Intl.DateTimeFormat("en-GB",{timeZone:"Asia/Ho_Chi_Minh",year:"numeric",month:"2-digit",day:"2-digit",hour:"2-digit",minute:"2-digit",second:"2-digit",hourCycle:"h23"}).format(d).replace(",","");}

async function owner(db:D1Database,auth:AuthContext):Promise<boolean>{
  if(auth.role!=="SUPERADMIN")return false;
  const r=await db.prepare("SELECT email FROM accounts WHERE login_id=?1").bind(auth.login_id).first<{email:string}>();
  return String(r?.email||"").trim().toLowerCase()===OWNER_EMAIL;
}

async function googleAccessToken(env:Env):Promise<string>{
  if(isStableEnvironment(env))return "__STABLE_BOUND_GAS__";
  const body=new URLSearchParams({client_id:env.GOOGLE_OAUTH_CLIENT_ID,client_secret:env.GOOGLE_OAUTH_CLIENT_SECRET,refresh_token:env.GOOGLE_OAUTH_REFRESH_TOKEN,grant_type:"refresh_token"});
  const r=await fetch("https://oauth2.googleapis.com/token",{method:"POST",headers:{"content-type":"application/x-www-form-urlencoded"},body});
  const j=await r.json<{access_token?:string;error?:string}>();if(!r.ok||!j.access_token)throw new Error(`OUTBOUND_GOOGLE_OAUTH:${j.error??r.status}`);return j.access_token;
}
function a1(sheet:string,range:string):string{return `'${sheet.replace(/'/g,"''")}'!${range}`;}
async function getValues(env:Env,token:string,sheet:string,range:string):Promise<unknown[][]>{
  if(isStableEnvironment(env)){const j=await stableSheetBridge<{ok:true;values?:unknown[][]}>(env,"outbound","get_values",{sheet,range});return j.values??[];}
  const url=`https://sheets.googleapis.com/v4/spreadsheets/${encodeURIComponent(env.GOOGLE_OUTBOUND_SHEET_ID)}/values/${encodeURIComponent(a1(sheet,range))}?valueRenderOption=FORMATTED_VALUE`;
  const r=await fetch(url,{headers:{authorization:`Bearer ${token}`}});if(!r.ok)throw new Error(`OUTBOUND_GOOGLE_READ:${sheet}:${r.status}`);return (await r.json<{values?:unknown[][]}>()).values??[];
}
async function putValues(env:Env,token:string,sheet:string,range:string,values:unknown[][]):Promise<void>{
  if(isStableEnvironment(env)){await stableSheetBridge(env,"outbound","put_values",{sheet,range,values});return;}
  const full=a1(sheet,range),url=`https://sheets.googleapis.com/v4/spreadsheets/${encodeURIComponent(env.GOOGLE_OUTBOUND_SHEET_ID)}/values/${encodeURIComponent(full)}?valueInputOption=RAW`;
  const r=await fetch(url,{method:"PUT",headers:{authorization:`Bearer ${token}`,"content-type":"application/json"},body:JSON.stringify({range:full,majorDimension:"ROWS",values})});if(!r.ok)throw new Error(`OUTBOUND_GOOGLE_PUT:${sheet}:${r.status}`);
}
async function appendValues(env:Env,token:string,sheet:string,range:string,values:unknown[][]):Promise<void>{
  if(isStableEnvironment(env)){await stableSheetBridge(env,"outbound","append_values",{sheet,range,values});return;}
  const full=a1(sheet,range),url=`https://sheets.googleapis.com/v4/spreadsheets/${encodeURIComponent(env.GOOGLE_OUTBOUND_SHEET_ID)}/values/${encodeURIComponent(full)}:append?valueInputOption=RAW&insertDataOption=INSERT_ROWS`;
  const r=await fetch(url,{method:"POST",headers:{authorization:`Bearer ${token}`,"content-type":"application/json"},body:JSON.stringify({range:full,majorDimension:"ROWS",values})});if(!r.ok)throw new Error(`OUTBOUND_GOOGLE_APPEND:${sheet}:${r.status}`);
}

async function hydrateLocations(env:Env):Promise<void>{
  const meta=await env.DB.prepare("SELECT locations_hydrated FROM outbound_meta WHERE singleton_id=1").first<{locations_hydrated:number}>();
  if(Number(meta?.locations_hydrated||0)===1)return;
  const token=await googleAccessToken(env),rows=await getValues(env,token,LOCATION_SHEET,"A2:A"),at=nowIso();
  const stmts: D1PreparedStatement[]=[];
  for(const row of rows){const location=norm(row[0]);if(!location)continue;stmts.push(env.DB.prepare(`INSERT INTO outbound_locations(location_key,location,version,created_at,updated_at) VALUES(?1,?2,1,?3,?3)
    ON CONFLICT(location_key) DO UPDATE SET location=excluded.location,updated_at=excluded.updated_at`).bind(key(location),location,at));}
  stmts.push(env.DB.prepare("UPDATE outbound_meta SET locations_hydrated=1,hydrated_at=?1 WHERE singleton_id=1").bind(at));
  await env.DB.batch(stmts);
}

async function existingByIdem(db:D1Database,idem:string):Promise<EventRow|null>{return db.prepare("SELECT * FROM events WHERE idempotency_key=?1 ORDER BY committed_at LIMIT 1").bind(idem).first<EventRow>();}

async function commit(env:Env,auth:AuthContext,plan:CommitPlan):Promise<{event:EventRow;duplicate:boolean}|Response>{
  for(let attempt=0;attempt<2;attempt++){
    const existing=await existingByIdem(env.DB,plan.idempotencyKey);if(existing)return{event:existing,duplicate:true};
    const a=await currentAuthority(env.DB) as unknown as Authority;
    if(a.mode!=="SERVICE_PRIMARY"||a.scope!=="PRODUCTION")return apiError("SERVICE_NOT_WRITE_AUTHORITY","CONFLICT",409,true);
    const eventId=crypto.randomUUID(),committed=nowIso(),seq=Number(a.authority_seq)+1,payloadJson=JSON.stringify(plan.payload),checksum=await sha256Hex(`${eventId}|${plan.eventType}|${plan.entityId}|${plan.idempotencyKey}|${payloadJson}`);
    const insert=env.DB.prepare(`INSERT INTO events(event_id,event_type,entity_type,entity_id,business_date,authority_epoch,authority_seq,service_generation,base_version,new_version,actor_id,actor_role,device_id,occurred_at,committed_at,payload_json,idempotency_key,origin,schema_version,checksum)
      SELECT ?1,?2,?3,?4,?5,authority_epoch,authority_seq+1,service_generation,?6,?7,?8,?9,?10,?11,?12,?13,?14,'PDA',1,?15
      FROM authority_state WHERE singleton_id=1 AND authority_epoch=?16 AND authority_seq=?17 AND mode='SERVICE_PRIMARY' AND scope='PRODUCTION' AND service_generation=?18 AND (${plan.preconditionSql})`)
      .bind(eventId,plan.eventType,plan.entityType,plan.entityId,plan.businessDate,plan.baseVersion,plan.newVersion,auth.login_id,auth.role,auth.device_id,committed,committed,payloadJson,plan.idempotencyKey,checksum,a.authority_epoch,a.authority_seq,a.service_generation,...plan.preconditionBindings);
    const stmts=[insert,...plan.projection(eventId),env.DB.prepare(`INSERT INTO outbound_replication_outbox(event_id,status,attempt_count,next_attempt_at) SELECT ?1,'PENDING',0,?2 WHERE EXISTS(SELECT 1 FROM events WHERE event_id=?1)`).bind(eventId,committed),env.DB.prepare(`UPDATE authority_state SET authority_seq=authority_seq+1,updated_at=?1 WHERE singleton_id=1 AND authority_epoch=?2 AND authority_seq=?3 AND service_generation=?4 AND EXISTS(SELECT 1 FROM events WHERE event_id=?5 AND authority_seq=?6)`).bind(committed,a.authority_epoch,a.authority_seq,a.service_generation,eventId,seq)];
    try{await env.DB.batch(stmts);}catch(e){const raced=await existingByIdem(env.DB,plan.idempotencyKey);if(raced)return{event:raced,duplicate:true};if(attempt===0)continue;throw e;}
    const event=await env.DB.prepare("SELECT * FROM events WHERE event_id=?1").bind(eventId).first<EventRow>();
    if(event)return{event,duplicate:false};
  }
  return apiError("AUTHORITY_FENCE_CHANGED","CONFLICT",409,true);
}

async function locationList(env:Env,auth:AuthContext):Promise<Response>{
  await hydrateLocations(env);
  const rows=(await env.DB.prepare("SELECT location FROM outbound_locations ORDER BY location COLLATE NOCASE").all<{location:string}>()).results??[];
  return json({ok:true,source:"SERVICE_D1",items:rows.map(x=>x.location),owner:await owner(env.DB,auth)});
}

async function locationMutate(env:Env,auth:AuthContext,body:Record<string,unknown>):Promise<Response>{
  if(!await owner(env.DB,auth))return apiError("OUTBOUND_OWNER_REQUIRED","PERMISSION",403);
  await hydrateLocations(env);
  const op=String(body.operation||"").trim().toUpperCase(),before=norm(body.before||body.location),after=norm(body.after||body.location),beforeKey=key(before),afterKey=key(after),idem=String(body.idempotency_key||body.event_id||"").trim();
  if(!idem)return apiError("OUTBOUND_IDEMPOTENCY_REQUIRED","VALIDATION",400);
  if(!["CREATE","UPDATE","DELETE"].includes(op))return apiError("OUTBOUND_LOCATION_OPERATION_INVALID","VALIDATION",400);
  if((op==="CREATE"||op==="UPDATE")&&!after)return apiError("OUTBOUND_LOCATION_REQUIRED","VALIDATION",400);
  if(op!=="CREATE"&&!before)return apiError("OUTBOUND_LOCATION_REQUIRED","VALIDATION",400);
  const current=beforeKey?await env.DB.prepare("SELECT version FROM outbound_locations WHERE location_key=?1").bind(beforeKey).first<{version:number}>():null;
  const nextVersion=Number(current?.version||0)+1,at=nowIso(),eventType=`OUTBOUND_LOCATION_${op}`;
  let precondition="1=1",bindings:unknown[]=[],projection:(eventId:string)=>D1PreparedStatement[];
  if(op==="CREATE"){
    precondition=`NOT EXISTS(SELECT 1 FROM outbound_locations WHERE location_key=?19)`;bindings=[afterKey];
    projection=(eventId)=>[env.DB.prepare(`INSERT INTO outbound_locations(location_key,location,version,created_at,updated_at) SELECT ?1,?2,1,?3,?3 WHERE EXISTS(SELECT 1 FROM events WHERE event_id=?4)`).bind(afterKey,after,at,eventId)];
  }else if(op==="UPDATE"){
    precondition=`EXISTS(SELECT 1 FROM outbound_locations WHERE location_key=?19) AND (?20=?19 OR NOT EXISTS(SELECT 1 FROM outbound_locations WHERE location_key=?20))`;bindings=[beforeKey,afterKey];
    projection=(eventId)=>[env.DB.prepare(`UPDATE outbound_locations SET location_key=?1,location=?2,version=version+1,updated_at=?3 WHERE location_key=?4 AND EXISTS(SELECT 1 FROM events WHERE event_id=?5)`).bind(afterKey,after,at,beforeKey,eventId)];
  }else{
    precondition=`EXISTS(SELECT 1 FROM outbound_locations WHERE location_key=?19)`;bindings=[beforeKey];
    projection=(eventId)=>[env.DB.prepare(`DELETE FROM outbound_locations WHERE location_key=?1 AND EXISTS(SELECT 1 FROM events WHERE event_id=?2)`).bind(beforeKey,eventId)];
  }
  const result=await commit(env,auth,{eventType,entityType:"OUTBOUND_LOCATION",entityId:op==="DELETE"?beforeKey:afterKey,businessDate:bangkokToday(),idempotencyKey:idem,payload:{operation:op,before,after,mnv:"",location:after||before},baseVersion:Number(current?.version||0),newVersion:nextVersion,projection,preconditionSql:precondition,preconditionBindings:bindings});
  if(result instanceof Response)return result;
  if(!result.duplicate){
    const exists=op==="DELETE"?null:await env.DB.prepare("SELECT location FROM outbound_locations WHERE location_key=?1").bind(afterKey).first<{location:string}>();
    if(op!=="DELETE"&&!exists)return apiError(op==="CREATE"?"OUTBOUND_LOCATION_DUPLICATE":"OUTBOUND_LOCATION_NOT_FOUND","CONFLICT",409);
  }
  return locationList(env,auth).then(async r=>{const j=await r.json<Record<string,unknown>>();return json({...j,idempotent:result.duplicate,event_id:result.event.event_id,replication:"OUTBOX_PENDING"});});
}

async function dropAppend(env:Env,auth:AuthContext,body:Record<string,unknown>):Promise<Response>{
  await hydrateLocations(env);
  const idem=String(body.idempotency_key||body.record_id||"").trim(),location=norm(body.location),scanQr=String(body.scan_qr||""),doNumber=String(body.do_number||"").trim(),countRaw=String(body.package_count||"").trim(),count=Number(countRaw),locationKey=key(location);
  if(!idem)return apiError("OUTBOUND_IDEMPOTENCY_REQUIRED","VALIDATION",400);
  if(!location)return apiError("OUTBOUND_LOCATION_REQUIRED","VALIDATION",400);
  if(!doNumber||doNumber.length>80)return apiError("OUTBOUND_DO_INVALID","VALIDATION",400);
  if(!/^\d+$/.test(countRaw)||!Number.isInteger(count)||count<=0||count>999999)return apiError("OUTBOUND_PACKAGE_COUNT_INVALID","VALIDATION",400);
  if(scanQr.length>2000)return apiError("OUTBOUND_QR_TOO_LONG","VALIDATION",400);
  const at=nowIso(),businessDate=bangkokToday();
  const result=await commit(env,auth,{eventType:"OUTBOUND_DROP_APPEND",entityType:"OUTBOUND_DROP",entityId:idem,businessDate,idempotencyKey:idem,payload:{mnv:"",record_id:idem,location,scan_qr:scanQr,do_number:doNumber,package_count:count,actor_display_name:auth.display_name},baseVersion:0,newVersion:1,preconditionSql:`EXISTS(SELECT 1 FROM outbound_locations WHERE location_key=?19)`,preconditionBindings:[locationKey],projection:(eventId)=>[env.DB.prepare(`INSERT INTO outbound_drop_records(record_id,location,business_date,scan_qr,do_number,package_count,actor_id,actor_display_name,created_at)
    SELECT ?1,?2,?3,?4,?5,?6,?7,?8,?9 WHERE EXISTS(SELECT 1 FROM events WHERE event_id=?10)`).bind(idem,location,businessDate,scanQr,doNumber,count,auth.login_id,auth.display_name,at,eventId)]});
  if(result instanceof Response)return result;
  const record=await env.DB.prepare("SELECT record_id,location,business_date,scan_qr,do_number,package_count,actor_id,actor_display_name,created_at FROM outbound_drop_records WHERE record_id=?1").bind(idem).first<Record<string,unknown>>();
  if(!record)return apiError("OUTBOUND_LOCATION_INVALID","VALIDATION",400);
  return json({ok:true,source:"SERVICE_D1",idempotent:result.duplicate,event_id:result.event.event_id,item:record,replication:"OUTBOX_PENDING"});
}

async function dropList(env:Env):Promise<Response>{
  const rows=(await env.DB.prepare("SELECT record_id,location,business_date,do_number,package_count,actor_id,actor_display_name,created_at FROM outbound_drop_records ORDER BY created_at DESC,record_id DESC LIMIT 300").all<Record<string,unknown>>()).results??[];
  return json({ok:true,source:"SERVICE_D1",items:rows});
}

async function dropDelete(env:Env,auth:AuthContext,body:Record<string,unknown>):Promise<Response>{
  const idsRaw=Array.isArray(body.record_ids)?body.record_ids:[],ids=[...new Set(idsRaw.map(x=>String(x||"").trim()).filter(Boolean))].slice(0,100);
  const idem=String(body.idempotency_key||body.event_id||"").trim();
  if(!idem)return apiError("OUTBOUND_IDEMPOTENCY_REQUIRED","VALIDATION",400);
  if(!ids.length)return apiError("OUTBOUND_DROP_IDS_REQUIRED","VALIDATION",400);
  const placeholders=ids.map((_,i)=>"?"+(i+1)).join(",");
  const found=(await env.DB.prepare(`SELECT record_id FROM outbound_drop_records WHERE record_id IN (${placeholders})`).bind(...ids).all<{record_id:string}>()).results??[];
  const foundIds=found.map(x=>x.record_id);if(!foundIds.length)return apiError("OUTBOUND_DROP_NOT_FOUND","VALIDATION",404);
  const result=await commit(env,auth,{eventType:"OUTBOUND_DROP_DELETE_SELECTED",entityType:"OUTBOUND_DROP",entityId:"BULK",businessDate:bangkokToday(),idempotencyKey:idem,payload:{mnv:"",record_ids:foundIds,rows_deleted:foundIds.length},baseVersion:0,newVersion:1,preconditionSql:"1=1",preconditionBindings:[],projection:(eventId)=>foundIds.map(id=>env.DB.prepare("DELETE FROM outbound_drop_records WHERE record_id=?1 AND EXISTS(SELECT 1 FROM events WHERE event_id=?2)").bind(id,eventId))});
  if(result instanceof Response)return result;
  return json({ok:true,source:"SERVICE_D1",idempotent:result.duplicate,rows_deleted:foundIds.length,event_id:result.event.event_id,replication:"OUTBOX_PENDING"});
}

async function dropClear(env:Env,auth:AuthContext,body:Record<string,unknown>):Promise<Response>{
  if(auth.role!=="SUPERADMIN")return apiError("SUPERADMIN_REQUIRED","PERMISSION",403);
  const idem=String(body.idempotency_key||body.event_id||"").trim();if(!idem)return apiError("OUTBOUND_IDEMPOTENCY_REQUIRED","VALIDATION",400);
  const count=await env.DB.prepare("SELECT COUNT(*) n FROM outbound_drop_records").first<{n:number}>(),rows=Number(count?.n||0);
  const result=await commit(env,auth,{eventType:"OUTBOUND_DROP_CLEAR",entityType:"OUTBOUND_DROP",entityId:"ALL",businessDate:bangkokToday(),idempotencyKey:idem,payload:{mnv:"",rows_deleted:rows},baseVersion:0,newVersion:1,preconditionSql:"1=1",preconditionBindings:[],projection:(eventId)=>[env.DB.prepare(`DELETE FROM outbound_drop_records WHERE EXISTS(SELECT 1 FROM events WHERE event_id=?1)`).bind(eventId)]});
  if(result instanceof Response)return result;
  return json({ok:true,source:"SERVICE_D1",idempotent:result.duplicate,rows_deleted:rows,remaining:0,event_id:result.event.event_id,replication:"OUTBOX_PENDING"});
}

export async function outboundAction(env:Env,auth:AuthContext,action:string,body:Record<string,unknown>):Promise<Response>{
  if(action==="outbound_location_list")return locationList(env,auth);
  if(action==="outbound_location_mutate")return locationMutate(env,auth,body);
  if(action==="outbound_drop_append")return dropAppend(env,auth,body);
  if(action==="outbound_drop_list")return dropList(env);
  if(action==="outbound_drop_delete")return dropDelete(env,auth,body);
  if(action==="outbound_drop_clear")return dropClear(env,auth,body);
  return apiError("OUTBOUND_ACTION_UNSUPPORTED","VALIDATION",400);
}

function parsePayload(e:EventRow):Record<string,unknown>{try{return JSON.parse(e.payload_json) as Record<string,unknown>;}catch{return{};}}
async function replicateOne(env:Env,token:string,e:EventRow):Promise<void>{
  const p=parsePayload(e);
  if(e.event_type==="OUTBOUND_DROP_APPEND"){
    const id=String(p.record_id||e.idempotency_key),ids=await getValues(env,token,DROP_SHEET,"H2:H");
    if(ids.some(r=>String(r[0]||"")===id))return;
    await appendValues(env,token,DROP_SHEET,"A:H",[[String(p.location||""),visibleDate(e.business_date),String(p.scan_qr||""),String(p.do_number||""),Number(p.package_count||0),String(p.actor_display_name||e.actor_id),visibleDateTime(e.occurred_at),id]]);return;
  }
  if(e.event_type==="OUTBOUND_DROP_DELETE_SELECTED"){
    const ids=new Set((Array.isArray(p.record_ids)?p.record_ids:[]).map(x=>String(x||"")));
    const rows=await getValues(env,token,DROP_SHEET,"A2:H");
    if(rows.length){
      const next=rows.map(r=>ids.has(String(r[7]||""))?["","","","","","","",""]:r);
      await putValues(env,token,DROP_SHEET,`A2:H${rows.length+1}`,next);
    }
    return;
  }
  if(e.event_type==="OUTBOUND_DROP_CLEAR"){
    const rows=await getValues(env,token,DROP_SHEET,"A2:H");if(rows.length)await putValues(env,token,DROP_SHEET,`A2:H${rows.length+1}`,rows.map(()=>["","","","","","","",""]));return;
  }
  if(e.event_type.startsWith("OUTBOUND_LOCATION_")){
    const rows=await getValues(env,token,LOCATION_SHEET,"A2:A"),values=rows.map(r=>norm(r[0])),keys=values.map(key),before=norm(p.before),after=norm(p.after),beforeKey=key(before),afterKey=key(after);
    if(e.event_type==="OUTBOUND_LOCATION_CREATE"){
      if(!keys.includes(afterKey))await appendValues(env,token,LOCATION_SHEET,"A:A",[[after]]);return;
    }
    if(e.event_type==="OUTBOUND_LOCATION_UPDATE"){
      const idx=keys.indexOf(beforeKey);if(idx>=0)await putValues(env,token,LOCATION_SHEET,`A${idx+2}:A${idx+2}`,[[after]]);else if(!keys.includes(afterKey))await appendValues(env,token,LOCATION_SHEET,"A:A",[[after]]);return;
    }
    if(e.event_type==="OUTBOUND_LOCATION_DELETE"){
      const idx=keys.indexOf(beforeKey);if(idx>=0)await putValues(env,token,LOCATION_SHEET,`A${idx+2}:A${idx+2}`,[[""]]);return;
    }
  }
}

export async function replicateOutboundPending(env:Env,limit=25):Promise<{ok:boolean;processed:number;pending:number;error?:string}>{
  const now=nowIso(),stale=new Date(Date.now()-15*60_000).toISOString();
  await env.DB.prepare("UPDATE outbound_replication_outbox SET status='RETRY',claimed_at=NULL,next_attempt_at=?1,last_error=COALESCE(last_error,'STALE_INFLIGHT_RECOVERED') WHERE status='INFLIGHT' AND (claimed_at IS NULL OR claimed_at<=?2)").bind(now,stale).run();
  const rows=(await env.DB.prepare("SELECT outbox_id,event_id,attempt_count FROM outbound_replication_outbox WHERE status IN ('PENDING','RETRY') AND next_attempt_at<=?1 ORDER BY outbox_id LIMIT ?2").bind(now,Math.max(1,Math.min(limit,50))).all<{outbox_id:number;event_id:string;attempt_count:number}>()).results??[];
  if(!rows.length){const p=await env.DB.prepare("SELECT COUNT(*) n FROM outbound_replication_outbox WHERE status IN ('PENDING','RETRY','INFLIGHT')").first<{n:number}>();return{ok:true,processed:0,pending:Number(p?.n||0)};}
  try{
    const token=await googleAccessToken(env),claimAt=nowIso();
    for(const row of rows){
      await env.DB.prepare("UPDATE outbound_replication_outbox SET status='INFLIGHT',claimed_at=?1,attempt_count=attempt_count+1,last_error=NULL WHERE outbox_id=?2 AND status IN ('PENDING','RETRY')").bind(claimAt,row.outbox_id).run();
      const e=await env.DB.prepare("SELECT * FROM events WHERE event_id=?1").bind(row.event_id).first<EventRow>();if(!e)throw new Error(`OUTBOUND_EVENT_MISSING:${row.event_id}`);
      await replicateOne(env,token,e);
      await env.DB.prepare("UPDATE outbound_replication_outbox SET status='SYNCED',claimed_at=NULL,replicated_at=?1,last_error=NULL WHERE outbox_id=?2").bind(nowIso(),row.outbox_id).run();
    }
    const p=await env.DB.prepare("SELECT COUNT(*) n FROM outbound_replication_outbox WHERE status IN ('PENDING','RETRY','INFLIGHT')").first<{n:number}>();return{ok:true,processed:rows.length,pending:Number(p?.n||0)};
  }catch(e){
    const msg=String(e).slice(0,500),next=new Date(Date.now()+10_000).toISOString();
    await env.DB.batch(rows.map(r=>env.DB.prepare("UPDATE outbound_replication_outbox SET status='RETRY',claimed_at=NULL,next_attempt_at=?1,last_error=?2 WHERE outbox_id=?3 AND status='INFLIGHT'").bind(next,msg,r.outbox_id)));
    const p=await env.DB.prepare("SELECT COUNT(*) n FROM outbound_replication_outbox WHERE status IN ('PENDING','RETRY','INFLIGHT')").first<{n:number}>();return{ok:false,processed:0,pending:Number(p?.n||0),error:msg};
  }
}

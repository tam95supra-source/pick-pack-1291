import { authenticate } from "./auth";
import { commitMutation, currentAuthority } from "./core";
import { bangkokToday, ensureCurrentBangkokBusinessDate } from "./business_date";
import { historicalSessionDetail } from "./historical_beta78";
import { outboundAction } from "./outbound_beta78";
import { mealAttendanceDates, mealAttendanceList } from "./meal_attendance";
import { apiError, b64u, b64uDecode, hmacB64u, json, nowIso, readJsonBody } from "./util";
import type { AuthContext } from "./domain";

type GasTokenPayload = { l?:string; r?:string; v?:string; s?:string; d?:string };
type Employee = { mnv:string; full_name:string; phone:string; main_position:string; supplier:string; department:string; site:string; warehouse:string; start_date:string; note:string };

function parseGasToken(token:string):GasTokenPayload|null{
  try{
    const first=token.split(".")[0]; if(!first)return null;
    return JSON.parse(new TextDecoder().decode(b64uDecode(first))) as GasTokenPayload;
  }catch{return null;}
}

async function validateGasSession(env:Env,gasToken:string,payload:GasTokenPayload):Promise<Record<string,unknown>|null>{
  const controller=new AbortController(); const timer=setTimeout(()=>controller.abort(),4500);
  try{
    const gasUrl=String(env.GAS_API_URL||"").trim();
    if(!gasUrl.startsWith("https://script.google.com/"))return null;
    const environmentId=String(env.ENVIRONMENT_ID||"BETA").toUpperCase(),serviceAudience=String(env.SERVICE_AUDIENCE||(environmentId==="STABLE"?"PICK_PACK_1291_STABLE":"PICK_PACK_1291_BETA"));
    const response=await fetch(gasUrl,{
      method:"POST",
      headers:{"content-type":"application/json; charset=utf-8","accept":"application/json","x-pick-pack-environment":environmentId,"x-pick-pack-audience":serviceAudience},
      body:JSON.stringify({action:"m2_authority_status",_token:gasToken,_device_id:String(payload.d||""),_app_channel:environmentId,_environment_id:environmentId,_service_audience:serviceAudience,_app_version:"m2-session-exchange-v1"}),
      signal:controller.signal,
    });
    const body=await response.json() as Record<string,unknown>;
    return response.ok&&body.ok===true?body:null;
  }catch{return null;}finally{clearTimeout(timer);}
}

export async function exchangeGasSession(request:Request,env:Env):Promise<Response>{
  const input=await readJsonBody<{gas_token?:string;device_id?:string;device_label?:string}>(request,64_000);
  const gasToken=String(input.gas_token||"").trim(),deviceId=String(input.device_id||"").trim().slice(0,180);
  if(!gasToken||!deviceId)return apiError("SESSION_EXCHANGE_FIELDS_REQUIRED","VALIDATION",400);
  const payload=parseGasToken(gasToken);
  if(!payload?.l||!payload.r||!payload.v||!payload.s||!payload.d)return apiError("GAS_SESSION_INVALID","AUTH",401);
  const discovery=await validateGasSession(env,gasToken,payload);
  if(!discovery)return apiError("GAS_SESSION_INVALID","AUTH",401);
  if(String(discovery.authority_mode||"")!=="SERVICE_PRIMARY")return apiError("SERVICE_NOT_PRIMARY","CONFLICT",409,true);

  const account=await env.DB.prepare("SELECT login_id,role,display_name,position,email,verifier_hash,status FROM accounts WHERE login_id=?1")
    .bind(String(payload.l)).first<{login_id:string;role:string;display_name:string;position:string;email:string;verifier_hash:string;status:string}>();
  if(!account||account.status!=="ACTIVE"||account.role!==String(payload.r))return apiError("SESSION_EXCHANGE_ACCOUNT_MISMATCH","AUTH",401);

  const current=await env.DB.prepare("SELECT session_id,device_id FROM auth_sessions WHERE login_id=?1").bind(account.login_id).first<{session_id:string;device_id:string}>();
  const reused=Boolean(current?.session_id&&current.device_id===deviceId);
  const sessionId=reused?String(current?.session_id):crypto.randomUUID(),issuedAt=nowIso();
  await env.DB.prepare(`INSERT INTO auth_sessions(login_id,session_id,device_id,issued_at) VALUES(?1,?2,?3,?4)
    ON CONFLICT(login_id) DO UPDATE SET session_id=excluded.session_id,device_id=excluded.device_id,issued_at=excluded.issued_at`)
    .bind(account.login_id,sessionId,deviceId,issuedAt).run();
  const environmentId=String(env.ENVIRONMENT_ID||"BETA").toUpperCase(),serviceAudience=String(env.SERVICE_AUDIENCE||(environmentId==="STABLE"?"PICK_PACK_1291_STABLE":"PICK_PACK_1291_BETA"));
  const servicePayload={l:account.login_id,r:account.role,v:account.verifier_hash,s:sessionId,d:deviceId,e:environmentId,a:serviceAudience};
  const encoded=b64u(new TextEncoder().encode(JSON.stringify(servicePayload)));
  const sig=await hmacB64u(new TextEncoder().encode(env.SERVICE_TOKEN_SECRET),encoded);
  return json({ok:true,token:`${encoded}.${sig}`,account:{login_id:account.login_id,role:account.role,display_name:account.display_name,position:account.position,email:account.email},session:{issued_at:issuedAt,device_label:String(input.device_label||"").slice(0,120),session_id:sessionId,reused},authority:discovery.authority,authority_mode:discovery.authority_mode,service_generation:discovery.service_generation});
}

async function businessDate(db:D1Database):Promise<string>{
  const date=bangkokToday();await ensureCurrentBangkokBusinessDate(db,date);return date;
}

function employeeJson(e:Employee|null){return e?{mnv:e.mnv,full_name:e.full_name,phone:e.phone,main_position:e.main_position,supplier:e.supplier,department:e.department,site:e.site,warehouse:e.warehouse,start_date:e.start_date,note:e.note}:null;}
function visibleWork(v:string){return v==="KHONG"?"KHÔNG":v;}

async function resourceOptions(db:D1Database,date:string,mnv:string):Promise<Record<string,unknown>>{
  const leaseRows=(await db.prepare("SELECT resource_type,resource_id,mnv FROM resource_leases").all<{resource_type:string;resource_id:string;mnv:string}>()).results??[];
  const busy=new Set(leaseRows.filter(x=>x.mnv!==mnv).map(x=>`${x.resource_type}|${x.resource_id}`));
  const usedRows=(await db.prepare("SELECT resource_type,resource_id,mnv FROM resource_daily_consumption WHERE business_date=?1").bind(date).all<{resource_type:string;resource_id:string;mnv:string}>()).results??[];
  const used=new Set(usedRows.filter(x=>x.mnv!==mnv).map(x=>`${x.resource_type}|${x.resource_id}`));
  const current=await db.prepare("SELECT pda_serial,user_pick,pack_table,user_pack FROM attendance_sessions WHERE mnv=?1 AND state='ACTIVE' ORDER BY business_date DESC,enter_at DESC LIMIT 1").bind(mnv).first<{pda_serial:string|null;user_pick:string|null;pack_table:string|null;user_pack:string|null}>();

  const pdasRaw=(await db.prepare("SELECT resource_id,status_label,available,metadata_json FROM resources WHERE resource_type='PDA' ORDER BY resource_id").all<{resource_id:string;status_label:string;available:number;metadata_json:string}>()).results??[];
  const pdas=pdasRaw.filter(x=>{
    const isCurrent=x.resource_id===current?.pda_serial;
    return isCurrent||(Number(x.available)===1&&!busy.has(`PDA|${x.resource_id}`));
  }).map(x=>{let m:Record<string,unknown>={};try{m=JSON.parse(x.metadata_json) as Record<string,unknown>;}catch{}return{serial:x.resource_id,last5:String(m["5 số cuối Seri"]||x.resource_id.slice(-5)),status:x.status_label};});

  const picksRaw=(await db.prepare("SELECT resource_id,available FROM resources WHERE resource_type='USER_PICK' ORDER BY resource_id").all<{resource_id:string;available:number}>()).results??[];
  const user_picks:string[]=[];
  const user_picks_reissue:Array<Record<string,unknown>>=[];
  for(const x of picksRaw){
    const id=x.resource_id,currentPick=id===current?.user_pick;
    if(currentPick){user_picks.push(id);continue;}
    if(Number(x.available)!==1||busy.has(`USER_PICK|${id}`))continue;
    if(used.has(`USER_PICK|${id}`))user_picks_reissue.push({id,busy:false,used_today:true,duplicate_user:true,note:"TRÙNG USER"});
    else user_picks.push(id);
  }

  const packsRaw=(await db.prepare("SELECT m.pack_table,m.shift,m.user_pack,m.available mapping_available,COALESCE(t.available,0) table_available,COALESCE(u.available,0) user_pack_available FROM resource_pack_map m LEFT JOIN resources t ON t.resource_type='PACK_TABLE' AND t.resource_id=m.pack_table LEFT JOIN resources u ON u.resource_type='USER_PACK' AND u.resource_id=m.user_pack ORDER BY m.pack_table,m.shift,m.user_pack").all<{pack_table:string;shift:string;user_pack:string;mapping_available:number;table_available:number;user_pack_available:number}>()).results??[];
  const pack_tables:Array<Record<string,unknown>>=[];
  const pack_tables_reissue:Array<Record<string,unknown>>=[];
  for(const x of packsRaw){
    const currentPair=x.pack_table===current?.pack_table&&x.user_pack===current?.user_pack;
    const row={table:x.pack_table,shift:x.shift,user_pack:x.user_pack};
    if(currentPair){pack_tables.push(row);continue;}
    if(Number(x.mapping_available)!==1||Number(x.table_available)!==1||Number(x.user_pack_available)!==1)continue;
    if(busy.has(`PACK_TABLE|${x.pack_table}`)||busy.has(`USER_PACK|${x.user_pack}`))continue;
    if(used.has(`USER_PACK|${x.user_pack}`))pack_tables_reissue.push({...row,duplicate_user:true,note:"TRÙNG USER"});
    else pack_tables.push(row);
  }
  return{ok:true,business_date:date,pdas,user_picks,user_picks_reissue,pack_tables,pack_tables_reissue,current};
}

async function employeeContext(env:Env,body:Record<string,unknown>):Promise<Response>{
  const mnv=String(body.mnv||"").trim();if(!mnv)return apiError("MNV_REQUIRED","VALIDATION",400);
  const date=await businessDate(env.DB),requestedSessionId=String(body.session_id||"").trim();
  const employee=await env.DB.prepare("SELECT mnv,full_name,phone,main_position,supplier,department,site,warehouse,start_date,note FROM employees WHERE mnv=?1").bind(mnv).first<Employee>();
  if(!employee)return apiError("EMPLOYEE_NOT_FOUND","VALIDATION",404);
  const requestedSession=requestedSessionId?await env.DB.prepare("SELECT session_id,mnv,business_date,shift,work_choice,state,pda_serial,user_pick,pack_table,user_pack,pda_enter_status,pda_exit_status,resource_note,enter_at,exit_at,entered_by,exited_by,version FROM attendance_sessions WHERE session_id=?1 AND mnv=?2").bind(requestedSessionId,mnv).first<Record<string,unknown>>():null;
  if(requestedSessionId&&!requestedSession)return apiError("SESSION_NOT_FOUND","VALIDATION",404);
  const currentSession=requestedSessionId?null:await env.DB.prepare("SELECT session_id,mnv,business_date,shift,work_choice,state,pda_serial,user_pick,pack_table,user_pack,pda_enter_status,pda_exit_status,resource_note,enter_at,exit_at,entered_by,exited_by,version FROM attendance_sessions WHERE business_date=?1 AND mnv=?2").bind(date,mnv).first<Record<string,unknown>>();
  const activeSession=requestedSessionId?null:await env.DB.prepare("SELECT session_id,mnv,business_date,shift,work_choice,state,pda_serial,user_pick,pack_table,user_pack,pda_enter_status,pda_exit_status,resource_note,enter_at,exit_at,entered_by,exited_by,version FROM attendance_sessions WHERE mnv=?1 AND state='ACTIVE' ORDER BY business_date DESC,enter_at DESC LIMIT 1").bind(mnv).first<Record<string,unknown>>();
  const session=requestedSession??activeSession??currentSession;
  const state=!session?"NOT_ENTERED":String(session.state)==="ACTIVE"?"ACTIVE":"ENDED";
  const sessionOut:Record<string,unknown>|null=session?{...session,work_choice:visibleWork(String(session.work_choice||""))}:null;
  const laborDate=String(session?.business_date||date);
  const laborRows=body.include_labor===true?(await env.DB.prepare("SELECT labor_id,mnv,business_date,shift,labor_type,time_marker,state,start_at,end_at,note,deduct_staff,start_event_id,finish_event_id,version FROM labor_sessions WHERE business_date=?1 AND mnv=?2 ORDER BY start_at ASC,labor_id ASC").bind(laborDate,mnv).all<Record<string,unknown>>()).results??[]:[];
  const activeLabor=laborRows.find(x=>String(x.state)==="OPEN")??null;
  const options=body.include_options===true?await resourceOptions(env.DB,laborDate,mnv):null;
  return json({ok:true,source:"SERVICE_D1",business_date:laborDate,employee:employeeJson(employee),state,session:sessionOut,active_labor:activeLabor,labor_intervals:laborRows,options});
}

async function laborDates(env:Env):Promise<Response>{
  const rows=(await env.DB.prepare("SELECT business_date,COUNT(*) item_count FROM labor_sessions GROUP BY business_date HAVING COUNT(*)>0 ORDER BY business_date DESC").all<{business_date:string;item_count:number}>()).results??[];
  return json({ok:true,source:"SERVICE_D1",dates:rows.map(x=>x.business_date),counts:Object.fromEntries(rows.map(x=>[x.business_date,Number(x.item_count||0)]))});
}

async function laborList(env:Env,body:Record<string,unknown>):Promise<Response>{
  const current=await businessDate(env.DB),requested=String(body.business_date||"").trim(),date=requested||current;
  if(!/^\d{4}-\d{2}-\d{2}$/.test(date))return apiError("BUSINESS_DATE_INVALID","VALIDATION",400);
  const exists=await env.DB.prepare("SELECT 1 ok FROM business_dates WHERE business_date=?1").bind(date).first<{ok:number}>();
  if(!exists)return json({ok:true,source:"SERVICE_D1",business_date:date,open_count:0,completed_count:0,items:[]});
  const rows=(await env.DB.prepare(`SELECT l.labor_id,l.mnv,l.business_date,l.shift,l.labor_type,l.time_marker,l.state,l.start_at,l.end_at,l.note,l.deduct_staff,l.start_event_id,l.finish_event_id,l.version,
    COALESCE(e.full_name,'') full_name,COALESCE(e.supplier,'') supplier,a.session_id attendance_session_id,a.state attendance_state
    FROM labor_sessions l LEFT JOIN employees e ON e.mnv=l.mnv
    LEFT JOIN attendance_sessions a ON a.mnv=l.mnv AND a.business_date=l.business_date
    WHERE l.business_date=?1 ORDER BY CASE WHEN l.state='OPEN' THEN 0 ELSE 1 END,l.start_at DESC,l.mnv`).bind(date).all<Record<string,unknown>>()).results??[];
  return json({ok:true,source:"SERVICE_D1",business_date:date,open_count:rows.filter(x=>String(x.state)==="OPEN").length,completed_count:rows.filter(x=>String(x.state)==="COMPLETED").length,items:rows});
}

async function oldActiveSessions(env:Env):Promise<Response>{
  const date=await businessDate(env.DB);
  const items=(await env.DB.prepare("SELECT s.session_id,s.mnv,s.business_date,s.shift,s.work_choice,s.state,s.pda_serial,s.user_pick,s.pack_table,s.user_pack,s.enter_at,s.version,COALESCE(e.full_name,'') full_name FROM attendance_sessions s LEFT JOIN employees e ON e.mnv=s.mnv WHERE s.state='ACTIVE' AND s.business_date<?1 ORDER BY s.business_date ASC,s.enter_at ASC,s.mnv ASC").bind(date).all<Record<string,unknown>>()).results??[];
  return json({ok:true,source:"SERVICE_D1",business_date:date,count:items.length,items});
}

async function oldActiveSessionsBulkExit(env:Env,auth:AuthContext):Promise<Response>{
  if(auth.role!=="SUPERADMIN")return apiError("SUPERADMIN_REQUIRED","PERMISSION",403);
  const date=await businessDate(env.DB);
  const items=(await env.DB.prepare(`SELECT s.session_id,s.mnv,s.business_date,s.shift,s.pda_serial,s.version,
      (SELECT COUNT(*) FROM labor_sessions l WHERE l.mnv=s.mnv AND l.business_date=s.business_date) labor_count
    FROM attendance_sessions s
    WHERE s.state='ACTIVE' AND s.business_date<?1
    ORDER BY s.business_date ASC,s.enter_at ASC,s.mnv ASC`).bind(date).all<Record<string,unknown>>()).results??[];
  let exited=0;const skippedLabor:Array<Record<string,unknown>>=[];const failed:Array<Record<string,unknown>>=[];
  for(const row of items){
    const sessionId=String(row.session_id||""),mnv=String(row.mnv||""),businessDateValue=String(row.business_date||"");
    if(Number(row.labor_count||0)>0){skippedLabor.push({session_id:sessionId,mnv,business_date:businessDateValue,reason:"HAS_LABOR"});continue;}
    try{
      await commitMutation(env.DB,env,auth,{
        event_id:crypto.randomUUID(),event_type:"ATTENDANCE_EXIT",entity_type:"ATTENDANCE_SESSION",entity_id:sessionId,
        business_date:businessDateValue,base_version:Number(row.version||0),timestamp:nowIso(),
        payload:{mnv,pda_exit_status:"SUPERADMIN_CONFIRMED",resource_note:"SUPERADMIN_BULK_OLD_SESSION_EXIT",superadmin_bulk_exit:true,pda_auto_confirmed:Boolean(String(row.pda_serial||""))},
        idempotency_key:`OLD_SESSION_BULK_EXIT|${sessionId}|${Number(row.version||0)}`,device_id:auth.device_id||"SUPERADMIN_BULK_EXIT",schema_version:1,client_source:"PDA"
      });
      exited++;
    }catch(error){failed.push({session_id:sessionId,mnv,business_date:businessDateValue,error:String(error instanceof Error?error.message:error).slice(0,160)});}
  }
  const remaining=(await env.DB.prepare("SELECT s.session_id,s.mnv,s.business_date,s.shift,s.work_choice,s.state,s.pda_serial,s.user_pick,s.pack_table,s.user_pack,s.enter_at,s.version,COALESCE(e.full_name,'') full_name FROM attendance_sessions s LEFT JOIN employees e ON e.mnv=s.mnv WHERE s.state='ACTIVE' AND s.business_date<?1 ORDER BY s.business_date ASC,s.enter_at ASC,s.mnv ASC").bind(date).all<Record<string,unknown>>()).results??[];
  return json({ok:true,source:"SERVICE_D1",business_date:date,exited,skipped_labor:skippedLabor.length,failed_count:failed.length,skipped_labor_items:skippedLabor,failed,remaining_count:remaining.length,items:remaining});
}

function eventLabel(type:string):string{return type==="ATTENDANCE_ENTER"?"Vào ca":type==="ATTENDANCE_EXIT"?"Ra ca":type==="RESOURCE_CHANGE"?"Đổi tài nguyên":type==="LABOR_START"?"Bắt đầu công nhật":type==="LABOR_FINISH"?"Hoàn thành công nhật":type;}

async function sharedHistory(env:Env,body:Record<string,unknown>):Promise<Response>{
  const requested=String(body.business_date||"").trim();const date=requested||await businessDate(env.DB),target=String(body.mnv||"").trim();
  const raw=(await env.DB.prepare("SELECT event_id,event_type,actor_id,committed_at,payload_json FROM events WHERE business_date=?1 ORDER BY authority_seq").bind(date).all<{event_id:string;event_type:string;actor_id:string;committed_at:string;payload_json:string}>()).results??[];
  const employeeRows=(await env.DB.prepare("SELECT mnv,full_name FROM employees").all<{mnv:string;full_name:string}>()).results??[];const names=new Map(employeeRows.map(x=>[x.mnv,x.full_name]));
  const timeline=raw.map(e=>{let p:Record<string,unknown>={};try{p=JSON.parse(e.payload_json) as Record<string,unknown>;}catch{}const mnv=String(p.mnv||"");return{scope:"SESSION",session_id:`${date}|${mnv}`,mnv,full_name:names.get(mnv)||"",shift:String(p.shift||""),event_type:e.event_type,label:eventLabel(e.event_type),at:e.committed_at,at_iso:e.committed_at,actor:e.actor_id,detail:String(p.labor_type||p.note||""),event_id:e.event_id};}).filter(x=>x.mnv&&(!target||x.mnv===target));
  if(target)return json({ok:true,source:"SERVICE_D1",history_engine:"M2_CANONICAL_D1",business_date:date,mnv:target,timeline});
  const groups:Record<string,{mnv:string;full_name:string;shift:string;state:string;event_count:number;last_time:string;last_at_iso:string;last_actor:string;last_label:string}>={};
  for(const e of timeline){let g=groups[e.mnv];if(!g)g=groups[e.mnv]={mnv:e.mnv,full_name:e.full_name,shift:e.shift,state:"ACTIVE",event_count:0,last_time:"",last_at_iso:"",last_actor:"",last_label:""};if(e.full_name)g.full_name=e.full_name;if(e.shift)g.shift=e.shift;g.event_count++;if(e.event_type==="ATTENDANCE_EXIT")g.state="ENDED";g.last_time=e.at;g.last_at_iso=e.at_iso;g.last_actor=e.actor;g.last_label=e.label;}
  const items=Object.values(groups).sort((a,b)=>(Date.parse(b.last_at_iso)||0)-(Date.parse(a.last_at_iso)||0));
  return json({ok:true,source:"SERVICE_D1",history_engine:"M2_CANONICAL_D1",business_date:date,total:items.length,active_count:items.filter(x=>x.state==="ACTIVE").length,ended_count:items.filter(x=>x.state==="ENDED").length,items});
}


async function lanManualMode(env:Env,auth:{login_id:string;role:string},body:Record<string,unknown>):Promise<Response>{
  const action=String(body.action||"");
  if(action==="lan_manual_mode_set"){
    if(auth.role!=="SUPERADMIN")return apiError("SUPERADMIN_REQUIRED","PERMISSION",403);
    const enabled=body.enabled===true,at=nowIso();
    await env.DB.prepare(`INSERT INTO lan_manual_mode(singleton_id,enabled,epoch,enabled_by,updated_at)
      VALUES(1,?1,1,?2,?3)
      ON CONFLICT(singleton_id) DO UPDATE SET enabled=excluded.enabled,epoch=lan_manual_mode.epoch+1,enabled_by=excluded.enabled_by,updated_at=excluded.updated_at`)
      .bind(enabled?1:0,auth.login_id,at).run();
  }
  const row=await env.DB.prepare("SELECT enabled,epoch,enabled_by,updated_at FROM lan_manual_mode WHERE singleton_id=1").first<{enabled:number;epoch:number;enabled_by:string;updated_at:string}>();
  return json({ok:true,manual_mode:{enabled:Number(row?.enabled||0)===1,epoch:Number(row?.epoch||0),enabled_by:String(row?.enabled_by||""),updated_at:String(row?.updated_at||"")}});
}

async function lanTestMode(env:Env,auth:{login_id:string;role:string},body:Record<string,unknown>):Promise<Response>{
  const action=String(body.action||"");
  if(action==="lan_test_mode_set"){
    if(auth.role!=="SUPERADMIN")return apiError("SUPERADMIN_REQUIRED","PERMISSION",403);
    const enabled=body.enabled===true;
    const at=nowIso();
    await env.DB.prepare(`INSERT INTO lan_test_mode(singleton_id,enabled,epoch,enabled_by,updated_at)
      VALUES(1,?1,1,?2,?3)
      ON CONFLICT(singleton_id) DO UPDATE SET enabled=excluded.enabled,epoch=lan_test_mode.epoch+1,enabled_by=excluded.enabled_by,updated_at=excluded.updated_at`)
      .bind(enabled?1:0,auth.login_id,at).run();
  }
  const row=await env.DB.prepare("SELECT enabled,epoch,enabled_by,updated_at FROM lan_test_mode WHERE singleton_id=1").first<{enabled:number;epoch:number;enabled_by:string;updated_at:string}>();
  return json({ok:true,test_mode:{enabled:Number(row?.enabled||0)===1,epoch:Number(row?.epoch||0),enabled_by:String(row?.enabled_by||""),updated_at:String(row?.updated_at||"")}});
}

export async function mobileRead(request:Request,env:Env):Promise<Response>{
  const auth=await authenticate(env.DB,env,request);if(!auth)return apiError("UNAUTHORIZED","AUTH",401);
  const body=await readJsonBody<Record<string,unknown>>(request,256_000),action=String(body.action||"");
  if(action==="employee_context")return employeeContext(env,body);
  if(action==="master_options")return json(await resourceOptions(env.DB,await businessDate(env.DB),String(body.mnv||"")));
  if(action==="history_shared")return sharedHistory(env,body);
  if(action==="old_active_sessions")return oldActiveSessions(env);
  if(action==="old_active_sessions_bulk_exit")return oldActiveSessionsBulkExit(env,auth);
  if(action==="historical_session_detail")return historicalSessionDetail(env,body);
  if(action==="meal_attendance_list")return mealAttendanceList(env,{business_date:String(body.business_date||"")});
  if(action==="meal_attendance_dates")return mealAttendanceDates(env);
  if(action==="labor_list")return laborList(env,body);
  if(action==="labor_dates")return laborDates(env);
  if(action==="lan_test_mode_get"||action==="lan_test_mode_set")return lanTestMode(env,auth,body);
  if(action==="lan_manual_mode_get"||action==="lan_manual_mode_set")return lanManualMode(env,auth,body);
  if(action.startsWith("outbound_"))return outboundAction(env,auth,action,body);
  if(action==="runtime_status")return json({ok:true,source:"SERVICE_D1",authority:await currentAuthority(env.DB),service_generation:env.SERVICE_GENERATION});
  return apiError("MOBILE_READ_ACTION_UNSUPPORTED","VALIDATION",400);
}

import type { AuthContext, CanonicalMutationRequest } from "./domain";
import { commitMutation, CoreError, currentAuthority } from "./core";
import { bangkokToday, ensureCurrentBangkokBusinessDate } from "./business_date";
import { nowIso } from "./util";

export interface LegacyMutationInput {
  action: "enter" | "exit" | "resource_change" | "labor_start" | "labor_finish" | "meal_checkin" | "meal_status" | "resilience_probe";
  payload: Record<string, unknown>;
  event_id?: string;
  business_date?: string;
  device_id?: string;
}

interface AttendanceVersionRow { session_id:string; state:string; version:number; }
interface LaborVersionRow { labor_id:string; state:string; version:number; }

function text(v:unknown,max=240):string{return String(v??"").trim().slice(0,max);}

async function currentBusinessDate(db:D1Database):Promise<string>{
  const date=bangkokToday();
  try{await ensureCurrentBangkokBusinessDate(db,date);return date;}catch{
    throw new CoreError("BUSINESS_DATE_NOT_BOOTSTRAPPED","INTEGRITY",503,true);
  }
}

async function attendance(db:D1Database,mnv:string,date:string):Promise<AttendanceVersionRow|null>{
  return db.prepare("SELECT session_id,state,version FROM attendance_sessions WHERE mnv=?1 AND business_date=?2").bind(mnv,date).first<AttendanceVersionRow>();
}

async function activeLabor(db:D1Database,mnv:string,date:string):Promise<LaborVersionRow|null>{
  return db.prepare("SELECT labor_id,state,version FROM labor_sessions WHERE mnv=?1 AND business_date=?2 AND state='OPEN' ORDER BY start_at DESC LIMIT 1").bind(mnv,date).first<LaborVersionRow>();
}

async function releaseEndedUserPackConsumption(db:D1Database,date:string,userPack:string):Promise<void>{
  if(!userPack)return;
  const active=await db.prepare("SELECT 1 AS ok FROM resource_leases WHERE resource_type='USER_PACK' AND resource_id=?1 AND business_date=?2 LIMIT 1").bind(userPack,date).first<{ok:number}>();
  if(active?.ok)return;
  // resource_daily_consumption is an exclusivity guard/projection, not the immutable Event Ledger.
  // Clearing only a stale USER_PACK guard lets a completed session's mapped user be issued again
  // in the same day; the original assignment remains preserved in canonical events/history.
  await db.prepare("DELETE FROM resource_daily_consumption WHERE business_date=?1 AND resource_type='USER_PACK' AND resource_id=?2").bind(date,userPack).run();
}

export async function legacyCanonical(db:D1Database,input:LegacyMutationInput,auth:AuthContext):Promise<CanonicalMutationRequest>{
  const payload=input.payload&&typeof input.payload==="object"?input.payload:{},mnv=text(payload.mnv,80);
  if(!mnv)throw new CoreError("MNV_REQUIRED","VALIDATION",400);
  const today=await currentBusinessDate(db);
  const explicit=text(input.business_date||payload.business_date,10);
  const businessDate=explicit||today;
  const a=await currentAuthority(db),device=text(input.device_id||payload._device_id||auth.device_id,180)||auth.device_id;
  const eventId=text(input.event_id||payload.event_id,180)||crypto.randomUUID();
  let eventType:CanonicalMutationRequest["event_type"],entityType:string,entityId:string,baseVersion=0,canonicalPayload:Record<string,unknown>={...payload,mnv};

  if(input.action==="enter"){
    const old=await attendance(db,mnv,businessDate);
    const pack=text(payload.user_pack||payload.userPack,180);await releaseEndedUserPackConsumption(db,businessDate,pack);
    eventType="ATTENDANCE_ENTER";entityType="ATTENDANCE_SESSION";entityId=old?.session_id||crypto.randomUUID();baseVersion=old?.version??0;
    canonicalPayload={mnv,shift:text(payload.shift,80),work_choice:text(payload.work_choice,40),pda_serial:text(payload.pda_serial||payload.pda,180),user_pick:text(payload.user_pick||payload.userPick,180),pack_table:text(payload.pack_table||payload.packTable,180),user_pack:pack,pda_enter_status:text(payload.pda_enter_status||payload.pda_status_at_enter,180),resource_note:text(payload.resource_note,500),duplicate_user:Boolean(payload.duplicate_user),note:text(payload.note,500)}; // S44_IDEMPOTENT_PDA_SESSION_ATTENDANCE
  }else if(input.action==="exit"||input.action==="resource_change"){
    const old=await attendance(db,mnv,businessDate);if(!old)throw new CoreError("ATTENDANCE_NOT_ENTERED","CONFLICT",409);
    if(input.action==="resource_change")await releaseEndedUserPackConsumption(db,businessDate,text(payload.user_pack||payload.userPack,180));
    eventType=input.action==="exit"?"ATTENDANCE_EXIT":"RESOURCE_CHANGE";entityType="ATTENDANCE_SESSION";entityId=old.session_id;baseVersion=old.version;
    canonicalPayload=input.action==="exit"?{mnv,pda_exit_status:text(payload.pda_exit_status,180),note:text(payload.note,500)}:{mnv,work_choice:text(payload.work_choice,40),pda_serial:text(payload.pda_serial||payload.pda,180),user_pick:text(payload.user_pick||payload.userPick,180),pack_table:text(payload.pack_table||payload.packTable,180),user_pack:text(payload.user_pack||payload.userPack,180),resource_note:text(payload.resource_note,500),duplicate_user:Boolean(payload.duplicate_user),note:text(payload.note,500)};
  }else if(input.action==="labor_start"){
    eventType="LABOR_START";entityType="LABOR_SESSION";entityId=text(payload.labor_id,180)||eventId;
    const existing=await db.prepare("SELECT version FROM labor_sessions WHERE labor_id=?1").bind(entityId).first<{version:number}>();baseVersion=existing?.version??0;
    canonicalPayload={mnv,session_id:text(payload.session_id,220),shift:text(payload.shift,80),labor_type:text(payload.labor_type,180),time_marker:text(payload.time_marker,120)||"-",start_at:text(payload.start_at,80),note:text(payload.note,500),deduct_staff:payload.deduct_staff??false};
  }else if(input.action==="meal_checkin"||input.action==="meal_status"){
    if(businessDate!==today)throw new CoreError("MEAL_WRITE_CURRENT_DAY_ONLY","PERMISSION",403);
    const existing=await db.prepare("SELECT status,actual_return_at,version FROM post_meal_attendance WHERE business_date=?1 AND mnv=?2").bind(businessDate,mnv).first<{status:string;actual_return_at:string|null;version:number}>();
    baseVersion=existing?.version??0;entityType="POST_MEAL_ATTENDANCE";entityId=`${businessDate}|${mnv}`;
    if(input.action==="meal_checkin"){
      eventType="MEAL_CHECKIN";canonicalPayload={mnv,status:"CHECKED_IN"};
    }else{
      const status=text(payload.status,40),reason=text(payload.reason_code,120),note=text(payload.reason_note,500),expected=text(payload.expected_return_at,80);
      if(!["NO_RETURN","LATE_EXPECTED"].includes(status))throw new CoreError("MEAL_STATUS_INVALID","VALIDATION",400);
      const allowed=new Set(["Xin về sớm","Đi hỗ trợ bộ phận/vị trí khác","Xin vào muộn","Nghỉ đột xuất","Có việc cá nhân","Được quản lý điều chuyển","Khác"]);
      if(!allowed.has(reason))throw new CoreError("MEAL_REASON_INVALID","VALIDATION",400);
      if(reason==="Khác"&&!note)throw new CoreError("MEAL_REASON_NOTE_REQUIRED","VALIDATION",400);
      if((status==="LATE_EXPECTED"||reason==="Xin vào muộn")&&(!expected||Number.isNaN(Date.parse(expected))))throw new CoreError("MEAL_EXPECTED_TIME_REQUIRED","VALIDATION",400);
      eventType="MEAL_STATUS_UPDATE";canonicalPayload={mnv,status,reason_code:reason,reason_note:note,expected_return_at:expected};
    }
  }else{
    const requestedLaborId=text(payload.labor_id,180);
    const open=requestedLaborId
      ?await db.prepare("SELECT labor_id,mnv,business_date,state,version FROM labor_sessions WHERE labor_id=?1").bind(requestedLaborId).first<LaborVersionRow&{mnv:string;business_date:string}>()
      :await activeLabor(db,mnv,businessDate);
    const correction=payload.correction===true;
    if(!open||(!correction&&open.state!=="OPEN")||(correction&&!["OPEN","COMPLETED"].includes(open.state))||("mnv" in open&&String(open.mnv)!==mnv)||("business_date" in open&&String(open.business_date)!==businessDate))throw new CoreError("LABOR_NOT_OPEN","CONFLICT",409);
    eventType="LABOR_FINISH";entityType="LABOR_SESSION";entityId=open.labor_id;baseVersion=open.version;
    canonicalPayload={mnv,session_id:text(payload.session_id,220),start_at:text(payload.start_at,80),end_at:text(payload.end_at,80),note:text(payload.note,500),correction};
  }

  return {event_id:eventId,event_type:eventType,entity_type:entityType,entity_id:entityId,business_date:businessDate,authority_epoch:a.authority_epoch,service_generation:a.service_generation,base_version:baseVersion,timestamp:text(payload.timestamp,80)||nowIso(),payload:canonicalPayload,idempotency_key:`legacy:${device}:${eventId}`,device_id:device,schema_version:1};
}

export async function commitLegacyMutation(db:D1Database,env:Env,auth:AuthContext,input:LegacyMutationInput):Promise<Record<string,unknown>>{
  const canonical=await legacyCanonical(db,input,auth),r=await commitMutation(db,env,auth,canonical),e=r.event;
  return {ok:true,idempotent:r.duplicate,duplicate:r.duplicate,result:{event_id:e.event_id,revision:e.authority_seq,authority_epoch:e.authority_epoch,new_version:e.new_version},event:e,projection:"SERVICE_D1"};
}

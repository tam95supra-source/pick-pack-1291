import { apiError, json, nowIso } from "./util";
import { bangkokToday } from "./business_date";

function retentionFloor():string{
  const d=new Date(`${bangkokToday()}T00:00:00+07:00`);
  d.setUTCDate(d.getUTCDate()-44);
  return d.toISOString().slice(0,10);
}

export async function historicalSessionDetail(env:Env,body:Record<string,unknown>):Promise<Response>{
  const sessionId=String(body.session_id||"").trim();
  const expectedDate=String(body.business_date||"").trim();
  const expectedMnv=String(body.mnv||"").trim();
  if(!sessionId)return apiError("SESSION_ID_REQUIRED","VALIDATION",400);

  const live=await env.DB.prepare(`SELECT session_id,mnv,business_date,shift,work_choice,state,pda_serial,user_pick,pack_table,user_pack,pda_enter_status,pda_exit_status,resource_note,enter_at,exit_at,entered_by,exited_by,version
    FROM attendance_sessions WHERE session_id=?1`).bind(sessionId).first<Record<string,unknown>>();
  const snap=live?null:await env.DB.prepare("SELECT session_id,mnv,business_date,snapshot_json,source_version FROM historical_session_snapshots WHERE session_id=?1").bind(sessionId).first<{session_id:string;mnv:string;business_date:string;snapshot_json:string;source_version:number}>();
  const session:Record<string,unknown>|null=live??(snap?JSON.parse(snap.snapshot_json) as Record<string,unknown>:null);
  const actualDate=String(session?.business_date||expectedDate||"");
  const floor=retentionFloor();
  if(actualDate&&actualDate<floor)return apiError("HISTORICAL_SESSION_OUTSIDE_RETENTION","VALIDATION",410,false,`Phiên ${actualDate} đã ngoài phạm vi lưu giữ 45 ngày.`);
  if(!session)return apiError("HISTORICAL_SESSION_NOT_FOUND","VALIDATION",404);
  const actualMnv=String(session.mnv||"");
  if(expectedDate&&actualDate!==expectedDate)return apiError("HISTORICAL_SESSION_DATE_MISMATCH","CONFLICT",409);
  if(expectedMnv&&actualMnv!==expectedMnv)return apiError("HISTORICAL_SESSION_MNV_MISMATCH","CONFLICT",409);

  if(live){
    const snapshot=JSON.stringify(live);
    await env.DB.prepare(`INSERT INTO historical_session_snapshots(session_id,mnv,business_date,snapshot_json,source_version,hydrated_at)
      VALUES(?1,?2,?3,?4,?5,?6)
      ON CONFLICT(session_id) DO UPDATE SET mnv=excluded.mnv,business_date=excluded.business_date,snapshot_json=excluded.snapshot_json,source_version=excluded.source_version,hydrated_at=excluded.hydrated_at
      WHERE historical_session_snapshots.source_version<=excluded.source_version`)
      .bind(sessionId,actualMnv,actualDate,snapshot,Number(live.version||0),nowIso()).run();
  }

  const employee=await env.DB.prepare("SELECT mnv,full_name,phone,main_position,supplier,department,site,warehouse,start_date,note FROM employees WHERE mnv=?1").bind(actualMnv).first<Record<string,unknown>>();
  const labor=(await env.DB.prepare("SELECT labor_id,shift,labor_type,time_marker,state,start_at,end_at,note,deduct_staff,version FROM labor_sessions WHERE mnv=?1 AND business_date=?2 ORDER BY start_at").bind(actualMnv,actualDate).all<Record<string,unknown>>()).results??[];
  const timeline=(await env.DB.prepare(`SELECT event_id,event_type,actor_id,occurred_at,committed_at,payload_json,authority_seq FROM events
    WHERE business_date=?1 AND json_extract(payload_json,'$.mnv')=?2 ORDER BY authority_epoch,authority_seq`).bind(actualDate,actualMnv).all<Record<string,unknown>>()).results??[];
  const resources=[
    {type:"PDA",value:String(session.pda_serial||"")},
    {type:"USER_PICK",value:String(session.user_pick||"")},
    {type:"PACK_TABLE",value:String(session.pack_table||"")},
    {type:"USER_PACK",value:String(session.user_pack||"")},
  ].filter(x=>x.value);
  return json({ok:true,source:"SERVICE_D1",retention_days:45,retention_floor:floor,identity:{session_id:sessionId,business_date:actualDate,mnv:actualMnv},employee,session,resources,labor,timeline,hydrated:true});
}

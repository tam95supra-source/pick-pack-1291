import { REPLICA_HEADERS, type EventRow } from "./domain";
import { nowIso } from "./util";
import { replicateMasterProjection } from "./master_replication";
import { isStableEnvironment, stableSheetBridge } from "./stable_sheet_bridge";

interface OutboxRow { outbox_id:number; event_id:string; attempt_count:number; }
interface GoogleToken { access_token?:string; expires_in?:number; error?:string; }
interface EmployeeRow { mnv:string;full_name:string;phone:string;main_position:string;supplier:string;department:string;site:string;warehouse:string; }
interface AttendanceReplicaRow { session_id:string;mnv:string;business_date:string;shift:string;work_choice:string;pda_serial:string|null;user_pick:string|null;pack_table:string|null;user_pack:string|null; }
interface LaborReplicaRow { labor_id:string;mnv:string;business_date:string;shift:string;labor_type:string;time_marker:string;start_at:string;end_at:string|null;note:string;deduct_staff:number;start_event_id:string;finish_event_id:string|null; }
interface AttendanceOperationalRow extends AttendanceReplicaRow,EmployeeRow {}
interface LaborOperationalRow extends LaborReplicaRow,EmployeeRow { attendance_session_id:string|null;attendance_work_choice:string|null; }
interface OperationalIndex { raEvents:Set<string>;userEvents:Set<string>;laborStartRows:Map<string,number>;laborFinishEvents:Set<string>;historyEvents:Set<string>; }

const RA_HEADERS=["Ngày","Ca","Mã nhân viên","Họ và tên","Số điện thoại","Nhà cung cấp","Bộ phận","Site","Kho","Vị trí chính","Vị trí trong ca","Seri PDA","User Pick","Bàn Pack","User Pack","Loại thao tác","Ghi chú","Người cập nhật","Thời gian cập nhật","Event ID","App action","App revision"] as const;
const USER_HEADERS=["Ngày","Ca","Mã nhân viên","Họ và tên","Nhà cung cấp","Bộ phận","Site","Vị trí trong ca","User","Người cập nhật","Event ID"] as const;
const LABOR_HEADERS=["Ngày","Ca","Mã nhân viên","Họ và tên","Số điện thoại","Nhà cung cấp","Bộ phận","Site","Kho","Vị trí chính","Vị trí trong ca","Thông tin công nhật","Thời gian bắt đầu","Thời gian kết thúc","Mốc thời gian","Trạng thái","Ghi chú","Người cập nhật","Thời gian cập nhật","Event ID","Finish Event ID","App revision","Khấu trừ nhân sự"] as const;
const HISTORY_HEADERS=["Ngày","Session ID","Mã nhân viên","Họ tên","Ca","Loại sự kiện","Nhãn sự kiện","Thời gian","Người xử lý","Chi tiết","Event ID","Phạm vi","App Revision"] as const;

async function googleAccessToken(env:Env):Promise<string>{
  if(isStableEnvironment(env))return "__STABLE_BOUND_GAS__";
  const body=new URLSearchParams({client_id:env.GOOGLE_OAUTH_CLIENT_ID,client_secret:env.GOOGLE_OAUTH_CLIENT_SECRET,refresh_token:env.GOOGLE_OAUTH_REFRESH_TOKEN,grant_type:"refresh_token"});
  const r=await fetch("https://oauth2.googleapis.com/token",{method:"POST",headers:{"content-type":"application/x-www-form-urlencoded"},body});
  const j=await r.json<GoogleToken>();if(!r.ok||!j.access_token)throw new Error(`GOOGLE_OAUTH:${j.error??r.status}`);return j.access_token;
}

function authHeaders(token:string,extra:HeadersInit={}):HeadersInit{return{authorization:`Bearer ${token}`,...extra};}
function a1(name:string,range:string):string{return `'${name.replace(/'/g,"''")}'!${range}`;}
function visibleDate(iso:string):string{const m=/^(\d{4})-(\d{2})-(\d{2})$/.exec(iso);return m?`${m[3]}/${m[2]}/${m[1]}`:iso;}
function visibleDateTime(iso:string):string{
  const d=new Date(iso);if(Number.isNaN(d.getTime()))return iso;
  return new Intl.DateTimeFormat("en-GB",{timeZone:"Asia/Ho_Chi_Minh",year:"numeric",month:"2-digit",day:"2-digit",hour:"2-digit",minute:"2-digit",second:"2-digit",hourCycle:"h23"}).format(d).replace(",","");
}
function workLabel(v:string):string{return v==="PICK"?"Pick":v==="PACK"?"Pack":"Không";}
function payload(e:EventRow):Record<string,unknown>{try{return JSON.parse(e.payload_json) as Record<string,unknown>;}catch{return{};}}
function ptext(p:Record<string,unknown>,key:string):string{return String(p[key]??"").trim();}
function pobj(p:Record<string,unknown>,key:string):Record<string,unknown>{const v=p[key];return v&&typeof v==="object"&&!Array.isArray(v)?v as Record<string,unknown>:{};}
function appendRowNumber(updatedRange:string):number|null{const m=/!A(\d+):/i.exec(updatedRange);return m?.[1]?Number(m[1]):null;}

async function getValues(env:Env,sheetId:string,token:string,sheet:string,range:string):Promise<unknown[][]>{
  if(isStableEnvironment(env)){const j=await stableSheetBridge<{ok:true;values?:unknown[][]}>(env,"primary","get_values",{sheet,range});return j.values??[];}
  const url=`https://sheets.googleapis.com/v4/spreadsheets/${encodeURIComponent(sheetId)}/values/${encodeURIComponent(a1(sheet,range))}?valueRenderOption=FORMATTED_VALUE`;
  const r=await fetch(url,{headers:authHeaders(token)});if(!r.ok)throw new Error(`GOOGLE_READ:${sheet}:${r.status}`);const j=await r.json<{values?:unknown[][]}>();return j.values??[];
}
async function batchGetValues(env:Env,sheetId:string,token:string,ranges:Array<[string,string]>):Promise<unknown[][][]>{
  if(isStableEnvironment(env)){const j=await stableSheetBridge<{ok:true;values?:unknown[][][]}>(env,"primary","batch_get",{ranges:ranges.map(([sheet,range])=>({sheet,range}))});return j.values??ranges.map(()=>[]);}
  const qs=ranges.map(([sheet,range])=>`ranges=${encodeURIComponent(a1(sheet,range))}`).join("&"),url=`https://sheets.googleapis.com/v4/spreadsheets/${encodeURIComponent(sheetId)}/values:batchGet?valueRenderOption=FORMATTED_VALUE&${qs}`;
  const r=await fetch(url,{headers:authHeaders(token)});if(!r.ok)throw new Error(`GOOGLE_BATCH_READ:${r.status}`);const j=await r.json<{valueRanges?:Array<{values?:unknown[][]}>}>();return ranges.map((_,i)=>j.valueRanges?.[i]?.values??[]);
}
async function putValues(env:Env,sheetId:string,token:string,sheet:string,range:string,values:unknown[][]):Promise<void>{
  if(isStableEnvironment(env)){await stableSheetBridge(env,"primary","put_values",{sheet,range,values});return;}
  const full=a1(sheet,range),url=`https://sheets.googleapis.com/v4/spreadsheets/${encodeURIComponent(sheetId)}/values/${encodeURIComponent(full)}?valueInputOption=RAW`;
  const r=await fetch(url,{method:"PUT",headers:authHeaders(token,{"content-type":"application/json"}),body:JSON.stringify({range:full,majorDimension:"ROWS",values})});
  if(!r.ok){const t=await r.text();throw new Error(`GOOGLE_PUT:${sheet}:${r.status}:${t.slice(0,200)}`);}
}
async function appendValues(env:Env,sheetId:string,token:string,sheet:string,range:string,values:unknown[][]):Promise<string>{
  if(!values.length)return"NOOP";
  if(isStableEnvironment(env)){const j=await stableSheetBridge<{ok:true;updated_range?:string}>(env,"primary","append_values",{sheet,range,values});return String(j.updated_range||"APPENDED");}
  const full=a1(sheet,range),url=`https://sheets.googleapis.com/v4/spreadsheets/${encodeURIComponent(sheetId)}/values/${encodeURIComponent(full)}:append?valueInputOption=RAW&insertDataOption=INSERT_ROWS`;
  const r=await fetch(url,{method:"POST",headers:authHeaders(token,{"content-type":"application/json"}),body:JSON.stringify({range:full,majorDimension:"ROWS",values})});
  if(!r.ok){const t=await r.text();throw new Error(`GOOGLE_APPEND:${sheet}:${r.status}:${t.slice(0,240)}`);}const j=await r.json<{updates?:{updatedRange?:string}}>();return j.updates?.updatedRange??"APPENDED";
}
async function batchPutValues(env:Env,sheetId:string,token:string,data:Array<{sheet:string;range:string;values:unknown[][]}>):Promise<void>{
  if(!data.length)return;
  if(isStableEnvironment(env)){for(const d of data)await stableSheetBridge(env,"primary","put_values",{sheet:d.sheet,range:d.range,values:d.values});return;}
  const url=`https://sheets.googleapis.com/v4/spreadsheets/${encodeURIComponent(sheetId)}/values:batchUpdate`,body={valueInputOption:"RAW",data:data.map(d=>({range:a1(d.sheet,d.range),majorDimension:"ROWS",values:d.values}))};
  const r=await fetch(url,{method:"POST",headers:authHeaders(token,{"content-type":"application/json"}),body:JSON.stringify(body)});if(!r.ok){const x=await r.text();throw new Error(`GOOGLE_BATCH_PUT:${r.status}:${x.slice(0,240)}`);}
}
function assertHeaderValues(sheet:string,values:unknown[][],headers:readonly string[]):void{const got=(values[0]??[]).map(String);if(JSON.stringify(got)!==JSON.stringify([...headers]))throw new Error(`GOOGLE_OPERATIONAL_SCHEMA_DRIFT:${sheet}`);}

async function ensureReplicaSheet(env:Env,token:string):Promise<Set<string>>{
  if(isStableEnvironment(env)){const j=await stableSheetBridge<{ok:true;ids?:string[]}>(env,"primary","ensure_replica",{});return new Set(j.ids??[]);}
  const id=env.GOOGLE_STAGING_SHEET_ID;
  const meta=await fetch(`https://sheets.googleapis.com/v4/spreadsheets/${encodeURIComponent(id)}?fields=sheets.properties(sheetId,title,hidden)`,{headers:authHeaders(token)});
  if(!meta.ok)throw new Error(`GOOGLE_META:${meta.status}`);
  const m=await meta.json<{sheets?:Array<{properties?:{sheetId?:number;title?:string;hidden?:boolean}}>}>();
  const p=m.sheets?.map(x=>x.properties).find(x=>x?.title==="__M1_SERVICE_REPLICA");
  if(!p){
    const create=await fetch(`https://sheets.googleapis.com/v4/spreadsheets/${encodeURIComponent(id)}:batchUpdate`,{method:"POST",headers:authHeaders(token,{"content-type":"application/json"}),body:JSON.stringify({requests:[{addSheet:{properties:{title:"__M1_SERVICE_REPLICA",hidden:true}}}]})});
    if(!create.ok)throw new Error(`GOOGLE_CREATE_REPLICA:${create.status}`);
  }else if(!p.hidden&&p.sheetId!==undefined){
    const hide=await fetch(`https://sheets.googleapis.com/v4/spreadsheets/${encodeURIComponent(id)}:batchUpdate`,{method:"POST",headers:authHeaders(token,{"content-type":"application/json"}),body:JSON.stringify({requests:[{updateSheetProperties:{properties:{sheetId:p.sheetId,hidden:true},fields:"hidden"}}]})});
    if(!hide.ok)throw new Error(`GOOGLE_HIDE_REPLICA:${hide.status}`);
  }
  const [header=[],ids=[]]=await batchGetValues(env,id,token,[["__M1_SERVICE_REPLICA","A1:T1"],["__M1_SERVICE_REPLICA","A2:A"]]);
  if(JSON.stringify((header[0]??[]).map(String))!==JSON.stringify([...REPLICA_HEADERS]))await putValues(env,id,token,"__M1_SERVICE_REPLICA","A1:T1",[[...REPLICA_HEADERS]]);
  return new Set(ids.map(r=>String(r[0]??"")).filter(Boolean));
}

function eventValues(e:EventRow):unknown[]{return[e.event_id,e.event_type,e.entity_type,e.entity_id,e.business_date,e.authority_epoch,e.authority_seq,e.service_generation,e.base_version,e.new_version,e.actor_id,e.actor_role,e.device_id,e.occurred_at,e.committed_at,e.idempotency_key,e.origin,e.schema_version,e.checksum,e.payload_json];}
async function appendTechnicalRows(env:Env,token:string,events:EventRow[]):Promise<string>{return appendValues(env,env.GOOGLE_STAGING_SHEET_ID,token,"__M1_SERVICE_REPLICA","A:T",events.map(eventValues));}

async function loadOperationalIndex(env:Env,token:string):Promise<OperationalIndex>{
  const id=env.GOOGLE_SOURCE_SHEET_ID,ranges:Array<[string,string]>=[
    ["RA - VÀO TRONG CA","A1:V1"],["CÔNG NHẬT","A1:W1"],["LỊCH SỬ NGHIỆP VỤ","A1:M1"],["THÔNG TIN USER CỦA NLĐ","A1:K1"],
    ["RA - VÀO TRONG CA","T2:T"],["CÔNG NHẬT","T2:U"],["LỊCH SỬ NGHIỆP VỤ","K2:K"],["THÔNG TIN USER CỦA NLĐ","K2:K"],
  ],v=await batchGetValues(env,id,token,ranges);
  assertHeaderValues("RA - VÀO TRONG CA",v[0]??[],RA_HEADERS);assertHeaderValues("CÔNG NHẬT",v[1]??[],LABOR_HEADERS);assertHeaderValues("LỊCH SỬ NGHIỆP VỤ",v[2]??[],HISTORY_HEADERS);assertHeaderValues("THÔNG TIN USER CỦA NLĐ",v[3]??[],USER_HEADERS);
  const raEvents=new Set((v[4]??[]).map(r=>String(r[0]??"")).filter(Boolean)),laborStartRows=new Map<string,number>(),laborFinishEvents=new Set<string>();
  for(let i=0;i<(v[5]??[]).length;i++){const r=(v[5]??[])[i]??[],start=String(r[0]??""),finish=String(r[1]??"");if(start)laborStartRows.set(start,i+2);if(finish)laborFinishEvents.add(finish);}
  const historyEvents=new Set((v[6]??[]).map(r=>String(r[0]??"")).filter(Boolean)),userEvents=new Set((v[7]??[]).map(r=>String(r[0]??"")).filter(Boolean));return{raEvents,userEvents,laborStartRows,laborFinishEvents,historyEvents};
}

async function appendHistory(env:Env,sheetId:string,token:string,index:OperationalIndex,e:EventRow,sessionId:string,mnv:string,name:string,shift:string,label:string,detail:string):Promise<void>{
  if(index.historyEvents.has(e.event_id))return;
  await appendValues(env,sheetId,token,"LỊCH SỬ NGHIỆP VỤ","A:M",[[visibleDate(e.business_date),sessionId,mnv,name,shift,e.event_type,label,visibleDateTime(e.occurred_at),e.actor_id,detail,e.event_id,"SERVICE_M2",e.authority_seq]]);index.historyEvents.add(e.event_id);
}

async function attendanceOperational(db:D1Database,entityId:string):Promise<AttendanceOperationalRow>{
  const r=await db.prepare(`SELECT s.session_id,s.mnv,s.business_date,s.shift,s.work_choice,s.pda_serial,s.user_pick,s.pack_table,s.user_pack,e.full_name,e.phone,e.main_position,e.supplier,e.department,e.site,e.warehouse
    FROM attendance_sessions s JOIN employees e ON e.mnv=s.mnv WHERE s.session_id=?1`).bind(entityId).first<AttendanceOperationalRow>();if(!r)throw new Error(`REPLICA_ATTENDANCE_MISSING:${entityId}`);return r;
}
async function laborOperational(db:D1Database,entityId:string):Promise<LaborOperationalRow>{
  const r=await db.prepare(`SELECT l.labor_id,l.mnv,l.business_date,l.shift,l.labor_type,l.time_marker,l.start_at,l.end_at,l.note,l.deduct_staff,l.start_event_id,l.finish_event_id,e.full_name,e.phone,e.main_position,e.supplier,e.department,e.site,e.warehouse,a.session_id AS attendance_session_id,a.work_choice AS attendance_work_choice
    FROM labor_sessions l JOIN employees e ON e.mnv=l.mnv LEFT JOIN attendance_sessions a ON a.mnv=l.mnv AND a.business_date=l.business_date WHERE l.labor_id=?1`).bind(entityId).first<LaborOperationalRow>();if(!r)throw new Error(`REPLICA_LABOR_MISSING:${entityId}`);return r;
}

async function replicateUserAssignments(db:D1Database,env:Env,sheetId:string,token:string,index:OperationalIndex,e:EventRow,s:AttendanceOperationalRow):Promise<number>{
  const r=await db.prepare("SELECT resource_type,resource_id FROM resource_daily_consumption WHERE first_event_id=?1 AND resource_type IN ('USER_PICK','USER_PACK') ORDER BY resource_type,resource_id").bind(e.event_id).all<{resource_type:string;resource_id:string}>();let n=0;
  for(const x of r.results??[]){const pos=x.resource_type==="USER_PICK"?"PICK":"PACK",key=`${e.event_id}:${pos}`;if(index.userEvents.has(key))continue;await appendValues(env,sheetId,token,"THÔNG TIN USER CỦA NLĐ","A:K",[[visibleDate(e.business_date),s.shift,s.mnv,s.full_name,s.supplier,s.department,s.site,pos,x.resource_id,e.actor_id,key]]);index.userEvents.add(key);n++;}
  return n;
}

function resourceChangeDetail(e:EventRow):string{
  const p=payload(e),before=pobj(p,"before"),after=pobj(p,"after"),labels:Record<string,string>={work_choice:"Vị trí",pda_serial:"PDA",user_pick:"User Pick",pack_table:"Bàn Pack",user_pack:"User Pack"},parts:string[]=[];
  if(Object.keys(after).length){for(const k of Object.keys(labels)){const a=ptext(before,k)||"—",b=ptext(after,k)||"—";if(a!==b)parts.push(`${labels[k]}: ${a} → ${b}`);}}
  if(!parts.length){for(const k of Object.keys(labels)){const v=ptext(p,k);if(v)parts.push(`${labels[k]}: ${v}`);}}
  return parts.join(" • ")||"Cập nhật công việc / tài nguyên trong ca";
}

async function replicateAttendanceEvent(db:D1Database,env:Env,sheetId:string,token:string,index:OperationalIndex,e:EventRow):Promise<void>{
  const s=await attendanceOperational(db,e.entity_id);await replicateUserAssignments(db,env,sheetId,token,index,e,s);
  if(e.event_type==="RESOURCE_CHANGE"){await appendHistory(env,sheetId,token,index,e,s.session_id,s.mnv,s.full_name,s.shift,"Cập nhật công việc / tài nguyên",resourceChangeDetail(e));return;}
  if(index.raEvents.has(e.event_id))return;
  const enter=e.event_type==="ATTENDANCE_ENTER",action=enter?"VÀO":"RA",appAction=enter?"ENTER":"EXIT";
  await appendValues(env,sheetId,token,"RA - VÀO TRONG CA","A:V",[[visibleDate(e.business_date),s.shift,s.mnv,s.full_name,s.phone,s.supplier,s.department,s.site,s.warehouse,s.main_position,"","","","","",action,"",e.actor_id,visibleDateTime(e.occurred_at),e.event_id,appAction,e.authority_seq]]);index.raEvents.add(e.event_id);
  await appendHistory(env,sheetId,token,index,e,s.session_id,s.mnv,s.full_name,s.shift,enter?"Vào ca":"Ra ca",`${enter?"Bắt đầu":"Kết thúc"} phiên • Vị trí chính: ${s.main_position||"—"}`);
}

async function replicateLaborStartOperational(db:D1Database,env:Env,sheetId:string,token:string,index:OperationalIndex,e:EventRow):Promise<void>{
  if(index.laborStartRows.has(e.event_id))return;
  const l=await laborOperational(db,e.entity_id);if(!l.attendance_session_id)throw new Error(`REPLICA_ATTENDANCE_FOR_LABOR_MISSING:${l.mnv}`);
  const updated=await appendValues(env,sheetId,token,"CÔNG NHẬT","A:W",[[visibleDate(e.business_date),l.shift,l.mnv,l.full_name,l.phone,l.supplier,l.department,l.site,l.warehouse,l.main_position,workLabel(l.attendance_work_choice??""),l.labor_type,visibleDateTime(l.start_at),"",l.time_marker,"Đang làm",l.note||"",e.actor_id,visibleDateTime(e.occurred_at),e.event_id,"",e.authority_seq,l.deduct_staff?"Có":"Không"]]);
  const row=appendRowNumber(updated);if(row!==null)index.laborStartRows.set(e.event_id,row);
  await appendHistory(env,sheetId,token,index,e,l.attendance_session_id,l.mnv,l.full_name,l.shift,"Bắt đầu công nhật",`${l.labor_type} • Bắt đầu ${visibleDateTime(l.start_at)} • Khấu trừ ${l.deduct_staff?"Có":"Không"}`);
}

async function replicateLaborFinishOperational(db:D1Database,env:Env,sheetId:string,token:string,index:OperationalIndex,e:EventRow):Promise<void>{
  if(index.laborFinishEvents.has(e.event_id))return;
  const l=await laborOperational(db,e.entity_id),row=index.laborStartRows.get(l.start_event_id);if(!row)throw new Error(`REPLICA_LABOR_START_ROW_MISSING:${l.start_event_id}`);
  const oldNote=l.note||String((await getValues(env,sheetId,token,"CÔNG NHẬT",`Q${row}:Q${row}`))[0]?.[0]??"");
  await putValues(env,sheetId,token,"CÔNG NHẬT",`M${row}:V${row}`,[[visibleDateTime(l.start_at),visibleDateTime(l.end_at||e.occurred_at),l.time_marker,"Hoàn thành",oldNote,e.actor_id,visibleDateTime(e.occurred_at),l.start_event_id,e.event_id,e.authority_seq]]);index.laborFinishEvents.add(e.event_id);
  const corrected=payload(e).correction===true;
  await appendHistory(env,sheetId,token,index,e,l.attendance_session_id||`${visibleDate(e.business_date)}|${l.mnv}`,l.mnv,l.full_name,l.shift,corrected?"Sửa công nhật":"Hoàn thành công nhật",`${l.labor_type} • ${visibleDateTime(l.start_at)} → ${visibleDateTime(l.end_at||e.occurred_at)} • Khấu trừ ${l.deduct_staff?"Có":"Không"}`);
}

function adminAuditLabel(type:string):string{const m:Record<string,string>={MASTER_STAFF_UPSERT:"Cập nhật nhân sự",MASTER_STAFF_DELETE:"Xóa nhân sự",ACCOUNT_UPSERT:"Tạo / sửa tài khoản",ACCOUNT_STATUS:"Đổi trạng thái tài khoản",ACCOUNT_EMAIL:"Đổi email tài khoản",ACCOUNT_PASSWORD:"Đổi mật khẩu",MASTER_STAFF_IMPORT:"Import nhân sự",ACCOUNT_LOGIN:"Đăng nhập",ACCOUNT_LOGOUT:"Đăng xuất",SETTINGS_CHANGE:"Đổi cài đặt",DOCUMENT_UPLOAD:"Tải biên bản",DOCUMENT_DELETE:"Xóa biên bản",DOCUMENT_CATEGORY_CREATE:"Thêm loại biên bản",DOCUMENT_CATEGORY_UPDATE:"Sửa loại biên bản",DOCUMENT_CATEGORY_DELETE:"Xóa loại biên bản"};return m[type]||type;}
async function replicateAdminAudit(env:Env,sheetId:string,token:string,index:OperationalIndex,e:EventRow):Promise<void>{
  const p=payload(e),targetType=ptext(p,"target_type")||e.entity_type,targetId=ptext(p,"target_id")||e.entity_id,targetLabel=ptext(p,"target_label"),detail=ptext(p,"detail");
  const mnv=targetType==="STAFF"?targetId:"";await appendHistory(env,sheetId,token,index,e,`ADMIN|${targetType}|${targetId}`,mnv,targetLabel,"",adminAuditLabel(e.event_type),detail);
}

function historyRow(e:EventRow,sessionId:string,mnv:string,name:string,shift:string,label:string,detail:string):unknown[]{return[visibleDate(e.business_date),sessionId,mnv,name,shift,e.event_type,label,visibleDateTime(e.occurred_at),e.actor_id,detail,e.event_id,"SERVICE_M2",e.authority_seq];}
type AssignmentRow={first_event_id:string;resource_type:string;resource_id:string};
async function replicateOperational(db:D1Database,env:Env,token:string,events:EventRow[]):Promise<{count:number;index:OperationalIndex|null}>{
  const a=await db.prepare("SELECT scope FROM authority_state WHERE singleton_id=1").first<{scope:string}>();if(a?.scope!=="PRODUCTION")return{count:0,index:null};
  const master=await replicateMasterProjection(db,env,token,events),index=await loadOperationalIndex(env,token),sheetId=env.GOOGLE_SOURCE_SHEET_ID;
  const attendanceEvents=events.filter(e=>["ATTENDANCE_ENTER","RESOURCE_CHANGE","ATTENDANCE_EXIT"].includes(e.event_type)),attendanceIds=[...new Set(attendanceEvents.map(e=>e.entity_id))],laborEvents=events.filter(e=>e.event_type==="LABOR_START"||e.event_type==="LABOR_FINISH"),laborIds=[...new Set(laborEvents.map(e=>e.entity_id))];
  const attendanceRows:AttendanceOperationalRow[]=attendanceIds.length?((await db.prepare(`SELECT s.session_id,s.mnv,s.business_date,s.shift,s.work_choice,s.pda_serial,s.user_pick,s.pack_table,s.user_pack,e.full_name,e.phone,e.main_position,e.supplier,e.department,e.site,e.warehouse FROM attendance_sessions s JOIN employees e ON e.mnv=s.mnv WHERE s.session_id IN (${attendanceIds.map(()=>"?").join(",")})`).bind(...attendanceIds).all<AttendanceOperationalRow>()).results??[]):[];
  const laborRows:LaborOperationalRow[]=laborIds.length?((await db.prepare(`SELECT l.labor_id,l.mnv,l.business_date,l.shift,l.labor_type,l.time_marker,l.start_at,l.end_at,l.note,l.deduct_staff,l.start_event_id,l.finish_event_id,e.full_name,e.phone,e.main_position,e.supplier,e.department,e.site,e.warehouse,a.session_id AS attendance_session_id,a.work_choice AS attendance_work_choice FROM labor_sessions l JOIN employees e ON e.mnv=l.mnv LEFT JOIN attendance_sessions a ON a.mnv=l.mnv AND a.business_date=l.business_date WHERE l.labor_id IN (${laborIds.map(()=>"?").join(",")})`).bind(...laborIds).all<LaborOperationalRow>()).results??[]):[];
  const eventIds=events.map(e=>e.event_id),assignments:AssignmentRow[]=eventIds.length?((await db.prepare(`SELECT first_event_id,resource_type,resource_id FROM resource_daily_consumption WHERE first_event_id IN (${eventIds.map(()=>"?").join(",")}) AND resource_type IN ('USER_PICK','USER_PACK') ORDER BY first_event_id,resource_type,resource_id`).bind(...eventIds).all<AssignmentRow>()).results??[]):[];
  const attMap=new Map(attendanceRows.map(x=>[x.session_id,x])),laborMap=new Map(laborRows.map(x=>[x.labor_id,x])),assignmentMap=new Map<string,AssignmentRow[]>();for(const x of assignments){const q=assignmentMap.get(x.first_event_id)??[];q.push(x);assignmentMap.set(x.first_event_id,q);}
  const ra:Array<{eventId:string;row:unknown[]}>=[],users:Array<{key:string;row:unknown[]}>=[],starts:Array<{eventId:string;row:unknown[]}>=[],finishes:Array<{event:EventRow;labor:LaborOperationalRow}>=[],hist:Array<{eventId:string;row:unknown[]}>=[];let n=0;
  const addHistory=(e:EventRow,sessionId:string,mnv:string,name:string,shift:string,label:string,detail:string)=>{if(!index.historyEvents.has(e.event_id)&&!hist.some(x=>x.eventId===e.event_id))hist.push({eventId:e.event_id,row:historyRow(e,sessionId,mnv,name,shift,label,detail)});};
  for(const e of events){
    if(["ATTENDANCE_ENTER","RESOURCE_CHANGE","ATTENDANCE_EXIT"].includes(e.event_type)){
      const s=attMap.get(e.entity_id);if(!s)throw new Error(`REPLICA_ATTENDANCE_MISSING:${e.entity_id}`);
      for(const x of assignmentMap.get(e.event_id)??[]){const pos=x.resource_type==="USER_PICK"?"PICK":"PACK",key=`${e.event_id}:${pos}`;if(!index.userEvents.has(key)&&!users.some(y=>y.key===key))users.push({key,row:[visibleDate(e.business_date),s.shift,s.mnv,s.full_name,s.supplier,s.department,s.site,pos,x.resource_id,e.actor_id,key]});}
      if(e.event_type==="RESOURCE_CHANGE")addHistory(e,s.session_id,s.mnv,s.full_name,s.shift,"Cập nhật công việc / tài nguyên",resourceChangeDetail(e));
      else{const enter=e.event_type==="ATTENDANCE_ENTER";if(!index.raEvents.has(e.event_id))ra.push({eventId:e.event_id,row:[visibleDate(e.business_date),s.shift,s.mnv,s.full_name,s.phone,s.supplier,s.department,s.site,s.warehouse,s.main_position,"","","","","",enter?"VÀO":"RA","",e.actor_id,visibleDateTime(e.occurred_at),e.event_id,enter?"ENTER":"EXIT",e.authority_seq]});addHistory(e,s.session_id,s.mnv,s.full_name,s.shift,enter?"Vào ca":"Ra ca",`${enter?"Bắt đầu":"Kết thúc"} phiên • Vị trí chính: ${s.main_position||"—"}`);}n++;continue;
    }
    if(e.event_type==="LABOR_START"){
      const l=laborMap.get(e.entity_id);if(!l)throw new Error(`REPLICA_LABOR_MISSING:${e.entity_id}`);if(!l.attendance_session_id)throw new Error(`REPLICA_ATTENDANCE_FOR_LABOR_MISSING:${l.mnv}`);if(!index.laborStartRows.has(e.event_id))starts.push({eventId:e.event_id,row:[visibleDate(e.business_date),l.shift,l.mnv,l.full_name,l.phone,l.supplier,l.department,l.site,l.warehouse,l.main_position,workLabel(l.attendance_work_choice??""),l.labor_type,visibleDateTime(l.start_at),"",l.time_marker,"Đang làm",l.note||"",e.actor_id,visibleDateTime(e.occurred_at),e.event_id,"",e.authority_seq,l.deduct_staff?"Có":"Không"]});addHistory(e,l.attendance_session_id,l.mnv,l.full_name,l.shift,"Bắt đầu công nhật",`${l.labor_type} • Bắt đầu ${visibleDateTime(l.start_at)} • Khấu trừ ${l.deduct_staff?"Có":"Không"}`);n++;continue;
    }
    if(e.event_type==="LABOR_FINISH"){
      const l=laborMap.get(e.entity_id);if(!l)throw new Error(`REPLICA_LABOR_MISSING:${e.entity_id}`);if(!index.laborFinishEvents.has(e.event_id))finishes.push({event:e,labor:l});const corrected=payload(e).correction===true;addHistory(e,l.attendance_session_id||`${visibleDate(e.business_date)}|${l.mnv}`,l.mnv,l.full_name,l.shift,corrected?"Sửa công nhật":"Hoàn thành công nhật",`${l.labor_type} • ${visibleDateTime(l.start_at)} → ${visibleDateTime(l.end_at||e.occurred_at)} • Khấu trừ ${l.deduct_staff?"Có":"Không"}`);n++;continue;
    }
    if(e.origin==="ADMIN_AUDIT"){
      const p=payload(e),targetType=ptext(p,"target_type")||e.entity_type,targetId=ptext(p,"target_id")||e.entity_id,targetLabel=ptext(p,"target_label"),detail=ptext(p,"detail"),mnv=targetType==="STAFF"?targetId:"";addHistory(e,`ADMIN|${targetType}|${targetId}`,mnv,targetLabel,"",adminAuditLabel(e.event_type),detail);n++;
    }
  }
  if(ra.length){await appendValues(env,sheetId,token,"RA - VÀO TRONG CA","A:V",ra.map(x=>x.row));for(const x of ra)index.raEvents.add(x.eventId);}
  if(users.length){await appendValues(env,sheetId,token,"THÔNG TIN USER CỦA NLĐ","A:K",users.map(x=>x.row));for(const x of users)index.userEvents.add(x.key);}
  if(starts.length){const updated=await appendValues(env,sheetId,token,"CÔNG NHẬT","A:W",starts.map(x=>x.row)),first=appendRowNumber(updated);if(first===null)throw new Error("REPLICA_LABOR_BATCH_ROW_UNKNOWN");starts.forEach((x,i)=>index.laborStartRows.set(x.eventId,first+i));}
  if(finishes.length){const plans=finishes.map(x=>{const row=index.laborStartRows.get(x.labor.start_event_id);if(!row)throw new Error(`REPLICA_LABOR_START_ROW_MISSING:${x.labor.start_event_id}`);return{...x,row};}),needNotes=plans.filter(x=>!x.labor.note),noteValues=needNotes.length?await batchGetValues(env,sheetId,token,needNotes.map(x=>["CÔNG NHẬT",`Q${x.row}:Q${x.row}`] as [string,string])):[],noteByEvent=new Map(needNotes.map((x,i)=>[x.event.event_id,String(noteValues[i]?.[0]?.[0]??"")]));await batchPutValues(env,sheetId,token,plans.map(x=>({sheet:"CÔNG NHẬT",range:`M${x.row}:V${x.row}`,values:[[visibleDateTime(x.labor.start_at),visibleDateTime(x.labor.end_at||x.event.occurred_at),x.labor.time_marker,"Hoàn thành",x.labor.note||noteByEvent.get(x.event.event_id)||"",x.event.actor_id,visibleDateTime(x.event.occurred_at),x.labor.start_event_id,x.event.event_id,x.event.authority_seq]]})));for(const x of plans)index.laborFinishEvents.add(x.event.event_id);}
  if(hist.length){await appendValues(env,sheetId,token,"LỊCH SỬ NGHIỆP VỤ","A:M",hist.map(x=>x.row));for(const x of hist)index.historyEvents.add(x.eventId);}
  return{count:n+master,index};
}

function retryDelaySeconds(attempt:number):number{return Math.min(900,Math.max(5,Math.pow(2,Math.min(8,attempt))*5));}

export async function replicatePending(db:D1Database,env:Env,limit=100):Promise<{ok:boolean;processed:number;appended:number;operational:number;pending:number;checkpoint?:string;error?:string}>{
  const staleClaimCutoff=new Date(Date.now()-15*60*1000).toISOString(),requeueAt=nowIso();
  await db.prepare("UPDATE sheet_replication_outbox SET status='RETRY',claim_token=NULL,claimed_at=NULL,next_attempt_at=?1,last_error_class=COALESCE(last_error_class,'STALE_INFLIGHT_RECOVERED'),last_error=COALESCE(last_error,'Recovered stale INFLIGHT claim for canonical retry') WHERE status='INFLIGHT' AND (claimed_at IS NULL OR claimed_at<=?2)").bind(requeueAt,staleClaimCutoff).run();
  const rows=await db.prepare("SELECT outbox_id,event_id,attempt_count FROM sheet_replication_outbox WHERE status IN ('PENDING','RETRY') AND next_attempt_at<=?1 ORDER BY outbox_id LIMIT ?2").bind(nowIso(),Math.max(1,Math.min(limit,100))).all<OutboxRow>(),due=rows.results??[];
  if(!due.length){const p=await db.prepare("SELECT COUNT(*) n FROM sheet_replication_outbox WHERE status IN ('PENDING','RETRY','INFLIGHT')").first<{n:number}>();return{ok:true,processed:0,appended:0,operational:0,pending:p?.n??0};}
  const claim=crypto.randomUUID(),claimAt=nowIso(),dueIds=due.map(x=>x.outbox_id),dueMarks=dueIds.map(()=>"?").join(",");let claimed:OutboxRow[]=[];
  try{
    await db.prepare(`UPDATE sheet_replication_outbox SET status='INFLIGHT',claim_token=?,claimed_at=?,attempt_count=attempt_count+1,last_error_class=NULL,last_error=NULL WHERE outbox_id IN (${dueMarks}) AND status IN ('PENDING','RETRY')`).bind(claim,claimAt,...dueIds).run();
    claimed=(await db.prepare("SELECT outbox_id,event_id,attempt_count FROM sheet_replication_outbox WHERE status='INFLIGHT' AND claim_token=?1 ORDER BY outbox_id").bind(claim).all<OutboxRow>()).results??[];
    if(!claimed.length){const pending=await db.prepare("SELECT COUNT(*) n FROM sheet_replication_outbox WHERE status IN ('PENDING','RETRY','INFLIGHT')").first<{n:number}>();return{ok:true,processed:0,appended:0,operational:0,pending:pending?.n??0};}
    const assertOwnership=async()=>{const ownership=await db.prepare("SELECT COUNT(*) n FROM sheet_replication_outbox WHERE status='INFLIGHT' AND claim_token=?1").bind(claim).first<{n:number}>();if((ownership?.n??0)!==claimed.length)throw new Error(`REPLICATION_CLAIM_LOST:${claim}`);await db.prepare("UPDATE sheet_replication_outbox SET claimed_at=?1 WHERE status='INFLIGHT' AND claim_token=?2").bind(nowIso(),claim).run();};
    await assertOwnership();const ids=claimed.map(x=>x.event_id),marks=ids.map(()=>"?").join(","),token=await googleAccessToken(env),present=await ensureReplicaSheet(env,token);await assertOwnership();
    const allEvents=(await db.prepare(`SELECT * FROM events WHERE event_id IN (${marks}) ORDER BY authority_epoch,authority_seq`).bind(...ids).all<EventRow>()).results??[];if(allEvents.length!==claimed.length||new Set(allEvents.map(e=>e.event_id)).size!==claimed.length)throw new Error("REPLICATION_EVENT_SET_MISMATCH");
    const technical=allEvents.filter(e=>!present.has(e.event_id));await assertOwnership();const checkpoint=await appendTechnicalRows(env,token,technical);await assertOwnership();const op=await replicateOperational(db,env,token,allEvents),operational=op.count;await assertOwnership();
    if(op.index)for(const e of allEvents){if(e.event_type==="ATTENDANCE_ENTER"||e.event_type==="ATTENDANCE_EXIT"){const raOk=op.index.raEvents.has(e.event_id),historyOk=op.index.historyEvents.has(e.event_id);if(!raOk||!historyOk)throw new Error(`REPLICATION_OPERATIONAL_INCOMPLETE:${e.event_id}:RA=${raOk?1:0}:HISTORY=${historyOk?1:0}`);}}
    await assertOwnership();const doneAt=nowIso();await db.prepare("UPDATE sheet_replication_outbox SET status='SYNCED',claim_token=NULL,claimed_at=NULL,replicated_at=?1,google_checkpoint=?2,last_error_class=NULL,last_error=NULL WHERE status='INFLIGHT' AND claim_token=?3").bind(doneAt,checkpoint,claim).run();const ackMarks=claimed.map(()=>"?").join(","),acked=await db.prepare(`SELECT COUNT(*) n FROM sheet_replication_outbox WHERE outbox_id IN (${ackMarks}) AND status='SYNCED'`).bind(...claimed.map(x=>x.outbox_id)).first<{n:number}>();if((acked?.n??0)!==claimed.length)throw new Error(`REPLICATION_ACK_FENCE_FAILED:${claim}`);
    const pending=await db.prepare("SELECT COUNT(*) n FROM sheet_replication_outbox WHERE status IN ('PENDING','RETRY','INFLIGHT')").first<{n:number}>();await db.prepare("UPDATE replication_status SET target_identity=?1,state='HEALTHY',checkpoint=?2,pending_count=?3,last_attempt_at=?4,last_success_at=?4,last_error_class=NULL,last_error=NULL,updated_at=?4 WHERE singleton_id=1").bind(isStableEnvironment(env)?"STABLE_PRIMARY_GAS:__M1_SERVICE_REPLICA":env.GOOGLE_STAGING_SHEET_ID,checkpoint,pending?.n??0,doneAt).run();return{ok:true,processed:claimed.length,appended:technical.length,operational,pending:pending?.n??0,checkpoint};
  }catch(e){const msg=String(e).slice(0,700),failedAt=nowIso(),maxAttempt=Math.max(1,...claimed.map(x=>x.attempt_count)),next=new Date(Date.now()+retryDelaySeconds(maxAttempt)*1000).toISOString();if(claimed.length)await db.prepare("UPDATE sheet_replication_outbox SET status='RETRY',claim_token=NULL,claimed_at=NULL,next_attempt_at=?1,last_error_class='TRANSIENT',last_error=?2 WHERE status='INFLIGHT' AND claim_token=?3").bind(next,msg,claim).run();const pending=await db.prepare("SELECT COUNT(*) n FROM sheet_replication_outbox WHERE status IN ('PENDING','RETRY','INFLIGHT')").first<{n:number}>();await db.prepare("UPDATE replication_status SET state='DEGRADED',pending_count=?1,retry_count=retry_count+1,last_attempt_at=?2,last_error_class='TRANSIENT',last_error=?3,updated_at=?2 WHERE singleton_id=1").bind(pending?.n??0,failedAt,msg).run();return{ok:false,processed:claimed.length,appended:0,operational:0,pending:pending?.n??0,error:msg};}
}

export async function replicationHealth(db:D1Database):Promise<Record<string,unknown>>{
  const results=await db.batch([
    db.prepare("SELECT target_kind,target_identity,schema_version,state,checkpoint,pending_count,retry_count,last_attempt_at,last_success_at,last_error_class,last_error,updated_at FROM replication_status WHERE singleton_id=1"),
    db.prepare("SELECT COUNT(*) n FROM sheet_replication_outbox WHERE status IN ('PENDING','RETRY','INFLIGHT')"),
  ]),row=(results[0]?.results?.[0]??{}) as Record<string,unknown>,actual=(results[1]?.results?.[0]??{}) as {n?:number};return{...row,pending_count:actual.n??0};
}

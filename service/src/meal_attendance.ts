import { bangkokToday, ensureCurrentBangkokBusinessDate } from "./business_date";
import { apiError, json } from "./util";
import { mealAlert, mealStatusView } from "./meal_policy";

const VALID_REASONS=new Set(["Xin về sớm","Đi hỗ trợ bộ phận/vị trí khác","Xin vào muộn","Nghỉ đột xuất","Có việc cá nhân","Được quản lý điều chuyển","Khác"]);

function safeDate(v:string):boolean{return /^\d{4}-\d{2}-\d{2}$/.test(v);}
function addDays(date:string,n:number):string{const d=new Date(date+"T00:00:00Z");d.setUTCDate(d.getUTCDate()+n);return d.toISOString().slice(0,10);}

async function materialize(env:Env,date:string):Promise<void>{
  const at=new Date().toISOString();
  await env.DB.prepare(`INSERT OR IGNORE INTO post_meal_attendance(
      business_date,mnv,shift,full_name_snapshot,supplier_snapshot,status,version,created_at,updated_at)
    SELECT s.business_date,s.mnv,s.shift,COALESCE(e.full_name,''),COALESCE(e.supplier,''),'PENDING',0,?2,?2
    FROM attendance_sessions s JOIN employees e ON e.mnv=s.mnv
    WHERE s.business_date=?1 AND s.enter_at IS NOT NULL`).bind(date,at).run();
}

function rank(status:string):number{return status==="OVERDUE_LATE"?0:status==="PENDING"?1:status==="LATE_EXPECTED"?2:status==="NO_RETURN"?3:4;}

export async function mealAttendanceDates(env:Env):Promise<Response>{
  const current=bangkokToday();await ensureCurrentBangkokBusinessDate(env.DB,current);
  await materialize(env,current);
  const floor=addDays(current,-13);
  const rows=(await env.DB.prepare("SELECT DISTINCT business_date FROM post_meal_attendance WHERE business_date>=?1 AND business_date<=?2 ORDER BY business_date DESC").bind(floor,current).all<{business_date:string}>()).results??[];
  return json({ok:true,source:"SERVICE_D1",retention_days:14,dates:rows.map(r=>String(r.business_date)).filter(safeDate)});
}

export async function mealAttendanceList(env:Env,body:{business_date?:string}):Promise<Response>{
  const current=bangkokToday();await ensureCurrentBangkokBusinessDate(env.DB,current);
  const date=String(body.business_date||current).slice(0,10);
  if(!safeDate(date))return apiError("BUSINESS_DATE_INVALID","VALIDATION",400);
  const floor=addDays(current,-13);
  if(date<floor||date>current)return apiError("MEAL_DATE_OUTSIDE_14_DAY_WINDOW","PERMISSION",403);
  if(date===current)await materialize(env,date);
  const rows=(await env.DB.prepare(`SELECT business_date,mnv,shift,full_name_snapshot,supplier_snapshot,status,checked_at,reason_code,reason_note,expected_return_at,actual_return_at,actor_id,device_id,version,created_at,updated_at
      FROM post_meal_attendance WHERE business_date=?1`).bind(date).all<Record<string,unknown>>()).results??[];
  const now=Date.now();
  const items=(rows.map(r=>({...r,status_view:mealStatusView(r,now)})) as Array<Record<string,unknown>&{status_view:string}>).sort((a,b)=>{
    const ra=rank(String(a.status_view)),rb=rank(String(b.status_view));if(ra!==rb)return ra-rb;
    const supplier=String(a.supplier_snapshot||"").localeCompare(String(b.supplier_snapshot||""),"vi",{numeric:true,sensitivity:"base"});if(supplier)return supplier;
    const mnv=String(a.mnv||"").localeCompare(String(b.mnv||""),"vi",{numeric:true,sensitivity:"base"});if(mnv)return mnv;
    return String(a.full_name_snapshot||"").localeCompare(String(b.full_name_snapshot||""),"vi",{sensitivity:"base"});
  });
  const bkk=new Date(now+7*3600_000),minutes=bkk.getUTCHours()*60+bkk.getUTCMinutes();
  const alert=mealAlert(items,minutes,now);
  return json({ok:true,source:"SERVICE_D1",business_date:date,current_day:date===current,retention_days:14,items,alert});
}

export function validateMealMutationPayload(action:string,payload:Record<string,unknown>):void{
  const status=String(payload.status||"");
  const reason=String(payload.reason_code||"").trim();
  const note=String(payload.reason_note||"").trim();
  const expected=String(payload.expected_return_at||"").trim();
  if(action==="meal_status"){
    if(!["NO_RETURN","LATE_EXPECTED"].includes(status))throw new Error("MEAL_STATUS_INVALID");
    if(!VALID_REASONS.has(reason))throw new Error("MEAL_REASON_INVALID");
    if(reason==="Khác"&&!note)throw new Error("MEAL_REASON_NOTE_REQUIRED");
    if(status==="LATE_EXPECTED"||reason==="Xin vào muộn"){
      if(!expected||Number.isNaN(Date.parse(expected)))throw new Error("MEAL_EXPECTED_TIME_REQUIRED");
    }
  }
}

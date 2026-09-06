import { commitAdminAudit } from "./admin_audit";
import type { AuthContext } from "./domain";
import { nowIso } from "./util";

type ReplayRow={
  audit_id:string;action:string;target_type:string;target_id:string;actor_id:string;
  actor_role:"ADMIN"|"SUPERADMIN";detail_json:string;created_at:string;
};
type ReplayCheckpoint={created_at:string;audit_id:string};

const REPLAY_TASK="document-audit-history-replay-v2";
const PAGE_SIZE=100;
const ACTIONS="'DOCUMENT_UPLOAD_COMPLETE','DOCUMENT_DELETE_SELECTED','DOCUMENT_UPDATE','CATEGORY_CREATE','CATEGORY_RENAME_ALL','CATEGORY_DELETE_ALL'";

function canonicalAction(action:string):string|null{
  if(action==="DOCUMENT_UPLOAD_COMPLETE")return "document_upload";
  if(action==="DOCUMENT_DELETE_SELECTED")return "document_delete";
  if(action==="DOCUMENT_UPDATE")return "document_update";
  if(action==="CATEGORY_CREATE")return "document_category_create";
  if(action==="CATEGORY_RENAME_ALL")return "document_category_update";
  if(action==="CATEGORY_DELETE_ALL")return "document_category_delete";
  return null;
}
function safeDetail(action:string,detail:Record<string,unknown>):Record<string,unknown>{
  if(action==="DOCUMENT_UPLOAD_COMPLETE")return{byte_size:Number(detail.byte_size||0),group_id:String(detail.group_id||""),page_index:Number(detail.page_index||1),page_count:Number(detail.page_count||1)};
  if(action==="DOCUMENT_DELETE_SELECTED")return{deleted_count:Number(detail.deleted_count||0),mutation_id:String(detail.mutation_id||"")};
  if(action==="DOCUMENT_UPDATE")return{before:detail.before||{},after:detail.after||{}};
  if(action==="CATEGORY_CREATE")return{};
  if(action==="CATEGORY_RENAME_ALL"||action==="CATEGORY_DELETE_ALL")return{category_id:String(detail.category_id||""),total_items:Number(detail.total_items||0),mutation_id:String(detail.mutation_id||"")};
  return{};
}
function parseDetail(raw:string):Record<string,unknown>{try{return JSON.parse(raw) as Record<string,unknown>;}catch{return{};}}
function parseCheckpoint(raw:string|undefined):ReplayCheckpoint{
  try{
    const v=JSON.parse(raw||"{}") as Partial<ReplayCheckpoint>;
    return{created_at:String(v.created_at||""),audit_id:String(v.audit_id||"")};
  }catch{return{created_at:"",audit_id:""};}
}
async function emit(env:Env,row:ReplayRow):Promise<void>{
  const action=canonicalAction(row.action);if(!action)return;
  const auth:AuthContext={login_id:row.actor_id,role:row.actor_role,display_name:row.actor_id,device_id:"document-audit-replay-v2",session_id:`doc-audit-${row.audit_id}`,verifier_hash:"internal"};
  const label=row.target_type==="DOCUMENT_CATEGORY"?"Loại biên bản":row.target_type==="DOCUMENT"?"Biên bản":"Thao tác biên bản";
  await commitAdminAudit(env.DB,auth,{
    action,event_id:`doc-audit-${row.audit_id}`,target_type:row.target_type,target_id:row.target_id,
    target_label:label,detail:JSON.stringify(safeDetail(row.action,parseDetail(row.detail_json))).slice(0,500),device_id:auth.device_id
  });
}
async function saveCheckpoint(env:Env,cp:ReplayCheckpoint):Promise<void>{
  const at=nowIso();
  await env.DB.prepare(`INSERT INTO service_maintenance(task_key,last_run_at,checkpoint,updated_at)
    VALUES(?1,?2,?3,?2)
    ON CONFLICT(task_key) DO UPDATE SET last_run_at=excluded.last_run_at,checkpoint=excluded.checkpoint,updated_at=excluded.updated_at`)
    .bind(REPLAY_TASK,at,JSON.stringify(cp)).run();
}

/**
 * Replays document audit history only after the dirty marker is raised by a failed
 * synchronous emit. Rows are traversed oldest-first using a durable checkpoint.
 * The dirty marker is cleared only when the page is terminal AND no newer failure
 * changed its generation timestamp while this pass was running.
 */
export async function flushDocumentAuditHistoryR5(env:Env):Promise<{emitted:number;scanned:number;remaining:boolean;failed:boolean}>{
  const dirty=await env.DB.prepare("SELECT value,updated_at FROM system_meta WHERE key='r5_document_audit_dirty'").first<{value:string;updated_at:string}>();
  if(dirty?.value!=="1")return{emitted:0,scanned:0,remaining:false,failed:false};
  const markerUpdatedAt=String(dirty.updated_at||"");
  const saved=await env.DB.prepare("SELECT checkpoint FROM service_maintenance WHERE task_key=?1").bind(REPLAY_TASK).first<{checkpoint:string}>();
  const cp=parseCheckpoint(saved?.checkpoint);
  const rows=await env.DB.prepare(`SELECT audit_id,action,target_type,target_id,actor_id,actor_role,detail_json,created_at
    FROM document_audit
    WHERE action IN (${ACTIONS})
      AND (?1='' OR created_at>?1 OR (created_at=?1 AND audit_id>?2))
    ORDER BY created_at ASC,audit_id ASC LIMIT ?3`)
    .bind(cp.created_at,cp.audit_id,PAGE_SIZE+1).all<ReplayRow>();
  const page=(rows.results||[]).slice(0,PAGE_SIZE),hasMore=(rows.results||[]).length>PAGE_SIZE;
  let emitted=0,scanned=0,failed=false,last=cp;
  for(const row of page){
    try{
      await emit(env,row);
      emitted++;
      scanned++;
      last={created_at:row.created_at,audit_id:row.audit_id};
    }catch{
      failed=true;
      break;
    }
  }
  if(scanned>0)await saveCheckpoint(env,last);
  const terminal=!failed&&!hasMore&&scanned===page.length;
  if(terminal){
    await env.DB.prepare("UPDATE system_meta SET value='0',updated_at=?1 WHERE key='r5_document_audit_dirty' AND value='1' AND updated_at=?2")
      .bind(nowIso(),markerUpdatedAt).run();
    const after=await env.DB.prepare("SELECT value FROM system_meta WHERE key='r5_document_audit_dirty'").first<{value:string}>();
    return{emitted,scanned,remaining:after?.value==="1",failed:false};
  }
  return{emitted,scanned,remaining:true,failed};
}

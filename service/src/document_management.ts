import { authenticate } from "./auth";
import { commitAdminAudit } from "./admin_audit";
import type { AuthContext } from "./domain";
import { apiError, json, nowIso, readJsonBody } from "./util";

type DocCategoryRow={
  category_id:string;display_name:string;normalized_name:string;status:string;
  created_at:string;created_by:string;updated_at:string;updated_by:string;
  mutation_state:string;mutation_id:string|null;
};
type DocMutationRow={
  mutation_id:string;idempotency_key:string;category_id:string;operation:"UPDATE"|"DELETE";
  old_display_name:string;new_display_name:string|null;new_normalized_name:string|null;
  state:"RUNNING"|"DONE"|"FAILED";total_items:number;processed_items:number;
  actor_id:string;actor_role:"ADMIN"|"SUPERADMIN";created_at:string;updated_at:string;
  completed_at:string|null;last_error:string|null;
};
type DocRow={
  document_id:string;idempotency_key:string;category_id:string;category_name_snapshot:string;
  uploader_id:string;uploader_name_snapshot:string;captured_at:string|null;created_at:string;updated_at:string;
  completed_at:string|null;status:string;file_name:string;mime_type:string;byte_size:number;sha256:string;md5:string;
  dhash64:string|null;width:number|null;height:number|null;source_kind:string;drive_file_id:string|null;
  duplicate_of_document_id:string|null;last_error:string|null;
  group_id:string|null;group_mode:string|null;page_index:number|null;page_count:number|null;note:string|null;
};
type DocDeleteMutationRow={
  mutation_id:string;idempotency_key:string;state:"RUNNING"|"DONE"|"FAILED";total_items:number;processed_items:number;
  actor_id:string;actor_role:"ADMIN"|"SUPERADMIN";created_at:string;updated_at:string;completed_at:string|null;last_error:string|null;
};

const MAX_IMAGE_BYTES=10*1024*1024;
const SIMILAR_DHASH_DISTANCE=16;
const MAX_DHASH_VARIANTS=4;
const RECENT_DHASH_SCAN_LIMIT=300;
const CATEGORY_MUTATION_BATCH=5;
const DOCUMENT_DELETE_BATCH=8;
// Beta108 owner-locked category mutation: rename-all/hard-delete durable job.

async function requireAdmin(request:Request,env:Env):Promise<AuthContext|Response>{
  const auth=await authenticate(env.DB,env,request);
  if(!auth)return apiError("UNAUTHORIZED","AUTH",401);
  if(auth.role!=="ADMIN"&&auth.role!=="SUPERADMIN")return apiError("ADMIN_REQUIRED","PERMISSION",403);
  return auth;
}
function isResponse(v:AuthContext|Response):v is Response{return v instanceof Response;}
function normalizeName(value:string):string{
  return value.trim().replace(/\s+/g," ").normalize("NFD").replace(/[\u0300-\u036f]/g,"").replace(/[Đđ]/g,"d").toLowerCase();
}
function safeName(value:string):string{
  return normalizeName(value).replace(/[^a-z0-9]+/g,"_").replace(/^_+|_+$/g,"").slice(0,44)||"bien_ban";
}
function localParts(iso:string){
  const d=new Date(iso);
  const parts=new Intl.DateTimeFormat("en-CA",{timeZone:"Asia/Ho_Chi_Minh",year:"numeric",month:"2-digit",day:"2-digit",hour:"2-digit",minute:"2-digit",second:"2-digit",hourCycle:"h23"}).formatToParts(d);
  const get=(type:string)=>parts.find(p=>p.type===type)?.value||"00";
  return{year:get("year"),month:get("month"),day:get("day"),hour:get("hour"),minute:get("minute"),second:get("second")};
}
function hammingHex64(a:string,b:string):number{
  let x=BigInt("0x"+a)^BigInt("0x"+b),count=0;
  while(x){count+=Number(x&1n);x>>=1n;}
  return count;
}
function escapeDriveQuery(v:string):string{return v.replace(/\\/g,"\\\\").replace(/'/g,"\\'");}
function categoryPublic(r:DocCategoryRow){return{category_id:r.category_id,display_name:r.display_name,status:r.status,mutation_state:r.mutation_state||"NONE",mutation_id:r.mutation_id||null};}
function mutationPublic(r:DocMutationRow){return{mutation_id:r.mutation_id,category_id:r.category_id,operation:r.operation,state:r.state,total_items:Number(r.total_items||0),processed_items:Number(r.processed_items||0),last_error:r.last_error||null};}
function documentPublic(r:DocRow){return{
  document_id:r.document_id,category_id:r.category_id,category_name:r.category_name_snapshot,
  uploader_id:r.uploader_id,uploader_name:r.uploader_name_snapshot,captured_at:r.captured_at,
  created_at:r.created_at,completed_at:r.completed_at,status:r.status,file_name:r.file_name,
  mime_type:r.mime_type,byte_size:Number(r.byte_size||0),width:r.width,height:r.height,source_kind:r.source_kind,
  duplicate_of_document_id:r.duplicate_of_document_id,group_id:r.group_id||r.document_id,group_mode:r.group_mode||"SINGLE",
  page_index:Number(r.page_index||1),page_count:Number(r.page_count||1),note:r.note||""
};}
function canonicalDocumentAction(action:string):string|null{
  if(action==="DOCUMENT_UPLOAD_COMPLETE")return "document_upload";
  if(action==="DOCUMENT_DELETE_SELECTED")return "document_delete";
  if(action==="CATEGORY_CREATE")return "document_category_create";
  if(action==="CATEGORY_RENAME_ALL")return "document_category_update";
  if(action==="CATEGORY_DELETE_ALL")return "document_category_delete";
  return null;
}
function documentHistoryDetail(action:string,detail:Record<string,unknown>):Record<string,unknown>{
  if(action==="DOCUMENT_UPLOAD_COMPLETE")return{
    byte_size:Number(detail.byte_size||0),group_id:String(detail.group_id||""),page_index:Number(detail.page_index||1),page_count:Number(detail.page_count||1)
  };
  if(action==="DOCUMENT_DELETE_SELECTED")return{deleted_count:Number(detail.deleted_count||0),mutation_id:String(detail.mutation_id||"")};
  if(action==="CATEGORY_CREATE")return{};
  if(action==="CATEGORY_RENAME_ALL")return{category_id:String(detail.category_id||""),total_items:Number(detail.total_items||0),mutation_id:String(detail.mutation_id||"")};
  if(action==="CATEGORY_DELETE_ALL")return{category_id:String(detail.category_id||""),total_items:Number(detail.total_items||0),mutation_id:String(detail.mutation_id||"")};
  return{};
}
async function emitDocumentHistory(env:Env,auth:AuthContext,auditId:string,action:string,targetType:string,targetId:string,detail:Record<string,unknown>){
  const canonical=canonicalDocumentAction(action);if(!canonical)return;
  const safeDetail=documentHistoryDetail(action,detail);
  const targetLabel=targetType==="DOCUMENT_CATEGORY"?"Loại biên bản":targetType==="DOCUMENT"?"Biên bản":"Thao tác biên bản";
  await commitAdminAudit(env.DB,auth,{
    action:canonical,event_id:`doc-audit-${auditId}`,target_type:targetType,target_id:targetId,
    target_label:targetLabel,detail:JSON.stringify(safeDetail).slice(0,500),device_id:auth.device_id
  });
}
async function audit(env:Env,auth:AuthContext,action:string,targetType:string,targetId:string,detail:Record<string,unknown>={}){
  const auditId=crypto.randomUUID(),at=nowIso();
  await env.DB.prepare("INSERT INTO document_audit(audit_id,action,target_type,target_id,actor_id,actor_role,detail_json,created_at) VALUES(?1,?2,?3,?4,?5,?6,?7,?8)")
    .bind(auditId,action,targetType,targetId,auth.login_id,auth.role,JSON.stringify(detail),at).run();
  try{await emitDocumentHistory(env,auth,auditId,action,targetType,targetId,detail);}catch{}
  return auditId;
}
export async function flushDocumentAuditHistory(env:Env):Promise<number>{
  const rows=await env.DB.prepare(`SELECT audit_id,action,target_type,target_id,actor_id,actor_role,detail_json,created_at FROM document_audit
    WHERE action IN ('DOCUMENT_UPLOAD_COMPLETE','DOCUMENT_DELETE_SELECTED','CATEGORY_CREATE','CATEGORY_RENAME_ALL','CATEGORY_DELETE_ALL')
    ORDER BY created_at DESC LIMIT 200`).all<{audit_id:string;action:string;target_type:string;target_id:string;actor_id:string;actor_role:"ADMIN"|"SUPERADMIN";detail_json:string;created_at:string}>();
  let emitted=0;
  for(const row of (rows.results||[]).reverse()){
    const eventId=`doc-audit-${row.audit_id}`;
    const exists=await env.DB.prepare("SELECT 1 AS ok FROM events WHERE event_id=?1").bind(eventId).first<{ok:number}>();if(exists?.ok)continue;
    const auth:AuthContext={login_id:row.actor_id,role:row.actor_role,display_name:row.actor_id,device_id:"document-audit-replay",session_id:eventId,verifier_hash:"internal"};
    const detail=(()=>{try{return JSON.parse(row.detail_json) as Record<string,unknown>}catch{return{}}})();
    try{await emitDocumentHistory(env,auth,row.audit_id,row.action,row.target_type,row.target_id,detail);emitted++;}catch{}
  }
  return emitted;
}
async function googleToken(env:Env):Promise<string>{
  const body=new URLSearchParams({
    client_id:env.GOOGLE_OAUTH_CLIENT_ID,
    client_secret:env.GOOGLE_OAUTH_CLIENT_SECRET,
    refresh_token:env.GOOGLE_OAUTH_REFRESH_TOKEN,
    grant_type:"refresh_token"
  });
  const r=await fetch("https://oauth2.googleapis.com/token",{method:"POST",headers:{"content-type":"application/x-www-form-urlencoded"},body});
  const j=await r.json<{access_token?:string;error?:string;error_description?:string}>();
  if(!r.ok||!j.access_token)throw new Error("DRIVE_OAUTH:"+String(j.error||r.status));
  return j.access_token;
}
async function driveJson<T>(token:string,url:string,init:RequestInit={}):Promise<{response:Response;json:T}>{
  const headers=new Headers(init.headers||{});
  headers.set("authorization",`Bearer ${token}`);
  headers.set("accept","application/json");
  const r=await fetch(url,{...init,headers});
  const text=await r.text();
  const j=(text?JSON.parse(text):{}) as T;
  if(!r.ok)throw new Error(`DRIVE_HTTP_${r.status}:${text.slice(0,300)}`);
  return{response:r,json:j};
}
async function cachedFolder(env:Env,pathKey:string):Promise<string|null>{
  return (await env.DB.prepare("SELECT drive_folder_id FROM document_drive_folders WHERE path_key=?1").bind(pathKey).first<{drive_folder_id:string}>())?.drive_folder_id||null;
}
async function rememberFolder(env:Env,pathKey:string,id:string){
  await env.DB.prepare("INSERT OR IGNORE INTO document_drive_folders(path_key,drive_folder_id,created_at) VALUES(?1,?2,?3)").bind(pathKey,id,nowIso()).run();
}
async function findFolder(token:string,name:string,parentId:string|null,appKey?:string,appValue?:string):Promise<string|null>{
  const clauses=[
    "mimeType = 'application/vnd.google-apps.folder'",
    "trashed = false",
    `name = '${escapeDriveQuery(name)}'`
  ];
  if(parentId)clauses.push(`'${escapeDriveQuery(parentId)}' in parents`);
  if(appKey&&appValue)clauses.push(`appProperties has { key='${escapeDriveQuery(appKey)}' and value='${escapeDriveQuery(appValue)}' }`);
  const u=new URL("https://www.googleapis.com/drive/v3/files");
  u.searchParams.set("q",clauses.join(" and "));
  u.searchParams.set("spaces","drive");
  u.searchParams.set("pageSize","10");
  u.searchParams.set("fields","files(id,name)");
  const {json:j}=await driveJson<{files?:Array<{id?:string}>}>(token,u.toString());
  return j.files?.find(x=>x.id)?.id||null;
}
async function createFolder(token:string,name:string,parentId:string|null,appProperties?:Record<string,string>):Promise<string>{
  const body:Record<string,unknown>={name,mimeType:"application/vnd.google-apps.folder"};
  if(parentId)body.parents=[parentId];
  if(appProperties)body.appProperties=appProperties;
  const {json:j}=await driveJson<{id?:string}>(token,"https://www.googleapis.com/drive/v3/files?fields=id",{
    method:"POST",headers:{"content-type":"application/json"},body:JSON.stringify(body)
  });
  if(!j.id)throw new Error("DRIVE_FOLDER_ID_MISSING");
  return j.id;
}
async function ensureFolder(env:Env,token:string,pathKey:string,name:string,parentId:string|null,appKey?:string,appValue?:string):Promise<string>{
  const cached=await cachedFolder(env,pathKey);
  if(cached)return cached;
  const found=await findFolder(token,name,parentId,appKey,appValue);
  const id=found||await createFolder(token,name,parentId,appKey&&appValue?{[appKey]:appValue}:undefined);
  await rememberFolder(env,pathKey,id);
  return id;
}
async function ensureDocumentMonthFolder(env:Env,token:string,createdAt:string):Promise<string>{
  const environment=String(env.ENVIRONMENT_ID||"BETA").toUpperCase();
  const p=localParts(createdAt);
  const root=await ensureFolder(env,token,"DOCROOT","PICK_PACK_1291",null,"pp1291_root","documents_v1");
  const envFolder=await ensureFolder(env,token,`DOCROOT/${environment}`,environment,root,"pp1291_environment",environment);
  const docs=await ensureFolder(env,token,`DOCROOT/${environment}/BIEN_BAN`,"BIEN_BAN",envFolder,"pp1291_documents","v1");
  const year=await ensureFolder(env,token,`DOCROOT/${environment}/BIEN_BAN/${p.year}`,p.year,docs);
  return ensureFolder(env,token,`DOCROOT/${environment}/BIEN_BAN/${p.year}/${p.month}`,p.month,year);
}
async function createUploadSession(env:Env,token:string,row:DocRow,folderId:string):Promise<string>{
  const u=new URL("https://www.googleapis.com/upload/drive/v3/files");
  u.searchParams.set("uploadType","resumable");
  u.searchParams.set("fields","id,name,size,mimeType,md5Checksum,appProperties,parents,thumbnailLink,createdTime");
  const metadata={
    name:row.file_name,
    parents:[folderId],
    appProperties:{
      pp1291_document_id:row.document_id,
      pp1291_environment:String(env.ENVIRONMENT_ID||"BETA").toUpperCase(),
      pp1291_category_id:row.category_id,
      pp1291_expected_md5:row.md5,
      pp1291_group_id:row.group_id||row.document_id,
      pp1291_page_index:String(row.page_index||1),
      pp1291_page_count:String(row.page_count||1)
    }
  };
  const r=await fetch(u.toString(),{
    method:"POST",
    headers:{
      authorization:`Bearer ${token}`,
      "content-type":"application/json; charset=utf-8",
      "x-upload-content-type":row.mime_type,
      "x-upload-content-length":String(row.byte_size)
    },
    body:JSON.stringify(metadata)
  });
  if(!r.ok)throw new Error(`DRIVE_RESUMABLE_${r.status}:${(await r.text()).slice(0,300)}`);
  const location=r.headers.get("location")||"";
  if(!location.startsWith("https://"))throw new Error("DRIVE_RESUMABLE_LOCATION_MISSING");
  return location;
}

function renamedDocumentFileName(row:DocRow,newCategoryName:string):string{
  const p=localParts(row.created_at);
  return `${safeName(newCategoryName)}_${safeName(row.uploader_name_snapshot)}_${p.year}${p.month}${p.day}_${p.hour}${p.minute}${p.second}_${row.document_id.slice(0,8)}.jpg`;
}
async function renameDriveFile(token:string,driveFileId:string,newName:string):Promise<void>{
  const {json:j}=await driveJson<{id?:string;name?:string;trashed?:boolean}>(
    token,`https://www.googleapis.com/drive/v3/files/${encodeURIComponent(driveFileId)}?fields=id,name,trashed`,{
      method:"PATCH",headers:{"content-type":"application/json"},body:JSON.stringify({name:newName})
    }
  );
  if(j.id!==driveFileId||j.name!==newName||j.trashed)throw new Error("DRIVE_RENAME_VERIFY_FAILED");
}
async function deleteDriveFile(token:string,driveFileId:string):Promise<void>{
  const r=await fetch(`https://www.googleapis.com/drive/v3/files/${encodeURIComponent(driveFileId)}`,{
    method:"DELETE",headers:{authorization:`Bearer ${token}`}
  });
  if(r.status===404)return;
  if(!r.ok)throw new Error(`DRIVE_DELETE_${r.status}:${(await r.text()).slice(0,200)}`);
}
function mutationAuth(job:DocMutationRow):AuthContext{
  return{login_id:job.actor_id,role:job.actor_role,display_name:job.actor_id,device_id:"document-category-mutation",session_id:job.mutation_id,verifier_hash:"internal"};
}
async function mutationById(env:Env,id:string):Promise<DocMutationRow|null>{
  return env.DB.prepare("SELECT * FROM document_category_mutations WHERE mutation_id=?1").bind(id).first<DocMutationRow>();
}
async function processDocumentCategoryMutation(env:Env,mutationId:string):Promise<DocMutationRow|null>{
  let job=await mutationById(env,mutationId);
  if(!job||job.state!=="RUNNING")return job;
  const category=await env.DB.prepare("SELECT * FROM document_categories WHERE category_id=?1").bind(job.category_id).first<DocCategoryRow>();
  if(!category){
    await env.DB.prepare("UPDATE document_category_mutations SET state='FAILED',updated_at=?1,last_error='DOCUMENT_CATEGORY_NOT_FOUND' WHERE mutation_id=?2").bind(nowIso(),mutationId).run();
    return mutationById(env,mutationId);
  }
  try{
    const token=await googleToken(env);
    if(job.operation==="UPDATE"){
      const rows=await env.DB.prepare(`SELECT * FROM document_records d
        WHERE d.category_id=?1 AND d.status='COMPLETE'
        AND NOT EXISTS(SELECT 1 FROM document_category_mutation_items i WHERE i.mutation_id=?2 AND i.document_id=d.document_id AND i.state='DONE')
        ORDER BY d.created_at ASC LIMIT ?3`).bind(job.category_id,job.mutation_id,CATEGORY_MUTATION_BATCH).all<DocRow>();
      for(const row of rows.results||[]){
        if(!row.drive_file_id)throw new Error("DOCUMENT_DRIVE_ID_MISSING");
        const newName=renamedDocumentFileName(row,job.new_display_name||category.display_name);
        await renameDriveFile(token,row.drive_file_id,newName);
        const at=nowIso();
        await env.DB.batch([
          env.DB.prepare("INSERT OR REPLACE INTO document_category_mutation_items(mutation_id,document_id,drive_file_id,old_file_name,new_file_name,state,last_error,updated_at) VALUES(?1,?2,?3,?4,?5,'DONE',NULL,?6)")
            .bind(job.mutation_id,row.document_id,row.drive_file_id,row.file_name,newName,at),
          env.DB.prepare("UPDATE document_records SET file_name=?1,updated_at=?2 WHERE document_id=?3").bind(newName,at,row.document_id)
        ]);
      }
      const left=await env.DB.prepare(`SELECT COUNT(*) AS n FROM document_records d WHERE d.category_id=?1 AND d.status='COMPLETE'
        AND NOT EXISTS(SELECT 1 FROM document_category_mutation_items i WHERE i.mutation_id=?2 AND i.document_id=d.document_id AND i.state='DONE')`)
        .bind(job.category_id,job.mutation_id).first<{n:number}>();
      const done=await env.DB.prepare("SELECT COUNT(*) AS n FROM document_category_mutation_items WHERE mutation_id=?1 AND state='DONE'").bind(job.mutation_id).first<{n:number}>();
      await env.DB.prepare("UPDATE document_category_mutations SET processed_items=?1,updated_at=?2,last_error=NULL WHERE mutation_id=?3")
        .bind(Number(done?.n||0),nowIso(),job.mutation_id).run();
      if(Number(left?.n||0)===0){
        const at=nowIso(),newName=job.new_display_name||category.display_name,newNorm=job.new_normalized_name||normalizeName(newName);
        await env.DB.batch([
          env.DB.prepare("UPDATE document_records SET category_name_snapshot=?1,updated_at=?2 WHERE category_id=?3").bind(newName,at,job.category_id),
          env.DB.prepare("UPDATE document_categories SET display_name=?1,normalized_name=?2,mutation_state='NONE',mutation_id=NULL,updated_at=?3,updated_by=?4 WHERE category_id=?5 AND mutation_id=?6")
            .bind(newName,newNorm,at,job.actor_id,job.category_id,job.mutation_id),
          env.DB.prepare("UPDATE document_category_mutations SET state='DONE',processed_items=total_items,updated_at=?1,completed_at=?1,last_error=NULL WHERE mutation_id=?2").bind(at,job.mutation_id)
        ]);
        await audit(env,mutationAuth(job),"CATEGORY_RENAME_ALL","DOCUMENT_CATEGORY",job.category_id,{from:job.old_display_name,to:newName,total_items:Number(job.total_items||0),mutation_id:job.mutation_id});
      }
    }else{
      const rows=await env.DB.prepare("SELECT * FROM document_records WHERE category_id=?1 ORDER BY created_at ASC LIMIT ?2")
        .bind(job.category_id,CATEGORY_MUTATION_BATCH).all<DocRow>();
      for(const row of rows.results||[]){
        if(row.drive_file_id)await deleteDriveFile(token,row.drive_file_id);
        const at=nowIso();
        await env.DB.batch([
          env.DB.prepare("INSERT OR REPLACE INTO document_category_mutation_items(mutation_id,document_id,drive_file_id,old_file_name,new_file_name,state,last_error,updated_at) VALUES(?1,?2,?3,?4,NULL,'DONE',NULL,?5)")
            .bind(job.mutation_id,row.document_id,row.drive_file_id,row.file_name,at),
          env.DB.prepare("DELETE FROM document_records WHERE document_id=?1").bind(row.document_id)
        ]);
      }
      const left=await env.DB.prepare("SELECT COUNT(*) AS n FROM document_records WHERE category_id=?1").bind(job.category_id).first<{n:number}>();
      const done=await env.DB.prepare("SELECT COUNT(*) AS n FROM document_category_mutation_items WHERE mutation_id=?1 AND state='DONE'").bind(job.mutation_id).first<{n:number}>();
      await env.DB.prepare("UPDATE document_category_mutations SET processed_items=?1,updated_at=?2,last_error=NULL WHERE mutation_id=?3")
        .bind(Number(done?.n||0),nowIso(),job.mutation_id).run();
      if(Number(left?.n||0)===0){
        const at=nowIso();
        await env.DB.batch([
          env.DB.prepare("DELETE FROM document_audit WHERE target_type='DOCUMENT' AND target_id IN (SELECT document_id FROM document_category_mutation_items WHERE mutation_id=?1)").bind(job.mutation_id),
          env.DB.prepare("DELETE FROM document_audit WHERE target_type='DOCUMENT_CATEGORY' AND target_id=?1").bind(job.category_id),
          env.DB.prepare("DELETE FROM document_categories WHERE category_id=?1 AND mutation_id=?2").bind(job.category_id,job.mutation_id),
          env.DB.prepare("DELETE FROM document_category_mutation_items WHERE mutation_id IN (SELECT mutation_id FROM document_category_mutations WHERE category_id=?1)").bind(job.category_id),
          env.DB.prepare("UPDATE document_category_mutations SET old_display_name='',new_display_name=NULL,new_normalized_name=NULL WHERE category_id=?1").bind(job.category_id),
          env.DB.prepare("UPDATE document_category_mutations SET state='DONE',processed_items=total_items,updated_at=?1,completed_at=?1,last_error=NULL WHERE mutation_id=?2").bind(at,job.mutation_id)
        ]);
        await audit(env,mutationAuth(job),"CATEGORY_DELETE_ALL","DOCUMENT_DELETE_RECEIPT",job.mutation_id,{category_id:job.category_id,total_items:Number(job.total_items||0),mutation_id:job.mutation_id});
      }
    }
  }catch(e){
    await env.DB.prepare("UPDATE document_category_mutations SET updated_at=?1,last_error=?2 WHERE mutation_id=?3")
      .bind(nowIso(),String(e).slice(0,500),job.mutation_id).run();
  }
  return mutationById(env,mutationId);
}
export async function processDocumentCategoryMutations(env:Env):Promise<{processed:number;active:number}>{
  const jobs=await env.DB.prepare("SELECT mutation_id FROM document_category_mutations WHERE state='RUNNING' ORDER BY updated_at ASC LIMIT 3").all<{mutation_id:string}>();
  let processed=0;
  for(const j of jobs.results||[]){await processDocumentCategoryMutation(env,j.mutation_id);processed++;}
  const active=await env.DB.prepare("SELECT COUNT(*) AS n FROM document_category_mutations WHERE state='RUNNING'").first<{n:number}>();
  return{processed,active:Number(active?.n||0)};
}

export async function documentCategories(request:Request,env:Env):Promise<Response>{
  const auth=await requireAdmin(request,env);if(isResponse(auth))return auth;
  const r=await env.DB.prepare("SELECT category_id,display_name,normalized_name,status,created_at,created_by,updated_at,updated_by,mutation_state,mutation_id FROM document_categories WHERE status='ACTIVE' ORDER BY display_name COLLATE NOCASE").all<DocCategoryRow>();
  return json({ok:true,items:(r.results||[]).map(categoryPublic),category_edit_delete_policy:"RENAME_ALL_OR_HARD_DELETE_WITH_CONFIRMATION"});
}
export async function documentCategoryMutate(request:Request,env:Env):Promise<Response>{
  const auth=await requireAdmin(request,env);if(isResponse(auth))return auth;
  const body=await readJsonBody<Record<string,unknown>>(request);
  const operation=String(body.operation||"CREATE").toUpperCase();
  const name=String(body.display_name||"").trim().replace(/\s+/g," ");
  if(operation==="CREATE"){
    if(name.length<2||name.length>80)return apiError("DOCUMENT_CATEGORY_NAME_INVALID","VALIDATION",400,false);
    const normalized=normalizeName(name),id=crypto.randomUUID(),at=nowIso();
    const reserved=await env.DB.prepare("SELECT mutation_id FROM document_category_mutations WHERE state='RUNNING' AND new_normalized_name=?1 LIMIT 1").bind(normalized).first<{mutation_id:string}>();
    if(reserved)return apiError("DOCUMENT_CATEGORY_EXISTS","CONFLICT",409,false);
    try{
      await env.DB.prepare("INSERT INTO document_categories(category_id,display_name,normalized_name,status,created_at,created_by,updated_at,updated_by,mutation_state,mutation_id) VALUES(?1,?2,?3,'ACTIVE',?4,?5,?4,?5,'NONE',NULL)")
        .bind(id,name,normalized,at,auth.login_id).run();
    }catch(e){
      if(String(e).toLowerCase().includes("unique"))return apiError("DOCUMENT_CATEGORY_EXISTS","CONFLICT",409,false);
      throw e;
    }
    await audit(env,auth,"CATEGORY_CREATE","DOCUMENT_CATEGORY",id,{display_name:name});
    return json({ok:true,item:{category_id:id,display_name:name,status:"ACTIVE",mutation_state:"NONE"}},201);
  }
  if(operation==="PROCESS"){
    const mutationId=String(body.mutation_id||"").trim();
    if(!mutationId)return apiError("DOCUMENT_CATEGORY_MUTATION_ID_REQUIRED","VALIDATION",400,false);
    const before=await mutationById(env,mutationId);
    if(!before)return apiError("DOCUMENT_CATEGORY_MUTATION_NOT_FOUND","VALIDATION",404,false);
    if(before.actor_id!==auth.login_id&&auth.role!=="SUPERADMIN")return apiError("DOCUMENT_CATEGORY_MUTATION_OWNER_REQUIRED","PERMISSION",403,false);
    const job=await processDocumentCategoryMutation(env,mutationId);
    return json({ok:true,mutation:job?mutationPublic(job):null});
  }
  if(operation!=="UPDATE"&&operation!=="DELETE")return apiError("DOCUMENT_CATEGORY_OPERATION_INVALID","VALIDATION",400,false);
  const categoryId=String(body.category_id||"").trim(),idem=String(body.idempotency_key||"").trim();
  if(!categoryId)return apiError("DOCUMENT_CATEGORY_ID_REQUIRED","VALIDATION",400,false);
  if(idem.length<8||idem.length>120)return apiError("DOCUMENT_IDEMPOTENCY_INVALID","VALIDATION",400,false);
  const prior=await env.DB.prepare("SELECT * FROM document_category_mutations WHERE idempotency_key=?1").bind(idem).first<DocMutationRow>();
  if(prior){
    const job=prior.state==="RUNNING"?await processDocumentCategoryMutation(env,prior.mutation_id):prior;
    return json({ok:true,idempotent:true,mutation:job?mutationPublic(job):null});
  }
  const category=await env.DB.prepare("SELECT category_id,display_name,normalized_name,status,created_at,created_by,updated_at,updated_by,mutation_state,mutation_id FROM document_categories WHERE category_id=?1 AND status='ACTIVE'")
    .bind(categoryId).first<DocCategoryRow>();
  if(!category)return apiError("DOCUMENT_CATEGORY_NOT_FOUND","VALIDATION",404,false);
  if(category.mutation_state!=="NONE")return apiError("DOCUMENT_CATEGORY_MUTATION_IN_PROGRESS","CONFLICT",409,true);
  let newNorm:string|null=null;
  if(operation==="UPDATE"){
    if(name.length<2||name.length>80)return apiError("DOCUMENT_CATEGORY_NAME_INVALID","VALIDATION",400,false);
    newNorm=normalizeName(name);
    if(newNorm===category.normalized_name&&name===category.display_name)return json({ok:true,no_change:true,item:categoryPublic(category)});
    const duplicate=await env.DB.prepare("SELECT category_id FROM document_categories WHERE normalized_name=?1 AND category_id<>?2 LIMIT 1").bind(newNorm,categoryId).first<{category_id:string}>();
    const reserved=await env.DB.prepare("SELECT mutation_id FROM document_category_mutations WHERE state='RUNNING' AND new_normalized_name=?1 LIMIT 1").bind(newNorm).first<{mutation_id:string}>();
    if(duplicate||reserved)return apiError("DOCUMENT_CATEGORY_EXISTS","CONFLICT",409,false);
  }
  const lockState=operation==="UPDATE"?"RENAMING":"DELETING",mutationId=crypto.randomUUID(),at=nowIso();
  const locked=await env.DB.prepare("UPDATE document_categories SET mutation_state=?1,mutation_id=?2,updated_at=?3,updated_by=?4 WHERE category_id=?5 AND mutation_state='NONE'")
    .bind(lockState,mutationId,at,auth.login_id,categoryId).run();
  if(Number(locked.meta?.changes||0)!==1)return apiError("DOCUMENT_CATEGORY_MUTATION_IN_PROGRESS","CONFLICT",409,true);
  try{
    const pending=await env.DB.prepare("SELECT COUNT(*) AS n FROM document_records WHERE category_id=?1 AND status<>'COMPLETE'").bind(categoryId).first<{n:number}>();
    if(Number(pending?.n||0)>0){
      await env.DB.prepare("UPDATE document_categories SET mutation_state='NONE',mutation_id=NULL,updated_at=?1,updated_by=?2 WHERE category_id=?3 AND mutation_id=?4")
        .bind(nowIso(),auth.login_id,categoryId,mutationId).run();
      return apiError("DOCUMENT_CATEGORY_PENDING_UPLOADS","CONFLICT",409,true);
    }
    const total=await env.DB.prepare("SELECT COUNT(*) AS n FROM document_records WHERE category_id=?1").bind(categoryId).first<{n:number}>();
    await env.DB.prepare(`INSERT INTO document_category_mutations(
      mutation_id,idempotency_key,category_id,operation,old_display_name,new_display_name,new_normalized_name,state,total_items,processed_items,
      actor_id,actor_role,created_at,updated_at,completed_at,last_error
    ) VALUES(?1,?2,?3,?4,?5,?6,?7,'RUNNING',?8,0,?9,?10,?11,?11,NULL,NULL)`)
      .bind(mutationId,idem,categoryId,operation,category.display_name,operation==="UPDATE"?name:null,newNorm,Number(total?.n||0),auth.login_id,auth.role,at).run();
    const job=await processDocumentCategoryMutation(env,mutationId);
    return json({ok:true,mutation:job?mutationPublic(job):null},202);
  }catch(e){
    await env.DB.prepare("UPDATE document_categories SET mutation_state='NONE',mutation_id=NULL,updated_at=?1,updated_by=?2 WHERE category_id=?3 AND mutation_id=?4")
      .bind(nowIso(),auth.login_id,categoryId,mutationId).run();
    throw e;
  }
}
export async function documentList(request:Request,env:Env):Promise<Response>{
  const auth=await requireAdmin(request,env);if(isResponse(auth))return auth;
  const u=new URL(request.url),limit=Math.min(100,Math.max(1,Number(u.searchParams.get("limit")||50)));
  const category=u.searchParams.get("category_id")?.trim()||"";
  const q=category
    ?env.DB.prepare("SELECT * FROM document_records WHERE status='COMPLETE' AND category_id=?1 ORDER BY completed_at DESC LIMIT ?2").bind(category,limit)
    :env.DB.prepare("SELECT * FROM document_records WHERE status='COMPLETE' ORDER BY completed_at DESC LIMIT ?1").bind(limit);
  const r=await q.all<DocRow>();
  return json({ok:true,items:(r.results||[]).map(documentPublic)});
}
export async function documentUploadSession(request:Request,env:Env):Promise<Response>{
  const auth=await requireAdmin(request,env);if(isResponse(auth))return auth;
  const body=await readJsonBody<Record<string,unknown>>(request);
  const categoryId=String(body.category_id||"").trim();
  const mimeType=String(body.mime_type||"").toLowerCase();
  const size=Number(body.byte_size||0);
  const sha256=String(body.sha256||"").toLowerCase();
  const md5=String(body.md5||"").toLowerCase();
  const dhash64=String(body.dhash64||"").toLowerCase();
  const dhashVariantsRaw=Array.isArray(body.dhash64_variants)?body.dhash64_variants:[];
  const dhashVariants=[dhash64,...dhashVariantsRaw.map(v=>String(v||"").toLowerCase())]
    .filter((v,i,a)=>v.length>0&&a.indexOf(v)===i).slice(0,MAX_DHASH_VARIANTS);
  const width=Number(body.width||0),height=Number(body.height||0);
  const sourceKind=String(body.source_kind||"").toUpperCase();
  const capturedAt=String(body.captured_at||"").trim()||null;
  const idempotency=String(body.idempotency_key||"").trim();
  const groupId=String(body.group_id||idempotency).trim().slice(0,120);
  const groupMode=String(body.group_mode||"SINGLE").trim().toUpperCase();
  const pageIndex=Number(body.page_index||1),pageCount=Number(body.page_count||1);
  const note=String(body.note||"").trim().slice(0,240);
  const allowSimilar=body.allow_similar===true;
  if(mimeType!=="image/jpeg")return apiError("DOCUMENT_IMAGE_MIME_INVALID","VALIDATION",400,false);
  if(!Number.isInteger(size)||size<=0||size>MAX_IMAGE_BYTES)return apiError("DOCUMENT_IMAGE_SIZE_INVALID","VALIDATION",400,false);
  if(!/^[0-9a-f]{64}$/.test(sha256)||!/^[0-9a-f]{32}$/.test(md5))return apiError("DOCUMENT_IMAGE_HASH_INVALID","VALIDATION",400,false);
  if(dhash64&&!/^[0-9a-f]{16}$/.test(dhash64))return apiError("DOCUMENT_IMAGE_FINGERPRINT_INVALID","VALIDATION",400,false);
  if(dhashVariants.some(v=>!/^[0-9a-f]{16}$/.test(v)))return apiError("DOCUMENT_IMAGE_FINGERPRINT_INVALID","VALIDATION",400,false);
  if(!Number.isInteger(width)||width<1||!Number.isInteger(height)||height<1)return apiError("DOCUMENT_IMAGE_DIMENSIONS_INVALID","VALIDATION",400,false);
  if(sourceKind!=="CAMERA"&&sourceKind!=="GALLERY")return apiError("DOCUMENT_IMAGE_SOURCE_INVALID","VALIDATION",400,false);
  if(idempotency.length<8||idempotency.length>120)return apiError("DOCUMENT_IDEMPOTENCY_INVALID","VALIDATION",400,false);
  if(groupId.length<8||!["SINGLE","MULTI_PAGE","MULTI_DOCUMENT"].includes(groupMode))return apiError("DOCUMENT_GROUP_INVALID","VALIDATION",400,false);
  if(!Number.isInteger(pageIndex)||!Number.isInteger(pageCount)||pageIndex<1||pageCount<1||pageIndex>pageCount||pageCount>60)return apiError("DOCUMENT_PAGE_INVALID","VALIDATION",400,false);

  const category=await env.DB.prepare("SELECT category_id,display_name,normalized_name,status,created_at,created_by,updated_at,updated_by,mutation_state,mutation_id FROM document_categories WHERE category_id=?1 AND status='ACTIVE'")
    .bind(categoryId).first<DocCategoryRow>();
  if(!category)return apiError("DOCUMENT_CATEGORY_NOT_FOUND","VALIDATION",404,false);
  if(category.mutation_state!=="NONE")return apiError("DOCUMENT_CATEGORY_MUTATION_IN_PROGRESS","CONFLICT",409,true);

  const prior=await env.DB.prepare("SELECT * FROM document_records WHERE idempotency_key=?1").bind(idempotency).first<DocRow>();
  if(prior){
    if(prior.sha256!==sha256||Number(prior.byte_size)!==size||prior.category_id!==categoryId)return apiError("DOCUMENT_IDEMPOTENCY_CONFLICT","CONFLICT",409,false);
    if(prior.status==="COMPLETE")return json({ok:true,already_complete:true,document:documentPublic(prior)});
  }else{
    const exact=await env.DB.prepare("SELECT * FROM document_records WHERE sha256=?1 AND status='COMPLETE' ORDER BY completed_at DESC LIMIT 1").bind(sha256).first<DocRow>();
    if(exact){
      return json({ok:false,error:{code:"DOCUMENT_EXACT_DUPLICATE",error_class:"CONFLICT",retryable:false},duplicate:{kind:"EXACT",document:documentPublic(exact)}},409);
    }
    if(dhashVariants.length>0&&!allowSimilar){
      const recent=await env.DB.prepare("SELECT * FROM document_records WHERE status='COMPLETE' AND dhash64 IS NOT NULL ORDER BY completed_at DESC LIMIT ?1").bind(RECENT_DHASH_SCAN_LIMIT).all<DocRow>();
      let best:{row:DocRow;distance:number}|null=null;
      for(const r of recent.results||[]){
        if(!r.dhash64||!/^[0-9a-f]{16}$/.test(r.dhash64))continue;
        for(const incoming of dhashVariants){
          const distance=hammingHex64(incoming,r.dhash64);
          if(distance<=SIMILAR_DHASH_DISTANCE&&(!best||distance<best.distance))best={row:r,distance};
        }
      }
      if(best){
        return json({ok:false,error:{code:"DOCUMENT_SIMILAR_IMAGE",error_class:"CONFLICT",retryable:false},duplicate:{kind:"SIMILAR",distance:best.distance,rotation_aware:true,threshold:SIMILAR_DHASH_DISTANCE,document:documentPublic(best.row)}},409);
      }
    }
  }

  const at=prior?.created_at||nowIso(),parts=localParts(at),documentId=prior?.document_id||crypto.randomUUID();
  const uploaderName=(auth.display_name||auth.login_id).trim()||auth.login_id;
  const fileName=prior?.file_name||`${safeName(category.display_name)}_${safeName(uploaderName)}_${parts.year}${parts.month}${parts.day}_${parts.hour}${parts.minute}${parts.second}_${documentId.slice(0,8)}.jpg`;
  let row=prior;
  if(!row){
    await env.DB.prepare(`INSERT INTO document_records(
      document_id,idempotency_key,category_id,category_name_snapshot,uploader_id,uploader_name_snapshot,captured_at,created_at,updated_at,status,
      file_name,mime_type,byte_size,sha256,md5,dhash64,width,height,source_kind,drive_file_id,duplicate_of_document_id,last_error,
      group_id,group_mode,page_index,page_count,note
    ) VALUES(?1,?2,?3,?4,?5,?6,?7,?8,?8,'PENDING',?9,?10,?11,?12,?13,?14,?15,?16,?17,NULL,NULL,NULL,?18,?19,?20,?21,?22)`)
      .bind(documentId,idempotency,category.category_id,category.display_name,auth.login_id,uploaderName,capturedAt,at,fileName,mimeType,size,sha256,md5,dhash64||null,width,height,sourceKind,groupId,groupMode,pageIndex,pageCount,note).run();
    row=await env.DB.prepare("SELECT * FROM document_records WHERE document_id=?1").bind(documentId).first<DocRow>()||null;
  }
  if(!row)return apiError("DOCUMENT_PENDING_CREATE_FAILED","INTERNAL",500,true);
  try{
    const token=await googleToken(env);
    const folderId=await ensureDocumentMonthFolder(env,token,row.created_at);
    const uploadUrl=await createUploadSession(env,token,row,folderId);
    await env.DB.prepare("UPDATE document_records SET status='PENDING',updated_at=?1,last_error=NULL WHERE document_id=?2").bind(nowIso(),row.document_id).run();
    return json({ok:true,document:documentPublic(row),upload_url:uploadUrl,upload_method:"PUT",upload_content_type:row.mime_type});
  }catch(e){
    const msg=String(e).slice(0,500);
    await env.DB.prepare("UPDATE document_records SET status='FAILED',updated_at=?1,last_error=?2 WHERE document_id=?3").bind(nowIso(),msg,row.document_id).run();
    const code=msg.includes("DRIVE_OAUTH")?"DOCUMENT_DRIVE_OAUTH_REQUIRED":"DOCUMENT_DRIVE_UNAVAILABLE";
    return apiError(code,"RESOURCE",503,true);
  }
}
export async function documentComplete(request:Request,env:Env):Promise<Response>{
  const auth=await requireAdmin(request,env);if(isResponse(auth))return auth;
  const body=await readJsonBody<Record<string,unknown>>(request);
  const documentId=String(body.document_id||"").trim(),driveFileId=String(body.drive_file_id||"").trim();
  if(!documentId||!driveFileId)return apiError("DOCUMENT_COMPLETE_INPUT_INVALID","VALIDATION",400,false);
  const row=await env.DB.prepare("SELECT * FROM document_records WHERE document_id=?1").bind(documentId).first<DocRow>();
  if(!row)return apiError("DOCUMENT_NOT_FOUND","VALIDATION",404,false);
  if(row.uploader_id!==auth.login_id&&auth.role!=="SUPERADMIN")return apiError("DOCUMENT_OWNER_OR_SUPERADMIN_REQUIRED","PERMISSION",403,false);
  if(row.status==="COMPLETE"){
    if(row.drive_file_id!==driveFileId)return apiError("DOCUMENT_ALREADY_COMPLETE_CONFLICT","CONFLICT",409,false);
    return json({ok:true,duplicate:true,document:documentPublic(row)});
  }
  try{
    const token=await googleToken(env);
    const fields="id,name,size,mimeType,md5Checksum,appProperties,parents,trashed";
    const {json:file}=await driveJson<{id?:string;name?:string;size?:string;mimeType?:string;md5Checksum?:string;appProperties?:Record<string,string>;trashed?:boolean}>(
      token,`https://www.googleapis.com/drive/v3/files/${encodeURIComponent(driveFileId)}?fields=${encodeURIComponent(fields)}`
    );
    if(file.trashed||file.id!==driveFileId||file.name!==row.file_name||file.mimeType!==row.mime_type||
       Number(file.size||0)!==Number(row.byte_size)||String(file.md5Checksum||"").toLowerCase()!==row.md5||
       file.appProperties?.pp1291_document_id!==row.document_id||
       file.appProperties?.pp1291_environment!==String(env.ENVIRONMENT_ID||"BETA").toUpperCase()){
      return apiError("DOCUMENT_DRIVE_VERIFY_FAILED","INTEGRITY",409,false);
    }
    const at=nowIso();
    await env.DB.prepare("UPDATE document_records SET status='COMPLETE',drive_file_id=?1,completed_at=?2,updated_at=?2,last_error=NULL WHERE document_id=?3")
      .bind(driveFileId,at,row.document_id).run();
    const complete=await env.DB.prepare("SELECT * FROM document_records WHERE document_id=?1").bind(row.document_id).first<DocRow>();
    await audit(env,auth,"DOCUMENT_UPLOAD_COMPLETE","DOCUMENT",row.document_id,{file_name:row.file_name,category_name:row.category_name_snapshot,byte_size:row.byte_size,sha256:row.sha256,group_id:row.group_id||row.document_id,page_index:Number(row.page_index||1),page_count:Number(row.page_count||1)});
    return json({ok:true,document:complete?documentPublic(complete):documentPublic({...row,status:"COMPLETE",drive_file_id:driveFileId,completed_at:at,updated_at:at})});
  }catch(e){
    await env.DB.prepare("UPDATE document_records SET updated_at=?1,last_error=?2 WHERE document_id=?3").bind(nowIso(),String(e).slice(0,500),row.document_id).run();
    return apiError("DOCUMENT_DRIVE_VERIFY_UNAVAILABLE","RESOURCE",503,true);
  }
}

function deleteMutationPublic(r:DocDeleteMutationRow){return{mutation_id:r.mutation_id,state:r.state,total_items:Number(r.total_items||0),processed_items:Number(r.processed_items||0),last_error:r.last_error||null};}
function deleteMutationAuth(job:DocDeleteMutationRow):AuthContext{return{login_id:job.actor_id,role:job.actor_role,display_name:job.actor_id,device_id:"document-delete-mutation",session_id:job.mutation_id,verifier_hash:"internal"};}
async function deleteMutationById(env:Env,id:string):Promise<DocDeleteMutationRow|null>{return env.DB.prepare("SELECT * FROM document_delete_mutations WHERE mutation_id=?1").bind(id).first<DocDeleteMutationRow>();}
async function processDocumentDeleteMutation(env:Env,mutationId:string):Promise<DocDeleteMutationRow|null>{
  let job=await deleteMutationById(env,mutationId);if(!job||job.state!=="RUNNING")return job;
  try{
    const token=await googleToken(env);
    const rows=await env.DB.prepare("SELECT mutation_id,document_id,drive_file_id,state FROM document_delete_items WHERE mutation_id=?1 AND state='PENDING' ORDER BY document_id LIMIT ?2")
      .bind(mutationId,DOCUMENT_DELETE_BATCH).all<{mutation_id:string;document_id:string;drive_file_id:string|null;state:string}>();
    for(const row of rows.results||[]){
      const doc=await env.DB.prepare("SELECT document_id,group_id,group_mode FROM document_records WHERE document_id=?1").bind(row.document_id)
        .first<{document_id:string;group_id:string|null;group_mode:string|null}>();
      const siblings=(doc?.group_id&&doc.group_mode==="MULTI_PAGE")
        ?(await env.DB.prepare("SELECT document_id FROM document_records WHERE group_id=?1 AND document_id<>?2 AND status='COMPLETE' ORDER BY page_index ASC,created_at ASC")
          .bind(doc.group_id,row.document_id).all<{document_id:string}>()).results||[]
        :[];
      if(row.drive_file_id)await deleteDriveFile(token,row.drive_file_id);
      const at=nowIso(),stmts:D1PreparedStatement[]=[
        env.DB.prepare("DELETE FROM document_records WHERE document_id=?1").bind(row.document_id),
        env.DB.prepare("UPDATE document_delete_items SET state='DONE',last_error=NULL,updated_at=?1 WHERE mutation_id=?2 AND document_id=?3").bind(at,mutationId,row.document_id)
      ];
      if(doc?.group_id&&doc.group_mode==="MULTI_PAGE"){
        const pageCount=siblings.length;
        siblings.forEach((x,i)=>stmts.push(env.DB.prepare("UPDATE document_records SET page_index=?1,page_count=?2,updated_at=?3 WHERE document_id=?4")
          .bind(i+1,pageCount,at,x.document_id)));
      }
      await env.DB.batch(stmts);
    }
    const done=await env.DB.prepare("SELECT COUNT(*) AS n FROM document_delete_items WHERE mutation_id=?1 AND state='DONE'").bind(mutationId).first<{n:number}>();
    const pending=await env.DB.prepare("SELECT COUNT(*) AS n FROM document_delete_items WHERE mutation_id=?1 AND state='PENDING'").bind(mutationId).first<{n:number}>();
    const at=nowIso();
    if(Number(pending?.n||0)===0){
      await env.DB.prepare("UPDATE document_delete_mutations SET state='DONE',processed_items=?1,updated_at=?2,completed_at=?2,last_error=NULL WHERE mutation_id=?3").bind(Number(done?.n||0),at,mutationId).run();
      job=await deleteMutationById(env,mutationId);
      if(job)await audit(env,deleteMutationAuth(job),"DOCUMENT_DELETE_SELECTED","DOCUMENT_DELETE_RECEIPT",mutationId,{deleted_count:Number(done?.n||0),mutation_id:mutationId});
      await env.DB.prepare("DELETE FROM document_delete_items WHERE mutation_id=?1").bind(mutationId).run();
    }else{
      await env.DB.prepare("UPDATE document_delete_mutations SET processed_items=?1,updated_at=?2,last_error=NULL WHERE mutation_id=?3").bind(Number(done?.n||0),at,mutationId).run();
    }
  }catch(e){
    await env.DB.prepare("UPDATE document_delete_mutations SET updated_at=?1,last_error=?2 WHERE mutation_id=?3").bind(nowIso(),String(e).slice(0,500),mutationId).run();
  }
  return deleteMutationById(env,mutationId);
}
export async function processDocumentDeleteMutations(env:Env):Promise<{processed:number;active:number}>{
  const jobs=await env.DB.prepare("SELECT mutation_id FROM document_delete_mutations WHERE state='RUNNING' ORDER BY updated_at ASC LIMIT 3").all<{mutation_id:string}>();
  let processed=0;for(const j of jobs.results||[]){await processDocumentDeleteMutation(env,j.mutation_id);processed++;}
  const active=await env.DB.prepare("SELECT COUNT(*) AS n FROM document_delete_mutations WHERE state='RUNNING'").first<{n:number}>();
  return{processed,active:Number(active?.n||0)};
}
export async function documentDeleteMutate(request:Request,env:Env):Promise<Response>{
  const auth=await requireAdmin(request,env);if(isResponse(auth))return auth;
  const body=await readJsonBody<Record<string,unknown>>(request),operation=String(body.operation||"START").toUpperCase();
  if(operation==="PROCESS"){
    const mutationId=String(body.mutation_id||"").trim();if(!mutationId)return apiError("DOCUMENT_DELETE_MUTATION_ID_REQUIRED","VALIDATION",400,false);
    const prior=await deleteMutationById(env,mutationId);if(!prior)return apiError("DOCUMENT_DELETE_MUTATION_NOT_FOUND","VALIDATION",404,false);
    if(prior.actor_id!==auth.login_id&&auth.role!=="SUPERADMIN")return apiError("DOCUMENT_DELETE_MUTATION_OWNER_REQUIRED","PERMISSION",403,false);
    const job=prior.state==="RUNNING"?await processDocumentDeleteMutation(env,mutationId):prior;
    return json({ok:true,mutation:job?deleteMutationPublic(job):null});
  }
  if(operation!=="START")return apiError("DOCUMENT_DELETE_OPERATION_INVALID","VALIDATION",400,false);
  const idem=String(body.idempotency_key||"").trim();if(idem.length<8||idem.length>120)return apiError("DOCUMENT_IDEMPOTENCY_INVALID","VALIDATION",400,false);
  const prior=await env.DB.prepare("SELECT * FROM document_delete_mutations WHERE idempotency_key=?1").bind(idem).first<DocDeleteMutationRow>();
  if(prior){const job=prior.state==="RUNNING"?await processDocumentDeleteMutation(env,prior.mutation_id):prior;return json({ok:true,idempotent:true,mutation:job?deleteMutationPublic(job):null});}
  const raw=Array.isArray(body.document_ids)?body.document_ids:[],ids=[...new Set(raw.map(x=>String(x||"").trim()).filter(Boolean))].slice(0,100);
  if(ids.length===0)return apiError("DOCUMENT_DELETE_IDS_REQUIRED","VALIDATION",400,false);
  const placeholders=ids.map((_,i)=>`?${i+1}`).join(",");
  const found=await env.DB.prepare(`SELECT * FROM document_records WHERE status='COMPLETE' AND document_id IN (${placeholders})`).bind(...ids).all<DocRow>();
  const rows=found.results||[];if(rows.length===0)return apiError("DOCUMENT_NOT_FOUND","VALIDATION",404,false);
  const mutationId=crypto.randomUUID(),at=nowIso();
  const stmts:D1PreparedStatement[]=[
    env.DB.prepare("INSERT INTO document_delete_mutations(mutation_id,idempotency_key,state,total_items,processed_items,actor_id,actor_role,created_at,updated_at) VALUES(?1,?2,'RUNNING',?3,0,?4,?5,?6,?6)")
      .bind(mutationId,idem,rows.length,auth.login_id,auth.role,at)
  ];
  for(const row of rows)stmts.push(env.DB.prepare("INSERT INTO document_delete_items(mutation_id,document_id,drive_file_id,category_id,category_name_snapshot,file_name,state,last_error,updated_at) VALUES(?1,?2,?3,NULL,NULL,NULL,'PENDING',NULL,?4)")
    .bind(mutationId,row.document_id,row.drive_file_id,at));
  await env.DB.batch(stmts);
  const job=await processDocumentDeleteMutation(env,mutationId);
  return json({ok:true,mutation:job?deleteMutationPublic(job):null,requested_count:ids.length,matched_count:rows.length},202);
}

export async function documentMedia(request:Request,env:Env,documentId:string):Promise<Response>{
  const auth=await requireAdmin(request,env);if(isResponse(auth))return auth;
  const row=await env.DB.prepare("SELECT * FROM document_records WHERE document_id=?1 AND status='COMPLETE'").bind(documentId).first<DocRow>();
  if(!row||!row.drive_file_id)return apiError("DOCUMENT_NOT_FOUND","VALIDATION",404,false);
  try{
    const token=await googleToken(env);
    const r=await fetch(`https://www.googleapis.com/drive/v3/files/${encodeURIComponent(row.drive_file_id)}?alt=media`,{
      headers:{authorization:`Bearer ${token}`,accept:row.mime_type}
    });
    if(!r.ok)return apiError("DOCUMENT_MEDIA_UNAVAILABLE","RESOURCE",r.status>=500?503:404,true);
    const headers=new Headers();
    headers.set("content-type",r.headers.get("content-type")||row.mime_type);
    headers.set("content-length",r.headers.get("content-length")||String(row.byte_size));
    headers.set("cache-control","private, max-age=300");
    headers.set("x-content-type-options","nosniff");
    return new Response(r.body,{status:200,headers});
  }catch{
    return apiError("DOCUMENT_MEDIA_UNAVAILABLE","RESOURCE",503,true);
  }
}

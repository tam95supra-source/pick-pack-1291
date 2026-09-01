import { authenticate } from "./auth";
import type { AuthContext } from "./domain";
import { apiError, json, nowIso, readJsonBody } from "./util";

type DocCategoryRow={
  category_id:string;display_name:string;normalized_name:string;status:string;
  created_at:string;created_by:string;updated_at:string;updated_by:string;
};
type DocRow={
  document_id:string;idempotency_key:string;category_id:string;category_name_snapshot:string;
  uploader_id:string;uploader_name_snapshot:string;captured_at:string|null;created_at:string;updated_at:string;
  completed_at:string|null;status:string;file_name:string;mime_type:string;byte_size:number;sha256:string;md5:string;
  dhash64:string|null;width:number|null;height:number|null;source_kind:string;drive_file_id:string|null;
  duplicate_of_document_id:string|null;last_error:string|null;
};

const MAX_IMAGE_BYTES=10*1024*1024;
const SIMILAR_DHASH_DISTANCE=6;
const RECENT_DHASH_SCAN_LIMIT=300;

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
function categoryPublic(r:DocCategoryRow){return{category_id:r.category_id,display_name:r.display_name,status:r.status};}
function documentPublic(r:DocRow){return{
  document_id:r.document_id,category_id:r.category_id,category_name:r.category_name_snapshot,
  uploader_id:r.uploader_id,uploader_name:r.uploader_name_snapshot,captured_at:r.captured_at,
  created_at:r.created_at,completed_at:r.completed_at,status:r.status,file_name:r.file_name,
  mime_type:r.mime_type,byte_size:Number(r.byte_size||0),width:r.width,height:r.height,source_kind:r.source_kind,
  duplicate_of_document_id:r.duplicate_of_document_id
};}
async function audit(env:Env,auth:AuthContext,action:string,targetType:string,targetId:string,detail:Record<string,unknown>={}){
  await env.DB.prepare("INSERT INTO document_audit(audit_id,action,target_type,target_id,actor_id,actor_role,detail_json,created_at) VALUES(?1,?2,?3,?4,?5,?6,?7,?8)")
    .bind(crypto.randomUUID(),action,targetType,targetId,auth.login_id,auth.role,JSON.stringify(detail),nowIso()).run();
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
      pp1291_expected_md5:row.md5
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

export async function documentCategories(request:Request,env:Env):Promise<Response>{
  const auth=await requireAdmin(request,env);if(isResponse(auth))return auth;
  const r=await env.DB.prepare("SELECT category_id,display_name,normalized_name,status,created_at,created_by,updated_at,updated_by FROM document_categories WHERE status='ACTIVE' ORDER BY display_name COLLATE NOCASE").all<DocCategoryRow>();
  return json({ok:true,items:(r.results||[]).map(categoryPublic),category_edit_delete_policy:"OWNER_DECISION_REQUIRED"});
}
export async function documentCategoryMutate(request:Request,env:Env):Promise<Response>{
  const auth=await requireAdmin(request,env);if(isResponse(auth))return auth;
  const body=await readJsonBody<Record<string,unknown>>(request);
  const operation=String(body.operation||"CREATE").toUpperCase();
  if(operation!=="CREATE"){
    return apiError("DOCUMENT_CATEGORY_EDIT_DELETE_OWNER_DECISION_REQUIRED","PERMISSION",409,false);
  }
  const name=String(body.display_name||"").trim().replace(/\s+/g," ");
  if(name.length<2||name.length>80)return apiError("DOCUMENT_CATEGORY_NAME_INVALID","VALIDATION",400,false);
  const normalized=normalizeName(name),id=crypto.randomUUID(),at=nowIso();
  try{
    await env.DB.prepare("INSERT INTO document_categories(category_id,display_name,normalized_name,status,created_at,created_by,updated_at,updated_by) VALUES(?1,?2,?3,'ACTIVE',?4,?5,?4,?5)")
      .bind(id,name,normalized,at,auth.login_id).run();
  }catch(e){
    if(String(e).toLowerCase().includes("unique"))return apiError("DOCUMENT_CATEGORY_EXISTS","CONFLICT",409,false);
    throw e;
  }
  await audit(env,auth,"CATEGORY_CREATE","DOCUMENT_CATEGORY",id,{display_name:name});
  return json({ok:true,item:{category_id:id,display_name:name,status:"ACTIVE"}},201);
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
  const width=Number(body.width||0),height=Number(body.height||0);
  const sourceKind=String(body.source_kind||"").toUpperCase();
  const capturedAt=String(body.captured_at||"").trim()||null;
  const idempotency=String(body.idempotency_key||"").trim();
  const allowSimilar=body.allow_similar===true;
  if(mimeType!=="image/jpeg")return apiError("DOCUMENT_IMAGE_MIME_INVALID","VALIDATION",400,false);
  if(!Number.isInteger(size)||size<=0||size>MAX_IMAGE_BYTES)return apiError("DOCUMENT_IMAGE_SIZE_INVALID","VALIDATION",400,false);
  if(!/^[0-9a-f]{64}$/.test(sha256)||!/^[0-9a-f]{32}$/.test(md5))return apiError("DOCUMENT_IMAGE_HASH_INVALID","VALIDATION",400,false);
  if(dhash64&&!/^[0-9a-f]{16}$/.test(dhash64))return apiError("DOCUMENT_IMAGE_FINGERPRINT_INVALID","VALIDATION",400,false);
  if(!Number.isInteger(width)||width<1||!Number.isInteger(height)||height<1)return apiError("DOCUMENT_IMAGE_DIMENSIONS_INVALID","VALIDATION",400,false);
  if(sourceKind!=="CAMERA"&&sourceKind!=="GALLERY")return apiError("DOCUMENT_IMAGE_SOURCE_INVALID","VALIDATION",400,false);
  if(idempotency.length<8||idempotency.length>120)return apiError("DOCUMENT_IDEMPOTENCY_INVALID","VALIDATION",400,false);

  const category=await env.DB.prepare("SELECT category_id,display_name,normalized_name,status,created_at,created_by,updated_at,updated_by FROM document_categories WHERE category_id=?1 AND status='ACTIVE'")
    .bind(categoryId).first<DocCategoryRow>();
  if(!category)return apiError("DOCUMENT_CATEGORY_NOT_FOUND","VALIDATION",404,false);

  const prior=await env.DB.prepare("SELECT * FROM document_records WHERE idempotency_key=?1").bind(idempotency).first<DocRow>();
  if(prior){
    if(prior.sha256!==sha256||Number(prior.byte_size)!==size||prior.category_id!==categoryId)return apiError("DOCUMENT_IDEMPOTENCY_CONFLICT","CONFLICT",409,false);
    if(prior.status==="COMPLETE")return json({ok:true,already_complete:true,document:documentPublic(prior)});
  }else{
    const exact=await env.DB.prepare("SELECT * FROM document_records WHERE sha256=?1 AND status='COMPLETE' ORDER BY completed_at DESC LIMIT 1").bind(sha256).first<DocRow>();
    if(exact){
      return json({ok:false,error:{code:"DOCUMENT_EXACT_DUPLICATE",error_class:"CONFLICT",retryable:false},duplicate:{kind:"EXACT",document:documentPublic(exact)}},409);
    }
    if(dhash64&&!allowSimilar){
      const recent=await env.DB.prepare("SELECT * FROM document_records WHERE status='COMPLETE' AND dhash64 IS NOT NULL ORDER BY completed_at DESC LIMIT ?1").bind(RECENT_DHASH_SCAN_LIMIT).all<DocRow>();
      let best:{row:DocRow;distance:number}|null=null;
      for(const r of recent.results||[]){
        if(!r.dhash64||!/^[0-9a-f]{16}$/.test(r.dhash64))continue;
        const distance=hammingHex64(dhash64,r.dhash64);
        if(distance<=SIMILAR_DHASH_DISTANCE&&(!best||distance<best.distance))best={row:r,distance};
      }
      if(best){
        return json({ok:false,error:{code:"DOCUMENT_SIMILAR_IMAGE",error_class:"CONFLICT",retryable:false},duplicate:{kind:"SIMILAR",distance:best.distance,document:documentPublic(best.row)}},409);
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
      file_name,mime_type,byte_size,sha256,md5,dhash64,width,height,source_kind,drive_file_id,duplicate_of_document_id,last_error
    ) VALUES(?1,?2,?3,?4,?5,?6,?7,?8,?8,'PENDING',?9,?10,?11,?12,?13,?14,?15,?16,?17,NULL,NULL,NULL)`)
      .bind(documentId,idempotency,category.category_id,category.display_name,auth.login_id,uploaderName,capturedAt,at,fileName,mimeType,size,sha256,md5,dhash64||null,width,height,sourceKind).run();
    row=await env.DB.prepare("SELECT * FROM document_records WHERE document_id=?1").bind(documentId).first<DocRow>()||undefined;
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
    await audit(env,auth,"DOCUMENT_UPLOAD_COMPLETE","DOCUMENT",row.document_id,{file_name:row.file_name,byte_size:row.byte_size,sha256:row.sha256});
    return json({ok:true,document:complete?documentPublic(complete):documentPublic({...row,status:"COMPLETE",drive_file_id:driveFileId,completed_at:at,updated_at:at})});
  }catch(e){
    await env.DB.prepare("UPDATE document_records SET updated_at=?1,last_error=?2 WHERE document_id=?3").bind(nowIso(),String(e).slice(0,500),row.document_id).run();
    return apiError("DOCUMENT_DRIVE_VERIFY_UNAVAILABLE","RESOURCE",503,true);
  }
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

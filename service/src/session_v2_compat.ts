import { authenticate } from "./auth";
import { CoreError } from "./core";
import { commitLegacyMutation } from "./legacy";
import { sessionWorkUpdate } from "./session_hotfix";
import { apiError, json, readJsonBody } from "./util";

type SessionRow = {
  session_id:string;mnv:string;business_date:string;shift:string;work_choice:string;state:string;
  pda_serial:string|null;user_pick:string|null;pack_table:string|null;user_pack:string|null;
  pda_enter_status:string|null;pda_exit_status:string|null;resource_note:string;enter_at:string|null;exit_at:string|null;
  entered_by:string|null;exited_by:string|null;version:number;
};

const sessionSelect="SELECT session_id,mnv,business_date,shift,work_choice,state,pda_serial,user_pick,pack_table,user_pack,pda_enter_status,pda_exit_status,resource_note,enter_at,exit_at,entered_by,exited_by,version FROM attendance_sessions WHERE session_id=?1";
const text=(v:unknown,max=240)=>String(v??"").trim().slice(0,max);

async function byId(db:D1Database,id:string):Promise<SessionRow|null>{
  return db.prepare(sessionSelect).bind(id).first<SessionRow>();
}

function assignment(sessionId:string,type:string,id:string,state:string){
  return {assignment_id:`${sessionId}:${type}`,resource_type:type,resource_id:id,state:state==="ACTIVE"?"ACTIVE":"USED"};
}
function positions(s:SessionRow){
  const state=s.state==="ACTIVE"?"ACTIVE":"USED",key=s.work_choice==="PICK"?"PICK":s.work_choice==="PACK"?"PACK":"";
  if(!key)return [];
  return [{position_id:`${s.session_id}:POSITION:${key}`,position_key:key,position_label:key==="PICK"?"Pick":"Pack",state}];
}
function assignments(s:SessionRow){
  const out:Record<string,unknown>[]=[];
  if(s.pda_serial)out.push(assignment(s.session_id,"PDA",s.pda_serial,s.state));
  if(s.user_pick)out.push(assignment(s.session_id,"USER_PICK",s.user_pick,s.state));
  if(s.pack_table)out.push(assignment(s.session_id,"PACK_TABLE",s.pack_table,s.state));
  if(s.user_pack)out.push(assignment(s.session_id,"USER_PACK",s.user_pack,s.state));
  return out;
}
async function projection(env:Env,s:SessionRow){
  const emp=await env.DB.prepare("SELECT main_position FROM employees WHERE mnv=?1").bind(s.mnv).first<{main_position:string}>();
  return {ok:true,source:"SERVICE_D1",session:s,positions:positions(s),resource_assignments:assignments(s),options:{},main_position:emp?.main_position??""};
}
function coreError(e:unknown):Response{
  if(e instanceof CoreError)return apiError(e.code,e.errorClass,e.status,e.retryable,e.conflict);
  return apiError("SESSION_V2_COMPAT_FAILED","INTERNAL",500,false,String(e).slice(0,220));
}

export async function sessionResourceSnapshotV2(request:Request,env:Env):Promise<Response>{
  const auth=await authenticate(env.DB,env,request);if(!auth)return apiError("UNAUTHORIZED","AUTH",401);
  const b=await readJsonBody<Record<string,unknown>>(request,64_000),id=text(b.session_id,220),mnv=text(b.mnv,80);
  if(!id)return apiError("SESSION_ID_REQUIRED","VALIDATION",400);
  const s=await byId(env.DB,id);if(!s)return apiError("SESSION_NOT_FOUND","VALIDATION",404);
  if(mnv&&mnv!==s.mnv)return apiError("SESSION_IDENTITY_MISMATCH","CONFLICT",409);
  return json(await projection(env,s));
}

export async function attendanceEnterV2(request:Request,env:Env):Promise<Response>{
  const auth=await authenticate(env.DB,env,request);if(!auth)return apiError("UNAUTHORIZED","AUTH",401);
  const b=await readJsonBody<Record<string,unknown>>(request,128_000),mnv=text(b.mnv,80),shift=text(b.shift,80),idem=text(b.idempotency_key,180)||crypto.randomUUID();
  if(!mnv||!shift)return apiError("ATTENDANCE_FIELDS_REQUIRED","VALIDATION",400);
  const ps=Array.isArray(b.positions)?b.positions as Record<string,unknown>[]:[],rs=Array.isArray(b.resources)?b.resources as Record<string,unknown>[]:[];
  const keys=ps.map(x=>text(x.position_key,40).toUpperCase());
  const get=(type:string)=>rs.find(x=>text(x.resource_type,40).toUpperCase()===type);
  const pda=get("PDA"),pick=get("USER_PICK"),table=get("PACK_TABLE"),pack=get("USER_PACK");
  const pdaId=text(pda?.resource_id,180),pickId=text(pick?.resource_id,180),tableId=text(table?.resource_id,180),packId=text(pack?.resource_id,180);
  const choice=keys.includes("PICK")||pdaId||pickId?"PICK":keys.includes("PACK")||tableId||packId?"PACK":"KHONG";
  try{
    const result=await commitLegacyMutation(env.DB,env,auth,{
      action:"enter",event_id:idem,
      payload:{mnv,shift,work_choice:choice,pda_serial:pdaId,user_pick:pickId,pack_table:tableId,user_pack:packId,pda_enter_status:text(pda?.pda_enter_status,180),duplicate_user:Boolean(pick?.duplicate_user||pack?.duplicate_user)}
    });
    const event=result.event as Record<string,unknown>,sid=text(event.entity_id,220),s=sid?await byId(env.DB,sid):null;
    return json(s?{...result,...await projection(env,s)}:result,201);
  }catch(e){return coreError(e);}
}

function resourceType(op:Record<string,unknown>):string{
  const direct=text(op.resource_type,40).toUpperCase();if(direct)return direct;
  const id=text(op.assignment_id,260).toUpperCase();
  for(const t of ["USER_PICK","PACK_TABLE","USER_PACK","PDA"])if(id.endsWith(":"+t))return t;
  return "";
}

export async function sessionResourceMutateV2(request:Request,env:Env):Promise<Response>{
  const auth=await authenticate(env.DB,env,request);if(!auth)return apiError("UNAUTHORIZED","AUTH",401);
  const b=await readJsonBody<Record<string,unknown>>(request,192_000),id=text(b.session_id,220),mnv=text(b.mnv,80),idem=text(b.idempotency_key,220);
  if(!id||!idem)return apiError("SESSION_RESOURCE_FIELDS_REQUIRED","VALIDATION",400);
  const s=await byId(env.DB,id);if(!s)return apiError("SESSION_NOT_FOUND","VALIDATION",404);
  if(mnv&&mnv!==s.mnv)return apiError("SESSION_IDENTITY_MISMATCH","CONFLICT",409);
  if(s.state!=="ACTIVE")return apiError("SESSION_NOT_ACTIVE","CONFLICT",409);
  const expected=Number(b.expected_version);if(Number.isInteger(expected)&&expected!==s.version)return apiError("SESSION_CHANGED","CONFLICT",409,false,{current_version:s.version});

  let shift=s.shift,choice=s.work_choice,pda=s.pda_serial??"",pick=s.user_pick??"",table=s.pack_table??"",pack=s.user_pack??"";
  const ops=Array.isArray(b.operations)?b.operations as Record<string,unknown>[]:[];
  if(!ops.length)return apiError("SESSION_RESOURCE_OPERATIONS_REQUIRED","VALIDATION",400);
  for(const op of ops){
    const kind=text(op.op,60).toUpperCase(),type=resourceType(op);
    if(kind==="UPDATE_SHIFT"){const v=text(op.shift,80);if(!v)return apiError("SHIFT_REQUIRED","VALIDATION",400);shift=v;continue;}
    if(kind==="ADD_POSITION"){const k=text(op.position_key,40).toUpperCase();choice=k==="PICK"?"PICK":k==="PACK"?"PACK":"KHONG";continue;}
    if(kind==="REMOVE_POSITION"){const k=text(op.position_key,40).toUpperCase();if(choice===k)choice=(pda||pick)?"PICK":(table||pack)?"PACK":"KHONG";continue;}
    if(!["ADD_RESOURCE","REPLACE_RESOURCE","REMOVE_RESOURCE"].includes(kind)||!["PDA","USER_PICK","PACK_TABLE","USER_PACK"].includes(type))return apiError("SESSION_RESOURCE_OPERATION_UNSUPPORTED","VALIDATION",400,false,{op:kind,resource_type:type});
    const value=kind==="REMOVE_RESOURCE"?"":kind==="REPLACE_RESOURCE"?text(op.new_resource_id,180):text(op.resource_id,180);
    if(kind!=="REMOVE_RESOURCE"&&!value)return apiError("RESOURCE_ID_REQUIRED","VALIDATION",400);
    if(type==="PDA")pda=value;else if(type==="USER_PICK")pick=value;else if(type==="PACK_TABLE")table=value;else if(type==="USER_PACK")pack=value;
  }
  if(pda||pick)choice="PICK";else if(table||pack)choice="PACK";else if(!["PICK","PACK"].includes(choice))choice="KHONG";

  const direct={session_id:id,idempotency_key:idem,shift,work_choice:choice,pda_serial:pda,user_pick:pick,pack_table:table,user_pack:pack,resource_note:s.resource_note,audit_note:text(b.audit_note,500),operations:ops};
  const forwarded=new Request(request.url,{method:"POST",headers:request.headers,body:JSON.stringify(direct)});
  const raw=await sessionWorkUpdate(forwarded,env),bodyText=await raw.text();
  let out:Record<string,unknown>;try{out=bodyText?JSON.parse(bodyText) as Record<string,unknown>:{};}catch{return new Response(bodyText,{status:raw.status,headers:{"content-type":"application/json"}});}
  if(!raw.ok){
    const err=out.error as Record<string,unknown>|undefined;
    if(raw.status===409&&text(err?.code,80)==="SESSION_WORK_CONFLICT")return apiError("SESSION_CHANGED","CONFLICT",409,true);
    return json(out,raw.status);
  }
  const updated=(out.session??null) as SessionRow|null;if(!updated)return apiError("SESSION_RESOURCE_RESULT_MISSING","INTERNAL",500);
  return json({...out,...await projection(env,updated)},raw.status);
}
